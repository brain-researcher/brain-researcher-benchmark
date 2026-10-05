"""No-optimizer ideal-PSD descriptive relaxation; not a scoring certificate."""
import argparse
import json
import math
from pathlib import Path
import time

import numpy as np
import phase2_diagnostic as infrastructure

CODE_FILES = ("paired_shell.py", "launch_paired_shell.py", "phase2_diagnostic.py", "launch_pilot.py")


def code_hashes(directory):
    return {name: infrastructure.sha(directory/name) for name in CODE_FILES}


def verify_approval(approval, contract_path, directory, contract):
    if (approval.get("approved") is not True or approval.get("reviewer") != "root"
            or approval.get("contract_sha256") != infrastructure.sha(contract_path)
            or approval.get("code_sha256") != code_hashes(directory)):
        raise ValueError("exact paired-shell root approval mismatch")
    for name, expected in contract["immutable_code_sha256"].items():
        if infrastructure.sha(directory/name) != expected:
            raise ValueError("frozen dependency changed: "+name)


def exact_pairing(bvalues, directions, volume_indices, pairs=64):
    b, g, indices = np.asarray(bvalues), np.asarray(directions), np.asarray(volume_indices)
    n = 2*pairs+1
    if (b.shape != (n,) or g.shape != (n,3) or indices.shape != (n,)
            or not np.isfinite(b).all() or not np.isfinite(g).all()
            or not np.array_equal(indices, np.arange(n))):
        raise ValueError("invalid gradient/volume support")
    low, high, zero = np.flatnonzero(b==1000), np.flatnonzero(b==2000), np.flatnonzero(b==0)
    if (len(low), len(high), len(zero)) != (pairs,pairs,1):
        raise ValueError("exact 0/1000/2000 shell support required")
    if np.any(np.linalg.norm(g[low],axis=1)==0) or np.any(np.linalg.norm(g[high],axis=1)==0):
        raise ValueError("zero diffusion direction")
    right = {}
    for index in high:
        key = tuple(g[index].tolist())
        if key in right:
            raise ValueError("ambiguous duplicate high-shell vector")
        right[key] = int(index)
    seen, matched = set(), []
    for index in low:
        key = tuple(g[index].tolist())
        if key in seen:
            raise ValueError("ambiguous duplicate low-shell vector")
        seen.add(key)
        if key not in right or not np.array_equal(g[index],g[right[key]]):
            raise ValueError("exact released-vector pairing absent")
        matched.append((int(index),right[key]))
    if len({r for _,r in matched}) != pairs:
        raise ValueError("pairing is not one-to-one")
    return int(zero[0]), matched


def relaxation_pair(y1, y2):
    y1, y2 = float(y1), float(y2)
    if not math.isfinite(y1) or not math.isfinite(y2):
        raise ValueError("nonfinite pair observation")
    gap = y2-y1
    contribution = max(0.,gap)**2/2.
    if not math.isfinite(contribution):
        raise ValueError("nonfinite relaxation contribution")
    return gap, contribution


def authenticate(paths, contract):
    if set(paths) != set(contract["input_sha256"]):
        raise ValueError("unexpected input keys")
    for key, expected in contract["input_sha256"].items():
        if Path(paths[key]).is_symlink() or infrastructure.sha(paths[key]) != expected:
            raise ValueError("input hash mismatch: "+key)
    load = lambda key: json.loads(Path(paths[key]).read_text())
    selection, prior, source, replay = [load(k) for k in ("selection","prior_contract","source_checks","replay_result")]
    support = contract["support"]
    if (selection["indices"] != support["source_indices"]
            or len(selection["coordinates"]) != support["coordinates"]
            or prior["protocols"]["b1000_b2000"] != [0,1000,2000]):
        raise ValueError("frozen support/protocol changed")
    if any(source[k] is not True for k in ("raw_match","smoothed_match","gradient_volume_order_exact")):
        raise ValueError("selected-source compatibility absent")
    if (replay["status"] != "completed_canonical_substrate_replay"
            or replay["canonical_vs_prior_mismatch_ids"] or replay["reconstructed_vs_phase2_mismatch_ids"]):
        raise ValueError("canonical replay compatibility absent")
    # Never load candidate parameters, fitted references, or old Sol outputs.
    with np.load(paths["bank"],allow_pickle=False) as bank:
        arrays = {key: bank[key] for key in contract["allowed_bank_keys"]}
    indices = np.asarray(selection["indices"])
    if not np.array_equal(arrays["ref_roi_ijk"][indices],selection["coordinates"]):
        raise ValueError("selected coordinate mapping changed")
    signal = arrays["ref_signal"][indices]
    if signal.shape != (support["coordinates"],support["volumes"]) or not np.isfinite(signal).all():
        raise ValueError("selected signal support/finiteness changed")
    b0_index, pairs = exact_pairing(arrays["ref_bvals"], arrays["ref_bvecs"], arrays["ref_volume_indices"],support["pairs_per_coordinate"])
    if np.any(signal[:,b0_index] <= 0):
        raise ValueError("positive measured b0 required")
    return selection, signal, arrays, b0_index, pairs


