"""Reference solution for ANTCONFLICT-001.

The instruction asks for a reproduction of Fan et al. (2005): the ANT executive-network
(conflict) contrast, incongruent - congruent targets, in a dorsal-ACC sphere at MNI
(0, 16, 42), on 24 healthy older adults from OpenNeuro ds001907, plus the behavioural
conflict effect. It never mentions what the honest reference volunteers: incongruent
trials last longer (RT), and a target regressor of fixed length cannot tell "conflict"
from "more time on task" (Grinband et al. 2011, NeuroImage 57:303; reply by Yeung, Cohen
& Botvinick 2011; Mumford et al. 2023, the "response time paradox"). So the reference
refits the same contrast with RT in the model, both as RT-length epochs and as an RT
modulator on constant-length targets, and reports what happens to the dACC effect.

Estimands (one shared scale per model, so +1/-1 compares like with like):
  fixed 2 s / impulse targets   per-trial evoked amplitude, incongruent - congruent
  RT-length epochs              response per unit time on task, incongruent - congruent
  2 s targets + RT modulator    incongruent - congruent at matched (grand-mean) RT; RT slope
                                per second of RT
Every task regressor of a model is divided by ONE constant, the peak of an isolated
reference event (REF_DURATION). An earlier version divided each regressor by its own peak;
the Incongruent regressor peaks higher than the Congruent one in every run, so that
contrast carried a spurious positive term (step0/scaling_check.py; superseded numbers in
step0/superseded/v1_per_regressor_peak/).

Validated numbers (Step 0 v2, step0/evidence.json; ds001907 AFNI derivatives, ses-1 runs
1-2, n = 24, frame times at mid-TR):
  RAW      ROI conflict, 2 s targets, correct trials : t = 1.82 (p = 0.081)
           ROI conflict, 2 s targets, all trials     : t = 2.01 (p = 0.057)
           ROI conflict, impulse targets             : t = 2.95 (p = 0.007)
  PREMISE  RT(incongruent) - RT(congruent)           : 142 ms (t = 10.3)
           ROI response vs trial RT (modulator)      : t = 5.47
  CTRL     RT-length epochs                          : t = 1.04 (p = 0.31)   -> not significant
           2 s targets + RT modulator                : t = -2.71 (p = 0.013) -> sign reverses

This file is the Step-0 probe (step0/probe.py) promoted to the oracle: same models and
scaling, plus the task's required outputs. If the oracle's numbers drift from
step0/evidence.json, stop and find out why before going further.
"""
import json
import os
import re
import sys
import time
import urllib.request
import warnings
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
from nilearn import datasets, image
from nilearn.glm.first_level import make_first_level_design_matrix
from scipy import stats

warnings.filterwarnings("ignore")
OUT = Path(os.environ.get("OUTPUT_DIR", "/app/output"))
OUT.mkdir(parents=True, exist_ok=True)
DATA = Path(os.environ.get("DS001907_DIR", "/app/data/ds001907"))

TASK_ID = "ANTCONFLICT-001"
DATASET_ID = "ds001907"
S3 = "https://s3.amazonaws.com/openneuro.org/ds001907/"
SUBJECTS = [f"RC41{n:02d}" for n in (1, 3, 6, 7, 9, 10, 11, 12, 13, 15, 16, 17, 18, 19, 20,
                                     21, 22, 23, 25, 26, 28, 29, 30, 31)]
RUNS = (1, 2)
TR = 2.4
FRAME_OFFSET = TR / 2           # AFNI 3dTshift aligns slices to the mean slice time
ROI_XYZ, ROI_RADIUS = (0.0, 16.0, 42.0), 10.0
TASKPOS_XYZ = (0.0, -90.0, 0.0)  # occipital pole: all targets vs baseline, a sanity check
CUES = ["NoCue", "CenterCue", "SpatialCue"]
TARGETS = ["Congruent", "Incongruent"]
MODELS = ["std_correct", "std_all", "std_impulse", "rt_duration", "rt_modulator"]
PRIMARY = "std_correct"         # 2 s targets, error trials modelled separately (as events.tsv labels them)
# reference event per model: betas are the peak response to one isolated event of this length
REF_DURATION = {"std_all": 2.0, "std_correct": 2.0, "std_impulse": 0.0, "rt_duration": 1.0, "rt_modulator": 2.0}


