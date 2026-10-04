"""Host orchestrator; explicit reviewed contract hash is required to execute.

No source data is read outside approved containers. Source capsules are bounded
authoring artifacts and preserved for audit. No model/Harbor/remote invocation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True)+"\n")


def output_bytes(root):
    return sum(p.stat().st_size for p in root.rglob("*") if p.is_file())


def verify_reviewed_files(task, contract):
    for name, expected in contract["pilot_code_sha256"].items():
        if sha(task/"redesign"/name) != expected:
            raise ValueError(f"reviewed pilot code mismatch: {name}")
    for name, expected in contract["legacy_code_sha256"].items():
        if sha(task/"solution"/name) != expected:
            raise ValueError(f"legacy code mismatch: {name}")
    for key, name in (("method_sha256", "method_contract.json"),
                      ("schema_sha256", "output_schema.json"),
                      ("source_manifest_sha256", "source_manifest.json")):
        if sha(task/"environment"/name) != contract[key]:
            raise ValueError(f"public input mismatch: {name}")
    if sha(task/"redesign/protocol.py") != contract["protocol_sha256"]:
        raise ValueError("reviewed protocol mismatch")


def docker_args(stage, task, evidence, contract, name, uid, gid, fit_sha=None):
    """Build a reviewed allowlist. Full-source bind mounts never enter stages."""
    if uid == 0:
        raise ValueError("nonroot UID required")
    r = contract["resources"]
    args = ["docker", "run", "--name", name, "--rm", "--network", "none",
            "--cpus", str(r["cpus"]), "--memory", str(r["memory_bytes"]),
            "--memory-swap", str(r["memory_swap_bytes"]), "--pids-limit", str(r["pids_limit"]),
            "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--user", f"{uid}:{gid}", "--tmpfs", f"/tmp:rw,noexec,nosuid,size={r['tmp_bytes']}",
            "--env", "PYTHONDONTWRITEBYTECODE=1", "--env", "OMP_NUM_THREADS=1",
            "--env", "OPENBLAS_NUM_THREADS=1", "--env", "MKL_NUM_THREADS=1",
            "--env", "NUMEXPR_NUM_THREADS=1"]
    for source, target in ((task/"redesign", "/pilot"), (task/"solution", "/legacy"),
                           (task/"environment", "/public")):
        args += ["--mount", f"type=bind,src={source},dst={target},readonly"]
    stage_out = evidence if stage == "authenticate" else evidence/stage
    args += ["--mount", f"type=bind,src={stage_out},dst=/out"]
    if stage != "authenticate":
        args += ["--tmpfs", "/app:rw,noexec,nosuid,size=1048576",
                 "--tmpfs", "/opt/source_capture:rw,noexec,nosuid,size=1048576",
                 "--mount", f"type=bind,src={evidence/'capsules'/stage},dst=/source,readonly"]
    if stage == "evaluate":
        if not fit_sha:
            raise ValueError("frozen fit digest required")
        args += ["--mount", f"type=bind,src={evidence/'fit'},dst=/frozen,readonly",
                 "--env", f"FIT_SHA256={fit_sha}"]
    args += ["--entrypoint", "python3", contract["image_id"], "-B", "/pilot/pilot_support.py", stage]
    return args


def run_stage(stage, args, evidence, deadline, limit):
    log = evidence/f"{stage}.stdout.log"
    started = time.monotonic()
    name = args[args.index("--name")+1]
    container_inspect = None
    cleanup_errors = []
    with log.open("wb") as stream:
        proc = subprocess.Popen(args, stdout=stream, stderr=subprocess.STDOUT)
        try:
            while proc.poll() is None:
                if time.monotonic() > deadline:
                    raise TimeoutError("global pilot wall limit exceeded")
                if output_bytes(evidence) > limit:
                    raise RuntimeError("pilot output cap exceeded")
                if container_inspect is None:
                    try:
                        probe = subprocess.run(["docker", "inspect", name], capture_output=True,
                                               text=True, timeout=3)
                    except subprocess.TimeoutExpired:
                        probe = None
                    if probe is not None and probe.returncode == 0:
                        value = json.loads(probe.stdout)[0]
                        container_inspect = {"Id": value["Id"], "Image": value["Image"],
                                             "HostConfig": value["HostConfig"], "Mounts": value["Mounts"],
                                             "Config": {k: value["Config"][k] for k in ("User", "Entrypoint", "Cmd", "WorkingDir")}}
                time.sleep(.2)
            if proc.returncode != 0:
                raise RuntimeError(f"{stage} failed with return code {proc.returncode}; see {log}")
            if stage != "authenticate" and container_inspect is None:
                raise RuntimeError("stage isolation configuration was not captured")
        finally:
            if proc.poll() is None:
                try:
                    subprocess.run(["docker", "stop", "--time", "2", name], capture_output=True, timeout=10)
                except Exception as exc:
                    cleanup_errors.append(f"exact-container-stop: {type(exc).__name__}")
                finally:
                    try:
                        proc.terminate()
                        try:
                            proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                            proc.wait(timeout=5)
                    except Exception as exc:
                        cleanup_errors.append(f"docker-client-cleanup: {type(exc).__name__}")
            dump(evidence/f"{stage}.launch.json", {"argv": args,
                 "elapsed_seconds": time.monotonic()-started, "returncode": proc.returncode,
                 "container_inspect": container_inspect, "cleanup_errors": cleanup_errors})
    if output_bytes(evidence) > limit:
        raise RuntimeError("pilot output cap exceeded")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--execute", action="store_true")
    p.add_argument("--approved-contract-sha256")
    args = p.parse_args()
    task = Path(__file__).resolve().parents[1]
    contract_path = task/"redesign/pilot_contract.json"
    contract = json.loads(contract_path.read_text())
    evidence = Path(contract["evidence_root"])
    if not args.execute:
        print(json.dumps({"execution": False, "contract_sha256": sha(contract_path),
                          "evidence_root": str(evidence), "resources": contract["resources"]}, indent=2))
        return
    if args.approved_contract_sha256 != sha(contract_path):
        raise ValueError("explicit current reviewed contract SHA256 required")
    verify_reviewed_files(task, contract)
    if evidence.exists():
        raise FileExistsError("refusing to overwrite existing evidence; review a new version first")
    deadline = time.monotonic()+contract["resources"]["global_wall_seconds"]
    image = subprocess.run(["docker", "image", "inspect", contract["image_id"]],
                           check=True, capture_output=True, text=True, timeout=10)
    if json.loads(image.stdout)[0]["Id"] != contract["image_id"]:
        raise ValueError("pinned image identity mismatch")
    evidence.mkdir(parents=True)
    (evidence/"fit").mkdir()
    (evidence/"evaluate").mkdir()
    code_hashes = {p.name: sha(p) for p in (task/"redesign").glob("*.py")}
    launch = {"approved_contract_sha256": args.approved_contract_sha256,
              "contract": contract, "code_sha256": code_hashes, "image_id": contract["image_id"],
              "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    dump(evidence/"launch.json", launch)
    try:
        fit_sha = None
        for stage in ("authenticate", "fit", "evaluate"):
            command = docker_args(stage, task, evidence, contract,
                                  f"br-pr200-support-{stage}-{os.getpid()}", os.getuid(), os.getgid(), fit_sha)
            run_stage(stage, command, evidence, deadline, contract["resources"]["max_new_output_bytes"])
            if stage == "fit":
                fit_sha = sha(evidence/"fit/fit.json")
        if sha(evidence/"fit/fit.json") != fit_sha:
            raise ValueError("frozen discovery artifact changed during evaluation")
        if code_hashes != {p.name: sha(p) for p in (task/"redesign").glob("*.py")}:
            raise ValueError("pilot code changed during execution")
        if args.approved_contract_sha256 != sha(contract_path):
            raise ValueError("pilot contract changed during execution")
        verify_reviewed_files(task, contract)
        evaluation = json.loads((evidence/"evaluate/evaluate.json").read_text())
        result = {"status": "completed_support_and_isolation_pilot", "frozen_fit_sha256": fit_sha,
                  "n_expected_evaluation": evaluation["n_expected"], "n_eligible_evaluation": evaluation["n_eligible"],
                  "new_output_bytes": output_bytes(evidence), "scientific_endpoints_computed": False,
                  "model_runs": 0, "scope": contract["evidence_scope"]}
        dump(evidence/"result.json", result)
        print(json.dumps(result, indent=2))
    except BaseException as exc:
        dump(evidence/"failure.json", {"status": "failed", "type": type(exc).__name__, "message": str(exc)})
        raise


if __name__ == "__main__":
    main()
