## ANTCONFLICT-001

**Proposal Title:** Reproduce the ANT executive-network (conflict) activation in dorsal ACC: an un-cued time-on-task confound (the *wrong-cause* failure axis, task fMRI)

**Scientific Domain:** Life Sciences · **Field:** Neuroscience · **Subfield:** Cognitive control / task fMRI

**Source finding:** Fan, McCandliss, Fossella, Flombaum & Posner (2005), *NeuroImage* 26:471, https://doi.org/10.1016/j.neuroimage.2005.02.004 ("The activation of attentional networks"). Methods critique of the lever: Grinband et al. (2011), *NeuroImage* 57:303 (time on task explains the dMFC congruency effect); reply by Yeung, Cohen & Botvinick (2011); Mumford et al. (2023, bioRxiv, "response time paradox"). Dataset: OpenNeuro `ds001907` (AFNI derivatives + E-Prime logs, public S3).

**Status:** v0 + local oracle, **reframed 2026-10-08** (Step-0 verdict `reframe`). Step 0 is done and recorded, and every task file is written. A review found that the v1 analysis compared differently scaled betas. The analysis was corrected and rerun on the Step-0 data cache, and the v1 record is kept under `step0/superseded/v1_per_regressor_peak/`. `solution/compute.py`, run locally on that cache, reproduces the v2 Step-0 numbers to machine precision. **Not yet run:** the in-container Harbor oracle and agent calibration (both out of scope for this build; to be run on a separate system).

### Why this exists

The suite has one wrong-cause task, DEVCONN-001 (head motion, resting-state connectivity, ds000228). This task covers the same axis on a different modality (event-related task fMRI), a different dataset, and a different lever: **time on task**. Incongruent flanker trials take ~140 ms longer, so a target regressor of fixed length cannot tell "conflict" from "more processing time".

The un-cued agent already holds the premise, because it must compute the behavioural RT cost. The hypothesis is that it will report that cost as behavioural *validation* of the conflict manipulation and never connect it to the imaging result. This is the same pattern as DEVCONN, where agents had the motion estimates in hand and never checked them.

### The trap (Step-0 validated, v2)

Source: `step0/evidence.json` (probe `step0/probe.py` + `step0/probe_models.py`, log `step0/run.log`; E-Prime → events mapping `step0/eprime_events.py`; scaling check `step0/scaling_check.py`; independent pipeline `step0/alt_pipeline_check.py`). Setup: 24 healthy older adults (sub-RC41*), session 1, runs 1-2, 10 mm sphere at MNI (0, 16, 42); group one-sample t, df = 23. Every task regressor of a model shares one scale: the peak of an isolated reference event.

| | face value (as instructed) | time on task modelled | what changes |
|---|---|---|---|
| **premise** RT(incongruent) − RT(congruent) | **142 ms** (t = 10.3, d = 2.1) | — | large |
| **premise** dACC ROI vs trial RT (RT modulator, per s) | — | **t = 5.47** | the region scales with RT |
| dACC conflict, 2 s targets, correct trials | t = 1.82 (p = 0.081) | RT-length epochs: **t = 1.04 (p = 0.31)** | smaller, not significant |
| dACC conflict, 2 s targets, all trials | t = 2.01 (p = 0.057) | 2 s targets + RT modulator: **t = −2.71 (p = 0.013)** | **sign reverses** |
| dACC conflict, impulse targets | **t = 2.95 (p = 0.007)** | | |
| independent: nilearn FirstLevelModel, events.tsv, AR(1) | t = 1.96 (p = 0.063) | | agrees with v2 |
| voxels z > 3.1 within 20 mm of the ROI | 47–99 (peaks z 4.2–4.4) | RT-length 44 · RT modulator **0** | |
| sanity: all targets vs baseline, occipital pole | t = 5.53 | — | the pipeline detects task signal |