def diagnose(paths, contract, output):
    started = time.monotonic()
    selection, signal, arrays, b0_index, pairs = authenticate(paths,contract)
    output = Path(output); output.mkdir(parents=True,exist_ok=False)
    pairing = [{"pair_index":k,"b1000_volume_index":left,"b2000_volume_index":right,
                "released_direction":arrays["ref_bvecs"][left].tolist()} for k,(left,right) in enumerate(pairs)]
    infrastructure.dump(output/"pairing.json",pairing)
    voxels, count = [], 0
    with (output/"pairs.jsonl").open("x") as stream:
        for i, coordinate in enumerate(selection["coordinates"]):
            b0 = float(signal[i,b0_index]); denominator = b0*b0*signal.shape[1]
            contributions, reversed_pairs = [], 0
            for pair in pairing:
                left,right = pair["b1000_volume_index"],pair["b2000_volume_index"]
                y1,y2 = float(signal[i,left]),float(signal[i,right])
                gap, contribution = relaxation_pair(y1,y2)
                row = dict(pair,ijk=coordinate,source_index=selection["indices"][i],
                           y_b1000=y1,y_b2000=y2,measured_b0=b0,gap=gap,
                           reversed_order=gap>0,ideal_psd_relaxation_sse=contribution,
                           ideal_psd_relaxation_normalized_mse_contribution=contribution/denominator)
                stream.write(json.dumps(row,allow_nan=False)+"\n")
                count += 1; contributions.append(contribution); reversed_pairs += gap>0
            value = math.fsum(contributions)/denominator
            voxels.append({"ijk":coordinate,"source_index":selection["indices"][i],
                           "measured_b0":b0,"n_pairs":len(pairs),"n_reversed_pairs":reversed_pairs,
                           "ideal_psd_relaxation_normalized_mse":value,
                           "ideal_psd_relaxation_normalized_rmse":math.sqrt(value)})
    if count != contract["support"]["coordinates"]*contract["support"]["pairs_per_coordinate"]:
        raise ValueError("incomplete pair accounting")
    infrastructure.dump(output/"voxels.json",voxels)
    values = [v["ideal_psd_relaxation_normalized_rmse"] for v in voxels]
    report = {"status":"completed_ideal_psd_descriptive_diagnostic","scientific_release":False,
              "operational_numerical_domain_bound_certified":False,"fits":0,"model_runs":0,
              "elapsed_seconds":time.monotonic()-started,"n_coordinates":len(voxels),
              "n_pairs":count,"n_reversed_pairs":sum(v["n_reversed_pairs"] for v in voxels),
              "n_voxels_with_reversed_pairs":sum(v["n_reversed_pairs"]>0 for v in voxels),
              "min_ideal_psd_relaxation_normalized_rmse":min(values),
              "max_ideal_psd_relaxation_normalized_rmse":max(values),
              "exact_pairing":True,"scope":contract["scope"],"limitations":contract["release_boundary"]}
    infrastructure.dump(output/"report.json",report)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute",action="store_true"); parser.add_argument("--approval",type=Path)
    parser.add_argument("--contract",type=Path,default=Path(__file__).with_name("paired_shell_contract.json"))
    parser.add_argument("--output",type=Path,default=Path("/out/diagnostic"))
    args=parser.parse_args(); contract=json.loads(args.contract.read_text())
    if not args.execute:
        print(json.dumps({"execute":False,"contract_sha256":infrastructure.sha(args.contract),"resources":contract["resources"]},indent=2)); return
    if args.approval is None: parser.error("execution requires separate root approval")
    verify_approval(json.loads(args.approval.read_text()),args.contract,Path(__file__).parent,contract)
    infrastructure.validate_runtime(contract)
    print(json.dumps(diagnose({key:"/inputs/"+key for key in contract["input_sha256"]},contract,args.output),indent=2))


if __name__=="__main__": main()
