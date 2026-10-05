# Design review — 2026-10-04

Disposition: suitable to commit as a **non-runnable design and arithmetic
prototype**, not as a qualified benchmark or difficulty result.

Root reviewed the question, contract, verifier plan, arithmetic and tests.
An independent read-only reviewer examined the scientific design and final
prototype. The reviewer did not execute tests or refit source observations.
Root independently ran `python -m pytest -q test_witness.py`: **46 passed**.
Fixtures are manufactured arithmetic controls, not scientific simulation
reproduction, source-data qualification or a Harbor oracle.

Changes made during review:

- No witness found is not proof of identifiability. Complete compliant searches
  may legitimately find no witnesses; caveats without numerical work may not.
- Separately normalized single/multi-shell loss sets need not nest, and found
  ambiguity lower bounds do not establish interval contraction.
- Rounded released gradient vectors must be preserved, with an explicit
  qualified norm tolerance rather than an undisclosed normalization.
- PSD boundary arithmetic is public and scale-aware. A tiny indefinite tensor
  cannot exploit an absolute tolerance to fabricate FA; no eigenvalue/FA
  clipping is used. Positive tiny tensors and rotated rank-one tensors have
  manufactured controls.
- Full-ROI profiling may be needlessly expensive. A prospectively selected
  outcome-independent profile subset is a proposed scope option, not a hidden
  exclusion of difficult cases.
- A single Sol pass/failure is not a pass-rate estimate.

Remaining release gates: justify the domain and discrepancy budgets; qualify
profile quality/coverage and boundary behavior; approve and run the bounded
real-data pilot; implement authenticated source binding and a complete public
schema/scoring contract; independent positive/negative controls; in-container
oracle; fresh frozen-version model calibration and trajectory review.

No old instruction, environment, oracle, verifier, raw output or score is changed
by this package. No scientific pilot or model run was launched.
