# Source-bound verifier design

This is a design, not an implemented release grader. `witness.py` implements
only the arithmetic in steps 3–4 below; it neither authenticates inputs nor
proves completeness of a search.

1. Authenticate original source hashes, corrected gradient orientation and
   preprocessing-only contract. Reconstruct the ROI and protocol signals, or
   verify an independently built source cache against those operations. The
   old `reference.npz` contains useful source arrays **and** obsolete fitted
   answer arrays: never mount the whole file as an agent input.
2. Require exact source-coordinate/protocol/budget/profile coverage and unique
   candidate identities. Include failures rather than dropping hard rows.
   Derive observation normalizations and budget/domain values from trusted
   artifacts, never from submitted fields.
3. Reconstruct `D`, `S0`, `f`, predicted signal, normalized discrepancy and FA.
   Reject nonfinite parameters, indefinite/zero tensors and domain violations.
   Do not clip negative eigenvalues or compare to a reference tensor. Different
   solvers, tensor parameterizations and eigenvector signs must be equivalent.
   A published, qualified tensor-relative cap must also bound any absolute PSD
   roundoff tolerance; otherwise tiny but materially indefinite tensors could
   pass. Report raw eigenvalues and effective tolerance, and calculate FA with
   scale-stable arithmetic. Prototype tolerances are test-only, not qualified.
4. A witness requires two valid candidates under the same source/protocol/
   budget, both below its public ceiling, with the public FA separation. Two
   equally poor fits, one duplicated fit or a self-declared residual do not
   qualify. The observed pair separation is only a lower bound on the range.
5. Enforce independently qualified **public** fit/profile quality and coverage
   requirements. This remains a release blocker: accepting unresolved labels
   without low-loss/profile evidence would make a caveat-only solution pass;
   secretly requiring a particular alternative fit would recreate the old
   problem. Neither is acceptable. A compliant numerical search may honestly
   report no witness at every voxel; do not force a positive ambiguity result.
6. Recompute descriptive summaries on complete support. Report unresolved
   coverage separately, not as zero width or identified tissue. No significance
   test treating 4,083 smoothed voxels as independent participants is supported.
7. Audit interpretation against numerical evidence with human review during
   authoring. Do not approximate scientific understanding with private prose
   keywords. Machine scoring should be tied to the explicit numeric contract.

## What a reference answer must contain

The new reference is a source-bound evidence package: independently checked
low-loss candidates, multiple admissible witnesses where found, full attempted
profile records and qualified numerical ceilings. It is **not** one canonical
FA map. Any independently valid candidate satisfying the same public criteria
must be accepted, including a better fit than the authoring solution.

Do not call numerical endpoint searches global extrema unless a valid bound is
provided. The proposal does not currently require or implement such a bound.
A reference answer that cannot establish required profile quality is a task
qualification failure, not evidence that models should fail.

## Adversarial qualification matrix

| Submission/control | Expected behavior |
| --- | --- |
| Valid separated fits from an alternative solver | Accept the numerical evidence |
| Better source fit than the reference | Accept; retain as evidence, do not point-match |
| Same fit twice; only change eigenvector signs | Reject as a separated-FA witness |
| Two widely separated but high-residual fits | Reject against public loss ceiling |
| Negative eigenvalues repaired only for reported FA | Reject physical-domain violation |
| Swap voxel signals, shell indices or gradient orientation | Reject source binding/arithmetic |
| S0 fixed in reported values but predictions use another intercept | Reject reconstructed signal inconsistency |
| Missing hard voxels or profile points | Reject coverage |
| All `no_witness_found` with no useful fits | Reject public numerical evidence requirement |
| No witness found after a valid search | Keep unresolved; never infer uniqueness |
| All rows have no witness but fulfill qualified fit/profile obligations | Accept the evidence; do not force an ambiguity outcome |
| Correct data with an unannounced alias/field representation | Fix public schema rather than score scientific failure |
| Wider/narrower ranges than anticipated, with valid evidence | Do not force an expected direction |

The optional two-protocol comparison uses differently normalized mean losses
and separately qualified ceilings; its admissible sets need not nest. Neither
their independently found FA-range lower bounds nor a change in their median
establishes true interval contraction or improved biological identification.

Near `f=1`, tissue signal can become arbitrarily small even though `f<1`.
Domain sensitivity and boundary flags must therefore be part of qualification;
excluding exactly `f=1` does not remove all practical degeneracy.

Prototype tests use manufactured numerical fixtures only. They show forward
model, invariance, domain, witness and fail-closed behavior. They do not establish
that the real data contain separated admissible solutions or a hard task.
