## ANTCONFLICT-001

**Proposal Title:** Reproduce the ANT executive-network (conflict) activation in dorsal ACC: an un-cued time-on-task confound (the *wrong-cause* failure axis, task fMRI)

**Scientific Domain:** Life Sciences · **Field:** Neuroscience · **Subfield:** Cognitive control / task fMRI

**Source finding:** Fan, McCandliss, Fossella, Flombaum & Posner (2005), *NeuroImage* 26:471, https://doi.org/10.1016/j.neuroimage.2005.02.004 ("The activation of attentional networks"). Methods critique of the lever: Grinband et al. (2011), *NeuroImage* 57:303 (time on task explains the dMFC congruency effect); reply by Yeung, Cohen & Botvinick (2011); Mumford et al. (2023, bioRxiv, "response time paradox"). Dataset: OpenNeuro `ds001907` (AFNI derivatives + E-Prime logs, public S3).

**Status:** v0 + local oracle. Step 0 is done and recorded, and every task file is written. `solution/compute.py` was run locally against the Step-0 data cache and reproduces the Step-0 numbers exactly. **Not yet run:** the in-container Harbor oracle, and agent calibration (both out of scope for this build; to be run on a separate system).

### Why this exists

The suite has one wrong-cause task, DEVCONN-001 (head motion, resting-state connectivity, ds000228). This task covers the same axis on a different modality (event-related task fMRI), a different dataset, and a different lever: **time on task**. Incongruent flanker trials take ~140 ms longer, so a target regressor of fixed length cannot tell "conflict" from "more processing time".

The un-cued agent already holds the premise, because it must compute the behavioural RT cost. The hypothesis is that it will report that cost as behavioural *validation* of the conflict manipulation and never connect it to the imaging result. This is the same pattern as DEVCONN, where agents had the motion estimates in hand and never checked them.

### The trap (Step-0 validated, real)

Source: `step0/evidence.json` (probe `step0/probe.py`, log `step0/run.log`; E-Prime → events mapping `step0/eprime_events.py`). Setup: 24 healthy older adults (sub-RC41*), session 1, runs 1-2, 10 mm sphere at MNI (0, 16, 42); group one-sample t, df = 23.

| | raw (as instructed) | time on task modelled | verdict |
|---|---|---|---|
| **premise** RT(incongruent) − RT(congruent) | **142 ms** (t = 10.3, d = 2.1) | — | large |
| **premise** dACC ROI vs trial RT (RT modulator) | — | **t = 6.84** | the region scales with RT |
| dACC conflict, 2 s targets, correct trials | t = 2.00 (p = 0.058) | RT-length epochs: **t = 1.34 (p = 0.19)** | **collapses** |
| dACC conflict, 2 s targets, all trials | **t = 2.19 (p = 0.039)** | 2 s targets + RT modulator: **t = −2.61 (p = 0.016)** | **reverses** |
| dACC conflict, impulse targets | **t = 3.22 (p = 0.004)** | | |
| voxels z > 3.1 within 20 mm of the ROI | 49–110 (peaks z 4.2–4.6) | RT-length 34 · RT modulator **0** | |
| sanity: all targets vs baseline, occipital pole | t = 5.53 | — | the pipeline detects task signal |

At face value the dACC conflict effect is present but modest. Once time on task is modelled it is no longer significant, or it reverses, while the ROI tracks RT strongly. On these data the dACC congruency effect cannot be separated from time on task.

**Honesty notes (no-fake-traps discipline, from Step 0):**
1. **Event provenance had to be rebuilt.** RT/accuracy-bearing events exist for only 6 subjects. I rebuilt everyone's trials from the E-Prime export:
   - BIDS run-N = block letter N, not presentation order;
   - two lead-in trials are dropped;
   - ReactionTime/Accuracy count late responses.

   The rebuild was validated exactly against all 12 derivative events files and all 48 raw events files (`step0/run.log`). RC4114 has no session-1 log and is excluded.
