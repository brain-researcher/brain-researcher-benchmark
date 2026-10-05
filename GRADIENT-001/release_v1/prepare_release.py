"""Package new build contexts from already-qualified, pinned evidence; no Docker/model execution.

This is an explicit root-authoring step. It never replaces the source task or
prior qualifications. Destination must not exist. Preparation is not a test run.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import zipfile
import numpy as np
from format import compact
from grading import authenticate_capsule, regular_bytes, require, strict_json

EVIDENCE_PINS = {
    "fit/fit.json": "b61ec1b9297d951ce0e441d6b9340993c793071372f8414b114d400519c96d43",
    "evaluate/evaluate.json": "33bae31295e444cf9f50b9f0e5f2640535a73d398f6d8df03280e05ca31acc66",
    "check_fit/check_fit.json": "fcb527c1e36e392399c4bf6513387b74373709411630302b2da3af62af2a7c40",
    "check_evaluate/check_evaluate.json": "a3e8a649014b87df0eeb48a1e6ca5462ac6056f6929f17e52948da68cd633deb",
    "fit/fit_arrays.npz": "4ae404a138ddd7c948c7fb8fd48b3ecbc964180b9d50a3a8e57094c5489ec668",
    "evaluate/evaluate_arrays.npz": "b3034a1543ab1796f7c5ce7b6249991781ee3dd6647802016283dfc9b3c0f6c0",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False)+"\n")


def oracle_zip(task, release, independent=False):
    redesign = task/"redesign"
    phase = json.loads((redesign/"phase2_contract.json").read_text())
    base = json.loads((redesign/"pilot_contract.json").read_text())
    files = {"__main__.py": release/"oracle_main.py", "format.py": release/"format.py"}
    for name in ("phase2_workflow.py", "pilot_support.py", "protocol.py"):
        files[name] = redesign/name
        require(sha(files[name]) == phase["code_sha256"][name], "qualified oracle orchestration pin")
    selected = "phase2_independent.py" if independent else "phase2_production.py"
    require(sha(redesign/selected) == phase["code_sha256"][selected], "qualified numerical pin")
    files["phase2_production.py"] = redesign/selected
    for name in ("core.py", "source_reader.py"):
        files[name] = task/"solution"/name
        require(sha(files[name]) == base["legacy_code_sha256"][name], "qualified source reader pin")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, path in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    return output.getvalue()


def prepare(destination, evidence):
    release = Path(__file__).resolve().parent
    task = release.parent
    require(not destination.exists(), "new destination required")
    contract = json.loads((release/"contract.json").read_text())
    for name, pin in EVIDENCE_PINS.items():
        require(sha(evidence/name) == pin, "qualified evidence pin: "+name)
    for name in ("check_fit/check_fit.json", "check_evaluate/check_evaluate.json"):
        require(json.loads((evidence/name).read_text())["status"] == "independent_arithmetic_agrees", "unqualified reference")
    fit = strict_json(regular_bytes(evidence/"fit/fit.json"))
    evaluation = strict_json(regular_bytes(evidence/"evaluate/evaluate.json"))
    for stage, ids in (("fit", contract["discovery_ids"]), ("evaluate", contract["evaluation_ids"])):
        capsule = evidence/"capsules"/stage
        raw = regular_bytes(capsule/"source_manifest.json")
        require(hashlib.sha256(raw).hexdigest() == contract["source_manifest_sha256"], "capsule manifest pin")
        authenticate_capsule(capsule, strict_json(raw), ids)
    destination.mkdir(parents=True)
    for folder in ("environment", "tests", "solution"):
        (destination/folder).mkdir()
    for name in ("instruction.md", "task.toml"):
        shutil.copyfile(release/name, destination/name)
    for folder, stage in (("environment", "fit"), ("tests", "evaluate")):
        root = destination/folder
        shutil.copyfile(release/folder/"Dockerfile", root/"Dockerfile")
        shutil.copytree(evidence/"capsules"/stage, root/"capsule")
        (root/"public").mkdir()
        shutil.copyfile(release/"contract.json", root/"public/contract.json")
        shutil.copyfile(release/"instruction.md", root/"public/method.md")
    shutil.copyfile(release/"solution/solve.sh", destination/"solution/solve.sh")
    (destination/"solution/oracle.pyz").write_bytes(oracle_zip(task, release))
    (destination/"solution/oracle_independent.pyz").write_bytes(oracle_zip(task, release, True))
    for name in ("grading.py", "sandbox.py", "verify.py"):
        shutil.copyfile(release/name, destination/"tests"/name)
    shutil.copyfile(release/"tests/test.sh", destination/"tests/test.sh")
    private = destination/"tests/private"
    private.mkdir()
    write_json(private/"discovery.json", compact(fit, "fit"))
    write_json(private/"evaluation.json", compact(evaluation, "evaluate"))
    arrays = {}
    for stage in ("fit", "evaluate"):
        with np.load(evidence/stage/(stage+"_arrays.npz"), allow_pickle=False) as archive:
            for key in archive.files:
                if key.startswith("discovery:") or stage == "evaluate":
                    if key.split(":")[-1] in ("operator", "stationary", "eigenvalues"):
                        arrays[key] = archive[key]
    np.savez_compressed(private/"operators.npz", **arrays)
    write_json(private/"pins.json", {p.name: sha(p) for p in sorted(private.iterdir())})
    write_json(destination/"preparation.json", {
        "status": "prepared_not_executed", "evidence_pins": EVIDENCE_PINS,
        "source_image_id": "sha256:19be0cc27dd1c6a1250b318d32c1dd628d49f4d8426122513e0f0f55e41760ca",
        "files": {p.relative_to(destination).as_posix(): sha(p) for p in sorted(destination.rglob("*")) if p.is_file()},
        "scope": "fixed source-backed references, no re-estimation, no difficulty claim"})
    print(json.dumps({"prepared": str(destination), "no_execution": True}))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--destination", type=Path, required=True)
    p.add_argument("--qualification", type=Path, required=True)
    args = p.parse_args()
    prepare(args.destination, args.qualification)
