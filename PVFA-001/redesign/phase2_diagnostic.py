"""Independent selected-source/residual diagnostic. No optimizer is imported.

This implements only the pinned NIfTI-1 uint16 variant, not a general image
reader. It never reselects coordinates or changes phase1 model/domain/budgets.
"""
import argparse
import collections
import csv
import gzip
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import struct
import sys
import time

import numpy as np


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""):
            digest.update(chunk)
    return digest.hexdigest()


def dump(path,value):
    Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")


def parse_nifti_header(header):
    if len(header) != 348:
        raise ValueError("truncated NIfTI header")
    if struct.unpack_from("<i",header)[0] == 348:
        endian = "<"
    elif struct.unpack_from(">i",header)[0] == 348:
        endian = ">"
    else:
        raise ValueError("not a NIfTI-1 header")
    if header[344:348] != b"n+1\x00":
        raise ValueError("single-file NIfTI-1 required")
    dim = struct.unpack_from(endian+"8h",header,40)
    dtype,bitpix = struct.unpack_from(endian+"2h",header,70)
    if dim[0] != 4 or min(dim[1:5]) <= 0 or dtype != 512 or bitpix != 16:
        raise ValueError("only positive-shape 4D uint16 is supported")
    offset,slope,intercept = struct.unpack_from(endian+"3f",header,108)
    if not math.isfinite(offset) or offset < 352 or int(offset) != offset:
        raise ValueError("invalid voxel byte offset")
    original_slope = slope if math.isfinite(slope) else None
    original_intercept = intercept if math.isfinite(intercept) else None
    if not math.isfinite(slope) or slope == 0:
        slope,intercept = 1.,0.
    elif not math.isfinite(intercept):
        raise ValueError("active scaling needs finite intercept")
    return {"shape":list(dim[1:5]),"endian":endian,"offset":int(offset),"slope":slope,"intercept":intercept,"stored_slope":original_slope,"stored_intercept":original_intercept,"datatype_code":dtype,"bitpix":bitpix}


def reflect_index(index,size):
    wrapped = index % (2*size)
    return wrapped if wrapped < size else 2*size-1-wrapped


def gaussian_samples(volume,coordinates,fwhm=.625,truncate=4.):
    sigma = fwhm/math.sqrt(8*math.log(2))
    radius = int(truncate*sigma+.5)
    offsets = np.arange(-radius,radius+1,dtype=int)
    kernel = np.exp(-.5*(offsets/sigma)**2); kernel /= kernel.sum()
    values = []
    for coordinate in coordinates:
        total = 0.
        for a,b,c in itertools.product(range(len(offsets)),repeat=3):
            ijk = [reflect_index(int(coordinate[d])+int(offsets[q]),volume.shape[d]) for d,q in enumerate((a,b,c))]
            total += float(volume[tuple(ijk)])*float(kernel[a]*kernel[b]*kernel[c])
        values.append(total)
    return np.asarray(values,dtype=float)


def reconstruct_selected(path,coordinates,indices,expected_shape,fwhm=.625,truncate=4.):
    coordinates = np.asarray(coordinates,dtype=int)
    indices = np.asarray(indices,dtype=int)
    if indices.ndim != 1 or len(indices) == 0 or not np.array_equal(indices,np.unique(indices)) or indices.min()<0:
        raise ValueError("volume indices must be unique, increasing and nonnegative")
    with gzip.open(path,"rb") as stream:
        meta = parse_nifti_header(stream.read(348))
        if meta["shape"] != list(expected_shape):
            raise ValueError("source shape mismatch")
        shape = tuple(meta["shape"])
        if coordinates.ndim != 2 or coordinates.shape[1] != 3 or np.any(coordinates<0) or np.any(coordinates>=np.asarray(shape[:3])) or indices.max()>=shape[3]:
            raise ValueError("coordinate/volume outside source")
        if len(stream.read(meta["offset"]-348)) != meta["offset"]-348:
            raise ValueError("truncated image offset")
        bytes_per_volume = int(np.prod(shape[:3]))*2
        raw,smooth = [],[]
        wanted = set(indices.tolist())
        for volume_index in range(int(indices.max())+1):
            data = stream.read(bytes_per_volume)
            if len(data) != bytes_per_volume:
                raise ValueError("truncated image volume")
            if volume_index not in wanted:
                continue
            volume = np.frombuffer(data,dtype=meta["endian"]+"u2").reshape(shape[:3],order="F").astype(float)
            volume *= meta["slope"]; volume += meta["intercept"]
            raw.append(volume[tuple(coordinates.T)])
            smooth.append(gaussian_samples(volume,coordinates,fwhm,truncate))
        return np.asarray(raw).T,np.asarray(smooth).T,meta