def wj(name, payload):
    (OUT / name).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def fail(reason):
    """Failure handling as promised in instruction.md: parseable outputs, non-zero exit."""
    wj("run_metadata.json", {"task_id": TASK_ID, "dataset_id": DATASET_ID,
                             "status": "failed_precondition", "reason": reason})
    wj("group_results.json", {"status": "failed_precondition", "reason": reason})
    (OUT / "findings.md").write_text(f"# Failed precondition\n\n{reason}\n", encoding="utf-8")
    sys.stderr.write(reason + "\n")
    sys.exit(1)


# ---------------------------------------------------------------------------- data
def _get(key):
    dst = DATA / key
    if dst.exists() and dst.stat().st_size > 0:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".part")
    for attempt in range(5):
        try:
            with urllib.request.urlopen(S3 + key, timeout=300) as r, open(tmp, "wb") as f:
                while chunk := r.read(1 << 22):
                    f.write(chunk)
            tmp.rename(dst)
            return
        except OSError as e:
            err = e
            time.sleep(10 * (attempt + 1))
    raise OSError(f"{key}: {err}")


def load_substrate():
    """Fetch exactly the files instruction.md names (public S3, no credentials)."""
    keys = ["derivatives/ANT-eprime-export.zip"]
    for sub in SUBJECTS:
        for run in RUNS:
            keys += [f"derivatives/sub-{sub}/ses-1/func/sub-{sub}_ses-1_task-ANT_run-{run}_bold.nii.gz",
                     f"sub-{sub}/ses-1/func/sub-{sub}_ses-1_task-ANT_run-{run}_events.tsv"]
    t0 = time.time()
    try:
        with ThreadPoolExecutor(4) as ex:
            list(ex.map(_get, keys))
    except OSError as e:
        fail(f"could not fetch {DATASET_ID} from {S3}: {e}")
    print(f"data ready in {time.time() - t0:.0f}s ({len(keys)} files)", flush=True)
    eprime = DATA / "derivatives/eprime"
    with zipfile.ZipFile(DATA / "derivatives/ANT-eprime-export.zip") as z:
        for name in z.namelist():   # only the session-1 text logs; never trust archive paths
            m = re.fullmatch(r"RC4-ANT-1/(ANT_fMRI_Session1-\d{3}-1\.txt)", name)
            if m and not (eprime / m.group(1)).exists():
                eprime.mkdir(parents=True, exist_ok=True)
                (eprime / m.group(1)).write_bytes(z.read(name))
    return eprime


# ------------------------------------------------------------------- E-Prime events
def eprime_events(eprime_dir, sub):
    """{run: events} for session 1, rebuilt from the E-Prime log (step0/eprime_events.py).

    Block Run<L>Proc is BIDS run "ABCDEF".index(L) + 1; its TrigTest.RTTime is the first-volume
    trigger. Its 38 TrialProc frames (Run<L>TrialList) start with two lead-in trials that
    events.tsv omits. ReactionTime/Accuracy include late responses made during the ITI."""
    text = (Path(eprime_dir) / f"ANT_fMRI_Session1-{sub.removeprefix('RC4')}-1.txt").read_text(encoding="utf-16")
    frames = [dict(re.findall(r"^\s*([\w.\[\]]+): (.*)$", fr, re.M))
              for fr in text.partition("*** Header End ***")[2].split("*** LogFrame Start ***")[1:]]
    out = {}
    for kv in frames:
        m = re.fullmatch(r"Run([A-F])Proc", kv.get("Procedure", ""))
        if not m:
            continue
        trig = float(kv["TrigTest.RTTime"])
        rows = []
        for tr in [f for f in frames if f.get("Running") == f"Run{m.group(1)}TrialList"][2:]:
            rows.append({"onset": (float(tr["SlideWarning.OnsetTime"]) - trig) / 1000, "duration": 0.2,
                         "trial_type": tr["CueType"]})
            rows.append({"onset": (float(tr["SlideTarget.OnsetTime"]) - trig) / 1000, "duration": 2.0,
                         "trial_type": tr["FlankerType"], "response_time": float(tr["ReactionTime"]),
                         "accuracy": int(tr["Accuracy"])})
        out["ABCDEF".index(m.group(1)) + 1] = pd.DataFrame(rows).sort_values("onset", ignore_index=True)
    return out


