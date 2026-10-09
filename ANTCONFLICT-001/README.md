# ANTCONFLICT-001 (archived at Step 0)

**Status:** dropped on 2026-10-08. Only the Step-0 record is kept here. The task that was built
(instruction, oracle, verifier, 30 calibration fixtures, proposal, spec) is in git history at
commit `9e77b1f`.

**Candidate.** Fan, McCandliss, Fossella, Flombaum & Posner 2005 (*NeuroImage* 26:471,
doi:10.1016/j.neuroimage.2005.02.004) reported that the ANT conflict contrast (incongruent −
congruent flanker) activates dorsal ACC. The test used OpenNeuro ds001907: AFNI derivatives,
24 healthy older adults (sub-RC41*), session 1, and a 10 mm sphere at MNI (0, 16, 42). The
intended hard-task lever was time on task. Incongruent trials are 139 ms slower, and a
fixed-duration GLM cannot separate conflict from longer processing (Grinband et al. 2011 vs
Yeung et al. 2011; Mumford et al. 2023).

**Why this pairing was archived.**

- **Runs 1–2: the gate could not be met.**
  - The first version (v1) divided each regressor by its own peak. Its +1/−1 contrast
    therefore compared betas on different scales. With one shared scale (v2), the face-value
    effect is not significant:
    - 2 s targets: p = 0.057 (all trials) and p = 0.081 (correct trials)
    - independent nilearn pipeline: p = 0.063
  - There was no significant RAW for CTRL to flip.
  - v1 evidence is kept unchanged in `step0/superseded/`.
- **Runs 1–6: second attempt under a rule fixed beforehand.**
  - `step0/runs1to6_decision_rule.md` was committed and pushed before any run 3–6 BOLD was
    analysed. Session 1 has six ANT runs, and the two-run restriction was a power choice.
  - With all six runs, RAW is robust:

    | Model | t | p |
    |---|---|---|
    | correct-trial 2 s targets | 5.64 | < 10⁻⁴ |
    | all-trial 2 s targets | 5.54 | < 10⁻⁴ |
    | impulse targets | 5.92 | < 10⁻⁴ |
    | independent nilearn pipeline, glover HRF, mid-TR | 6.33 | < 10⁻⁴ |
    | independent nilearn pipeline, every HRF and slice-timing variant | 3.8–6.3 | ≤ 0.001 |

  - CTRL does not flip it, because the two RT controls disagree:
    - RT modulator on 2 s targets: t = −0.57, p = 0.58, a null.
    - RT-length epochs: t = 3.86, p = 0.0008, attenuated but still significant.
  - Criterion 4 of the rule fails, so the verdict is `archive`.
- **No fair fixed oracle.**
  - In a noise-free simulation (`step0/scaling_check.py`), a response that only scales with
    RT gives about 0 under both controls.
  - The data give a null at matched RT, but a larger incongruent response per second of time
    on task.
  - So the data neither show that RT accounts for the effect nor that the effect survives RT
    control. A wrong-cause key would have to take one side of an unresolved modelling debate.
- **Other findings.**
  - The significant reversal under the RT modulator on two runs (t = −2.71) did not persist
    on six runs (t = −0.57).
  - Premise checks hold on six runs: RT cost 139 ms (t = 11.2); trial-level RT slope in the
    ROI t = 8.8; occipital all-targets control t = 5.3.
  - The raw `events.tsv` of RC4110 runs 5–6 leaves 8 E-Prime errors without the
    `TargetErr` label. The derivative events agree with E-Prime that these trials are
    errors. The probe takes accuracy from E-Prime and is unaffected.

**Files.**

- `step0/probe.py` holds the main analysis, with models and regressor scaling in
  `step0/probe_models.py`. `step0/eprime_events.py` rebuilds trial-level RT and accuracy
  from the E-Prime export and validates the result against the events files.
- `step0/scaling_check.py` gives the noise-free estimands. `step0/alt_pipeline_check.py` is
  the independent nilearn pipeline on `events.tsv`.
- `step0/run*.log`, `step0/alt_pipeline_check*.log` and `step0/outputs/` hold the logs and
  outputs. Files with a `_runs1-6` suffix come from the second attempt.
- `step0/evidence.json` is the full record, with sha256-bound artifact references.

Rerun with:

```
DS001907_DIR=<ds001907> EPRIME_DIR=<unzipped RC4-ANT-1> RUNS=1,2,3,4,5,6 python step0/probe.py
DS001907_DIR=<ds001907> RUNS=1,2,3,4,5,6 python step0/alt_pipeline_check.py
```

Leave out `RUNS` to get the two-run analysis. The data is public at
`s3://openneuro.org/ds001907/`; session 1 runs 1–6 are about 60 GB.
