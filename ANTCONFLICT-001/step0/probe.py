"""Step-0 probe for ANTCONFLICT-001: a throwaway script, NOT the oracle.

Claim (Fan et al. 2005, NeuroImage 26:471, doi 10.1016/j.neuroimage.2005.02.004): the ANT
executive/conflict contrast (incongruent - congruent flanker) activates the dorsal anterior
cingulate / posterior medial frontal cortex (dACC/pMFC).

Lever (un-cued in the task): time on task. Incongruent trials are slower, and a GLM whose
target regressors have a fixed duration cannot tell "conflict" from "longer
processing". Grinband et al. 2011 (NeuroImage 57:303) argue the dMFC congruency effect is
time on task; Yeung, Cohen & Botvinick 2011 dispute it. Mumford et al. 2023 (bioRxiv,
"response time paradox") recommend a constant-duration + RT-modulator model.

Measured here on OpenNeuro ds001907 AFNI derivatives (MNI 2 mm, nuisance-regressed,
blurred), healthy-aging group (sub-RC41*), session 1, runs 1-2. Trial-level RT/accuracy
come from derivatives/ANT-eprime-export.zip via step0/eprime_events.py (exact match to the
six subjects' derivative events.tsv); RC4114 has no session-1 E-Prime log, so n = 24:
  RAW      incongruent - congruent in a 10 mm sphere at MNI (0, 16, 42), with three
           standard target models (all trials / correct-only / impulse)
  PREMISE  behavioural conflict effect: RT(incongruent) - RT(congruent)
  CTRL     the same contrast with RT modelled: (a) RT-duration epochs, (b) RT parametric
           modulator on constant-duration targets
  NEG-CTRL task-positive response (all targets vs baseline) in the same pipeline

    DS001907_DIR=/path/to/ds001907 EPRIME_DIR=/path/to/RC4-ANT-1 \
        python step0/probe.py 2>&1 | tee step0/run.log
    # variant: naive frame times (no slice-timing offset) -> outputs/*_frame_offset0.*
    FRAME_OFFSET=0 DS001907_DIR=... EPRIME_DIR=... python step0/probe.py > step0/run_frame_offset0.log 2>&1
    # superseded v1 scaling (each regressor divided by its own peak); reproduces step0/superseded/v1_per_regressor_peak/
    SCALING=per_regressor_peak PROBE_OUT=/tmp/v1 DS001907_DIR=... EPRIME_DIR=... python step0/probe.py
    # second Step-0 attempt on all six session-1 runs (step0/runs1to6_decision_rule.md) -> outputs/*_runs1-6.*
    RUNS=1,2,3,4,5,6 DS001907_DIR=... EPRIME_DIR=... python step0/probe.py > step0/run_runs1-6.log 2>&1

Models and regressor scaling live in step0/probe_models.py. v2 (current) puts every task
regressor of a model on one scale, so the +1/-1 contrast compares like with like.
"""
import json
import os
import sys
import time
import warnings
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
from nilearn import datasets, image
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eprime_events import subject_events, validate  # noqa: E402
from probe_models import MODELS, TARGETS, TR, design  # noqa: E402

warnings.filterwarnings("ignore")
DATA = Path(os.environ.get("DS001907_DIR", "ds001907"))
EPRIME = Path(os.environ.get("EPRIME_DIR", DATA / "derivatives/RC4-ANT-1"))
# AFNI 3dTshift (the "tshift" block) aligns every slice to the mean slice time, so volume i is
# sampled at (i + 0.5) * TR. FRAME_OFFSET=0 reproduces the naive i * TR grid (recorded variant).
FRAME_OFFSET = float(os.environ.get("FRAME_OFFSET", TR / 2))
# Regressor scaling (step0/probe_models.py). "common" is current; "per_regressor_peak" reproduces
# the superseded v1 run (step0/superseded/v1_per_regressor_peak/), whose +1/-1 contrast compared
# betas on different scales (step0/scaling_check.py).
SCALING = os.environ.get("SCALING", "common")
OUT = Path(os.environ.get("PROBE_OUT", Path(__file__).resolve().parent / "outputs"))
OUT.mkdir(parents=True, exist_ok=True)
SUBJECTS = [f"RC41{n:02d}" for n in (1, 3, 6, 7, 9, 10, 11, 12, 13, 15, 16, 17, 18, 19, 20,
                                     21, 22, 23, 25, 26, 28, 29, 30, 31)]   # RC4114: no E-Prime log
