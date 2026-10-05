"""Separate Harbor verifier entrypoint. Candidate is only executed after fit certification."""
import hashlib
import json
from pathlib import Path
import traceback
import numpy as np
from grading import (authenticate_capsule, compare, evaluation_reference, regular_bytes,
                     require, strict_json, validate_discovery)
from sandbox import run_candidate


def verify():
    private = Path("/private")
    pins = strict_json(regular_bytes(private/"pins.json"))
    for name, pin in pins.items():
        raw = regular_bytes(private/name, 64*1024**2)
        require(hashlib.sha256(raw).hexdigest() == pin, "private qualification pin mismatch")
    contract = strict_json(regular_bytes("/public/contract.json"))
    manifest_raw = regular_bytes("/sandbox/data/source_manifest.json")
    require(hashlib.sha256(manifest_raw).hexdigest() == contract["source_manifest_sha256"], "source manifest pin")
    manifest = strict_json(manifest_raw)
    authenticate_capsule("/sandbox/data", manifest, contract["evaluation_ids"])
    fit_raw, code_raw = (regular_bytes("/submission/"+name) for name in ("discovery.json", "evaluate.py"))
    fit = strict_json(fit_raw)
    expected_fit = strict_json(regular_bytes(private/"discovery.json"))
    expected_eval = strict_json(regular_bytes(private/"evaluation.json"))
    with np.load(private/"operators.npz", allow_pickle=False) as data:
        arrays = {key: data[key] for key in data.files}
    validate_discovery(fit, expected_fit, arrays)
    # Critical order: no submitted code execution until discovery certified.
    output, receipt = run_candidate(fit_raw, code_raw)
    answer = strict_json(output)
    compare(evaluation_reference(expected_eval, fit, arrays), answer, "evaluation")
    Path("/logs/verifier/evaluation.json").write_bytes(output)
    return receipt


if __name__ == "__main__":
    logs = Path("/logs/verifier")
    logs.mkdir(parents=True, exist_ok=True)
    reward = 0.0
    try:
        receipt = verify()
        reward = 1.0
        receipt.update(status="accepted", scope="fixed-cohort method validation; not positive-result requirement")
    except Exception as exc:
        receipt = {"status": "rejected", "error": str(exc), "exception_type": type(exc).__name__}
        traceback.print_exc()
    (logs/"receipt.json").write_text(json.dumps(receipt, indent=2)+"\n")
    (logs/"reward.txt").write_text(str(reward)+"\n")
