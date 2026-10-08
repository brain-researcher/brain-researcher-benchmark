"""A different, defensible pipeline: what a typical agent would run.

nilearn FirstLevelModel on the raw BIDS events.tsv as shipped (errors already TargetErr/CueErr),
both runs in one model (fixed effects), AR(1) noise model, no signal scaling, cosine drift at
nilearn's default 0.01 Hz, contrast "Incongruent - Congruent" (effect size) averaged over the
10 mm dACC sphere. Variants: HRF glover (nilearn default) or spm; slice_time_ref 0.5 (as the
instruction states) or 0 (nilearn's default, i.e. ignoring the mid-TR reference).

"psc_glover_str0" is nilearn's full default, including percent-signal-change scaling. The
derivatives are nuisance-regression residuals whose voxel means are ~0 (median |mean|/SD
~2e-4 in sub-RC4101 run-1), so that scaling divides by ~0 and its values are not usable.

Used to set the verifier's imaging tolerances: subject-level ROI values from a pipeline like
this must pass test_outputs.py, so its checks compare against the reference by correlation
and by plausible ranges, never by exact values. Fits are restricted to the sphere's voxels.

    DS001907_DIR=/path/to/ds001907 python step0/alt_pipeline_check.py > step0/alt_pipeline_check.log
    # session-1 runs 1-6 (step0/runs1to6_decision_rule.md); outputs get a _runs1-6 suffix
    RUNS=1,2,3,4,5,6 DS001907_DIR=... python step0/alt_pipeline_check.py > step0/alt_pipeline_check_runs1-6.log
"""
import json
import os
import warnings
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
from nilearn import datasets, image
from nilearn.glm.first_level import FirstLevelModel
from scipy import stats

warnings.filterwarnings("ignore")
DATA = Path(os.environ["DS001907_DIR"])
OUT = Path(os.environ.get("PROBE_OUT", Path(__file__).resolve().parent / "outputs"))
RUNS = [int(r) for r in os.environ.get("RUNS", "1,2").split(",")]
TAG = "" if RUNS == [1, 2] else f"_runs{RUNS[0]}-{RUNS[-1]}"
SUBJECTS = [f"RC41{n:02d}" for n in (1, 3, 6, 7, 9, 10, 11, 12, 13, 15, 16, 17, 18, 19, 20,
                                     21, 22, 23, 25, 26, 28, 29, 30, 31)]
VARIANTS = {**{f"{h}_str{s:g}": (h, s, False) for h in ("glover", "spm") for s in (0.5, 0.0)},
            "psc_glover_str0": ("glover", 0.0, 0)}


def main():
    first = nib.load(DATA / f"derivatives/sub-{SUBJECTS[0]}/ses-1/func/sub-{SUBJECTS[0]}_ses-1_task-ANT_run-1_bold.nii.gz")
    brain = image.resample_to_img(datasets.load_mni152_brain_mask(resolution=2), first, interpolation="nearest").get_fdata() > 0
    ijk = np.indices(first.shape[:3]).reshape(3, -1).T
    mm = nib.affines.apply_affine(first.affine, ijk)
    roi = (np.linalg.norm(mm - np.array([0.0, 16.0, 42.0]), axis=1) <= 10).reshape(first.shape[:3]) & brain
    # fit on a box around the sphere (identical voxelwise fits, far less memory)
    lo, hi = np.argwhere(roi).min(0) - 1, np.argwhere(roi).max(0) + 2
    box = tuple(slice(a, b) for a, b in zip(lo, hi))
    roi_box = roi[box]
    mask = nib.Nifti1Image(roi_box.astype(np.uint8), first.slicer[box].affine)
    rows = []
    for sub in SUBJECTS:
        imgs = []
        for r in RUNS:
            full = nib.load(DATA / f"derivatives/sub-{sub}/ses-1/func/sub-{sub}_ses-1_task-ANT_run-{r}_bold.nii.gz")
            imgs.append(nib.Nifti1Image(np.asarray(full.dataobj[box], dtype=np.float32), full.slicer[box].affine))
        evs = [pd.read_csv(DATA / f"sub-{sub}/ses-1/func/sub-{sub}_ses-1_task-ANT_run-{r}_events.tsv", sep="\t") for r in RUNS]
        row = {"subject": f"sub-{sub}"}
        for name, (hrf, str_, scaling) in VARIANTS.items():
            m = FirstLevelModel(t_r=2.4, slice_time_ref=str_, hrf_model=hrf, noise_model="ar1", signal_scaling=scaling,
                                mask_img=mask, smoothing_fwhm=None, minimize_memory=True).fit(imgs, events=evs)
            eff = m.compute_contrast("Incongruent - Congruent", output_type="effect_size")
            row[name] = float(eff.get_fdata()[roi_box].mean())
        rows.append(row)
        print(sub, " ".join(f"{k}={v:+.4f}" for k, v in row.items() if k != "subject"), flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / f"alt_pipeline_subjects{TAG}.csv", index=False)
    summary = {}
    for name in VARIANTS:
        t, p = stats.ttest_1samp(df[name], 0.0)
        summary[name] = {"mean": float(df[name].mean()), "t": float(t), "p": float(p)}
    print(json.dumps(summary, indent=2))
    (OUT / f"alt_pipeline_check{TAG}.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
