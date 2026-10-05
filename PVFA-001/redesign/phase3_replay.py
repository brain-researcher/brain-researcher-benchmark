"""Append-only unchanged-candidate replay, dry-run unless exact root approved.

Both substrates use the frozen phase2 arithmetic. This isolates numerical
representation, not a new independent forward model or scientific experiment.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import phase2_diagnostic as arithmetic


CODE_FILES = ("phase3_replay.py", "launch_phase3.py", "phase2_diagnostic.py", "launch_pilot.py")


def code_hashes(directory):
    return {name:arithmetic.sha(directory/name) for name in CODE_FILES}


def verify_approval(approval, contract_path, directory, contract):
    if (approval.get("approved") is not True or approval.get("reviewer") != "root"
        or approval.get("contract_sha256") != arithmetic.sha(contract_path)
        or approval.get("code_sha256") != code_hashes(directory)):
        raise ValueError("phase3 exact root approval mismatch")
    for name, expected in contract["immutable_code_sha256"].items():
        if arithmetic.sha(directory/name) != expected:
            raise ValueError("frozen dependency changed: "+name)


def compare_metrics(metrics, previous, checks, feasible_key):
    agreement = {"feasibility_agrees": metrics["feasible"] == previous[feasible_key]}
    for key, tolerance in (("loss",checks["normalized_mse_atol"]),("fa",checks["fa_atol"])):
        if key in previous:
            difference = abs(metrics[key]-previous[key])
            agreement[key+"_abs_difference"] = difference
            agreement[key+"_agrees"] = difference <= tolerance
    return agreement


def compare_candidate(attempt, phase2_check, canonical, reconstructed, bvalues, directions, domain, checks):
    row = {"attempt_id":attempt["attempt_id"], "ijk":attempt["ijk"],
        "protocol":attempt["protocol"], "algorithm":attempt["algorithm"],
        "prior_admissible":attempt.get("admissible",False)}
    if "parameters" not in attempt:
        row.update(status="no_retained_candidate", prior_error=attempt.get("error"))
        return row
    row["parameters_sha256"] = hashlib.sha256(json.dumps(attempt["parameters"],sort_keys=True,allow_nan=False).encode()).hexdigest()
    _, left = arithmetic.prediction_and_metrics(attempt["parameters"],canonical,bvalues,directions,domain)
    _, right = arithmetic.prediction_and_metrics(attempt["parameters"],reconstructed,bvalues,directions,domain)
    row.update(status="replayed",canonical=left,reconstructed=right,
        canonical_comparison=compare_metrics(left,attempt,checks,"admissible"),
        reconstructed_comparison=compare_metrics(right,phase2_check,checks,"feasible"),
        substrate_feasibility_difference=left["feasible"] != right["feasible"],
        canonical_b0=float(canonical[np.asarray(bvalues)==0][0]),
        reconstructed_b0=float(reconstructed[np.asarray(bvalues)==0][0]))
    return row


def authenticate(paths, contract):
    for key, expected in contract["input_sha256"].items():
        if Path(paths[key]).is_symlink() or arithmetic.sha(paths[key]) != expected:
            raise ValueError("input identity mismatch: "+key)
    load = lambda key: json.loads(Path(paths[key]).read_text())
    prior, phase2_contract = load("prior_contract"),load("phase2_contract")
    selection, prior_report, phase2_report = load("selection"),load("prior_report"),load("phase2_report")
    source_checks = load("phase2_source_checks")
    if not source_checks["raw_match"] or not source_checks["smoothed_match"] or not source_checks["gradient_volume_order_exact"]:
        raise ValueError("phase2 selected-source compatibility was not established")
    if phase2_report["status"] != "completed_with_arithmetic_disagreements" or phase2_report["arithmetic_disagreement_attempt_ids"] != contract["arithmetic"]["expected_historical_difference_ids"]:
        raise ValueError("unexpected historical phase2 result")
    support = contract["support"]
    if selection["indices"] != support["source_indices"] or len(selection["coordinates"]) != support["coordinates"]:
        raise ValueError("selection changed")
    if prior["protocols"] != phase2_contract["protocols"]:
        raise ValueError("protocol identity mismatch")
    with np.load(paths["bank"],allow_pickle=False) as bank:
        arrays = {key:bank[key] for key in contract["allowed_bank_keys"]}
    with np.load(paths["phase2_selected"],allow_pickle=False) as selected:
        rebuilt = {key:selected[key] for key in ("coordinates","volume_indices","smoothed","bvalues","directions")}
    indices = np.asarray(selection["indices"])
    coordinates = np.asarray(selection["coordinates"])
    for left,right in ((arrays["ref_roi_ijk"][indices],coordinates),(rebuilt["coordinates"],coordinates),
        (arrays["ref_volume_indices"],rebuilt["volume_indices"]),(arrays["ref_bvals"],rebuilt["bvalues"]),
        (arrays["ref_bvecs"],rebuilt["directions"]),(rebuilt["volume_indices"],np.arange(129))):
        if not np.array_equal(left,right):
            raise ValueError("selected coordinate/gradient/volume mapping changed")
    canonical = arrays["ref_signal"][indices]
    if canonical.shape != (16,129) or rebuilt["smoothed"].shape != (16,129) or not np.isfinite(canonical).all() or not np.isfinite(rebuilt["smoothed"]).all():
        raise ValueError("selected signals changed shape or finiteness")
    difference = float(np.max(np.abs(canonical-rebuilt["smoothed"])))
    if difference > phase2_contract["arithmetic_checks"]["selected_smoothed_atol"]:
        raise ValueError("selected-substrate compatibility bound exceeded")
    attempts = [json.loads(line) for line in Path(paths["attempts"]).read_text().splitlines()]
    checks = [json.loads(line) for line in Path(paths["phase2_checks"]).read_text().splitlines()]
    wanted_ids = list(range(support["attempt_slots"]))
    if [a["attempt_id"] for a in attempts] != wanted_ids or [c["attempt_id"] for c in checks] != wanted_ids:
        raise ValueError("attempt/check slots incomplete")
    if sum("parameters" in a for a in attempts) != support["retained_candidates"]:
        raise ValueError("retained-candidate count changed")
    coordinate_support = {tuple(c) for c in coordinates.tolist()}
    for attempt,check in zip(attempts,checks):
        if tuple(attempt["ijk"]) not in coordinate_support or attempt["protocol"] not in prior["protocols"] or any(attempt[k] != check[k] for k in ("attempt_id","ijk","protocol","algorithm")):
            raise ValueError("attempt/check support mismatch")
        if ("parameters" in attempt) != (check["status"] == "reconstructed"):
            raise ValueError("candidate presence mismatch")
    if len(prior_report["sensitivity"]) != support["sensitivity_rows"] or len(phase2_report["best_residual_summaries"]) != support["best_representatives"]:
        raise ValueError("receipt representative coverage changed")
    return canonical,rebuilt,prior,phase2_contract,selection,attempts,checks,prior_report,phase2_report,difference


def replay(paths, contract, output):
    output = Path(output); output.mkdir(parents=True,exist_ok=False)
    started = time.monotonic()
    canonical,rebuilt,prior,phase2_contract,selection,attempts,checks,prior_report,phase2_report,source_difference = authenticate(paths,contract)
    index = {tuple(c):i for i,c in enumerate(selection["coordinates"])}
    replayed = []
    with (output/"candidate_replay.jsonl").open("x") as stream:
        for attempt,check in zip(attempts,checks):
            i = index[tuple(attempt["ijk"])]; mask = np.isin(rebuilt["bvalues"],prior["protocols"][attempt["protocol"]])
            row = compare_candidate(attempt,check,canonical[i,mask],rebuilt["smoothed"][i,mask],rebuilt["bvalues"][mask],rebuilt["directions"][mask],prior["domain"],phase2_contract["arithmetic_checks"])
            replayed.append(row); stream.write(json.dumps(row,allow_nan=False)+"\n")
    retained = [row for row in replayed if row["status"]=="replayed"]
    bad = lambda key:[row["attempt_id"] for row in retained if any(value is False for name,value in row[key].items() if name.endswith("_agrees"))]
    canonical_mismatches, reconstructed_mismatches = bad("canonical_comparison"),bad("reconstructed_comparison")
    substrate_differences = [r["attempt_id"] for r in retained if r["substrate_feasibility_difference"]]
    representatives = []
    for previous in phase2_report["best_residual_summaries"]:
        row = replayed[previous["attempt_id"]]
        representatives.append({"ijk":previous["ijk"],"protocol":previous["protocol"],"attempt_id":previous["attempt_id"],
            "prior_normalized_rmse":previous["normalized_rmse"],"canonical":row["canonical"],"reconstructed":row["reconstructed"]})
    endpoints = []
    for previous in prior_report["sensitivity"]:
        item = {key:previous[key] for key in ("ijk","protocol","budget","view","left_candidate","right_candidate")}
        for side in ("left","right"):
            row = replayed[previous[side+"_candidate"]]
            item[side+"_canonical_feasible"] = row["canonical"]["feasible"]
            item[side+"_reconstructed_feasible"] = row["reconstructed"]["feasible"]
        endpoints.append(item)
    arithmetic.dump(output/"representative_audit.json",representatives)
    arithmetic.dump(output/"endpoint_membership_audit.json",endpoints)
    agrees = not canonical_mismatches and not reconstructed_mismatches and substrate_differences == contract["arithmetic"]["expected_historical_difference_ids"]
    report = {"status":"completed_canonical_substrate_replay" if agrees else "completed_with_unexpected_replay_disagreements",
        "scientific_release":False,"fits":0,"elapsed_seconds":time.monotonic()-started,
        "n_attempt_slots":len(replayed),"n_retained_candidates":len(retained),"n_without_candidate":len(replayed)-len(retained),
        "canonical_feasible_count":sum(r["canonical"]["feasible"] for r in retained),
        "reconstructed_feasible_count":sum(r["reconstructed"]["feasible"] for r in retained),
        "canonical_vs_prior_mismatch_ids":canonical_mismatches,"reconstructed_vs_phase2_mismatch_ids":reconstructed_mismatches,
        "substrate_feasibility_difference_ids":substrate_differences,"selected_signal_max_abs_difference":source_difference,
        "representative_difference_ids":[r["attempt_id"] for r in representatives if r["canonical"]["feasible"] != r["reconstructed"]["feasible"]],
        "n_endpoint_rows_with_membership_difference":sum(any(e[s+"_canonical_feasible"] != e[s+"_reconstructed_feasible"] for s in ("left","right")) for e in endpoints),
        "prior_phase2_status_preserved":phase2_report["status"],"scope":contract["scope"],"limitations":contract["release_boundary"]}
    arithmetic.dump(output/"report.json",report)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("--execute",action="store_true"); p.add_argument("--approval",type=Path)
    p.add_argument("--contract",type=Path,default=Path(__file__).with_name("phase3_contract.json")); p.add_argument("--output",type=Path,default=Path("/out/replay"))
    args=p.parse_args(); contract=json.loads(args.contract.read_text())
    if not args.execute:
        print(json.dumps({"execute":False,"contract_sha256":arithmetic.sha(args.contract),"resources":contract["resources"]},indent=2)); return
    if args.approval is None: p.error("execution requires separate root approval")
    verify_approval(json.loads(args.approval.read_text()),args.contract,Path(__file__).parent,contract)
    arithmetic.validate_runtime(contract)
    report=replay({key:"/inputs/"+key for key in contract["input_sha256"]},contract,args.output)
    print(json.dumps(report,indent=2))


if __name__=="__main__": main()