def prediction_and_metrics(parameters,signal,bvalues,directions,domain):
    coeff = np.asarray(parameters["D"],dtype=float)
    if coeff.shape != (6,) or not np.isfinite(coeff).all():
        raise ValueError("invalid retained tensor")
    s0,f = float(parameters["S0"]),float(parameters["f"])
    if not math.isfinite(s0) or not math.isfinite(f):
        raise ValueError("invalid retained scalar")
    tensor = np.array([[coeff[0],coeff[1],coeff[3]],[coeff[1],coeff[2],coeff[4]],[coeff[3],coeff[4],coeff[5]]])
    predicted = []
    for b,direction in zip(bvalues,directions):
        # Explicit matrix-vector scalar contraction, independent of phase1 code.
        q = sum(float(direction[i])*float(tensor[i,j])*float(direction[j]) for i in range(3) for j in range(3))
        predicted.append(s0*((1-f)*math.exp(-float(b)*q)+f*math.exp(-float(b)*.003)))
    predicted = np.asarray(predicted)
    b0 = float(signal[np.asarray(bvalues)==0][0])
    residual = (predicted-np.asarray(signal))/b0
    eigenvalues = np.linalg.eigvalsh(tensor)
    scale = float(np.max(np.abs(eigenvalues)))
    if scale == 0:
        fa = None
    else:
        eig = eigenvalues/scale
        fa = math.sqrt(1.5*float(np.sum((eig-eig.mean())**2))/float(np.sum(eig*eig)))
    allowance = min(domain["eigenvalue_arithmetic_atol"],domain["eigenvalue_arithmetic_rtol"]*scale)
    feasible = (scale>0 and np.all(eigenvalues>=domain["eigenvalue_min"]-allowance)
        and np.all(eigenvalues<=domain["eigenvalue_max"]+allowance)
        and domain["fraction_min"]<=f<=domain["fraction_max"]
        and domain["s0_ratio_min"]<=s0/b0<=domain["s0_ratio_max"])
    return predicted,{"loss":float(np.dot(residual,residual)/len(residual)),"fa":fa,"eigenvalues":eigenvalues.tolist(),"feasible":bool(feasible),"eigenvalue_roundoff_allowance":allowance,"S0_ratio":s0/b0}


def validate_runtime(contract):
    if f"{sys.version_info.major}.{sys.version_info.minor}" != contract["software"]["python"] or np.__version__ != contract["software"]["numpy"]:
        raise ValueError("runtime version mismatch")
    for name in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"):
        if os.environ.get(name)!="1": raise ValueError("thread cap absent")
    memory = Path("/sys/fs/cgroup/memory.max").read_text().strip()
    quota,period = Path("/sys/fs/cgroup/cpu.max").read_text().split()
    if memory=="max" or int(memory)>contract["resources"]["memory_bytes"] or quota=="max" or int(quota)/int(period)>1:
        raise ValueError("resource cgroup cap absent")
    if {p.name for p in Path("/sys/class/net").iterdir()}!={"lo"}:
        raise ValueError("network isolation absent")


