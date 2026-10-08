"""First-level target models and regressor scaling shared by step0/probe.py and step0/scaling_check.py.

SCALING
  "common"              (v2, current) every task regressor of a model is divided by ONE constant,
                        the peak of an isolated reference event of that model (REF_DURATION), so
                        the +1/-1 incongruent - congruent contrast compares betas in the same units.
  "per_regressor_peak"  (v1, superseded) each task regressor divided by its own peak. The two
                        condition regressors then have different scales and +1/-1 no longer
                        estimates an amplitude difference (step0/scaling_check.py).
"""
from functools import lru_cache

import numpy as np
import pandas as pd
from nilearn.glm.first_level import make_first_level_design_matrix

TR = 2.4
CUES = ["NoCue", "CenterCue", "DoubleCue", "SpatialCue"]
TARGETS = ["Congruent", "Incongruent"]
MODELS = ["std_all", "std_correct", "std_impulse", "rt_duration", "rt_modulator"]
# Reference event per model. Betas are then "peak response to one isolated event of this
# length": a 2 s target; an impulse; 1 s of time on task (RT-length epochs). In the modulator
# model the RT slope is per second of RT on a 2 s target.
REF_DURATION = {"std_all": 2.0, "std_correct": 2.0, "std_impulse": 0.0, "rt_duration": 1.0, "rt_modulator": 2.0}


def target_events(ev, model):
    """Build the events table for one model. `ev` is from eprime_events.subject_events()."""
    ev = ev.copy()
    ev["rt"] = pd.to_numeric(ev["response_time"], errors="coerce") / 1000.0
    ev["acc"] = pd.to_numeric(ev["accuracy"], errors="coerce")
    cues = ev[ev.trial_type.isin(CUES)][["onset", "duration", "trial_type"]]
    tg = ev[ev.trial_type.isin(TARGETS)].copy()
    good = (tg.acc == 1) & tg.rt.notna()
    rows = [cues]
    if model == "std_all":                       # as given in events.tsv
        rows.append(tg[["onset", "duration", "trial_type"]])
    elif model == "std_impulse":                 # same, zero-duration targets
        rows.append(tg[["onset", "trial_type"]].assign(duration=0.0))
    elif model in ("std_correct", "rt_modulator", "rt_duration"):
        ok = tg[good].copy()
        if model == "rt_duration":
            ok["duration"] = ok.rt
        rows.append(ok[["onset", "duration", "trial_type"]])
        bad = tg[~good]
        if len(bad):
            rows.append(bad[["onset", "duration"]].assign(trial_type="ErrorOrMiss"))
        if model == "rt_modulator":
            rows.append(ok[["onset", "duration"]].assign(
                trial_type="RTmod", modulation=ok.rt - ok.rt.mean()))
    out = pd.concat(rows, ignore_index=True)
    if "modulation" in out:
        out = out.fillna({"modulation": 1.0})
    return out.sort_values("onset")


@lru_cache(maxsize=None)
def iso_peak(duration):
    """Peak of the regressor of ONE isolated event, on the TR grid nilearn uses (onsets swept
    across a TR so the continuous peak is not missed between samples)."""
    ft = np.arange(40) * TR
    return max(make_first_level_design_matrix(
        ft, pd.DataFrame({"onset": [10.0 + o], "duration": [duration], "trial_type": ["e"]}),
        hrf_model="spm", drift_model=None)["e"].max() for o in np.linspace(0, TR, 97))


def design(frame_times, ev, model, scaling="common"):
    X = make_first_level_design_matrix(frame_times, target_events(ev, model), hrf_model="spm",
                                       drift_model="cosine", high_pass=1 / 128)
    task_cols = [c for c in X.columns if not c.startswith(("drift", "constant"))]
    if scaling == "common":
        X[task_cols] = X[task_cols] / iso_peak(REF_DURATION[model])
    elif scaling == "per_regressor_peak":
        X[task_cols] = X[task_cols] / X[task_cols].abs().max()
    else:
        raise ValueError(scaling)
    return X