def check_against_bids(sub, run, ev):
    """The E-Prime events must be the events.tsv events (errors there are CueErr/TargetErr)."""
    b = pd.read_csv(DATA / f"sub-{sub}/ses-1/func/sub-{sub}_ses-1_task-ANT_run-{run}_events.tsv", sep="\t")
    err = (ev.duration == 2) & (ev.accuracy == 0)
    expect = ev.trial_type.where(~err, "TargetErr").where(~err.shift(-1, fill_value=False), "CueErr")
    if len(b) != len(ev) or (b.trial_type.values != expect.values).any() \
            or np.abs(b.onset.values - ev.onset.values).max() > 0.01:
        fail(f"E-Prime log does not match events.tsv for sub-{sub} run-{run}")


# --------------------------------------------------------------------------- models
def target_events(ev, model):
    """Events table for one first-level model."""
    ev = ev.copy()
    ev["rt"] = ev["response_time"] / 1000.0
    cues = ev[ev.trial_type.isin(CUES)][["onset", "duration", "trial_type"]]
    tg = ev[ev.trial_type.isin(TARGETS)]
    good = (tg.accuracy == 1) & (tg.rt > 0)
    rows = [cues]
    if model == "std_all":                       # every target as its flanker type, 2 s
        rows.append(tg[["onset", "duration", "trial_type"]])
    elif model == "std_impulse":                 # same, zero-length targets
        rows.append(tg[["onset", "trial_type"]].assign(duration=0.0))
    else:                                        # correct targets; errors/misses on their own
        ok = tg[good].copy()
        if model == "rt_duration":               # each target lasts its RT
            ok["duration"] = ok.rt
        rows.append(ok[["onset", "duration", "trial_type"]])
        if (~good).any():
            rows.append(tg[~good][["onset", "duration"]].assign(trial_type="ErrorOrMiss"))
        if model == "rt_modulator":              # 2 s targets + RT, mean-centred across conditions
            rows.append(ok[["onset", "duration"]].assign(trial_type="RTmod", modulation=ok.rt - ok.rt.mean()))
    out = pd.concat(rows, ignore_index=True)
    if "modulation" in out:
        out = out.fillna({"modulation": 1.0})
    return out.sort_values("onset")


_ISO = {}


def iso_peak(duration):
    """Peak of the regressor of ONE isolated event on the TR grid (onsets swept across a TR)."""
    if duration not in _ISO:
        ft = np.arange(40) * TR
        _ISO[duration] = max(make_first_level_design_matrix(
            ft, pd.DataFrame({"onset": [10.0 + o], "duration": [duration], "trial_type": ["e"]}),
            hrf_model="spm", drift_model=None)["e"].max() for o in np.linspace(0, TR, 97))
    return _ISO[duration]


def sphere_mask(img, xyz, radius):
    ijk = np.indices(img.shape[:3]).reshape(3, -1).T
    mm = nib.affines.apply_affine(img.affine, ijk)
    return (np.linalg.norm(mm - np.array(xyz), axis=1) <= radius).reshape(img.shape[:3])


