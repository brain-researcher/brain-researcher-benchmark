"""Bounded real-data feasibility pilot. Default is plan-only, never execution.

Execute only in a root-approved, capped offline container. Original sources and
old model outputs are immutable. This code never reads fitted reference arrays.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import numpy as np
from scipy.optimize import least_squares, minimize
from scipy.spatial.transform import Rotation

from witness import Domain, EvidenceError, candidate_metrics


class PilotStop(RuntimeError):
    pass


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            h.update(block)
    return h.hexdigest()


def select_indices(ijk, n):
    ijk = np.asarray(ijk)
    if ijk.ndim != 2 or ijk.shape[1] != 3 or ijk.dtype.kind not in "iu":
        raise ValueError("invalid coordinate array")
    if len(np.unique(ijk, axis=0)) != len(ijk) or not 0 < n <= len(ijk):
        raise ValueError("duplicate coordinates or impossible sample size")
    order = np.lexsort((ijk[:, 2], ijk[:, 1], ijk[:, 0]))
    positions = ((2*np.arange(n)+1)*len(ijk)) // (2*n)
    return order[positions]


def verify_approval(approval, contract_path):
    if approval.get("approved") is not True or approval.get("reviewer") != "root":
        raise ValueError("explicit root review required")
    if approval.get("contract_sha256") != sha256(contract_path):
        raise ValueError("approval does not bind this contract")
    for name in ("pilot.py", "witness.py"):
        if approval.get("code_sha256", {}).get(name) != sha256(Path(__file__).with_name(name)):
            raise ValueError(f"approval does not bind {name}")


def verify_runtime(contract):
    """Require Linux container resource caps; external launcher is authoritative."""
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        if os.environ.get(name) != "1":
            raise ValueError(f"{name} must equal 1 before Python import")
    root = Path("/sys/fs/cgroup")
    memory = (root / "memory.max").read_text().strip()
    quota, period = (root / "cpu.max").read_text().split()
    caps = contract["resources"]
    if memory == "max" or int(memory) > caps["memory_bytes"]:
        raise ValueError("container memory cap absent/too large")
    if quota == "max" or int(quota)/int(period) > caps["cpus"]:
        raise ValueError("container CPU cap absent/too large")
    if {p.name for p in Path("/sys/class/net").iterdir()} != {"lo"}:
        raise ValueError("offline container must expose only loopback")
    import scipy
    if f"{sys.version_info.major}.{sys.version_info.minor}" != contract["software"]["python_major_minor"]:
        raise ValueError("Python major/minor version mismatch")
    if np.__version__ != contract["software"]["numpy"] or scipy.__version__ != contract["software"]["scipy"]:
        raise ValueError("numerical library version mismatch")


def authenticate_source(paths, contract):
    source = contract["source"]
    pairs = {"bank": "bank_sha256", "receipt": "receipt_sha256", "report": "independent_report_sha256", "manifest": "manifest_sha256", "preprocessing": "preprocessing_contract_sha256"}
    for role, key in pairs.items():
        if Path(paths[role]).is_symlink() or sha256(paths[role]) != source[key]:
            raise ValueError(f"source authority hash mismatch: {role}")
    receipt = json.loads(Path(paths["receipt"]).read_text())
    report = json.loads(Path(paths["report"]).read_text())
    manifest = json.loads(Path(paths["manifest"]).read_text())
    if receipt["reference"]["sha256"] != source["bank_sha256"]:
        raise ValueError("receipt does not bind source bank")
    if receipt["source"]["manifest_sha256"] != source["manifest_sha256"]:
        raise ValueError("receipt does not bind source manifest")
    if report["status"] != "passed" or report["mode"] != "complete_source_check":
        raise ValueError("independent full-source validation missing")
    if report["source_manifest_sha256"] != source["manifest_sha256"] or report["source_roi_count"] != source["n_roi"]:
        raise ValueError("independent source identity mismatch")
    wanted_hashes = {x["path"]: x["sha256"] for x in manifest["files"]}
    if report["source_sha256"] != wanted_hashes:
        raise ValueError("source file identity mismatch")
    for record in manifest["files"]:
        path = Path(paths["raw_source"])/record["path"]
        if path.is_symlink() or path.stat().st_size != record["size_bytes"] or sha256(path) != record["sha256"]:
            raise ValueError(f"current raw-source identity mismatch: {record['path']}")
    checks = {x["name"]: x for x in report["checks"]}
    if not all(checks.get(name, {}).get("passed") is True for name in source["required_report_checks"]):
        raise ValueError("required independent source check missing/failed")
    if checks["source_signal"]["detail"]["max_abs_difference"] != 0:
        raise ValueError("cached signals differ from independently reconstructed source")
    allowed = ["ref_roi_ijk", "ref_signal", "ref_bvals", "ref_bvecs"]
    if source["allowed_bank_keys"] != allowed:
        raise ValueError("source bank allowlist changed")
    with np.load(paths["bank"], allow_pickle=False) as z:
        arrays = {name: z[name] for name in allowed}
    if list(arrays["ref_signal"].shape) != source["signal_shape"]:
        raise ValueError("source signal shape mismatch")
    if arrays["ref_roi_ijk"].shape != (source["n_roi"], 3):
        raise ValueError("ROI shape mismatch")
    if arrays["ref_bvals"].shape != (129,) or arrays["ref_bvecs"].shape != (129, 3):
        raise ValueError("protocol shape mismatch")
    if not np.isfinite(arrays["ref_signal"]).all() or np.any(arrays["ref_signal"] < 0):
        raise ValueError("invalid source observations")
    return arrays


def domain_from_contract(contract):
    names = Domain.__dataclass_fields__
    return Domain(**{name: contract["domain"][name] for name in names})


def tensor6(D):
    return [float(D[0,0]), float(D[0,1]), float(D[1,1]), float(D[0,2]), float(D[1,2]), float(D[2,2])]


def unpack_eigensystem(x, fixed_f):
    R = Rotation.from_rotvec(x[3:6]).as_matrix()
    D = (R * (x[:3]*.001)) @ R.T
    return D, x[6], x[7] if fixed_f is None else fixed_f


def direct_tensor(q):
    return np.array([[q[0],q[1],q[3]], [q[1],q[2],q[4]], [q[3],q[4],q[5]]])*.001


def forward_eigensystem(x, b, g, fixed_f, d_iso):
    D, ratio, fraction = unpack_eigensystem(x, fixed_f)
    tissue = np.exp(-b*np.einsum("ni,ij,nj->n", g, D, g))
    return ratio*((1-fraction)*tissue + fraction*np.exp(-b*d_iso))


def forward_direct(x, b, g, fixed_f, d_iso):
    # Separately coded scalar quadratic form, not the eigensystem objective.
    gx, gy, gz = g.T
    q = .001*(x[0]*gx*gx + 2*x[1]*gx*gy + x[2]*gy*gy + 2*x[3]*gx*gz + 2*x[4]*gy*gz + x[5]*gz*gz)
    fraction = x[7] if fixed_f is None else fixed_f
    return x[6]*((1-fraction)*np.exp(-b*q) + fraction*np.exp(-b*d_iso))


def fit_once(y, b, g, algorithm, fixed_f, start, contract, deadline):
    domain = domain_from_contract(contract)
    scale = float(y[b == 0][0])
    target = y/scale
    calls = 0
    settings = contract["search"]
    d_iso = contract["model"]["isotropic_diffusivity"]
    def tick():
        nonlocal calls
        if time.monotonic() >= deadline:
            raise PilotStop("wall_cap")
        calls += 1
        if calls > settings["max_objective_calls_per_fit"]:
            raise RuntimeError("objective_call_cap")
    if algorithm == "trf_eigensystem":
        x0 = list(np.array(start["eigenvalues"])*1000) + start["rotvec"] + [start["S0_ratio"]]
        lo = [domain.eigenvalue_min*1000]*3 + [-np.pi]*3 + [domain.s0_ratio_min]
        hi = [domain.eigenvalue_max*1000]*3 + [np.pi]*3 + [domain.s0_ratio_max]
        if fixed_f is None:
            x0 += [start["free_f"]]; lo += [domain.fraction_min]; hi += [domain.fraction_max]
        def residual(x):
            tick()
            return forward_eigensystem(x,b,g,fixed_f,d_iso)-target
        result = least_squares(residual, x0, bounds=(lo,hi), **settings["trf"])
        D, ratio, fraction = unpack_eigensystem(result.x, fixed_f)
    elif algorithm == "slsqp_direct_tensor":
        R = Rotation.from_rotvec(start["rotvec"]).as_matrix()
        D0 = (R*np.array(start["eigenvalues"])) @ R.T
        x0 = list(np.array(tensor6(D0))*1000) + [start["S0_ratio"]]
        upper = domain.eigenvalue_max*1000
        bounds = [(0,upper),(-upper,upper),(0,upper),(-upper,upper),(-upper,upper),(0,upper),(domain.s0_ratio_min,domain.s0_ratio_max)]
        if fixed_f is None:
            x0 += [start["free_f"]]; bounds += [(domain.fraction_min,domain.fraction_max)]
        def objective(x):
            tick()
            return float(np.mean((forward_direct(x,b,g,fixed_f,d_iso)-target)**2))
        def inequalities(x):
            e = np.linalg.eigvalsh(direct_tensor(x))*1000
            return np.r_[e-domain.eigenvalue_min*1000, domain.eigenvalue_max*1000-e]
        result = minimize(objective, x0, method="SLSQP", bounds=bounds,
                          constraints=[{"type":"ineq", "fun":inequalities}], options=settings["slsqp"])
        D, ratio = direct_tensor(result.x), result.x[6]
        fraction = result.x[7] if fixed_f is None else fixed_f
    else:
        raise ValueError("unknown algorithm")
    params = {"D":tensor6(D), "S0":float(ratio*scale), "f":float(fraction)}
    row = {"parameters":params, "optimizer_success":bool(result.success), "optimizer_status":int(result.status), "message":str(result.message), "nfev_reported":int(result.nfev), "objective_calls":calls}
    try:
        metrics = candidate_metrics(y,b,g,params,domain)
        row.update(admissible=True, loss=metrics["loss"], fa=metrics["fa"], minimum_raw_eigenvalue=metrics["minimum_raw_eigenvalue"])
    except EvidenceError as exc:
        row.update(admissible=False, rejection=str(exc))
    e = np.linalg.eigvalsh(D)
    margin = settings["boundary_flag_fraction_of_parameter_span"]
    dtol = margin*(domain.eigenvalue_max-domain.eigenvalue_min)
    stol = margin*(domain.s0_ratio_max-domain.s0_ratio_min)
    ftol = margin*(domain.fraction_max-domain.fraction_min)
    row["boundary_diagnostics"] = {"minimum_eigenvalue":float(e.min()), "maximum_eigenvalue":float(e.max()), "S0_ratio":float(ratio), "tissue_signal_fraction":float(1-fraction),
        "eigenvalue_lower":bool(e.min() <= domain.eigenvalue_min+dtol), "eigenvalue_upper":bool(e.max() >= domain.eigenvalue_max-dtol),
        "S0_lower":bool(ratio <= domain.s0_ratio_min+stol), "S0_upper":bool(ratio >= domain.s0_ratio_max-stol),
        "f_lower":bool(fraction <= domain.fraction_min+ftol), "f_upper":bool(fraction >= domain.fraction_max-ftol)}
    return row


def sensitivity_summary(rows, contract, planned_pairs=None):
    groups = {key: [] for key in (planned_pairs or [])}
    for row in rows:
        groups.setdefault((tuple(row["ijk"]),row["protocol"]), []).append(row)
    out = []
    for (ijk, protocol), attempts in groups.items():
        candidates = [x for x in attempts if x.get("admissible")]
        best = min((x["loss"] for x in candidates), default=None)
        for budget in contract["sensitivity"]["added_squared_normalized_residual_budgets"]:
            ceiling = None if best is None else best + budget
            for view, upper in contract["sensitivity"]["fraction_views"].items():
                valid = [x for x in candidates if x["loss"] <= ceiling and x["parameters"]["f"] <= upper]
                state = "not_attempted" if not attempts else ("no_feasible_candidate" if not candidates else ("feasible_candidates_found" if valid else "no_candidates_in_view"))
                record = {"ijk":list(ijk),"protocol":protocol,"budget":budget,"loss_ceiling":ceiling,"view":view,"n_candidates":len(valid),"best_found_loss_full_pool":best,"status":state,"n_attempted":len(attempts),"n_feasible_full_pool":len(candidates)}
                if valid:
                    low, high = min(valid,key=lambda x:x["fa"]), max(valid,key=lambda x:x["fa"])
                    record.update(fa_separation_lower_bound=high["fa"]-low["fa"], left_candidate=low["attempt_id"],right_candidate=high["attempt_id"])
                else:
                    record.update(fa_separation_lower_bound=None,left_candidate=None,right_candidate=None)
                out.append(record)
    return out


def run_pilot(arrays, contract, output_dir):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    selected = select_indices(arrays["ref_roi_ijk"], contract["selection"]["n_voxels"])
    started = time.monotonic()
    deadline = started + contract["resources"]["wall_seconds"]
    rows, status = [], "completed_bounded_pilot"
    selection = {"indices":selected.tolist(),"coordinates":arrays["ref_roi_ijk"][selected].tolist(),"method":contract["selection"]["method"]}
    (output/"selection.json").write_text(json.dumps(selection,indent=2)+"\n")
    try:
        with (output/"attempts.jsonl").open("x") as stream:
            for index in selected:
                for protocol, shells in contract["protocols"].items():
                    mask = np.isin(arrays["ref_bvals"], shells)
                    y, b, g = arrays["ref_signal"][index,mask], arrays["ref_bvals"][mask], arrays["ref_bvecs"][mask]
                    for fraction in [None]+contract["search"]["profile_f"]:
                        for start_id, start in enumerate(contract["search"]["starts"]):
                            for algorithm in contract["search"]["algorithms"]:
                                if len(rows) >= contract["search"]["max_fits"]:
                                    raise PilotStop("fit_cap")
                                if time.monotonic() >= deadline:
                                    raise PilotStop("wall_cap")
                                row = {"attempt_id":len(rows),"ijk":arrays["ref_roi_ijk"][index].tolist(),"source_index":int(index),"protocol":protocol,"fixed_f":fraction,"start_id":start_id,"algorithm":algorithm}
                                try:
                                    row.update(fit_once(y,b,g,algorithm,fraction,start,contract,deadline))
                                except PilotStop as exc:
                                    row.update(admissible=False,error_type="PilotStop",error=str(exc),attempt_aborted=True)
                                    rows.append(row)
                                    stream.write(json.dumps(row,allow_nan=False)+"\n"); stream.flush()
                                    raise
                                except Exception as exc:
                                    row.update(admissible=False,error_type=type(exc).__name__,error=str(exc))
                                rows.append(row)
                                stream.write(json.dumps(row,allow_nan=False)+"\n"); stream.flush()
                                if stream.tell() > contract["resources"]["max_output_bytes"]:
                                    raise PilotStop("output_cap")
    except PilotStop as exc:
        status = "partial_"+str(exc)
    planned_pairs = [(tuple(arrays["ref_roi_ijk"][index].tolist()), protocol) for index in selected for protocol in contract["protocols"]]
    report = {"status":status,"elapsed_seconds":time.monotonic()-started,"n_attempts":len(rows),"n_admissible":sum(bool(x.get("admissible")) for x in rows),"n_optimizer_success":sum(bool(x.get("optimizer_success")) for x in rows),"selection":selection,"sensitivity":sensitivity_summary(rows,contract,planned_pairs),"claim":contract["interpretation"]}
    (output/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract",type=Path,default=Path(__file__).with_name("pilot_contract.json"))
    parser.add_argument("--execute",action="store_true")
    parser.add_argument("--approval",type=Path)
    for name in ("bank","receipt","report","manifest","preprocessing","raw-source","output"):
        parser.add_argument("--"+name,type=Path)
    args = parser.parse_args()
    contract = json.loads(args.contract.read_text())
    if not args.execute:
        print(json.dumps({"status":"plan_only_no_source_loaded","contract_sha256":sha256(args.contract),"resources":contract["resources"],"max_fits":contract["search"]["max_fits"]},indent=2))
        return
    if any(getattr(args,name) is None for name in ("approval","bank","receipt","report","manifest","preprocessing","raw_source","output")):
        parser.error("execution requires approval and all explicitly named source/output paths")
    verify_approval(json.loads(args.approval.read_text()),args.contract)
    verify_runtime(contract)
    arrays = authenticate_source({name:getattr(args,name) for name in ("bank","receipt","report","manifest","preprocessing","raw_source")},contract)
    result = run_pilot(arrays,contract,args.output)
    print(json.dumps({key:result[key] for key in ("status","elapsed_seconds","n_attempts","n_admissible")}))


if __name__ == "__main__":
    main()