At face value the dACC conflict effect is weak and depends on the target model: it is positive in all three standard models, but significant only with impulse targets. With time on task modelled, the RT-length model attenuates the effect and it is not significant; the RT-modulator model reverses its sign, significantly. Meanwhile the ROI tracks RT strongly. These are three different outcomes (attenuation, loss of significance, sign reversal), and none of them shows that the dACC carries no conflict signal. The defensible conclusion is narrower: **the positive conflict difference is sensitive to how RT is modelled, so on these data it does not establish a conflict-specific dACC response.**

**What the correction changed (v1 → v2).** v1 divided each task regressor by its own peak and then applied +1/−1 to the Incongruent/Congruent betas. The two regressors' peaks differ: Incongruent is higher in every run, by 3% for 2 s targets and 10% (0.60–1.77) for RT-length epochs, because the trial sequence is fixed and incongruent epochs are longer. So the contrast was m_I·b_I − m_C·b_C, which adds a positive term wherever the region responds to targets at all. On noise-free signals with no conflict effect it returned +0.047 (2 s targets); the shared scale returns exactly 0, and it recovers a planted 10% effect exactly (`step0/scaling_check.py`). The refactored probe reproduces the v1 files bit-for-bit with `SCALING=per_regressor_peak`, so scaling is the only change.

| | v1 (superseded) | v2 |
|---|---|---|
| 2 s targets, all trials | t = 2.19 (p = 0.039) | t = 2.01 (p = 0.057) |
| 2 s targets, correct trials | t = 2.00 (p = 0.057) | t = 1.82 (p = 0.081) |
| impulse targets | t = 3.22 (p = 0.004) | t = 2.95 (p = 0.007) |
| RT-length epochs | t = 1.34 (p = 0.19) | t = 1.04 (p = 0.31) |
| 2 s + RT modulator | t = −2.61 (p = 0.016) | t = −2.71 (p = 0.013) |
| ROI RT slope | t = 6.84 (per-run peak units) | t = 5.47 (per second of RT) |

**Why this is a reframe, not the original task.** v1 described "a modest significant effect that is entirely accounted for by RT". After the fix, the most standard face-value models are already not significant, and so is an independent nilearn pipeline. For the default analysis, then, the lever no longer turns a positive verdict into a null. The RT dependency is still real and measured: the positive difference does not survive either RT model, and it reverses at matched RT. But a flat "does not reproduce" now reaches roughly the reference's verdict without the reasoning. **Whether failing such an answer is fair is the open question for calibration** (see Difficulty). If hand re-scoring says it is not, retire the wrong-cause framing; the task would then be an easy control at best.

**Honesty notes (no-fake-traps discipline, from Step 0):**
1. **Event provenance had to be rebuilt.** RT/accuracy-bearing events exist for only 6 subjects. I rebuilt everyone's trials from the E-Prime export:
   - BIDS run-N = block letter N, not presentation order;
   - two lead-in trials are dropped;
   - ReactionTime/Accuracy count late responses.

   The rebuild was validated exactly against all 12 derivative events files and all 48 raw events files (`step0/run.log`). RC4114 has no session-1 log and is excluded.