def authenticate(paths,contract):
    for key,value in contract["input_sha256"].items():
        if Path(paths[key]).is_symlink() or sha(paths[key])!=value:
            raise ValueError("input hash mismatch: "+key)
    manifest = json.loads(Path(paths["manifest"]).read_text())
    for record in manifest["files"]:
        file = Path(paths["raw"])/record["path"]
        if file.is_symlink() or file.stat().st_size!=record["size_bytes"] or sha(file)!=record["sha256"]:
            raise ValueError("raw source hash mismatch: "+record["path"])
    prior = json.loads(Path(paths["prior_contract"]).read_text())
    selection = json.loads(Path(paths["selection"]).read_text())
    if selection["indices"]!=contract["selection"]["source_indices"] or len(selection["coordinates"])!=contract["selection"]["n"]:
        raise ValueError("selection changed")
    if prior["protocols"]!=contract["protocols"]:
        raise ValueError("protocol changed")
    with np.load(paths["bank"],allow_pickle=False) as bank:
        arrays = {key:bank[key] for key in contract["source_reconstruction"]["allowed_bank_keys"]}
    indices = np.asarray(selection["indices"])
    coordinates = np.asarray(selection["coordinates"])
    if not np.array_equal(arrays["ref_roi_ijk"][indices],coordinates):
        raise ValueError("cache coordinate mapping differs")
    bvalues = np.loadtxt(Path(paths["raw"])/"HARDI193.bval")
    directions = np.loadtxt(Path(paths["raw"])/"HARDI193.bvec")
    volume_indices = arrays["ref_volume_indices"]
    if not np.array_equal(volume_indices,np.arange(129)) or bvalues.shape!=(193,) or directions.shape!=(193,3):
        raise ValueError("source acquisition layout mismatch")
    if not np.array_equal(bvalues[volume_indices],arrays["ref_bvals"]) or not np.array_equal(directions[volume_indices],arrays["ref_bvecs"]):
        raise ValueError("cached gradient/volume order mismatch")
    attempts = [json.loads(line) for line in Path(paths["attempts"]).read_text().splitlines()]
    if len(attempts)!=768 or [a["attempt_id"] for a in attempts]!=list(range(768)):
        raise ValueError("prior attempt coverage mismatch")
    support = {tuple(c) for c in coordinates.tolist()}
    if any(tuple(a["ijk"]) not in support or a["protocol"] not in contract["protocols"] for a in attempts):
        raise ValueError("prior attempt support mismatch")
    return arrays,prior,selection,attempts,bvalues,directions


def descriptive_qc(values,bvalues,observed_b0,fitted_s0=None):
    values = np.asarray(values)
    mask = np.asarray(bvalues)>0
    result = {"n":int(values.size),"nonfinite":int((~np.isfinite(values)).sum()),"negative":int((values<0).sum()),"zero":int((values==0).sum()),"diffusion_above_observed_b0":int((values[mask]>observed_b0).sum())}
    if fitted_s0 is not None:
        result["diffusion_above_fitted_S0"] = int((values[mask]>fitted_s0).sum())
    return result


def shell_summaries(predicted,observed,bvalues):
    residual = (np.asarray(predicted)-observed)/observed[np.asarray(bvalues)==0][0]
    total = float(np.dot(residual,residual))
    result = []
    for shell in sorted(set(np.asarray(bvalues).tolist())):
        selected = residual[np.asarray(bvalues)==shell]
        sse = float(np.dot(selected,selected))
        result.append({"bvalue":shell,"n":len(selected),"mean_normalized_residual":float(selected.mean()),"normalized_rmse":float(np.sqrt(np.mean(selected**2))),"normalized_sse":sse,"sse_fraction":sse/total if total>0 else None})
    return result