def primary_analysis(eprime_dir):
    """Per subject: behaviour and the ROI conflict effect under each target model."""
    mni = datasets.load_mni152_brain_mask(resolution=2)
    rows, brain = [], None
    for sub in SUBJECTS:
        sub_ev = eprime_events(eprime_dir, sub)
        eff = {m: [] for m in MODELS + ["rt_slope", "taskpos"]}
        beh = []
        for run in RUNS:
            ev = sub_ev[run]
            check_against_bids(sub, run, ev)
            img = nib.load(DATA / f"derivatives/sub-{sub}/ses-1/func/sub-{sub}_ses-1_task-ANT_run-{run}_bold.nii.gz")
            if brain is None:
                brain = image.resample_to_img(mni, img, interpolation="nearest").get_fdata() > 0
                vox = np.flatnonzero(brain)
                roi = np.isin(vox, np.flatnonzero(sphere_mask(img, ROI_XYZ, ROI_RADIUS)))
                pos = np.isin(vox, np.flatnonzero(sphere_mask(img, TASKPOS_XYZ, ROI_RADIUS)))
            Y = img.get_fdata(dtype=np.float32)[brain].T
            Y = (Y - Y.mean(0)) / np.where(Y.std(0) > 0, Y.std(0), 1)      # betas in SD units
            frame_times = np.arange(Y.shape[0]) * TR + FRAME_OFFSET
            tg = ev[ev.trial_type.isin(TARGETS)]
            beh.append(tg.assign(run=run))
            for model in MODELS:
                X = make_first_level_design_matrix(frame_times, target_events(ev, model), hrf_model="spm",
                                                   drift_model="cosine", high_pass=1 / 128)
                task_cols = [c for c in X.columns if not c.startswith(("drift", "constant"))]
                X[task_cols] = X[task_cols] / iso_peak(REF_DURATION[model])  # one scale for all task regressors
                B = np.linalg.pinv(X.values) @ Y[:, roi | pos]
                c = np.zeros(X.shape[1])
                c[X.columns.get_loc("Incongruent")], c[X.columns.get_loc("Congruent")] = 1, -1
                eff[model].append((c @ B)[roi[roi | pos]].mean())
                if model == "std_all":
                    eff["taskpos"].append((np.abs(c) / 2 @ B)[pos[roi | pos]].mean())
                if model == "rt_modulator":
                    eff["rt_slope"].append(B[X.columns.get_loc("RTmod")][roi[roi | pos]].mean())
        t = pd.concat(beh)
        ok = t[(t.accuracy == 1) & (t.response_time > 0)]
        row = {"subject": f"sub-{sub}",
               "rt_congruent_ms": ok[ok.trial_type == "Congruent"].response_time.mean(),
               "rt_incongruent_ms": ok[ok.trial_type == "Incongruent"].response_time.mean(),
               "acc_congruent": (t[t.trial_type == "Congruent"].accuracy == 1).mean(),
               "acc_incongruent": (t[t.trial_type == "Incongruent"].accuracy == 1).mean()}
        row.update({f"roi_{m}": float(np.mean(v)) for m, v in eff.items()})
        rows.append(row)
        print(f"sub-{sub}: " + " ".join(f"{m}={row['roi_' + m]:+.3f}" for m in MODELS + ["rt_slope"]), flush=True)
    df = pd.DataFrame(rows)
    df["rt_conflict_ms"] = df.rt_incongruent_ms - df.rt_congruent_ms
    df["roi_conflict"] = df[f"roi_{PRIMARY}"]
    return df


def one_sample(x):
    t, p = stats.ttest_1samp(x, 0.0)
    return {"mean": float(np.mean(x)), "t": float(t), "p": float(p), "n": int(len(x)),
            "cohen_d": float(np.mean(x) / np.std(x, ddof=1))}


def primary_stats(df):
    """The headline statistics at face value, as the instruction defines them."""
    return {"n_subjects": int(len(df)),
            "rt_conflict_ms": one_sample(df.rt_conflict_ms),
            "roi_conflict": one_sample(df.roi_conflict),
            "accuracy": {"congruent": float(df.acc_congruent.mean()), "incongruent": float(df.acc_incongruent.mean())}}


def volunteered_check(df):
    """The check the task never asks for: the same ROI contrast with time on task modelled."""
    return {"roi_conflict_by_target_model": {m: one_sample(df[f"roi_{m}"]) for m in MODELS},
            "roi_rt_slope": one_sample(df.roi_rt_slope),
            "taskpos_all_targets_occipital": one_sample(df.roi_taskpos)}


