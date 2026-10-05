# PVFA experimental source/report publication

This branch publishes the experimental **source and reports**, separately from
the original PR #156 repair and its unchanged historical raw reward. It is not a
new calibrated benchmark, a portable launcher, or a complete runnable release.

## Read these reports in order

- `PILOT_RESULT.md`: bounded exploratory fit/search results on the selected scan.
- `PHASE2_RESULT.md`: independent source and residual checks.
- `PHASE3_RESULT.md`: unchanged-candidate numerical replay; no new fits.
- `PAIRED_SHELL_RESULT.md`: the latest no-optimizer adequacy diagnostic (proposal
  A). Read its limitations before interpreting residuals or difficulty.

Proposal A was executed under its bounded contract. Proposal B's **128-fit search
extension has not been run**. Earlier proposal/review documents are
historical snapshots, not claims that later documented diagnostics never ran.
Neither numerical replay nor a model-derived necessary-condition diagnostic
supplies a calibrated noise model, a biological validation, a global-optimum
certificate, or a scientifically justified passing discrepancy threshold.

## Runtime and artifact boundary

The source snapshot is projected from `d31bb52d39bf333ae415f4d6971c93bd84cf1a72` without importing that
private branch's ancestors. Implementation Python/JSON files are unchanged.
The branch is based on the safe original-repair publication `98b57501d917646d9205cb813a8c66f67c3a9b7b`. All newly
reachable commits exclude the rebuilt verifier bank. Older public history is
unchanged; no claim is made to erase obsolete objects previously public.

Source-data capsules, selected-signal arrays, fit pools, full raw diagnostic
receipts, container images, and private reference banks are not included here.
Runtime scripts record the original host layout and frozen artifact identities;
they are execution snapshots, not permission to launch new analyses. A qualified
operator needs the separately held hash-bound inputs, approved resource contract,
and reviewed launch environment. See `../PRIVATE_ARTIFACTS.md` for the original
verifier bank boundary; its manifest does not provision every experimental input.

Source-free unit tests verify implementation arithmetic and fail-closed contracts
only. They are not real-data scientific validation. No new model attempt, score
regrade, or 128-fit extension was performed by this publication export.