if os.environ.get("SUBJECTS"):  # smoke tests only; the recorded run uses all 25
    SUBJECTS = os.environ["SUBJECTS"].split(",")
RUNS = [int(r) for r in os.environ.get("RUNS", "1,2").split(",")]
TAG = (("" if FRAME_OFFSET == TR / 2 else f"_frame_offset{FRAME_OFFSET:g}") + ("" if SCALING == "common" else f"_{SCALING}")
       + ("" if RUNS == [1, 2] else f"_runs{RUNS[0]}-{RUNS[-1]}"))
ROI_XYZ, ROI_RADIUS = (0.0, 16.0, 42.0), 10.0
TASKPOS_XYZ = (0.0, -90.0, 0.0)          # occipital pole, all-targets negative control


def sphere_mask(img, xyz, radius):
    ijk = np.indices(img.shape[:3]).reshape(3, -1).T
    mm = nib.affines.apply_affine(img.affine, ijk)
    return (np.linalg.norm(mm - np.array(xyz), axis=1) <= radius).reshape(img.shape[:3])



t0 = time.time()
validate(EPRIME, DATA)
mni = datasets.load_mni152_brain_mask(resolution=2)
rows, maps, beh = [], {m: [] for m in MODELS}, []
grid = None
for sub in SUBJECTS:
    sub_eff = {m: [] for m in MODELS}
    sub_pos = []
    sub_ev = subject_events(EPRIME, sub)
    for run in RUNS:
        bold = DATA / f"derivatives/sub-{sub}/ses-1/func/sub-{sub}_ses-1_task-ANT_run-{run}_bold.nii.gz"
        if not bold.exists() or run not in sub_ev:
            print(f"missing {sub} run-{run}", flush=True)
            continue
        img = nib.load(bold)
        if grid is None:
            grid = img
            brain = image.resample_to_img(mni, img, interpolation="nearest").get_fdata() > 0
            roi = sphere_mask(img, ROI_XYZ, ROI_RADIUS) & brain
            pos = sphere_mask(img, TASKPOS_XYZ, ROI_RADIUS) & brain
            print(f"grid {img.shape} roi voxels {roi.sum()} taskpos voxels {pos.sum()}", flush=True)
        Y = img.get_fdata(dtype=np.float32)[brain].T            # T x V
        Y = (Y - Y.mean(0)) / np.where(Y.std(0) > 0, Y.std(0), 1)  # z-score: betas in SD units
        ev = sub_ev[run]
        frame_times = np.arange(Y.shape[0]) * TR + FRAME_OFFSET
        tg = ev[ev.trial_type.isin(TARGETS)]
        rt = pd.to_numeric(tg.response_time, errors="coerce")
        acc = pd.to_numeric(tg.accuracy, errors="coerce")
        for cond in TARGETS:
            m = (tg.trial_type == cond) & (acc == 1) & rt.notna()
            beh.append({"subject": sub, "run": run, "cond": cond, "rt_ms": float(rt[m].mean()),
                        "acc": float((acc[tg.trial_type == cond] == 1).mean())})
        for model in MODELS:
            X = design(frame_times, ev, model, SCALING)
            B = np.linalg.pinv(X.values) @ Y                          # p x V (OLS)
            c = np.zeros(X.shape[1]); c[X.columns.get_loc("Incongruent")] = 1; c[X.columns.get_loc("Congruent")] = -1
            sub_eff[model].append(c @ B)
            if model == "std_all":
                ca = np.zeros(X.shape[1]); ca[X.columns.get_loc("Incongruent")] = ca[X.columns.get_loc("Congruent")] = 0.5
                sub_pos.append(ca @ B)
            if model == "rt_modulator":
                sub_eff.setdefault("rt_slope", []).append(B[X.columns.get_loc("RTmod")])
    if not sub_eff["std_all"]:
        continue
    vol_idx = np.flatnonzero(brain)
    roi_cols = np.isin(vol_idx, np.flatnonzero(roi))
    pos_cols = np.isin(vol_idx, np.flatnonzero(pos))
    row = {"subject": sub, "n_runs": len(sub_eff["std_all"])}
    for model in MODELS + ["rt_slope"]:
        eff = np.mean(sub_eff[model], axis=0)
        if model in MODELS:
            maps[model].append(eff)
        row[f"roi_{model}"] = float(eff[roi_cols].mean())
    row["taskpos_all_targets"] = float(np.mean(sub_pos, axis=0)[pos_cols].mean())
    rows.append(row)
    print(f"{time.time()-t0:6.0f}s {sub}: " + " ".join(f"{k[4:]}={v:+.3f}" for k, v in row.items() if k.startswith("roi_")), flush=True)

