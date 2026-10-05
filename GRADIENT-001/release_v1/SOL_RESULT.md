# Fresh Sol Max calibration — 2026-10-04

**Outcome: reward1.0 in one fresh, frozen GPT-6.1 Sol Max attempt.**
Source/code/trajectory review supports a legitimate solution, not answer leakage
or a verifier shortcut. This version is a qualified methods/control candidate;
the run does **not** support classifying it as Sol-resistant. One attempt is not
a pass-rate estimate or evidence that every agent/model will solve it.

## Frozen execution

- Core implementation: `ac00521`; qualification/runtime report: `bb4f6f0`.
- Model `openai/gpt-6.1-sol`, effort `max`, Codex CLI0.160.0, k1, zero retries.
  Exact model/effort also verified in the raw session's turn context.
- Native Harbor completed one trial, no errors/exceptions. Agent time816.443s
  (13.6min); full launcher865.299s; held-out evaluator3.930s.
- The same task, images, estimator, source partitions, tolerances and verifier
  used for oracle/control qualification were retained. No post-result edit,
  regrade, hint, restart or model-specific scoring exception was used.
- Coding agent stopped before the separate offline verifier started. Actual
  receipts show2CPU/8GiB, no extra swap/GPU, bounded tmpfs, unprivileged evaluator,
  immutable captured fit and no surviving candidate processes. Terminal cleanup
  succeeded; no owned containers/networks remained.

Trial:
`/home/zijiaochen/projects/brain_researcher_benchmark/tracking/scientific_release_2026-10-04/jobs/pr200-heldout-v1-sol61-max-k1/GRADIENT-HELDOUT-001__z6cDnDu/`.

## Raw trajectory and code review

The primary and two independent review agents inspected the retained trajectory,
raw session, captured code/output and runtime receipts without rerunning or
modifying the submission. Review found:

1. The sole task prompt is the frozen public instruction. Observed commands read
   public/discovery files, implement new code and run discovery-only self-tests.
   No private verifier/oracle imports, held-out source access or network fetch
   were observed. The image boundary excludes those source/private files.
2. The agent implemented original-storage float64 decoding, atlas parcel means,
   nuisance regression and exact-constant/activity guards. It selected support
   from the discovery intersection, formed the group FC and computed all10
   leave-one-person-out fits on that frozen support.
3. The submitted evaluator contains actual source-based estimation, signed
   sparsification/tie handling, nonstationary largest-algebraic eigensystems and
   each participant's own network-C calculation. It loads the captured discovery
   support/axis, computes held-out operators and projects that fixed axis for
   Rayleigh transfer; it does not substitute held-out optimal axes or hardcode
   expected participant measurements.
4. The agent wrote an alternate numerical cross-check, exact-constant/rank/
   degenerate-spectrum/null tests and a resource-limited CLI self-test. Its
   relabelled-data CLI test explicitly hardlinks **discovery** files under
   evaluation IDs; it is not access to the real held-out data. Those tests are
   agent self-checks, not independent scientific replications.
5. The frozen real evaluation retained all10 slots:9 defined plus
   `sub-pixar124` with source-inactive parcel119 and dependent nulls. Mean
   Rayleigh fraction0.5740165411839219; range0.3339446525698709–0.7355950115329685.
   Discovery C=-1.4012944324090497 (`between`); mixed individual signs are retained.
   No forced-positive-paper finding or unsupported population inference appears
   in the final response.

The only observed command failure was unavailable `rg`; the agent successfully
used standard alternatives. It was not a task/science failure or a job retry.

## Authoritative artifacts

All paths below are relative to the release evidence root
`tracking/scientific_release_2026-10-04/`; full hashes are also collected in
`sol_evidence_summary.json`.

- Job `result.json`: `2b77f1f3e55a16594f5c3e4e34eb81c653d067bd170f92a4329d095d91cc88c4`.
- Trial `result.json`: `05c2f678febe73f70e5389010cdf3d85cbcf73568d99e40263e225ca87f39806`.
- `agent/trajectory.json`: `71c88c8224a2505497cb483b6acd6a686bd6d1aa75229c19c3162dfe5192d320`.
- Captured `discovery.json`: `a5d2092dec9d5728810e8980ebbfaf7b9c67d0ddf37b5808d97d511aaf3cf576`.
- Captured `evaluate.py`: `588ffe8f30a4f88e92c896420878b738682f8bbde25df57f4554a2e199c072a4`.
- `verifier/evaluation.json`: `3653c50522762488ded8eba51f711f90abe4ef23e1acf1c091f7ca4cba7691c0`.

Raw Codex stdout, full session JSONL, resolved configuration, verification stdout,
image/runtime receipts, reward and cleanup evidence are retained alongside these
artifacts. The historical original #200 raw0 and its task/output bytes remain
unchanged: this is a **new task version and new trial**, not a repaired old score.

## Decision

Keep this version as a transparent paper-derived method-validation/control
candidate, not as a validated hard task. It still does not reproduce the original
adult-HCP finding, establish anatomical validity, population/age effects or
statistical significance. Real source cases here have simple leading blocks;
passing this cohort alone does not certify every degenerate-spectrum case.

To pursue difficulty, design a substantively different scientific inference or
robustness question and justify its data/estimand/evaluation contract **before**
another calibration. Do not hide the estimator, tighten tolerances, add arbitrary
formatting traps, force a positive finding, or count old schema zeros as failures.
No further model run, source analysis, push or merge is authorized by this report.
