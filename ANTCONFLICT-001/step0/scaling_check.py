"""What does the incongruent - congruent contrast estimate under each regressor scaling?

The v1 probe/oracle divided EACH task regressor by its own peak and then applied +1/-1 to
the Incongruent/Congruent betas. That is only an amplitude difference if both regressors
share one scale. They do not: on ds001907 the Incongruent regressor peaks higher than the
Congruent one in every run (overlap of the fixed trial sequence; longer RT epochs). With
per-regressor scaling the contrast is m_I*b_I - m_C*b_C = m_I*(b_I - b_C) + (m_I - m_C)*b_C,
so a task-positive region (b_C > 0) gets a positive "conflict" term with no conflict at all.

v2 divides every task regressor of a model by ONE constant: the peak of an isolated reference
event (2 s target; impulse; 1 s of time on task for RT-length epochs). Betas are then in
common units and +1/-1 estimates the intended quantity:
  fixed 2 s / impulse targets   per-trial evoked amplitude, incongruent - congruent
  RT-length epochs              response per unit time on task, incongruent - congruent
                                (zero if the response only scales with RT)
  2 s targets + RT modulator    incongruent - congruent at matched (grand-mean) RT

This script needs no BOLD. It (1) reports the per-condition peak ratio m_I/m_C of every
design, and (2) fits every model to NOISE-FREE signals generated from each subject's real
events under known ground truths, so the fitted contrast is the estimand's expected value:
  null           all targets: same 2 s response, no RT dependence
  time_on_task   all targets: RT-length epochs at one rate (no conflict-specific signal)
  conflict       2 s response, incongruent amplitude 1.1 x congruent, no RT dependence
Cue responses (amplitude 0.5) are added in every scenario.

    EPRIME_DIR=/path/to/RC4-ANT-1 python step0/scaling_check.py > step0/scaling_check.log
"""
import json
import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from nilearn.glm.first_level import make_first_level_design_matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eprime_events import subject_events  # noqa: E402
from probe_models import MODELS, TR, design, iso_peak, target_events  # noqa: E402

warnings.filterwarnings("ignore")
EPRIME = Path(os.environ["EPRIME_DIR"])
OUT = Path(__file__).resolve().parent / "outputs"
SUBJECTS = [f"RC41{n:02d}" for n in (1, 3, 6, 7, 9, 10, 11, 12, 13, 15, 16, 17, 18, 19, 20,
                                     21, 22, 23, 25, 26, 28, 29, 30, 31)]
FT = np.arange(149) * TR + TR / 2


def truth(ev, scenario):
    """Noise-free signal (149,) for one run, in units of an isolated 2 s target's peak."""
    ev = ev.copy()
    ev["rt"] = pd.to_numeric(ev.response_time, errors="coerce") / 1000
    tg = ev[ev.duration == 2].copy()
    cues = ev[ev.duration != 2][["onset", "duration"]].assign(trial_type="cue", modulation=0.5)
    if scenario == "null":
        tg = tg[["onset", "duration"]].assign(modulation=1.0)
    elif scenario == "conflict":
        tg = tg[["onset", "duration"]].assign(modulation=np.where(tg.trial_type == "Incongruent", 1.1, 1.0))
    elif scenario == "time_on_task":   # one rate per second of RT (misses: 2 s)
        tg = tg.assign(duration=tg.rt.where(tg.rt > 0, 2.0))[["onset", "duration"]].assign(modulation=1.0)
    ev2 = pd.concat([cues, tg.assign(trial_type="target")], ignore_index=True)
    X = make_first_level_design_matrix(FT, ev2, hrf_model="spm", drift_model=None)
    return (X["cue"] + X["target"]).values / iso_peak(2.0)


def main():
    ratios, fits = [], []
    for sub in SUBJECTS:
        sub_ev = subject_events(EPRIME, sub)
        for run in (1, 2):
            ev = sub_ev[run]
            for model in MODELS:
                Xraw = make_first_level_design_matrix(FT, target_events(ev, model), hrf_model="spm",
                                                      drift_model="cosine", high_pass=1 / 128)
                ratios.append({"model": model, "ratio_I_over_C": Xraw.Incongruent.abs().max() / Xraw.Congruent.abs().max()})
                for scaling in ("per_regressor_peak", "common"):
                    X = design(FT, ev, model, scaling)
                    c = np.zeros(X.shape[1])
                    c[X.columns.get_loc("Incongruent")], c[X.columns.get_loc("Congruent")] = 1, -1
                    P = np.linalg.pinv(X.values)
                    for scen in ("null", "time_on_task", "conflict"):
                        b = P @ truth(ev, scen)
                        fits.append({"model": model, "scaling": scaling, "scenario": scen, "contrast": float(c @ b),
                                     "congruent_beta": float(b[X.columns.get_loc("Congruent")])})
    r = pd.DataFrame(ratios).groupby("model").ratio_I_over_C.agg(["mean", "min", "max"])
    f = pd.DataFrame(fits).groupby(["scenario", "model", "scaling"]).agg(
        contrast=("contrast", "mean"), contrast_min=("contrast", "min"), contrast_max=("contrast", "max"),
        congruent_beta=("congruent_beta", "mean"))
    pd.set_option("display.width", 160)
    print("Per-condition peak ratio m_I / m_C of the unscaled regressors (48 runs):")
    print(r.round(4).to_string())
    print("\nIncongruent - congruent contrast fitted to noise-free signals (mean, min, max over 48 runs):")
    print(f.round(4).to_string())
    out = {"peak_ratio_I_over_C": r.round(4).to_dict(orient="index"),
           "noise_free_contrast": {f"{s}|{m}|{sc}": {k: round(float(v), 4) for k, v in row.items()}
                                   for (s, m, sc), row in f.iterrows()}}
    (OUT / "scaling_check.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
