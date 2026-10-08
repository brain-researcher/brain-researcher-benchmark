"""Regenerate the numeric calibration fixtures (calibration/fixtures/num-*/) from _base/.

Each fixture changes the oracle's outputs in one way, to show that the compute checks in
tests/test_outputs.py catch it (or, for the alternative pipelines, accept it):

  num-user-tamper          every roi_conflict = 0, group ROI mean 987 / t 123, no run_metadata.json
  num-missing-metadata     run_metadata.json deleted
  num-duplicate-subject    one row relabelled as another listed participant
  num-shuffled-labels      participant labels permuted across rows
  num-shuffled-roi         roi_conflict permuted (group statistics unchanged by construction)
  num-sign-flipped         congruent - incongruent instead of incongruent - congruent
  num-group-other-model    group ROI statistics taken from a different target model than the CSV
  num-alt-pipeline         nilearn FirstLevelModel, glover HRF, mid-TR, AR(1), raw units, own metadata schema
  num-naive-frame-times    the same with nilearn's default slice_time_ref = 0

    python ANTCONFLICT-001/calibration/make_numeric_fixtures.py
"""
import csv
import json
import math
from pathlib import Path

import numpy as np
from scipy import stats

HERE = Path(__file__).resolve().parent
TASK = HERE.parent
FX = HERE / "fixtures"
BASE = FX / "_base"


def read_rows():
    with open(BASE / "subjects.csv", newline="") as f:
        return list(csv.DictReader(f))


