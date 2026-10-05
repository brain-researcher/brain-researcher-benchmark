# Phase 3 result: numerical-substrate diagnosis confirmed

The unchanged-candidate replay completed successfully. Using the exact canonical
cached signal reproduces all available phase-1 metrics and classifications;
using the independently reconstructed signal reproduces phase 2. The six
differences are strict S0/b0 boundary roundoff, not different fitted parameters,
forward-model predictions, or a need to relax scientific bounds.

## Retained evidence

Root ran committed code `8e67fe90326f420a9d88fc8bcbfd7970da186157` under contract
SHA-256 `938baf9f77d1393523dc2b4d270010bf244d2808d4d9b85fa29fc8a839815b31`.
Evidence root:
`/home/zijiaochen/projects/brain_researcher_benchmark/tracking/scientific_release_2026-10-04/pr156_replay`.

- Status: `completed_canonical_substrate_replay`; scientific release: false.
- All 768 slots retained: 672 unchanged candidates and 96 missing candidates.
- Canonical feasible count: 635; reconstructed feasible count: 629.
- Canonical versus phase-1 mismatches: zero; reconstructed versus phase-2
  mismatches: zero.
- No membership change among the 32 fixed best representatives or the endpoints
  of the 288 prior sensitivity rows.
- Zero fits, no regrading, no domain/tolerance changes, no replaced pool.
- Host elapsed time: 1.026 s; replay routine: 0.344 s. Exit 0, no OOM, empty
  stderr, and exact-owned container cleanup succeeded.

`result.json` SHA-256:
`07baf997b1afbfde5267a15fd60c51bbf7c4b384b0b633652f2bb3d4db9659ba`.
`replay/candidate_replay.jsonl` SHA-256:
`660f4ac3858c72fd800859bb41f8b0c0534597dc8deaee7ac69992eff7d4da9a`.

## Exact diagnosis

Both evaluations use the same frozen phase-2 arithmetic; only the signal
representation differs. Maximum signal difference is `1.1368683772161603e-13`.
For example, at (32,70,30), canonical b0 is `64.07383958902018` and reconstructed
b0 is `64.07383958902015`. The unchanged S0 then gives ratios
`1.4999999999999998` and `1.5000000000000002`, respectively.

Attempts 16, 40, 66, and 647 cross the upper ratio boundary this way. Attempts
317 and 319 cross the lower boundary from `0.5` to `0.49999999999999994`.
All six original feasibility decisions are reproduced on the original exact
numerical substrate. No epsilon or clipping was introduced to force agreement.
Phase 2 remains recorded as `completed_with_arithmetic_disagreements`; this
new receipt explains it rather than overwriting it.

## Scientific boundary and next gate

This closes the selected numerical-substrate compatibility question, not model
adequacy or benchmark readiness. The previously reported 6–25% normalized
residuals, boundary dependence, and finite-search limitations remain. Neither
data noise, acquisition problems, physical gradient orientation, nor biological
identifiability is resolved. The replay uses an existing independent arithmetic
implementation and is not a third independent replication.

`ADEQUACY_SEARCH_PROPOSAL.md` remains design-only: a no-optimizer paired-shell
constraint diagnostic, requiring explicit numerical-PSD certification before
any rigorous accepted-domain lower-bound claim, and a separately reviewed
fixed 128-fit search extension. Neither was run or authorized by this replay.
Those prospective studies must precede any scientifically justified discrepancy
contract; they must not select a passing cutoff from these observed residuals.
No Sol run or claim about task hardness follows from this engineering result.