def diagnose(paths,contract,output):
    output = Path(output); output.mkdir(parents=True,exist_ok=False)
    started = time.monotonic()
    arrays,prior,selection,attempts,bvalues,directions = authenticate(paths,contract)
    indices = np.asarray(selection["indices"])
    coordinates = np.asarray(selection["coordinates"])
    volumes = arrays["ref_volume_indices"]
    cfg = contract["source_reconstruction"]
    raw,smooth,header = reconstruct_selected(Path(paths["raw"])/"HARDI193.nii.gz",coordinates,volumes,cfg["shape"],cfg["smoothing_fwhm_voxels"],cfg["truncate"])
    cached_raw = arrays["ref_raw_signal"][indices][:,volumes]
    cached_smooth = arrays["ref_signal"][indices]
    checks = contract["arithmetic_checks"]
    raw_diff = float(np.max(np.abs(raw-cached_raw)))
    smooth_diff = float(np.max(np.abs(smooth-cached_smooth)))
    source_report = {"header":header,"n_coordinates":len(coordinates),"n_volumes":len(volumes),"raw_max_abs_difference":raw_diff,"smoothed_max_abs_difference":smooth_diff,"raw_match":raw_diff<=checks["selected_raw_atol"],"smoothed_match":smooth_diff<=checks["selected_smoothed_atol"],"gradient_volume_order_exact":True,"gradient_orientation_physically_validated":False,"full_roi_reconstructed":False,"selected_signal_reconstructed_independently":True}
    dump(output/"source_checks.json",source_report)
    np.savez_compressed(output/"selected_source.npz",coordinates=coordinates,volume_indices=volumes,raw=raw,smoothed=smooth,bvalues=bvalues[volumes],directions=directions[volumes])
    if not source_report["raw_match"] or not source_report["smoothed_match"]:
        raise ValueError("independent selected source differs from cache; no residual interpretation allowed")
    coordinate_index = {tuple(c):i for i,c in enumerate(coordinates.tolist())}
    candidate_checks = []
    reconstructed = {}
    with (output/"candidate_checks.jsonl").open("x") as stream:
        for attempt in attempts:
            record = {"attempt_id":attempt["attempt_id"],"ijk":attempt["ijk"],"protocol":attempt["protocol"],"algorithm":attempt["algorithm"],"prior_admissible":attempt.get("admissible",False),"prior_optimizer_success":attempt.get("optimizer_success")}
            if "parameters" not in attempt:
                record.update(status="no_retained_candidate",prior_error=attempt.get("error"))
            else:
                row = coordinate_index[tuple(attempt["ijk"])]; mask = np.isin(bvalues[volumes],contract["protocols"][attempt["protocol"]])
                prediction,metrics = prediction_and_metrics(attempt["parameters"],smooth[row,mask],bvalues[volumes][mask],directions[volumes][mask],prior["domain"])
                record.update(status="reconstructed",**metrics)
                record["feasibility_agrees"] = metrics["feasible"]==attempt.get("admissible",False)
                if "loss" in attempt:
                    record["loss_abs_difference"] = abs(metrics["loss"]-attempt["loss"])
                    record["loss_agrees"] = record["loss_abs_difference"]<=checks["normalized_mse_atol"]
                if "fa" in attempt:
                    record["fa_abs_difference"] = abs(metrics["fa"]-attempt["fa"])
                    record["fa_agrees"] = record["fa_abs_difference"]<=checks["fa_atol"]
                reconstructed[attempt["attempt_id"]] = (prediction,metrics)
            candidate_checks.append(record)
            stream.write(json.dumps(record,allow_nan=False)+"\n")
    best_rows = []
    csv_fields = ["i","j","k","protocol","attempt_id","original_volume_index","bvalue","gx","gy","gz","observed_raw","observed_smoothed","predicted","normalized_residual","squared_normalized_residual"]
    with (output/"best_directional_residuals.csv").open("x",newline="") as stream:
        writer = csv.DictWriter(stream,fieldnames=csv_fields); writer.writeheader()
        for coordinate in selection["coordinates"]:
            for protocol,shells in contract["protocols"].items():
                pool = [a for a in attempts if a["ijk"]==coordinate and a["protocol"]==protocol and a.get("admissible")]
                best = min(pool,key=lambda a:a["loss"]) # frozen phase1 criterion, not refit/reselection
                prediction,metrics = reconstructed[best["attempt_id"]]
                row = coordinate_index[tuple(coordinate)]; mask = np.isin(bvalues[volumes],shells)
                observed = smooth[row,mask]; original = raw[row,mask]; b = bvalues[volumes][mask]; g = directions[volumes][mask]
                b0 = float(observed[b==0][0]); residual = (prediction-observed)/b0
                best_rows.append({"ijk":coordinate,"protocol":protocol,"attempt_id":best["attempt_id"],"loss":metrics["loss"],"fa":metrics["fa"],"normalized_rmse":math.sqrt(metrics["loss"]),"shells":shell_summaries(prediction,observed,b),"raw_qc":descriptive_qc(original,b,float(original[b==0][0])),"smoothed_qc":descriptive_qc(observed,b,b0,best["parameters"]["S0"]),"prior_boundaries":best["boundary_diagnostics"]})
                for t,volume in enumerate(volumes[mask]):
                    writer.writerow(dict(zip(csv_fields,[*coordinate,protocol,best["attempt_id"],int(volume),float(b[t]),*g[t].tolist(),float(original[t]),float(observed[t]),float(prediction[t]),float(residual[t]),float(residual[t]**2)])))
    solver_summary = {}
    for algorithm in prior["search"]["algorithms"]:
        subset = [a for a in attempts if a["algorithm"]==algorithm]
        solver_summary[algorithm] = {"attempts":len(subset),"admissible":sum(bool(a.get("admissible")) for a in subset),"optimizer_success":sum(bool(a.get("optimizer_success")) for a in subset),"error_counts":dict(collections.Counter(a.get("error",a.get("rejection","none")) for a in subset if not a.get("admissible"))),"boundary_flag_counts":dict(collections.Counter(k for a in subset for k,v in a.get("boundary_diagnostics",{}).items() if isinstance(v,bool) and v))}
    failures = [c["attempt_id"] for c in candidate_checks if any(c.get(k) is False for k in ("feasibility_agrees","loss_agrees","fa_agrees"))]
    result = {"status":"completed_independent_diagnostic" if not failures else "completed_with_arithmetic_disagreements","elapsed_seconds":time.monotonic()-started,"source_checks":source_report,"n_attempts_checked":len(candidate_checks),"n_candidates_reconstructed":len(reconstructed),"arithmetic_disagreement_attempt_ids":failures,"maximum_loss_abs_difference":max(c.get("loss_abs_difference",0) for c in candidate_checks),"maximum_fa_abs_difference":max(c.get("fa_abs_difference",0) for c in candidate_checks),"best_residual_summaries":best_rows,"prior_solver_summary":solver_summary,"fits":0,"scope":contract["scope"],"limitations":contract["release_boundary"]}
    dump(output/"report.json",result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--execute",action="store_true"); p.add_argument("--approval",type=Path)
    p.add_argument("--contract",type=Path,default=Path(__file__).with_name("phase2_contract.json"))
    p.add_argument("--output",type=Path,default=Path("/out/diagnostic"))
    args = p.parse_args(); contract = json.loads(args.contract.read_text())
    if not args.execute:
        print(json.dumps({"execute":False,"contract_sha256":sha(args.contract),"resources":contract["resources"],"fits":0},indent=2)); return
    if args.approval is None: p.error("execution requires root-reviewed approval")
    approval = json.loads(args.approval.read_text())
    if approval.get("approved") is not True or approval.get("reviewer")!="root" or approval.get("contract_sha256")!=sha(args.contract):
        raise ValueError("root approval mismatch")
    for name in ("phase2_diagnostic.py","launch_phase2.py","launch_pilot.py"):
        if approval.get("code_sha256",{}).get(name)!=sha(Path(__file__).with_name(name)):
            raise ValueError("approved code mismatch: "+name)
    validate_runtime(contract)
    paths = {key:"/inputs/"+key for key in contract["input_sha256"]}; paths["raw"]="/app/data/sherbrooke"
    report = diagnose(paths,contract,args.output)
    print(json.dumps({k:report[k] for k in ("status","elapsed_seconds","n_candidates_reconstructed","arithmetic_disagreement_attempt_ids","fits")}))


if __name__=="__main__": main()