2. **The first probe run was null, and it was wrong.** With naive frame times (volume i at i·TR) the raw dACC effect is t = 0.07. The derivatives are AFNI `tshift`-corrected to the mean slice time, so volumes sit at (i + 0.5)·TR. An onset-shift fit confirmed this (best R² at −1.2 to −2.4 s with naive frame times), and the reference was chosen on those grounds, not by its effect on the contrast. The naive run is kept as a recorded variant (`*_frame_offset0.*`). In that run the lever result still holds (RT-length t = −0.08, RT modulator t = −3.39). The instruction pins "slice-time corrected to the middle of each TR" so the compute step is not where agents diverge.
3. **The raw effect is weak** (p = 0.039 / 0.058 for the two 2 s-target models). The task is not "a robust effect collapses"; it is "a modest effect that is entirely accounted for by RT". The verifier therefore accepts both a "reproduces" and a "does not reproduce" face-value framing, provided RT/time on task is linked to the imaging result.
4. **The RT-modulator reversal is partly arithmetic.** It is the expected result when a region scales with RT and carries no extra congruency signal (Mumford 2023). Centring RT within condition would reproduce the fixed-length estimate by construction, so it is not used. The RT-length model is the cleaner "no longer significant" test.
5. **The interpretation is contested.** Conflict-monitoring theory predicts dACC activity scales with RT (Yeung et al. 2011). The reference concludes only that the incongruent − congruent difference adds nothing beyond RT here, not that conflict monitoring is refuted.
6. **Older cohort, 2 of 6 runs.** Both limit power for the raw effect, not for the lever (RT slope t = 6.8). The between-subject correlation of the ROI effect with the RT cost is r = 0.09 (n.s.). It is recorded, not used: the time-on-task account is trial-level.

### Verifier (2 plain checks)

`tests/test_outputs.py`:
1. **Compute check.** `subjects.csv` has ≥ 22 participants with a finite `roi_conflict`; the mean RT conflict effect, from both the CSV and `group_results.json`, is in 120–165 ms (measured 142; the mean/median/all-trial variants give 138–145); a group ROI t is reported.
2. **Judgement check.** `findings.md` must link RT / time on task to the *imaging* result, within one sentence that also names the brain side (dACC, ROI, activation, …). Any one of these counts:
   - (a) RT entered the model and the effect collapses or reverses;
   - (b) RT explains or confounds the effect;
   - (c) the effect is driven by, attributable to, or cannot be separated from time on task;
   - (d) a "time-on-task artifact".

   Guards against the recurring pipeline-vocabulary false pass:
   - "conflict effect" alone does not count as brain-side, because it is also the behavioural RT cost;
   - "RT outliers / trimming" phrases do not count as modelling RT;
   - a negated "no RT modulator was used" does not count.

**Offline discrimination** (`python tools/check_verifier.py ANTCONFLICT-001`, all fixtures synthetic except the reference; no agent has run yet):

| fixture | expected | observed |
|---|---|---|
| reference (oracle findings.md, verbatim) | PASS | PASS |
| correct: RT-length epochs wording | PASS | PASS |
| correct: "cannot be separated from time on task" + modulator | PASS | PASS |
| flat "reproduces", RT cost as behavioural validation (hypothesised modal answer) | FAIL | FAIL |
| flat "weak / does not reproduce" (correct-trials p = 0.058) | FAIL | FAIL |
| pipeline names an RT parametric modulator, flat reproduction | FAIL | FAIL |
| vague hedge ("RT differences can influence BOLD in general") | FAIL | FAIL |
| behavioural "conflict effect reflects longer RTs" + dACC in the same sentence | FAIL | FAIL |
| "controlled for RT outliers" + flat null | FAIL | FAIL |
| "no RT modulator was used" + flat null | FAIL | FAIL |

A further 14 ad-hoc phrasings were checked while tuning, 7 that should pass and 7 that should fail; all behave as intended. The two hardest negatives are now fixtures.

### Difficulty (NOT YET MEASURED)

Oracle reward: not run in-container yet. The local run of `solution/compute.py` (Python 3.14, same pins) reproduces `step0/evidence.json` exactly.

| agent | runs | reward | what it did (hand re-score) |
|---|---|---|---|
| **GPT-5.5 (codex, xhigh)** | 0 | — | not run |
| **Claude Opus 4.8** | 0 | — | not run |

The hypothesis to test (`step0/evidence.json` → `agent_headroom_hypothesis`) is that agents fit the default event model from `events.tsv`, report the RT cost as validation, and give a flat verdict. Do not call this task hard until ≥ 2 families × k ≥ 3 fail it for that reason, and the fails have been hand re-scored. When real agent findings.md files exist, add them as fixtures. They are the real test of the judgement regex.

### Cost

`hard`. cpus 4, mem 8 GB, storage 40 GB, internet on. At runtime the task downloads 48 BOLD runs × ~424 MB (~20 GB), 48 events files and the 6.6 MB E-Prime zip from the public OpenNeuro S3 bucket. That took ~35 min at ~9 MB/s on the authoring host and should be faster on cloud runners. The analysis takes ~1.5 min (5 GLMs × 48 runs; 92 s locally) with a peak RSS of 1.5 GB. Timeouts: agent 10800 s, verifier 3600 s, build 2400 s. Deps: numpy 2.5.3, scipy 1.18.1, pandas 3.0.6, nibabel 5.4.2, nilearn 0.14.1, scikit-learn 1.9.1. Dev runs can point `DS001907_DIR` at a host cache to skip the download (local only, never committed).
