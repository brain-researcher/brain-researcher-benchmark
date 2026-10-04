"""Bounded source/support pilot stages. No FC, eigensolve or model invocation."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys

import numpy as np
from scipy import linalg

sys.path.insert(0, "/legacy")
import core
import source_reader as reader
from protocol import discovery_support, evaluation_eligibility, metadata_split


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+"\n")


def allowed_rows(manifest, people):
    people = set(people)
    return [row for row in manifest["files"]
            if row.get("participant_id") is None or row["participant_id"] in people]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def authenticate_capsule(root, manifest, people):
    """No full-source fallback; exact closed capsule inventory and pinned bytes."""
    rows = allowed_rows(manifest, people)
    expected = {row["path"] for row in rows} | {"source_manifest.json"}
    observed = set()
    for item in root.rglob("*"):
        require(not item.is_symlink(), "symlink in source capsule")
        if item.is_file():
            observed.add(item.relative_to(root).as_posix())
        else:
            require(item.is_dir(), "special source member")
    require(observed == expected, "source capsule inventory not exact allowlist")
    hashes = {}
    for row in rows:
        reader.read_member(root, row)
        hashes[row["path"]] = row["sha256"]
    return hashes


def no_bandpass_activity(raw, confounds, geometry):
    """Public inherited cleaning branch; deliberately no filtering or FC."""
    require(raw.shape == (168, 400) and confounds.shape == (168, 15), "source dimensions")
    require(np.isfinite(raw[:, geometry]).all() and np.isnan(raw[:, ~geometry]).all(),
            "source geometry/finite disagreement")
    require(np.isfinite(confounds).all(), "nonfinite selected confound")
    c = core.detrend(confounds)
    c -= np.mean(c, axis=0)
    sd = np.std(c, axis=0, ddof=0)
    sd[sd < core.EPS] = 1
    c /= sd
    q, r, _ = linalg.qr(c, mode="economic", pivoting=True)
    q = q[:, np.abs(np.diag(r)) > 100*core.EPS]
    cleaned = np.full_like(raw, np.nan)
    y = core.detrend(raw[:, geometry])
    y -= q @ (q.T @ y)
    cleaned[:, geometry] = y
    rows, active = [], np.zeros(400, dtype=bool)
    for index in range(400):
        if geometry[index]:
            raw_sd = core.norm(core.centered(raw[:, index])) / math.sqrt(167)
            threshold = 1e-12 * math.sqrt(168) * max(1, raw_sd)
            residual = core.norm(core.centered(cleaned[:, index]))
            active[index] = residual > threshold
            row = dict(parcel_id=index+1, geometry=True, raw_sample_sd=raw_sd,
                       residual_centered_l2=residual, activity_threshold=threshold,
                       active=bool(active[index]))
        else:
            row = dict(parcel_id=index+1, geometry=False, raw_sample_sd=None,
                       residual_centered_l2=None, activity_threshold=None, active=False)
        rows.append(row)
    return rows, active, int(q.shape[1])


def stage_isolation(root, manifest, opposite, *, fit_path=None):
    probes = []
    require(os.getuid() != 0, "pilot stages must be nonroot")
    for row in manifest["files"]:
        if row.get("participant_id") not in set(opposite):
            continue
        for path in (root/row["path"], Path("/app/data/gradient")/row["path"]):
            try:
                with path.open("rb") as handle:
                    handle.read(1)
            except (FileNotFoundError, PermissionError):
                probes.append({"path": str(path), "read_denied": True})
            else:
                raise ValueError(f"opposite partition readable: {path}")
    require(not list(Path("/opt/source_capture").iterdir()), "baked capture not covered")
    require(not list(Path("/app").iterdir()), "baked app source not covered")
    readonly = None
    if fit_path is not None:
        try:
            fd = os.open(fit_path, os.O_WRONLY)
        except OSError as exc:
            require(exc.errno in (13, 30), "unexpected fit-artifact write probe failure")
            readonly = True
        else:
            os.close(fd)
            raise ValueError("frozen fit artifact is writable")
    return {"uid": os.getuid(), "gid": os.getgid(), "opposite_read_probes": probes,
            "baked_app_covered": True, "baked_capture_covered": True,
            "frozen_fit_write_denied": readonly}


def authenticate_and_stage(contract, out):
    inputs = reader.authenticate("/app/data/gradient", "/app/method_contract.json",
                                 "/app/output_schema.json")
    manifest = inputs["manifest"]
    cols, rows = reader.table(reader.read_member(inputs["root"], reader.member(inputs, "participants")), "\t")
    by_id = {row["participant_id"]: row for row in rows}
    require(len(by_id) == len(rows), "duplicate source participant metadata")
    people = inputs["method"]["source"]["participant_ids"]
    selected = [{"participant_id": sid, "age": float(by_id[sid]["Age"]),
                 "child_adult": by_id[sid]["Child_Adult"]} for sid in people]
    split = metadata_split(selected)
    require(split == {key: contract["cohort"][key] for key in split}, "metadata split differs")
    manifest_raw = (inputs["root"]/"source_manifest.json").read_bytes()
    for stage, key in (("fit", "discovery"), ("evaluate", "evaluation")):
        capsule = out / "capsules" / stage
        capsule.mkdir(parents=True, exist_ok=False)
        (capsule/"source_manifest.json").write_bytes(manifest_raw)
        for row in allowed_rows(manifest, split[key]):
            target = capsule / row["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(reader.read_member(inputs["root"], row))
        authenticate_capsule(capsule, manifest, split[key])
    reader.reauthenticate(inputs, "/app/method_contract.json", "/app/output_schema.json")
    receipt = {"stage": "authenticate", "source_files_authenticated": len(manifest["files"]),
               "identity": inputs["identity"], "metadata": selected, "split": split,
               "new_signal_analysis": False, "all_source_hashes": {r["path"]: r["sha256"] for r in manifest["files"]}}
    json_write(out/"authentication.json", receipt)
    return receipt


def source_support_stage(stage, contract, root, out):
    manifest_raw = (root/"source_manifest.json").read_bytes()
    require(hashlib.sha256(manifest_raw).hexdigest() == contract["source_manifest_sha256"], "source manifest pin")
    manifest = json.loads(manifest_raw)
    key, other = ("discovery", "evaluation") if stage == "fit" else ("evaluation", "discovery")
    people, opposite = contract["cohort"][key], contract["cohort"][other]
    hashes = authenticate_capsule(root, manifest, people)
    fit_path = Path("/frozen/fit.json") if stage == "evaluate" else None
    isolation = stage_isolation(root, manifest, opposite, fit_path=fit_path)
    method = json.loads(Path("/public/method_contract.json").read_text())
    inputs = {"root": root, "manifest": manifest, "method": method}
    common = reader.load_common(inputs)
    all_active, person_rows = [], []
    for sid in people:
        br, cr = reader.member(inputs, "bold", sid), reader.member(inputs, "confounds", sid)
        bold, affine, header = reader.decode_image(reader.read_member(root, br), br["path"].endswith(".gz"), 4)
        require(bold.shape == (50, 59, 50, 168), "unexpected original BOLD shape")
        columns, records = reader.table(reader.read_member(root, cr), "\t")
        require(len(records) == 168 and set(core.CONFOUNDS) <= set(columns), "nuisance source structure")
        confounds = np.array([[float(row[name]) for name in core.CONFOUNDS] for row in records])
        indices = reader.support(common["atlas"], common["atlas_affine"], bold.shape[:3], affine)
        raw = np.full((168, 400), np.nan)
        for frame in range(168):
            volume = bold[..., frame].ravel(order="C")
            for parcel, idx in enumerate(indices):
                if len(idx):
                    raw[frame, parcel] = np.mean(np.ascontiguousarray(volume[idx], dtype=np.float64), dtype=np.float64)
        geometry = np.array([len(idx) > 0 for idx in indices], dtype=bool)
        diagnostics, active, rank = no_bandpass_activity(raw, confounds, geometry)
        for row, idx in zip(diagnostics, indices):
            row.update(n_voxels=len(idx), support_sha256=hashlib.sha256(np.asarray(idx, dtype="<i8").tobytes()).hexdigest())
        person_rows.append({"participant_id": sid, "header": header, "nuisance_rank": rank,
                            "n_geometry": int(geometry.sum()), "n_active": int(active.sum()),
                            "parcel_diagnostics": diagnostics})
        all_active.append(active)
        del bold, raw
        print(json.dumps({"progress": stage, "participant_id": sid, "active": int(active.sum())}), flush=True)
    active_matrix = np.asarray(all_active)
    receipt = {"stage": stage, "people": person_rows, "source_hashes": hashes,
               "isolation": isolation, "source_manifest_sha256": contract["source_manifest_sha256"],
               "scope": "support and eligibility only; no FC/gradients/endpoints",
               "spatial_limit": contract["scientific_scope"]["spatial_limit"]}
    if stage == "fit":
        support = discovery_support(active_matrix)
        labels = [row["network"] for row in common["labels"]]
        coverage = {network: {"source": labels.count(network),
                             "retained": sum(bool(flag) and lab == network for flag, lab in zip(support, labels))}
                    for network in core.NETWORKS}
        require(support.any() and all(row["retained"] > 0 for row in coverage.values()), "empty discovery/network support")
        receipt.update(discovery_ids=people, frozen_support=support.tolist(),
                       retained_source_parcel_ids=(np.flatnonzero(support)+1).tolist(), network_coverage=coverage)
    else:
        frozen_raw = fit_path.read_bytes()
        require(hashlib.sha256(frozen_raw).hexdigest() == os.environ["FIT_SHA256"], "frozen fit hash mismatch")
        frozen = json.loads(frozen_raw)
        require(frozen["discovery_ids"] == opposite, "wrong frozen discovery cohort")
        support = np.asarray(frozen["frozen_support"], dtype=bool)
        eligible = evaluation_eligibility(active_matrix, support)
        receipt.update(frozen_fit_sha256=hashlib.sha256(frozen_raw).hexdigest(),
                       n_expected=len(people), n_eligible=int(eligible.sum()),
                       eligibility=[{"participant_id": sid, "eligible": bool(ok),
                                     "inactive_on_frozen_support": (np.flatnonzero(support & ~active)+1).tolist()}
                                    for sid, ok, active in zip(people, eligible, active_matrix)])
    require(authenticate_capsule(root, manifest, people) == hashes, "capsule changed")
    json_write(out/f"{stage}.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["authenticate", "fit", "evaluate"])
    args = parser.parse_args()
    contract = json.loads(Path("/pilot/pilot_contract.json").read_text())
    for name, pin in contract["pilot_code_sha256"].items():
        require(digest(Path("/pilot")/name) == pin, "reviewed pilot code pin mismatch")
    for name, pin in contract["legacy_code_sha256"].items():
        require(digest(Path("/legacy")/name) == pin, "legacy numerical code pin mismatch")
    require(digest("/pilot/protocol.py") == contract["protocol_sha256"], "protocol pin mismatch")
    require(digest("/public/method_contract.json") == contract["method_sha256"], "method pin mismatch")
    require(digest("/public/output_schema.json") == contract["schema_sha256"], "schema pin mismatch")
    out = Path("/out")
    if args.stage == "authenticate":
        authenticate_and_stage(contract, out)
    else:
        source_support_stage(args.stage, contract, Path("/source"), out)


if __name__ == "__main__":
    main()
