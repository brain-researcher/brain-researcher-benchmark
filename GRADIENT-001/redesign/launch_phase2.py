"""Phase2 host launcher; unchanged phase1 watchdog and container restrictions."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

from launch_support_pilot import docker_args, dump, output_bytes, run_stage, sha, verify_reviewed_files


def stage_command(stage, task, evidence, base, name, fit_sha=None):
    analysis = stage.removeprefix("check_")
    command = docker_args(analysis, task, evidence, base, name, os.getuid(), os.getgid(), fit_sha)
    command[-2:] = ["/pilot/phase2_stage.py", stage]
    if analysis == "evaluate":
        old = f"type=bind,src={evidence/'fit'},dst=/frozen,readonly"
        command[command.index(old)] = f"type=bind,src={evidence/'fit/fit.json'},dst=/frozen/fit.json,readonly"
    if stage.startswith("check_"):
        original = f"type=bind,src={evidence/analysis},dst=/out"
        command[command.index(original)] = f"type=bind,src={evidence/stage},dst=/out"
        at = command.index("--entrypoint")
        extra = ["--mount", f"type=bind,src={evidence/analysis},dst=/submitted,readonly"]
        if stage == "check_evaluate":
            extra += ["--mount", f"type=bind,src={evidence/'check_fit/check_fit.json'},dst=/checked/check_fit.json,readonly"]
        command[at:at] = extra
    return command


def validate_code(task, phase, base):
    verify_reviewed_files(task, base)
    if sha(task/"redesign/pilot_contract.json") != phase["base_pilot_contract_sha256"]:
        raise ValueError("base pilot contract changed")
    expected_names = {"phase2_production.py", "phase2_independent.py", "phase2_workflow.py",
                      "phase2_compare.py", "phase2_stage.py", "launch_phase2.py"}
    if not expected_names <= set(phase["code_sha256"]):
        raise ValueError("phase2 reviewed code pins not complete")
    for name, expected in phase["code_sha256"].items():
        if sha(task/"redesign"/name) != expected:
            raise ValueError(f"reviewed phase2 file changed: {name}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--execute", action="store_true")
    p.add_argument("--approved-contract-sha256")
    args = p.parse_args()
    task = Path(__file__).resolve().parents[1]
    phase_path = task/"redesign/phase2_contract.json"
    phase = json.loads(phase_path.read_text())
    base = json.loads((task/"redesign/pilot_contract.json").read_text())
    if not args.execute:
        print(json.dumps({"execution": False, "contract_sha256": sha(phase_path),
                          "scope": "five-stage source-backed endpoint qualification", "resources": phase["resources"]}, indent=2))
        return
    if args.approved_contract_sha256 != sha(phase_path):
        raise ValueError("current reviewed phase2 contract SHA256 required")
    validate_code(task, phase, base)
    if phase["resources"] != base["resources"]:
        raise ValueError("phase2 must retain reviewed resource caps")
    evidence = Path(phase["evidence_root"])
    if evidence.exists():
        raise FileExistsError("refusing to overwrite phase2 evidence")
    deadline = time.monotonic()+phase["resources"]["global_wall_seconds"]
    image = subprocess.run(["docker", "image", "inspect", base["image_id"]],
                           capture_output=True, text=True, check=True, timeout=10)
    if json.loads(image.stdout)[0]["Id"] != base["image_id"]:
        raise ValueError("pinned image identity")
    evidence.mkdir(parents=True)
    for stage in phase["stages"]:
        if stage != "authenticate":
            (evidence/stage).mkdir()
    dump(evidence/"launch.json", {"contract": phase, "approved_contract_sha256": args.approved_contract_sha256,
         "code_sha256": phase["code_sha256"], "image_id": base["image_id"],
         "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    try:
        frozen_sha = None
        for stage in phase["stages"]:
            validate_code(task, phase, base)
            if sha(phase_path) != args.approved_contract_sha256:
                raise ValueError("phase2 contract changed between stages")
            command = stage_command(stage, task, evidence, base, f"br-pr200-phase2-{stage}-{os.getpid()}", frozen_sha)
            run_stage(stage, command, evidence, deadline, phase["resources"]["max_new_output_bytes"])
            if stage == "fit":
                frozen_sha = sha(evidence/"fit/fit.json")
            elif frozen_sha and sha(evidence/"fit/fit.json") != frozen_sha:
                raise ValueError("frozen fit changed")
        validate_code(task, phase, base)
        if sha(phase_path) != args.approved_contract_sha256:
            raise ValueError("contract changed during qualification")
        evaluated = json.loads((evidence/"evaluate/evaluate.json").read_text())
        checks = [json.loads((evidence/s/f"{s}.json").read_text()) for s in ("check_fit", "check_evaluate")]
        if not all(x["status"] == "independent_arithmetic_agrees" for x in checks):
            raise ValueError("independent arithmetic qualification incomplete")
        result = {"status": "completed_endpoint_numerical_qualification", "n_expected": evaluated["n_expected"],
                  "n_defined_transfer": evaluated["n_defined"], "mean_fraction": evaluated["mean_fraction"],
                  "frozen_fit_sha256": frozen_sha, "new_output_bytes": output_bytes(evidence),
                  "model_runs": 0, "reward": None, "scope": phase["qualification_not_benchmark_pass"],
                  "shared_dependencies": phase["independence"]["shared"]}
        dump(evidence/"result.json", result)
        print(json.dumps(result, indent=2))
    except BaseException as exc:
        dump(evidence/"failure.json", {"status": "failed", "type": type(exc).__name__, "message": str(exc)})
        raise


if __name__ == "__main__":
    main()
