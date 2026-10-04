"""Separate, read-only-source qualification stages; no model or reward code."""
import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np

from pilot_support import authenticate_and_stage, json_write
from phase2_compare import audit_accounting, compare_arrays, compare_report, validate_fit_axis
from phase2_workflow import compute, load_partition


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(stage, phase, base):
    output = Path("/out")
    if stage == "authenticate":
        authenticate_and_stage(base, output)
        return
    checking = stage.startswith("check_")
    analysis = stage.removeprefix("check_")
    if checking:
        import phase2_independent as engine
    else:
        import phase2_production as engine
    frozen = None
    frozen_sha = None
    if analysis == "evaluate":
        frozen_sha = sha("/frozen/fit.json")
        if frozen_sha != os.environ["FIT_SHA256"]:
            raise ValueError("immutable fit digest mismatch before evaluation")
        frozen = json.loads(Path("/frozen/fit.json").read_text())
        if checking:
            prior = json.loads(Path("/checked/check_fit.json").read_text())
            if prior["status"] != "independent_arithmetic_agrees" or prior["submitted_json_sha256"] != frozen_sha:
                raise ValueError("evaluation checker requires certified exact frozen fit")
    people, labels, provenance = load_partition(analysis, base, engine)
    report, arrays = compute(analysis, people, labels, engine, frozen)
    report["source_manifest_sha256"] = base["source_manifest_sha256"]
    report["qualification_contract_sha256"] = sha("/pilot/phase2_contract.json")
    if checking:
        submitted_path = Path("/submitted")/f"{analysis}.json"
        submitted = json.loads(submitted_path.read_text())
        with np.load(Path("/submitted")/f"{analysis}_arrays.npz", allow_pickle=False) as data:
            observed_arrays = {key: data[key] for key in data.files}
        envelopes = phase["engineering_envelopes_not_final_scoring_tolerances"]
        scalars = compare_report(report, submitted, envelopes["scalar"])
        numbers = compare_arrays(arrays, observed_arrays, envelopes)
        accounting = audit_accounting(submitted, arrays, base, frozen)
        axis_certificate = validate_fit_axis(submitted, arrays, envelopes["spectral_certificate"]) if analysis == "fit" else None
        result = {"status": "independent_arithmetic_agrees", "stage": stage,
                  "submitted_json_sha256": sha(submitted_path), "comparison": numbers,
                  "scalar_comparison": scalars, "independent_accounting": accounting,
                  "frozen_axis_certificate": axis_certificate, "source_provenance": provenance,
                  "independently_computed_report": report,
                  "shared_dependencies": phase["independence"]["shared"]}
        json_write(output/f"{stage}.json", result)
    else:
        json_write(output/f"{analysis}.json", report)
        np.savez_compressed(output/f"{analysis}_arrays.npz", **arrays)
        json_write(output/f"{analysis}.provenance.json", provenance)
    if frozen_sha and sha("/frozen/fit.json") != frozen_sha:
        raise ValueError("frozen fit changed during evaluation")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=["authenticate", "fit", "evaluate", "check_fit", "check_evaluate"])
    args = p.parse_args()
    phase = json.loads(Path("/pilot/phase2_contract.json").read_text())
    if sha("/pilot/pilot_contract.json") != phase["base_pilot_contract_sha256"]:
        raise ValueError("base pilot contract changed")
    base = json.loads(Path("/pilot/pilot_contract.json").read_text())
    for name, expected in phase["code_sha256"].items():
        if sha(Path("/pilot")/name) != expected:
            raise ValueError(f"unreviewed phase2 code: {name}")
    for name, expected in base["legacy_code_sha256"].items():
        if sha(Path("/legacy")/name) != expected:
            raise ValueError(f"unreviewed legacy code: {name}")
    if sha("/public/method_contract.json") != base["method_sha256"]:
        raise ValueError("public method pin mismatch")
    if sha("/public/output_schema.json") != base["schema_sha256"]:
        raise ValueError("public schema pin mismatch")
    run(args.stage, phase, base)


if __name__ == "__main__":
    main()