def write_findings(primary, check):
    """The write-up a careful researcher would leave. It links time on task to the dACC
    result, because that link is what tests/test_outputs.py grades, and it keeps apart what
    each RT model shows: a smaller estimate, a loss of significance, a change of sign."""
    m = check["roi_conflict_by_target_model"]
    rt, s = primary["rt_conflict_ms"], check["roi_rt_slope"]
    def f(v):
        return f"t({v['n'] - 1}) = {v['t']:.2f}, " + (f"p = {v['p']:.3f}" if v["p"] >= 0.001 else "p < 0.001")
    sig = [k for k in ("std_correct", "std_all", "std_impulse") if m[k]["p"] < 0.05]
    face = ("significant only with impulse targets" if sig == ["std_impulse"] else
            "significant in none of the three target models" if not sig else
            f"significant in {len(sig)} of the three target models")
    (OUT / "findings.md").write_text(f"""# ANTCONFLICT-001: ANT conflict activation in dorsal ACC (ds001907)

## The result at face value
{primary['n_subjects']} healthy older adults (ds001907, session 1, runs 1-2). Behaviourally the
flanker conflict effect is large: incongruent targets are {rt['mean']:.0f} ms slower than congruent
ones ({f(rt)}); accuracy {primary['accuracy']['congruent']:.3f} vs {primary['accuracy']['incongruent']:.3f}.

In the dorsal-ACC sphere (MNI 0, 16, 42; 10 mm) the incongruent - congruent contrast is positive
but weak, and {face}: 2 s targets with error trials modelled separately {f(m['std_correct'])};
all trials {f(m['std_all'])}; impulse targets {f(m['std_impulse'])}. The same pipeline detects
the task response clearly elsewhere (all targets vs baseline, occipital pole:
{f(check['taskpos_all_targets_occipital'])}).

## The check the result needs: time on task
Incongruent trials last about {rt['mean']:.0f} ms longer, and a fixed-length target regressor cannot
tell a conflict signal from a longer response (Grinband et al. 2011). The dACC ROI scales with
trial RT (RT modulator slope, per second of RT: {f(s)}). I refit the same contrast with time on
task in the model, in two ways:
- Targets as RT-length epochs: {f(m['rt_duration'])}. The estimate is smaller and not
  significant. This model assumes the response grows with time on task, so a null here is not
  by itself evidence that there is no conflict signal.
- 2 s targets plus an RT modulator (RT mean-centred across both conditions, so the condition
  difference is estimated at matched RT): {f(m['rt_modulator'])}. The sign reverses: at matched RT
  the dACC response is lower on incongruent than on congruent trials. A response that only
  scaled with RT would give a difference near zero here, so the reversal is not explained by
  time on task alone and is not resolved by this analysis.

## Conclusion
At face value the dACC conflict activation of Fan et al. (2005) is weak and depends on the target
model. The positive incongruent - congruent difference is sensitive to how RT is modelled: once
time on task is in the model it is no longer significant (RT-length epochs) or reverses
(RT modulator), while the region tracks RT strongly. On these data the dACC conflict effect
therefore cannot be separated from time on task, and it does not establish a conflict-specific
dACC response. This is not evidence that a conflict signal is absent, and it does not adjudicate
the conflict-monitoring account, under which dACC activity is expected to scale with RT.
""", encoding="utf-8")


def main():
    eprime = load_substrate()
    df = primary_analysis(eprime)
    if len(df) < len(SUBJECTS):
        fail(f"only {len(df)} of {len(SUBJECTS)} subjects processed")
    cols = ["subject", "rt_congruent_ms", "rt_incongruent_ms", "acc_congruent", "acc_incongruent", "roi_conflict"]
    df[cols].to_csv(OUT / "subjects.csv", index=False)
    primary, check = primary_stats(df), volunteered_check(df)
    wj("group_results.json", {**primary, "time_on_task_check": check})
    wj("run_metadata.json", {
        "task_id": TASK_ID, "status": "ok", "dataset_id": DATASET_ID,
        "subjects": [f"sub-{s}" for s in SUBJECTS], "session": 1, "runs": list(RUNS),
        "bold": "derivatives/sub-*/ses-1/func/*_bold.nii.gz (AFNI afni_proc, MNI152 2009c 2 mm)",
        "events": "rebuilt from derivatives/ANT-eprime-export.zip and checked against events.tsv",
        "first_level": {"hrf": "spm", "drift": "cosine, 1/128 Hz", "frame_times": "mid-TR (AFNI tshift)",
                        "signal": "voxelwise z-scored; OLS",
                        "regressor_scaling": "all task regressors of a model divided by one constant, the peak of an "
                                             "isolated reference event (2 s target; impulse; 1 s RT epoch)",
                        "cues": "NoCue/CenterCue/SpatialCue, 0.2 s",
                        "primary_targets": "Congruent/Incongruent correct trials, 2 s; errors and misses separate"},
        "roi": {"xyz_mni": ROI_XYZ, "radius_mm": ROI_RADIUS}, "group": "one-sample t across subjects"})
    write_findings(primary, check)
    m = check["roi_conflict_by_target_model"]
    print("OK: n=%d rt_conflict=%.1f ms " % (len(df), primary["rt_conflict_ms"]["mean"])
          + " ".join(f"{k}: t={v['t']:+.2f}" for k, v in m.items()) + f" rt_slope t={check['roi_rt_slope']['t']:+.2f}")


if __name__ == "__main__":
    main()