df = pd.DataFrame(rows)
df.to_csv(OUT / f"subject_roi_effects{TAG}.csv", index=False)
b = pd.DataFrame(beh).groupby(["subject", "cond"]).agg(rt_ms=("rt_ms", "mean"), acc=("acc", "mean")).unstack("cond")
conflict_rt = b["rt_ms"]["Incongruent"] - b["rt_ms"]["Congruent"]
b.to_csv(OUT / f"subject_behaviour{TAG}.csv")


def one_sample(x):
    t, p = stats.ttest_1samp(x, 0.0)
    return {"mean": float(np.mean(x)), "t": float(t), "p": float(p), "n": int(len(x)),
            "cohen_d": float(np.mean(x) / np.std(x, ddof=1))}


metrics = {"n_subjects": int(len(df)), "runs": RUNS, "frame_offset_s": FRAME_OFFSET, "scaling": SCALING, "roi": {"xyz_mni": ROI_XYZ, "radius_mm": ROI_RADIUS},
           "raw": {}, "controlled": {}, "voxelwise_z_gt_3.1": {}}
metrics["premise"] = {"rt_conflict_ms": one_sample(conflict_rt.values),
                      "rt_congruent_ms": float(b["rt_ms"]["Congruent"].mean()),
                      "rt_incongruent_ms": float(b["rt_ms"]["Incongruent"].mean()),
                      "acc_congruent": float(b["acc"]["Congruent"].mean()),
                      "acc_incongruent": float(b["acc"]["Incongruent"].mean()),
                      "rt_slope_in_roi": one_sample(df["roi_rt_slope"].values)}
metrics["negative_control_taskpos_all_targets"] = one_sample(df["taskpos_all_targets"].values)
for model in MODELS:
    key = "raw" if model.startswith("std") else "controlled"
    metrics[key][model] = one_sample(df[f"roi_{model}"].values)
    # voxelwise group one-sample t, converted to z; count suprathreshold voxels in a 20 mm medial-frontal sphere
    M = np.array(maps[model])
    t, p = stats.ttest_1samp(M, 0.0, axis=0)
    z = stats.norm.isf(p / 2) * np.sign(t)
    if os.environ.get("MAPS_DIR"):  # optional group z-maps (large; not part of the recorded outputs)
        zimg = np.zeros(grid.shape[:3], np.float32); zimg[brain] = z
        Path(os.environ["MAPS_DIR"]).mkdir(parents=True, exist_ok=True)
        nib.save(nib.Nifti1Image(zimg, grid.affine), Path(os.environ["MAPS_DIR"]) / f"z_{model}{TAG}.nii.gz")
    near = np.isin(np.flatnonzero(brain), np.flatnonzero(sphere_mask(grid, ROI_XYZ, 20.0)))
    peak = int(np.argmax(np.where(near, z, -np.inf)))
    peak_xyz = nib.affines.apply_affine(grid.affine, np.unravel_index(np.flatnonzero(brain)[peak], grid.shape[:3]))
    metrics["voxelwise_z_gt_3.1"][model] = {"whole_brain": int((z > 3.1).sum()), "within_20mm_of_roi": int((z[near] > 3.1).sum()),
                                           "peak_z_within_20mm": float(z[peak]), "peak_xyz": [float(v) for v in peak_xyz]}
# the conflict effect across subjects vs the behavioural RT cost (does the brain effect track RT?)
if len(df) >= 3:
    r, p = stats.pearsonr(conflict_rt.loc[df.subject].values, df["roi_std_all"].values)
    metrics["premise"]["roi_std_all_vs_rt_conflict"] = {"r": float(r), "p": float(p)}
(OUT / f"metrics{TAG}.json").write_text(json.dumps(metrics, indent=2))
print(json.dumps(metrics, indent=2))
print(f"total {time.time()-t0:.0f}s")
