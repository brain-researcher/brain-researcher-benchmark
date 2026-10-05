"""Dry-run-first bounded phase2 diagnostic launcher; no prior file is modified."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import uuid

# Reuse only frozen host isolation/logging helpers, never scientific functions.
import launch_pilot as infra


CODE_FILES = ("phase2_diagnostic.py","launch_phase2.py","launch_pilot.py")


def code_hashes(redesign):
    return {name:infra.sha(redesign/name) for name in CODE_FILES}


def verify(approval,contract_path,redesign,contract):
    if approval.get("approved") is not True or approval.get("reviewer")!="root" or approval.get("contract_sha256")!=infra.sha(contract_path) or approval.get("code_sha256")!=code_hashes(redesign):
        raise ValueError("phase2 exact root approval mismatch")
    for name,expected in contract["immutable_prior_code_sha256"].items():
        if infra.sha(redesign/name)!=expected:
            raise ValueError("prior code changed: "+name)


def host_inputs(task,contract):
    prior = Path(contract["prior_root"])
    return {"bank":task/"tests/reference.npz","manifest":task/"environment/data_manifest.json",
        "method":task/"environment/method_contract.json","prior_contract":task/"redesign/pilot_contract.json",
        "attempts":prior/"pilot/attempts.jsonl","selection":prior/"pilot/selection.json",
        "prior_report":prior/"pilot/report.json","prior_result":prior/"result.json"}


def build_command(task,evidence,approval_path,contract,token,uid,gid):
    if uid<=0 or gid<0: raise ValueError("nonroot runtime required")
    r = contract["resources"]
    if (r["cpus"],r["memory_bytes"],r["memory_swap_bytes"],r["global_wall_seconds"],r["max_output_bytes"],r["fits"])!=(1,2147483648,2147483648,900,67108864,0):
        raise ValueError("phase2 resource/scope caps changed")
    if r["network"] or r["gpu"]: raise ValueError("network/GPU outside scope")
    name = "br-pr156-phase2-"+token
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
    args += ["--entrypoint","python3",contract["image_id"],"-B","/pilot/phase2_diagnostic.py",
        "--execute","--approval","/approval.json","--contract","/pilot/phase2_contract.json","--output","/out/diagnostic"]
    return name,args


def execute(task,contract_path,approval_path,approval,contract):
    started = time.monotonic(); deadline=started+contract["resources"]["global_wall_seconds"]
    verify(approval,contract_path,task/"redesign",contract)
    infra.remaining(deadline)
    inputs = host_inputs(task,contract)
    for key,path in inputs.items():
        infra.remaining(deadline)
        if path.is_symlink() or infra.sha(path)!=contract["input_sha256"][key]:
            raise ValueError("phase2 host input hash mismatch: "+key)
    infra.remaining(deadline)
    evidence = Path(contract["evidence_root"])
    if evidence.exists(): raise FileExistsError("refusing existing phase2 evidence directory")
    token=uuid.uuid4().hex
    name,args=build_command(task,evidence,approval_path,contract,token,os.getuid(),os.getgid())
    evidence.mkdir(parents=True,exist_ok=False)
    launch={"argv":args,"approval":approval,"contract":contract,"code_sha256":code_hashes(task/"redesign"),"fits":0,"started_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
    infra.dump(evidence/"launch.json",launch)
    target,proc=name,None
    try:
        image=json.loads(infra.bounded(["docker","image","inspect",contract["image_id"]],deadline).stdout)[0]
        if image["Id"]!=contract["image_id"]: raise ValueError("image identity mismatch")
        target=infra.bounded(args,deadline).stdout.strip()
        if len(target)!=64 or any(c not in "0123456789abcdef" for c in target):
            target=name; raise ValueError("Docker create did not return exact container ID")
        infra.dump(evidence/"container.before.json",infra.public_inspect(infra.inspect_owned(target,token,deadline)))
        attach=["docker","start","--attach",target]; infra.dump(evidence/"attach.argv.json",attach)
        with (evidence/"stdout.log").open("xb") as out,(evidence/"stderr.log").open("xb") as err:
            proc=subprocess.Popen(attach,stdout=out,stderr=err)
            while proc.poll() is None:
                infra.remaining(deadline)
                if infra.output_size(evidence)>contract["resources"]["max_output_bytes"]: raise RuntimeError("phase2 output cap exceeded")
                time.sleep(min(.1,infra.remaining(deadline)))
        after=infra.inspect_owned(target,token,deadline)
        infra.dump(evidence/"container.after.json",infra.public_inspect(after))
        if proc.returncode!=0 or after["State"]["ExitCode"]!=0: raise RuntimeError("phase2 container failed; see retained logs")
        verify(approval,contract_path,task/"redesign",contract)
        for key,path in inputs.items():
            if infra.sha(path)!=contract["input_sha256"][key]: raise ValueError("input changed during diagnostic: "+key)
        infra.remaining(deadline)
        if infra.output_size(evidence)>contract["resources"]["max_output_bytes"]: raise RuntimeError("phase2 output cap exceeded")
        report=json.loads((evidence/"diagnostic/report.json").read_text())
        result={"status":report["status"],"elapsed_seconds":time.monotonic()-started,"n_candidates_reconstructed":report["n_candidates_reconstructed"],"fits":0,"source_checks":report["source_checks"],"arithmetic_disagreement_attempt_ids":report["arithmetic_disagreement_attempt_ids"],"scope":contract["scope"]}
        infra.dump(evidence/"result.json",result)
        return result
    except BaseException as exc:
        failure={"status":"failed_or_incomplete","type":type(exc).__name__,"message":str(exc),"elapsed_seconds":time.monotonic()-started,"target":target,"fits":0}
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
            except Exception as exc: cleanup.append({"action":"client_cleanup_failed","type":type(exc).__name__,"message":str(exc)})
        infra.dump(evidence/"cleanup.json",cleanup)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--execute",action="store_true"); p.add_argument("--approval",type=Path)
    args=p.parse_args(); task=Path(__file__).resolve().parents[1]; contract_path=task/"redesign/phase2_contract.json"
    contract=json.loads(contract_path.read_text())
    if not args.execute:
        print(json.dumps({"execute":False,"contract_sha256":infra.sha(contract_path),"code_sha256":code_hashes(task/"redesign"),"resources":contract["resources"],"evidence_root":contract["evidence_root"]},indent=2)); return
    if args.approval is None: p.error("execution requires phase2 root approval outside evidence directory")
    approval=json.loads(args.approval.read_text())
    print(json.dumps(execute(task,contract_path,args.approval,approval,contract),indent=2))


if __name__=="__main__": main()