2. **The first probe run was null, and it was wrong.** With naive frame times (volume i at i·TR) the raw dACC effect is t = 0.12. The derivatives are AFNI `tshift`-corrected to the mean slice time, so volumes sit at (i + 0.5)·TR. An onset-shift fit confirmed this (best R² at −1.2 to −2.4 s with naive frame times), and the reference was chosen on those grounds, not by its effect on the contrast. The naive run is kept as a recorded variant (`*_frame_offset0.*`: RT-length t = 0.44, RT modulator t = −3.42). nilearn's `FirstLevelModel` defaults to `slice_time_ref = 0`, which is this case (t = −0.31 in the independent pipeline). The instruction pins "slice-time corrected to the middle of each TR" for that reason.
3. **The raw effect is weak and model-dependent** (p = 0.057 / 0.081 for 2 s targets, 0.007 for impulse targets). The verifier therefore accepts both a "reproduces" and a "does not reproduce" face-value framing, provided RT / time on task is linked to the imaging result with evidence.
4. **Attenuation, loss of significance and reversal are different claims.** The RT-length model's null is not evidence of absence. It also returns ~0 for a genuine fixed-amplitude conflict effect (`scaling_check`), so on its own it cannot separate the accounts. The RT-modulator reversal is **not** what pure time on task predicts: that gives ~0. On the data, the trial-level RT slope × 142 ms predicts an incongruent − congruent difference about three times the one observed, so the dACC congruency difference is *smaller* than RT scaling predicts. Why is unresolved (non-linear RT–BOLD relation, RT variance from cues, or a genuinely lower incongruent response at matched RT).
5. **The interpretation is contested.** Conflict-monitoring theory predicts dACC activity scales with RT (Yeung et al. 2011). The reference concludes only that the positive difference does not establish a conflict-specific response here, not that conflict monitoring is refuted or that the dACC carries no conflict signal.
6. **The derivatives are residuals.** Voxel means are ~0 (nuisance regression already applied), so percent-signal-change scaling, nilearn's default, divides by ~0 and gives unusable imaging values. This is an on-path hazard unrelated to the lever, and the imaging compute check fails such outputs (subject-level r = 0.60 vs the 0.6 bar). The instruction does not mention it; flag it if calibration shows agents failing there.
7. **Older cohort, 2 of 6 runs.** Both limit power for the raw effect, not for the RT slope (t = 5.5). The between-subject correlation of the ROI effect with the RT cost is r = 0.08 (n.s.). It is recorded, not used: the time-on-task account is trial-level.

### Verifier (3 compute checks, 1 judgement check)