def write_rows(d, rows):
    with open(d / "subjects.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def one_sample(x):
    x = np.asarray(x, float)
    t, p = stats.ttest_1samp(x, 0.0)
    return {"mean": float(x.mean()), "t": float(t), "p": float(p), "n": int(len(x))}


def group(rows, roi=None):
    g = json.loads((BASE / "group_results.json").read_text())
    g = {k: v for k, v in g.items() if k != "time_on_task_check"}
    g["roi_conflict"] = one_sample([float(r["roi_conflict"]) for r in rows]) if roi is None else roi
    g["rt_conflict_ms"] = one_sample([float(r["rt_incongruent_ms"]) - float(r["rt_congruent_ms"]) for r in rows])
    g["n_subjects"] = len(rows)
    return g


def fixture(name, note, expect, rows=None, group_results=None, metadata=None, remove=()):
    d = FX / name
    d.mkdir(exist_ok=True)
    for f in d.iterdir():
        f.unlink()
    (d / "findings.md").write_bytes((FX / "reference/findings.md").read_bytes())  # prose held fixed
    if rows is not None:
        write_rows(d, rows)
    if group_results is not None:
        (d / "group_results.json").write_text(json.dumps(group_results, indent=2, sort_keys=True))
    if metadata is not None:
        (d / "run_metadata.json").write_text(json.dumps(metadata, indent=2))
    lines = [f"note = {json.dumps(note)}"]
    if remove:
        lines.append(f"remove = {json.dumps(list(remove))}")
    lines.append("[expect]")
    lines += [f'{json.dumps(k) if k == "*" else k} = "{v}"' for k, v in expect.items()]
    (d / "expect.toml").write_text("\n".join(lines) + "\n")


def main():
    base = read_rows()
    rng = np.random.default_rng(20261008)
    MD, BEH, ROI, JUDGE = ("test_required_outputs_and_metadata", "test_participants_and_behaviour",
                           "test_dacc_contrast_computed", "test_reproduction_recognises_time_on_task")

    rows = [{**r, "roi_conflict": "0"} for r in base]
    g = json.loads((BASE / "group_results.json").read_text())
    g["roi_conflict"]["mean"], g["roi_conflict"]["t"] = 987, 123
    fixture("num-user-tamper", "numeric tamper reported in review (2026-10-08): original behaviour kept, every "
            "roi_conflict set to 0, group ROI mean 987 and t 123, run_metadata.json deleted; v1 verifier passed it",
            {MD: "fail", BEH: "pass", ROI: "fail", JUDGE: "pass"}, rows, g, remove=["run_metadata.json"])

    fixture("num-missing-metadata", "numeric, synthetic: run_metadata.json deleted, everything else the oracle's",
            {MD: "fail", BEH: "pass", ROI: "pass", JUDGE: "pass"}, remove=["run_metadata.json"])

    rows = [dict(r) for r in base]
    rows[-1]["subject"] = rows[-2]["subject"]
    fixture("num-duplicate-subject", "numeric, synthetic: the last row relabelled as the participant above it",
            {BEH: "fail"}, rows, group(rows))

    perm = rng.permutation(len(base))
    rows = [{**r, "subject": base[j]["subject"]} for r, j in zip(base, perm)]
    fixture("num-shuffled-labels", "numeric, synthetic: participant labels permuted across rows (the data no longer "
            "belong to the participant named)", {BEH: "fail"}, rows, group(rows))

    perm = rng.permutation(len(base))
    rows = [{**r, "roi_conflict": base[j]["roi_conflict"]} for r, j in zip(base, perm)]
    fixture("num-shuffled-roi", "numeric, synthetic: roi_conflict permuted across participants; group mean and t "
            "are unchanged, so only the subject-level imaging check can catch it",
            {MD: "pass", BEH: "pass", ROI: "fail"}, rows, group(rows))

    rows = [{**r, "roi_conflict": repr(-float(r["roi_conflict"]))} for r in base]
    fixture("num-sign-flipped", "numeric, synthetic: congruent - incongruent written instead of incongruent - congruent",
            {MD: "pass", BEH: "pass", ROI: "fail"}, rows, group(rows))

    impulse = json.loads((BASE / "group_results.json").read_text())["time_on_task_check"]["roi_conflict_by_target_model"]["std_impulse"]
    fixture("num-group-other-model", "numeric, synthetic: subjects.csv has the 2 s correct-trial model, but the group "
            "ROI test reported is the impulse model's", {MD: "pass", BEH: "pass", ROI: "fail"},
            group_results=group(base, roi={k: impulse[k] for k in ("mean", "t", "p")}))

    alt = {r["subject"]: r for r in csv.DictReader(open(TASK / "step0/outputs/alt_pipeline_subjects.csv"))}
    for name, col, note in (
            ("num-alt-pipeline", "glover_str0.5", "numeric, alternative pipeline (step0/alt_pipeline_check.py): nilearn "
             "FirstLevelModel on events.tsv, glover HRF, slice_time_ref 0.5, AR(1), no signal scaling (raw units); "
             "different run_metadata schema. A defensible alternative: all compute checks must pass"),
            ("num-naive-frame-times", "glover_str0", "numeric, alternative pipeline: as num-alt-pipeline but with nilearn's "
             "default slice_time_ref = 0 (ignores the instruction's mid-TR note; face-value t = -0.31). Kept passing the "
             "compute checks: the imaging values are still the contrast on these data")):
        rows = [{**r, "roi_conflict": alt[r["subject"]][col]} for r in base]
        meta = {"dataset": "OpenNeuro ds001907 (AFNI derivatives)", "participants": len(rows),
                "participant_ids": [r["subject"].removeprefix("sub-") for r in rows], "session": "ses-1",
                "runs": "run-1, run-2",
                "model": f"nilearn FirstLevelModel, glover HRF, slice_time_ref={col.split('str')[1]}, AR(1), cosine drift "
                         "0.01 Hz, events.tsv as shipped (TargetErr/CueErr separate), contrast Incongruent - Congruent "
                         "effect size averaged in a 10 mm sphere at (0, 16, 42)"}
        fixture(name, note, {"*": "pass"}, rows, group(rows), metadata=meta)
    print("wrote", sorted(p.name for p in FX.glob("num-*")))


if __name__ == "__main__":
    main()
