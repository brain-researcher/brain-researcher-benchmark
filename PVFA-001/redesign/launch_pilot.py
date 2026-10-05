"""Dry-run-first host launcher for the exact reviewed #156 feasibility pilot.

All subprocesses are bounded. The 900-second global deadline starts before
Docker image inspection and therefore includes raw-source authentication.
Cleanup acts only on this launch's random ownership label and exact container.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import uuid


CODE_FILES = ("pilot.py", "witness.py", "launch_pilot.py")
OWNER_LABEL = "brain-researcher.pilot-owner"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value,indent=2,sort_keys=True)+"\n")


def code_hashes(redesign):
    return {name:sha(redesign/name) for name in CODE_FILES}


def verify_approval(approval, contract_path, redesign):
    if approval.get("approved") is not True or approval.get("reviewer") != "root":
        raise ValueError("explicit root approval required")
    if approval.get("contract_sha256") != sha(contract_path):
        raise ValueError("approved contract hash mismatch")
    if approval.get("code_sha256") != code_hashes(redesign):
        raise ValueError("approved code hashes mismatch")


def remaining(deadline, cap=10):
    seconds = min(float(cap),deadline-time.monotonic())
    if seconds <= 0:
        raise TimeoutError("global pilot wall limit exceeded")
    return seconds


def bounded(args, deadline, cap=10, check=True):
    return subprocess.run(args,capture_output=True,text=True,timeout=remaining(deadline,cap),check=check)


def mount(source,target,readonly=True):
    source = Path(source).resolve()
    if any(x in str(source) for x in (",","\n","\r")):
        raise ValueError("unsupported mount path")
    return ["--mount",f"type=bind,src={source},dst={target}"+(",readonly" if readonly else "")]


def build_create(task, evidence, approval_path, contract, token, uid, gid):
    if uid <= 0 or gid < 0:
        raise ValueError("nonroot runtime identity required")
    r = contract["resources"]
    if (r["cpus"],r["memory_bytes"],r["memory_swap_bytes"],r["global_wall_seconds"]) != (1,2147483648,2147483648,900):
        raise ValueError("reviewed resource caps changed")
    if r["gpu"] or r["network"]:
        raise ValueError("GPU/network are outside pilot scope")
    name = "br-pr156-pilot-"+token
    args = ["docker","create","--name",name,"--label",OWNER_LABEL+"="+token,
        "--network","none","--runtime","runc","--cpus","1",
        "--memory",str(r["memory_bytes"]),"--memory-swap",str(r["memory_swap_bytes"]),
        "--pids-limit",str(r["pids_limit"]),"--read-only","--cap-drop","ALL",
        "--security-opt","no-new-privileges","--user",f"{uid}:{gid}",
        "--tmpfs",f"/tmp:rw,noexec,nosuid,size={r['tmp_bytes']}"]
    for env in ("PYTHONDONTWRITEBYTECODE=1","OMP_NUM_THREADS=1","OPENBLAS_NUM_THREADS=1","MKL_NUM_THREADS=1","NUMEXPR_NUM_THREADS=1","NVIDIA_VISIBLE_DEVICES=void"):
        args += ["--env",env]
    binds = [(task/"redesign","/pilot"),(task/"tests/reference.npz","/source-bank.npz"),
        (task/"environment/data_manifest.json","/source-manifest.json"),
        (task/"environment/method_contract.json","/preprocessing.json"),
        (Path(contract["host_source_receipt"]),"/source-receipt.json"),
        (Path(contract["host_independent_report"]),"/source-report.json"),
        (approval_path,"/approval.json")]
    for source,target in binds:
        args += mount(source,target)
    args += mount(evidence,"/out",readonly=False)
    args += ["--entrypoint","python3",contract["software"]["image_id"],"-B","/pilot/pilot.py",
        "--execute","--contract","/pilot/pilot_contract.json","--approval","/approval.json",
        "--bank","/source-bank.npz","--receipt","/source-receipt.json","--report","/source-report.json",
        "--manifest","/source-manifest.json","--preprocessing","/preprocessing.json",
        "--raw-source","/app/data/sherbrooke","--output","/out/pilot"]
    return name,args


def owned(inspect,token):
    return inspect.get("Config",{}).get("Labels",{}).get(OWNER_LABEL) == token


def public_inspect(value):
    return {"Id":value["Id"],"Image":value["Image"],"State":value["State"],
        "HostConfig":value["HostConfig"],"Mounts":value["Mounts"],
        "Config":{name:value["Config"].get(name) for name in ("User","Entrypoint","Cmd","Labels")}}


def inspect_owned(target,token,deadline):
    result = bounded(["docker","inspect",target],deadline,cap=3,check=False)
    if result.returncode:
        raise RuntimeError("owned container inspection failed: "+result.stderr.strip())
    value = json.loads(result.stdout)[0]
    if not owned(value,token):
        raise RuntimeError("container ownership label mismatch; refusing action")
    return value


def cleanup_owned(target,token):
    """Emergency cleanup has its own short bound, never an unscoped Docker stop."""
    events = []
    if not target:
        return events
    try:
        result = subprocess.run(["docker","inspect",target],capture_output=True,text=True,timeout=3)
        if result.returncode:
            return [{"action":"inspect","returncode":result.returncode,"message":result.stderr.strip()}]
        info = json.loads(result.stdout)[0]
        if not owned(info,token):
            return [{"action":"refused","reason":"ownership label mismatch"}]
        exact_id = info["Id"]
        if all(key in info for key in ("State","HostConfig","Mounts","Image")):
            events.append({"action":"owned_state_before_cleanup","container_inspect":public_inspect(info)})
        # rm --force only targets the freshly resolved, ownership-checked ID.
        result = subprocess.run(["docker","rm","--force",exact_id],capture_output=True,text=True,timeout=5)
        events.append({"action":"remove_owned_container","id":exact_id,"returncode":result.returncode,"stderr":result.stderr.strip()})
    except Exception as exc:
        events.append({"action":"cleanup_failed","type":type(exc).__name__,"message":str(exc)})
    return events


def output_size(path):
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def execute(task,contract_path,approval_path,approval,contract):
    redesign = task/"redesign"
    verify_approval(approval,contract_path,redesign)
    evidence = Path(contract["evidence_root"])
    if evidence.exists():
        raise FileExistsError("evidence root already exists; refusing overwrite")
    started = time.monotonic()
    deadline = started+contract["resources"]["global_wall_seconds"]
    token = uuid.uuid4().hex
    name,args = build_create(task,evidence,approval_path,contract,token,os.getuid(),os.getgid())
    evidence.mkdir(parents=True,exist_ok=False)
    launch = {"status":"starting","argv":args,"approval":approval,"contract":contract,
        "code_sha256":code_hashes(redesign),"ownership_token":token,
        "started_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
        "authority":"current raw hashes and historical complete preprocessing reconstruction; no fresh preprocessing"}
    dump(evidence/"launch.json",launch)
    target,proc = name,None
    try:
        image = json.loads(bounded(["docker","image","inspect",contract["software"]["image_id"]],deadline).stdout)[0]
        if image["Id"] != contract["software"]["image_id"]:
            raise ValueError("pinned image identity mismatch")
        created = bounded(args,deadline)
        target = created.stdout.strip()
        if len(target) != 64 or any(c not in "0123456789abcdef" for c in target):
            target = name
            raise RuntimeError("Docker create did not return an exact container ID")
        before = inspect_owned(target,token,deadline)
        dump(evidence/"container.before.json",public_inspect(before))
        attach = ["docker","start","--attach",target]
        dump(evidence/"attach.argv.json",attach)
        with (evidence/"stdout.log").open("xb") as out, (evidence/"stderr.log").open("xb") as err:
            proc = subprocess.Popen(attach,stdout=out,stderr=err)
            while proc.poll() is None:
                remaining(deadline)
                if output_size(evidence)>contract["resources"]["max_output_bytes"]:
                    raise RuntimeError("pilot output cap exceeded")
                time.sleep(min(.1,remaining(deadline)))
        after = inspect_owned(target,token,deadline)
        dump(evidence/"container.after.json",public_inspect(after))
        if proc.returncode != 0 or after["State"]["ExitCode"] != 0:
            raise RuntimeError(f"pilot container failed: docker={proc.returncode}, container={after['State']['ExitCode']}")
        verify_approval(approval,contract_path,redesign)
        report = json.loads((evidence/"pilot/report.json").read_text())
        remaining(deadline)
        if output_size(evidence)>contract["resources"]["max_output_bytes"]:
            raise RuntimeError("pilot output cap exceeded")
        launch.update(status=report["status"],elapsed_seconds=time.monotonic()-started,
                      n_attempts=report["n_attempts"],n_admissible=report["n_admissible"],
                      scientific_release=False,model_runs=0)
        dump(evidence/"result.json",launch)
        return launch
    except BaseException as exc:
        failure = {"status":"failed_or_incomplete","type":type(exc).__name__,"message":str(exc),"elapsed_seconds":time.monotonic()-started,"target":target}
        if isinstance(exc,(subprocess.CalledProcessError,subprocess.TimeoutExpired)):
            failure["subprocess_argv"] = exc.cmd
            for field in ("stdout","stderr"):
                value = getattr(exc,field,None)
                failure[field] = value.decode(errors="replace") if isinstance(value,bytes) else value
        dump(evidence/"failure.json",failure)
        raise
    finally:
        cleanup = cleanup_owned(target,token)
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill(); proc.wait(timeout=3)
            except Exception as exc:
                cleanup.append({"action":"client_cleanup_failed","type":type(exc).__name__,"message":str(exc)})
        dump(evidence/"cleanup.json",cleanup)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--execute",action="store_true")
    p.add_argument("--approval",type=Path)
    args = p.parse_args()
    task = Path(__file__).resolve().parents[1]
    contract_path = task/"redesign/pilot_contract.json"
    contract = json.loads(contract_path.read_text())
    if not args.execute:
        print(json.dumps({"execute":False,"contract_sha256":sha(contract_path),"code_sha256":code_hashes(task/"redesign"),"evidence_root":contract["evidence_root"],"resources":contract["resources"]},indent=2))
        return
    if args.approval is None:
        p.error("--execute requires a root-reviewed approval JSON")
    approval = json.loads(args.approval.read_text())
    result = execute(task,contract_path,args.approval,approval,contract)
    print(json.dumps({key:result[key] for key in ("status","elapsed_seconds","n_attempts","n_admissible")},indent=2))


if __name__ == "__main__":
    main()