`tests/test_outputs.py`. The compute checks compare with the reference only through correlations and plausible ranges, so defensible pipelines pass (`num-alt-pipeline`, `num-naive-frame-times`):
1. **Outputs and metadata.** All four outputs exist; `run_metadata.json` parses, is not a failed precondition, names ds001907, the participants (IDs or count), runs 1 and 2, and a first-level model with its HRF.
2. **Participants and behaviour.** Participant labels are recognised, unique, within the listed 24 and ≥ 22 present. RTs are finite, in ms (250–3000), and accuracy is a proportion. Mean RT cost is 120–165 ms (measured 142; the trimmed, median and all-trial variants give 133–145). Labels carry their own data: per-participant overall RT has r ≥ 0.9 and RT cost r ≥ 0.6 with the reference (trimmed, median and late-excluded alternatives 0.987+ / 0.79–0.99; shuffled 99th percentile 0.50). `group_results.json` `rt_conflict_ms` {mean, t, p} must be the one-sample test of the CSV, and `n_subjects` must match.
3. **dACC contrast.** At least 22 finite `roi_conflict` values, not all identical. Their best correlation with the reference subject-level effects (2 s all / 2 s correct / impulse) must be ≥ 0.6: sensible pipelines give 0.69–0.99, shuffled values 0.54 at the 99th percentile, and sign-flipped values are negative. `roi_conflict` {mean, t, p} must be the one-sample test of the CSV.
4. **Judgement.** `findings.md` must link RT / time on task to the imaging result. Either it reports that with RT in the model the dACC effect is no longer significant or reverses (read across the claim's sentence and the next, with a brain-side token nearby), or it attributes the imaging effect to RT (explained by, driven by, cannot be separated from, sensitive to how RT is modelled, an RT artefact), cautious modals allowed. It fails if:
   - it **denies** the link ("RT does not explain the dACC activation", "reflects conflict rather than RT", "independent of RT");
   - it reports only that the effect **survives** RT control ("remained significant and did not weaken"), with no collapse or reversal elsewhere;
   - the RT claim is **hypothetical or self-declared untested** ("if RT were modelled ... might");
   - the RT claim has **no evidence**: no statistic next to an RT-model claim and no RT-adjusted analysis in `group_results.json`. The instruction is unchanged, so this asks for nothing new and reveals nothing.

   Polarity is read from negation scope ("did not weaken" is survival; "did not survive" and "not robust to" are loss). Partial negations ("not explained by RT alone") count as neither link nor denial. Attenuation alone is not loss of significance. The old guards stay: "conflict effect" alone is not brain-side, RT outliers / trimming is not modelling RT, a negated or nuisance-only RT modulator is not the check.

**Offline discrimination** (`python tools/check_verifier.py ANTCONFLICT-001`: 30 fixtures, 0 mismatches; all synthetic except the reference; no agent has run yet). `calibration/make_numeric_fixtures.py` regenerates the `num-*` fixtures.

| fixture | expected | v1 verifier |
|---|---|---|
| reference (oracle findings.md, verbatim) | PASS | PASS |
| correct: RT-length wording · cannot-separate · cautious multi-sentence · not-evidence-of-absence · conflict-monitoring reading · mixed RT models | PASS | PASS |
| reviewed false pass: "RT does not explain the dACC activation." | FAIL | **PASS** |
| reviewed false pass: "After controlling for RT, dACC activation remained significant and did not weaken." | FAIL | **PASS** |
| denial paraphrases · contradictory claims · hypothetical caveat · attenuated-only · unsupported attribution | FAIL | **PASS** |
| flat reproduces / flat weak / pipeline RT-modulator / vague hedge / behavioural reflects RT / RT trimming / negated modulator | FAIL | FAIL |
| numeric: reviewed tamper (ROI all 0, group 987 / t 123, no metadata) | FAIL compute | **PASS** |
| numeric: missing metadata · duplicate subject · shuffled labels · shuffled ROI · sign flipped · group stats from another model | FAIL compute | **PASS** |
| numeric: alternative nilearn pipeline (raw units, other schema) · naive frame times | PASS | PASS |

A held-out battery of 15 further phrasings (6 should pass, 9 should fail) also behaves as intended. It caught one miss, an untested "could in principle confound" caveat, which is now fixed.

### Difficulty (NOT YET MEASURED)

Oracle reward: not run in-container yet. The local run of `solution/compute.py` (Python 3.14, same pins) reproduces the v2 Step-0 numbers to machine precision, and its outputs pass all four checks.

| agent | runs | reward | what it did (hand re-score) |
|---|---|---|---|
| **GPT-5.5 (codex, xhigh)** | 0 | — | not run |
| **Claude Opus 4.8** | 0 | — | not run |

The hypothesis to test (`step0/evidence.json` → `agent_headroom_hypothesis`) is that agents fit the default event model from `events.tsv` and give a flat verdict. After the correction that verdict is most likely "does not reproduce / weak trend" (null with nilearn's default `slice_time_ref`), with the RT cost cited only as behavioural validation. Do not call this task hard until ≥ 2 families × k ≥ 3 fail it for that reason, and the fails have been hand re-scored. Hand re-scoring must also answer the reframe question: is a flat, non-overclaiming "does not reproduce" a fair fail? If not, retire the wrong-cause framing. Agents that keep percent-signal scaling on these residual data fail the imaging compute check; count those separately from judgement fails. When real agent findings.md files exist, add them as fixtures. They are the real test of the judgement check.

### Cost

`hard`. cpus 4, mem 8 GB, storage 40 GB, internet on. At runtime the task downloads 48 BOLD runs × ~424 MB (~20 GB), 48 events files and the 6.6 MB E-Prime zip from the public OpenNeuro S3 bucket. That took ~35 min at ~9 MB/s on the authoring host and should be faster on cloud runners. The analysis takes ~2.5 min (5 GLMs × 48 runs; 162 s locally) with a peak RSS of 1.5 GB. Timeouts: agent 10800 s, verifier 3600 s, build 2400 s. Deps: numpy 2.5.3, scipy 1.18.1, pandas 3.0.6, nibabel 5.4.2, nilearn 0.14.1, scikit-learn 1.9.1. Dev runs can point `DS001907_DIR` at a host cache to skip the download (local only, never committed).
