# Design review — 2026-10-04

Disposition: suitable to commit as a **non-runnable design and arithmetic
prototype**, not as a source-qualified benchmark or difficulty result.

Root reviewed the question, contract, feasibility evidence and prototype.
An independent read-only reviewer examined the scientific design and final
arithmetic without executing tests or decoding new source arrays. Root reran
`python -m pytest -q test_protocol.py`: **25 passed**. These manufactured
fixtures are engineering checks, not a new MRI result or oracle run.

Changes made during review:

- No held-out Procrustes, sign selection, or component selection is fitted to
  improve the primary outcome. A discovery axis is evaluated directly on each
  held-out operator after explicit stationary-mode projection.
- Discovery-only support is frozen. A held-out source-inactive person remains
  a counted null row rather than collapsing all other people's scores or
  changing the training support.
- The transfer numerator, denominator, stationary overlap and spectral
  diagnostics are retained. A flat nontrivial spectrum can yield ratio one
  without a preferred direction; average spectral energy and the excess over
  it expose this case without inventing a significance threshold.
- Network configuration is distinct from transfer and global DMN-apex claims.
  Complete unresolved eigenspaces have a range, not a favorable chosen axis.
- Numerical scaling is made explicit and tested at tiny/large scales. Basis
  invariance is qualified by numerical resolution of the represented span.
- The cohort is an already inspected public developmental movie convenience
  sample, not pristine validation data or the paper's HCP cohort.

Remaining release gates: authenticate source and metadata split; measure
coverage and suitability of the inherited spatial approximation; implement and
test discovery-only fit/evaluate isolation; independently reconstruct/certify
operators and spectra; finish public schemas and source-backed grading; oracle
and adversarial controls; frozen-version model calibration and trajectory review.

No old task files, source observations, oracle results, raw Sol outputs or
scores were changed. No source pilot, cohort expansion or new Sol run occurred.
