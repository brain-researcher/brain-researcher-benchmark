"""Shared public experiment orchestration, with separately implemented arithmetic.

Sharing identity/schema/order policy is explicit; the checker reconstructs each
source image and every numerical operation through phase2_independent instead.
"""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, "/legacy")
import source_reader as reader
from pilot_support import authenticate_capsule, stage_isolation
from protocol import metadata_split

GAP = 4e-8


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_partition(stage, base, engine, root=Path("/source")):
    source_raw = (root/"source_manifest.json").read_bytes()
    require(hashlib.sha256(source_raw).hexdigest() == base["source_manifest_sha256"], "source manifest pin")
    manifest = json.loads(source_raw)
    partition = "discovery" if stage == "fit" else "evaluation"
    opposite = "evaluation" if stage == "fit" else "discovery"
    people = base["cohort"][partition]
    hashes = authenticate_capsule(root, manifest, people)
    isolation = stage_isolation(root, manifest, base["cohort"][opposite],
                                fit_path=Path("/frozen/fit.json") if stage == "evaluate" else None)
    def row(role, person=None):
        found = [r for r in manifest["files"] if r["role"] == role and r.get("participant_id") == person]
        require(len(found) == 1, "exact source role/participant join")
        return found[0]
    def raw(role, person=None):
        return reader.read_member(root, row(role, person))
    _, all_metadata = reader.table(raw("participants"), "\t")
    by_id = {r["participant_id"]: r for r in all_metadata}
    require(len(by_id) == len(all_metadata), "duplicate source participant")
    ids = base["cohort"]["discovery"]+base["cohort"]["evaluation"]
    records = [{"participant_id": p, "age": float(by_id[p]["Age"]),
                "child_adult": by_id[p]["Child_Adult"]} for p in ids]
    split = metadata_split(records)
    require(split == {k: base["cohort"][k] for k in split}, "source-derived fixed split mismatch")
    labels = reader.parse_lut(raw("atlas_labels"))
    parcel_ids = np.array([r["parcel_id"] for r in labels])
    atlas, atlas_affine, _ = engine.decode(raw("atlas_image"), row("atlas_image")["path"].endswith(".gz"), 3)
    nuisance_names = json.loads(Path("/public/method_contract.json").read_text())["cleaning"]["confounds"]
    loaded = []
    for pid in people:
        bold, affine, metadata = engine.decode(raw("bold", pid), True, 4)
        require(bold.shape == (50, 59, 50, 168), "fixed BOLD dimensions")
        fields, confound_rows = reader.table(raw("confounds", pid), "\t")
        require(len(confound_rows) == 168 and set(nuisance_names) <= set(fields), "nuisance inventory")
        confounds = np.array([[float(r[n]) for n in nuisance_names] for r in confound_rows])
        require(np.isfinite(confounds).all(), "nonfinite selected nuisance")
        means, counts = engine.extract(bold, affine, atlas, atlas_affine, parcel_ids)
        person = engine.clean(means, confounds, counts)
        person.update(participant_id=pid, raw=means, header=metadata)
        loaded.append(person)
        del bold
        print(json.dumps({"stage": stage, "path": engine.__name__, "person": pid,
                          "active": int(person["active"].sum())}), flush=True)
    require(authenticate_capsule(root, manifest, people) == hashes, "source changed during reconstruction")
    return loaded, labels, {"source_hashes": hashes, "isolation": isolation, "split": split}


def fit_axis_valid(spec):
    return spec["stationary_gap"] > GAP and spec["principal_gap"] > GAP


def spectral_receipt(spec):
    return {"leading_eigenvalue": float(spec["values"][0]),
            "principal_gap": spec["principal_gap"], "stationary_gap": spec["stationary_gap"],
            "leading_block_dimension": spec["block"]}


def embed(fc, parcel_ids, labels, engine):
    k, stationary, membership = engine.operator(fc, parcel_ids)
    spec = engine.spectral(k, stationary)
    summary = spectral_receipt(spec)
    summary["network_C"] = engine.network_range(spec, stationary, labels)
    return summary, {"fc": fc, "operator": k, "stationary": stationary,
                     "sparsity": membership, "eigenvalues": spec["values"],
                     "leading_basis": spec["vectors"][:, :spec["block"]]}, spec


