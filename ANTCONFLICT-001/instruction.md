# Reproducing the ANT executive-network (conflict) activation in dorsal ACC (ANTCONFLICT-001)

## Scientific context

Fan, McCandliss, Fossella, Flombaum and Posner (2005, *NeuroImage* 26:471, "The activation
of attentional networks", doi:10.1016/j.neuroimage.2005.02.004) ran an event-related fMRI
version of the Attention Network Test (ANT). They reported that the **executive-control
network**, indexed by the flanker **conflict contrast (incongruent − congruent targets)**,
activates the **dorsal anterior cingulate cortex** together with lateral prefrontal cortex.
A dorsal-ACC response to flanker and Stroop conflict is one of the most replicated findings in
cognitive-control neuroimaging, and it is the empirical basis of the conflict-monitoring
account of ACC function.

## Task

Using OpenNeuro **`ds001907`** ("ANT: Healthy aging and Parkinson's disease"), **reproduce
this result in the healthy-aging group and report whether it holds on these data.**

Everything is public, with no credentials, at `https://s3.amazonaws.com/openneuro.org/ds001907/<key>`:

- **Participants:** the 24 healthy older adults who have a session-1 behavioural log:
  `RC4101 RC4103 RC4106 RC4107 RC4109 RC4110 RC4111 RC4112 RC4113 RC4115 RC4116 RC4117
  RC4118 RC4119 RC4120 RC4121 RC4122 RC4123 RC4125 RC4126 RC4128 RC4129 RC4130 RC4131`.
  Use session 1, ANT runs 1 and 2.
- **BOLD:** `derivatives/sub-<id>/ses-1/func/sub-<id>_ses-1_task-ANT_run-<n>_bold.nii.gz`
  (about 420 MB each, 48 files). These are the dataset's AFNI `afni_proc.py` outputs:
  despiked; slice-time corrected to the middle of each TR; motion corrected; nonlinearly
  normalised to MNI152 2009c at 2 mm; blurred; cleaned with ANATICOR. No task model has been
  applied. TR = 2.4 s, 149 volumes.
- **Events:** `sub-<id>/ses-1/func/sub-<id>_ses-1_task-ANT_run-<n>_events.tsv`, with onsets in
  seconds from the first volume. Each trial is a cue (`NoCue`, `CenterCue`, `SpatialCue`)
  followed by a flanker target (`Congruent`, `Incongruent`). On error trials these are
  labelled `CueErr` and `TargetErr` instead.
- **Per-trial responses:** `derivatives/ANT-eprime-export.zip`, which holds E-Prime 2 text logs
  (UTF-16). Participant `RC4<NNN>`'s session 1 is `RC4-ANT-1/ANT_fMRI_Session1-<NNN>-1.txt`.
  How the logs map onto the events files:
  - Each scanned block is a `Run<L>Proc` frame. Its `TrigTest.RTTime` is the first-volume
    trigger, in ms.
  - BIDS run *n* is block letter *n* of A–F, so run-1 is `RunA` and run-2 is `RunB`.
  - A block's trials are the `TrialProc` frames in `Run<L>TrialList`, in order. The first
    two trials are lead-in trials and do not appear in `events.tsv`.
  - `SlideTarget.OnsetTime` minus the trigger gives the target onset in `events.tsv`.
  - Use the `ReactionTime` (ms) and `Accuracy` fields.

The analysis has two parts:

- **Behaviour.** Per participant, compute mean RT on correct trials and accuracy, separately
  for congruent and incongruent targets. The behavioural conflict effect is
  RT(incongruent) − RT(congruent). Test it across participants.
- **Imaging.** For each run, fit a first-level GLM with the cue and target events convolved
  with a canonical HRF. Form the **incongruent − congruent** contrast and combine the two
  runs per participant. Average each participant's contrast over a **10 mm-radius sphere at
  MNI (0, 16, 42)** (dorsal ACC, the location reported for this contrast in the
  literature). Run a group one-sample t-test across the 24 participants.

The modelling choices the analysis leaves to the analyst (HRF, temporal filtering, signal
normalisation, error trials) should follow common practice.

Report, in plain terms, **whether the dorsal-ACC conflict activation reproduces on these
data**, stating only what your analysis actually supports.

## Output Location

Write all outputs to `${OUTPUT_DIR}` (default `/app/output`).

## Required Outputs

- `subjects.csv`: one row per participant, with columns
  `subject, rt_congruent_ms, rt_incongruent_ms, acc_congruent, acc_incongruent, roi_conflict`.
  `roi_conflict` is the participant's incongruent − congruent effect averaged over the ROI.
- `group_results.json`: `n_subjects`, plus the group tests as
  `{"rt_conflict_ms": {"mean": ..., "t": ..., "p": ...}, "roi_conflict": {"mean": ..., "t": ..., "p": ...}}`.
- `run_metadata.json`: dataset id, the participants and runs used, the first-level model
  specification, and the choices you made.
- `findings.md`: a short written summary stating whether the dorsal-ACC conflict activation
  reproduces on these data. State only what your analysis actually supports.

## Failure handling

If the dataset cannot be resolved, exit non-zero with `failed_precondition` and a
non-empty reason, and still write parseable `run_metadata.json`, `group_results.json`,
and `findings.md`.
