# PVFA identifiability redesign — diagnostic work, not a released benchmark

This directory is an isolated experimental redesign. It does **not** replace the
evaluated task, its oracle, its verifier, or its historical score.

## Current evidence index (2026-10-04 local date)

- `PILOT_RESULT.md`: completed bounded fitting feasibility study; no scientific
  adequacy or model-hardness conclusion.
- `PHASE2_RESULT.md`: selected-source and residual diagnostic, with numerical
  disagreements preserved in its original receipt.
- `PHASE3_RESULT.md`: unchanged-candidate replay explained those disagreements
  as numerical-substrate boundary roundoff; no new fits.
- `PAIRED_SHELL_RESULT.md`: completed no-optimizer, ideal-PSD paired-shell
  descriptive diagnostic on the same 16 voxels, with all 1,024 pairs retained.
  This is **not** an operational numerical-domain bound or a noise estimate.
- `ADEQUACY_SEARCH_PROPOSAL.md` is the historical proposal: its part A has now
  been implemented and run in the explicitly non-certified descriptive form;
  part B's 128-fit extension remains unimplemented and unauthorized. See
  `PAIRED_SHELL_REVIEW.md` and the hash-bound contract for the exact executed scope.

No Sol run or original-output regrade has been performed for this redesign.
Source-specific evidence and reference arrays remain private. Public source and
reports do not constitute a portable runnable release: diagnostic launchers
depend on separately provisioned pinned private inputs, image and approval.

## Original proposal and interpretation

The scientific question is whether materially different tissue-FA values can
explain the same measured signal within a **publicly defined discrepancy
budget**, under the stated two-compartment model. A passing witness demonstrates
ambiguity within that model and budget. It does not establish true tissue FA,
a statistical confidence interval, or non-identifiability under every possible
acquisition/model.

Files:

- `draft_instruction.md`: proposed agent-facing question and evidence outputs.
- `scientific_contract.json`: fixed source identities and release-blocking choices.
- `verifier_design.md`: proposed source-bound grading and adversarial checks.
- `qualification_plan.md`: bounded next steps and required resource decisions.
- `witness.py`, `test_witness.py`: solver-independent arithmetic prototype and
  manufactured unit tests; these are **not real-data qualification**.

Run the source-free unit tests from this directory with
`python -m pytest -q test_witness.py`. The prototype intentionally rejects an
unqualified release contract. It does not assign a Harbor reward.

Base: PR #156 task version `bc97e76f8787040f1ee7b6a72beb14e74d21c235`.
Original source manifest: `../environment/data_manifest.json`.

## Paper connection

Henriques et al. (2017), [Eq. 1, Eq. 8 and Figure 4](https://samuelstjean.github.io/downloads/Henriques_et_al_2017.pdf),
anchor the signal model, signal-space residual and comparison of conventional
versus free-water-model FA. This proposal adds a sensitivity question; it does
not claim to reproduce their exact figure/cohort. Their in-vivo analysis excludes
high b-values to limit unmodelled non-Gaussian diffusion, which is why a b=3500
holdout is not the default validation target here.

Golub et al., [Theory 2.1, Figures 5–7 and Discussion 5.2–5.6](https://arxiv.org/pdf/2007.06359),
motivate separating plausible maps, fitting behavior and specificity. Their
effective-fraction notation uses a **tissue** fraction; this task consistently
uses `f` for the **free-water signal fraction**. Their results do not supply the
answer for this Sherbrooke acquisition.

## Release status

**Not runnable as a benchmark yet.** The scientific adequacy/noise contract,
public scoring discrepancy budget, and search-completeness requirements remain
unqualified despite completed bounded diagnostics. Keep this a model-conditioned
sensitivity/diagnosis study unless those choices can be independently justified.
Do not infer task difficulty from numerical disagreements or select a passing
cutoff from observed residuals.