def compute(stage, people, labels, engine, frozen=None):
    """Recipe dispatch only. Arrays are private QA, not future required outputs."""
    ids = [p["participant_id"] for p in people]
    active = np.array([p["active"] for p in people])
    support = active.all(axis=0) if stage == "fit" else np.asarray(frozen["frozen_support"], dtype=bool)
    require(support.shape == (400,) and support.any(), "frozen support dimensions")
    all_networks = [r["network"] for r in labels]
    networks = np.asarray(all_networks)[support]
    require(set(networks) == set(all_networks), "all networks must remain represented")
    parcel_ids = np.array([r["parcel_id"] for r in labels])[support]
    arrays, rows, fcs = {}, [], []
    for person in people:
        pid = person["participant_id"]
        for key in ("raw", "clean", "counts", "active", "raw_sd", "residual_norm", "threshold"):
            arrays[f"{pid}:{key}"] = person[key]
        invalid = (np.flatnonzero(support & ~person["active"])+1).tolist()
        record = {"participant_id": pid, "partition": "discovery" if stage == "fit" else "evaluation",
                  "nuisance_rank": int(person["rank"]), "inactive_on_frozen_support": invalid,
                  "source_status": "source_inactive" if invalid else "defined"}
        if invalid:
            require(stage == "evaluate", "discovery intersection violated")
            record.update(transfer={"status": "source_inactive", "fraction": None},
                          spectrum=None, network_C={"status": "source_inactive", "lower": None, "upper": None})
        else:
            fc = engine.correlation(person["clean"][:, support])
            summary, numerical, spec = embed(fc, parcel_ids, networks, engine)
            for key, value in numerical.items():
                arrays[f"{pid}:{key}"] = value
            record.update(spectrum={k: v for k, v in summary.items() if k != "network_C"}, network_C=summary["network_C"])
            if stage == "fit":
                fcs.append(fc)
            elif frozen["axis_status"] != "defined":
                record["transfer"] = {"status": "discovery_axis_unresolved", "fraction": None}
            else:
                axis = np.asarray(frozen["discovery_axis"])
                record["transfer"] = engine.transfer(axis, numerical["operator"], numerical["stationary"], spec,
                                                      frozen["discovery_spectrum"]["principal_gap"])
        rows.append(record)
    report = {"schema_version": f"gradient-phase2-{stage}-v1", "people": rows,
              "frozen_support": support.tolist(), "parcel_ids": parcel_ids.tolist(),
              "network_labels": networks.tolist(), "n_expected": len(people)}
    if stage == "fit":
        group_fc = np.mean(fcs, axis=0)
        group_fc = np.triu(group_fc, 1)+np.triu(group_fc, 1).T+np.eye(len(group_fc))
        summary, numerical, spec = embed(group_fc, parcel_ids, networks, engine)
        for key, value in numerical.items():
            arrays[f"discovery:{key}"] = value
        valid = fit_axis_valid(spec)
        report.update(discovery_ids=ids, axis_status="defined" if valid else "discovery_axis_unresolved",
                      discovery_axis=spec["vectors"][:, 0].tolist() if valid else None,
                      discovery_spectrum={k: v for k, v in summary.items() if k != "network_C"},
                      discovery_network_C=summary["network_C"], leave_one_out=[])
        for i, omitted in enumerate(ids):
            loo_fc = np.mean([fc for j, fc in enumerate(fcs) if j != i], axis=0)
            loo_fc = np.triu(loo_fc, 1)+np.triu(loo_fc, 1).T+np.eye(len(loo_fc))
            k, s, selection = engine.operator(loo_fc, parcel_ids)
            loo = engine.spectral(k, s)
            eligible = valid and fit_axis_valid(loo)
            report["leave_one_out"].append({"omitted_participant": omitted,
                "principal_gap": loo["principal_gap"], "stationary_gap": loo["stationary_gap"],
                "squared_axis_overlap": float((spec["vectors"][:, 0]@loo["vectors"][:, 0])**2) if eligible else None,
                "status": "defined" if eligible else "axis_unresolved"})
            arrays[f"loo:{omitted}:sparsity"] = selection
    else:
        values = [r["transfer"]["fraction"] for r in rows if r["transfer"]["status"] == "defined"]
        report.update(n_defined=len(values), mean_fraction=float(np.mean(values)) if values else None,
                      minimum_fraction=min(values) if values else None, maximum_fraction=max(values) if values else None,
                      leave_one_valid_person_mean_range=([float(min(np.mean(values[:i]+values[i+1:]) for i in range(len(values)))),
                                                        float(max(np.mean(values[:i]+values[i+1:]) for i in range(len(values))))]
                                                       if len(values) > 1 else None))
    return report, arrays
