# Superseded: Step-0 v1 (per-regressor peak scaling)

These are the original Step-0 probe outputs and logs, recorded 2026-10-08. They are kept
byte-for-byte, so the sha256 values under `superseded` in `step0/evidence.json` still match.
They were superseded the same day.

**Why.** The v1 probe and oracle divided each task regressor by its own peak and then applied
+1/-1 to the Incongruent/Congruent betas. On ds001907 the Incongruent regressor peaks higher than
the Congruent one in every run. The trial sequence is fixed, and incongruent RT epochs are longer:
the mean ratio is 1.03 for 2 s targets and 1.10 for RT-length epochs. So the contrast was
m_I*b_I - m_C*b_C = m_I*(b_I - b_C) + (m_I - m_C)*b_C. That adds a positive term in any region
that responds to targets. `step0/scaling_check.py` shows it on noise-free signals: with no
conflict effect, v1 scaling gives +0.047 (2 s targets) and a shared scale gives 0.

**What changed.** Only the scaling. `reproduced_by_current_probe.log` is the current
`step0/probe.py` run with `SCALING=per_regressor_peak`, and its outputs are identical to the files
here. The v2 results are in `step0/outputs/` and `step0/run.log`.

| model | v1 t (p) | v2 t (p) |
|---|---|---|
| 2 s targets, all trials | 2.19 (0.039) | 2.01 (0.057) |
| 2 s targets, correct trials | 2.00 (0.057) | 1.82 (0.081) |
| impulse targets | 3.22 (0.004) | 2.95 (0.007) |
| RT-length epochs | 1.34 (0.19) | 1.04 (0.31) |
| 2 s + RT modulator | -2.61 (0.016) | -2.71 (0.013) |
| ROI RT slope | 6.84 | 5.47 (per second of RT) |

The v1 oracle outputs and verifier are in git history (commit 06805dd).
