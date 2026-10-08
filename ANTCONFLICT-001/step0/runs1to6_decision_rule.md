# Step 0, second attempt: session-1 runs 1-6 (decision rule fixed before the data were analysed)

Written 2026-10-08. At this time runs 3-6 were still downloading and none of their BOLD had
been analysed. Runs 1-2 were already known. They are why this attempt exists: v2 face value
p = 0.057 (all trials), p = 0.081 (correct trials); independent nilearn pipeline p = 0.063.

## Why

On runs 1-2, RAW is not significant, so the gate ("CTRL flips RAW from significant to null")
was never met. ds001907 has six ANT runs in session 1 (blocks A-F of the same E-Prime log). The
two-run restriction was a power choice, not a property of the data. This attempt asks whether
the full session gives a significant RAW that the RT controls then remove.

## Fixed analysis

Unchanged from v2 except for the run list:
- `step0/probe.py` with `RUNS=1,2,3,4,5,6`, common regressor scaling and mid-TR frame times
- the same 24 participants, 10 mm sphere at MNI (0, 16, 42), models and group test
- `step0/alt_pipeline_check.py` with the same six runs, as the independent "typical agent"
  pipeline

The E-Prime mapping for runs 3-6 is checked by `eprime_events.validate()`. It must match the
derivative events of the six subjects that have them, and every subject's raw events.tsv.

Session 2 is not used, whatever this result. Adding it after seeing session 1 would be a
second look.

## Decision rule

**RAW holds** only if all three hold:
1. oracle model `std_correct`: t > 0, p < 0.01
2. `std_all`: t > 0, p < 0.05
3. independent pipeline, glover HRF, slice_time_ref 0.5: t > 0, p < 0.05

**CTRL flips RAW** only if both hold:
4. `rt_duration`: p >= 0.05
5. `rt_modulator`: p >= 0.05, in either direction. A significant negative modulator contrast
   is a reversal that pure time on task does not predict (noise-free simulation: about 0;
   `step0/scaling_check.py`). It does not count as a null.

**Verdict.**
- 1-5 all hold: proceed to a rebuild on six runs (instruction, oracle, verifier, fixtures).
- Otherwise: `archive`. Log the kill on TASK_BOARD.md and stop.

No other variant (subject set, ROI, HRF, error handling, sessions) may be added to rescue a
failed rule.
