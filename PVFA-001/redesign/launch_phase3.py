"""Dry-run-first 60-second append-only replay launcher; no fitting authorized."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import uuid

import launch_pilot as infra
import phase3_replay as replay


def host_inputs(task, contract):
    prior, phase2 = Path(contract["prior_root"]),Path(contract["phase2_root"])
    return {"bank":task/"tests/reference.npz", "prior_contract":task/"redesign/pilot_contract.json",
        "attempts":prior/"pilot/attempts.jsonl", "selection":prior/"pilot/selection.json", "prior_report":prior/"pilot/report.json",
        "phase2_contract":task/"redesign/phase2_contract.json", "phase2_report":phase2/"diagnostic/report.json",
        "phase2_selected":phase2/"diagnostic/selected_source.npz", "phase2_checks":phase2/"diagnostic/candidate_checks.jsonl",
        "phase2_source_checks":phase2/"diagnostic/source_checks.json"}


def build_command(task, evidence, approval_path, contract, token, uid, gid):
    if uid <= 0 or gid < 0: raise ValueError("nonroot runtime required")
    r = contract["resources"]
    if (r["cpus"],r["memory_bytes"],r["memory_swap_bytes"],r["global_wall_seconds"],r["max_output_bytes"],r["fits"],r["pids_limit"],r["tmp_bytes"]) != (1,2147483648,2147483648,60,16777216,0,128,16777216):
        raise ValueError("reviewed replay resource/scope caps changed")
    if r["network"] or r["gpu"]: raise ValueError("network/GPU outside replay scope")
    name = "br-pr156-replay-"+token
    args = ["docker","create","--name",name,"--label",infra.OWNER_LABEL+"="+token,
        "--network","none","--runtime","runc","--cpus","1","--memory",str(r["memory_bytes"]),
        "--memory-swap",str(r["memory_swap_bytes"]),"--pids-limit",str(r["pids_limit"]),
        "--read-only","--cap-drop","ALL","--security-opt","no-new-privileges","--user",f"{uid}:{gid}",
        "--tmpfs",f"/tmp:rw,noexec,nosuid,size={r['tmp_bytes']}"]
    for env in ("PYTHONDONTWRITEBYTECODE=1","OMP_NUM_THREADS=1","OPENBLAS_NUM_THREADS=1","MKL_NUM_THREADS=1","NUMEXPR_NUM_THREADS=1","NVIDIA_VISIBLE_DEVICES=void"):
        args += ["--env",env]
    args += infra.mount(task/"redesign","/pilot")
    args += infra.mount(approval_path,"/approval.json")
    for key,path in host_inputs(task,contract).items(): args += infra.mount(path,"/inputs/"+key)
    args += infra.mount(evidence,"/out",readonly=False)
    args += ["--entrypoint","python3",contract["image_id"],"-B","/pilot/phase3_replay.py",
        "--execute","--approval","/approval.json","--contract","/pilot/phase3_contract.json","--output","/out/replay"]
    return name,args


def authenticate_host(inputs, contract, deadline):
    if set(inputs) != set(contract["input_sha256"]): raise ValueError("unexpected host input keys")
    for key,path in inputs.items():
        infra.remaining(deadline)
        if path.is_symlink() or replay.arithmetic.sha(path) != contract["input_sha256"][key]:
            raise ValueError("host input hash mismatch: "+key)
    infra.remaining(deadline)


def execute(task, contract_path, approval_path, approval, contract):
    started = time.monotonic(); deadline = started+contract["resources"]["global_wall_seconds"]
    replay.verify_approval(approval,contract_path,task/"redesign",contract)
    inputs = host_inputs(task,contract); authenticate_host(inputs,contract,deadline)
    evidence = Path(contract["evidence_root"])
    if evidence.exists(): raise FileExistsError("refusing existing replay evidence directory")
    token=uuid.uuid4().hex
    name,args=build_command(task,evidence,approval_path,contract,token,os.getuid(),os.getgid())
    evidence.mkdir(parents=True,exist_ok=False)
    infra.dump(evidence/"launch.json",{"argv":args,"approval":approval,"contract":contract,
        "code_sha256":replay.code_hashes(task/"redesign"),"fits":0,"scientific_release":False,
        "started_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())})
    target,proc=name,None
    try:
        image=json.loads(infra.bounded(["docker","image","inspect",contract["image_id"]],deadline).stdout)[0]
        if image["Id"] != contract["image_id"]: raise ValueError("image identity mismatch")
        target=infra.bounded(args,deadline).stdout.strip()
        if len(target)!=64 or any(c not in "0123456789abcdef" for c in target):
            target=name; raise ValueError("Docker create did not return exact container ID")
        infra.dump(evidence/"container.before.json",infra.public_inspect(infra.inspect_owned(target,token,deadline)))
        attach=["docker","start","--attach",target]; infra.dump(evidence/"attach.argv.json",attach)
        with (evidence/"stdout.log").open("xb") as out,(evidence/"stderr.log").open("xb") as err:
            proc=subprocess.Popen(attach,stdout=out,stderr=err)
            while proc.poll() is None:
                infra.remaining(deadline)
                if infra.output_size(evidence)>contract["resources"]["max_output_bytes"]: raise RuntimeError("replay output cap exceeded")
                time.sleep(min(.1,infra.remaining(deadline)))
        after=infra.inspect_owned(target,token,deadline)
        infra.dump(evidence/"container.after.json",infra.public_inspect(after))
        if proc.returncode!=0 or after["State"]["ExitCode"]!=0: raise RuntimeError("replay container failed; see retained logs")
        replay.verify_approval(approval,contract_path,task/"redesign",contract)
        authenticate_host(inputs,contract,deadline)
        if infra.output_size(evidence)>contract["resources"]["max_output_bytes"]: raise RuntimeError("replay output cap exceeded")
        report=json.loads((evidence/"replay/report.json").read_text())
        result=dict(report,host_elapsed_seconds=time.monotonic()-started)
        infra.dump(evidence/"result.json",result)
        return result
    except BaseException as exc:
        failure={"status":"failed_or_incomplete","type":type(exc).__name__,"message":str(exc),
            "elapsed_seconds":time.monotonic()-started,"target":target,"fits":0}
        if isinstance(exc,(subprocess.CalledProcessError,subprocess.TimeoutExpired)):
            failure["subprocess_argv"]=exc.cmd
            for name in ("stdout","stderr"):
                value=getattr(exc,name,None); failure[name]=value.decode(errors="replace") if isinstance(value,bytes) else value
        infra.dump(evidence/"failure.json",failure)
        raise
    finally:
        cleanup=infra.cleanup_owned(target,token)
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
                try: proc.wait(timeout=3)
                except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=3)
            except Exception as exc:
                cleanup.append({"action":"client_cleanup_failed","type":type(exc).__name__,"message":str(exc)})
        infra.dump(evidence/"cleanup.json",cleanup)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--execute",action="store_true"); p.add_argument("--approval",type=Path)
    args=p.parse_args(); task=Path(__file__).resolve().parents[1]; contract_path=task/"redesign/phase3_contract.json"
    contract=json.loads(contract_path.read_text())
    if not args.execute:
        print(json.dumps({"execute":False,"contract_sha256":infra.sha(contract_path),"code_sha256":replay.code_hashes(task/"redesign"),
            "resources":contract["resources"],"evidence_root":contract["evidence_root"]},indent=2)); return
    if args.approval is None: p.error("execution requires root approval outside evidence directory")
    print(json.dumps(execute(task,contract_path,args.approval,json.loads(args.approval.read_text()),contract),indent=2))


if __name__=="__main__": main()
