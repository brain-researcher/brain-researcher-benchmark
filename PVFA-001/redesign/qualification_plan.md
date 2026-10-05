# Qualification TODO and decision contract

## Completed in this proposal

- Kept evaluated task and raw Sol output untouched; new files only.
- Defined model/budget-conditioned witness evidence instead of point-matching.
- Preserved exact source identity, preprocessing and descriptive sample scope.
- Inspected legacy bank **keys/shapes only**: 4,083 ROI coordinates; smoothed
  b0+1000+2000 signal array `(4083,129)`; original sampled signals `(4083,193)`.
- Added and tested source-free witness arithmetic with manufactured fixtures.
- No real-data fitting, cache creation, source download, Docker run or Sol run.

## 1. Approve a bounded real-data pilot before running it

Resolve these choices in `scientific_contract.json` and commit them before
inspecting redesign outcomes:

- Parameter domain: physically admissible tissue tensor, fitted S0 relative to
  measured b0, and treatment of near-pure-free-water boundary cases. Bounds
  should be justified and sensitivity-tested, not selected to manufacture FA
  separation. Keeping `f=1` out of tissue-FA witnesses avoids assigning tissue
  FA when that compartment contributes no signal.
- Publish and qualify arithmetic tolerances separately from scientific domain
  limits. A rank-deficient PSD tensor may produce tiny negative eigenvalues
  under rotation/roundoff, and released rounded b-vectors need not have norm
  one to 1e-8. The prototype exposes both tolerances explicitly; its unit-test
  choices (1e-15 mm²/s absolute, 1e-12 tensor-relative cap, and 1e-6 gradient
  norm) are **not release calibration**. The effective eigenvalue tolerance is
  `min(atol, rtol * max(abs(eigenvalues)))`; an absolute tolerance alone could
  admit materially indefinite near-zero tensors. Scale-normalized FA avoids
  underflow for tiny positive tensors; no clipping is performed.
  Preserve source vector values rather than silently renormalizing them.
- A deterministic voxel selection independent of redesign fit outcomes, plus
  a complete-ROI qualification plan. Do not handpick the legacy 49 numeric
  disagreements as the new task population.
- CPU count, memory, wall time, maximum fits, optimizer settings for authoring
  only, cache location, read-only source mounts and a stop condition. Start
  with existing authenticated cached observations; no new download/GPU needed.
- Whether the single-shell sensitivity is retained. It introduces both a
  second b-value and more observations, so it cannot isolate shell design at a
  fixed measurement budget. Per-protocol mean-SSE ceilings are not guaranteed
  nested sets, and comparing witness lower bounds does not measure actual
  interval contraction. A nested-constraint redesign would be a separate
  prospective contract decision.

Concrete recommended pilot, **proposed, not launched or approved**:

- 16 ROI voxels, selected by the midpoints of 16 equal index bins after
  lexicographic `(i,j,k)` sorting. Selection depends only on the frozen ROI,
  not old Sol errors, redesign residuals or ambiguity outcomes.
- Two protocols; two independent optimizer implementations; two starts for a
  baseline and each of five fraction-profile points. Select those five points
  prospectively after reviewing the parameter domain. Maximum **768 fits**
  (`16 * 2 * 2 * 2 * (1 + 5)`), with no retry beyond that budget.
- **1 CPU, 2 GiB memory, 15 minutes wall time, zero GPU/network**; BLAS threads
  limited to one. Read-only authenticated source cache. Write pilot evidence
  to a separate versioned authoring directory, never original outputs.
- Stop on provenance failure, wall/memory/fit cap; retain partial receipts and
  report incompleteness. Do not stop because a desired ambiguity pattern has
  appeared. These caps test feasibility, not scientific adequacy.

If full `4083 × protocols × profile points × starts` is too costly, retain
complete ROI bookkeeping and low-loss fits but move intensive profiles to a
public, deterministic, outcome-independent audit subset fixed before fits.
Limit profile conclusions to that subset; no population-wide ambiguity claim
or choosing only the hardest legacy voxels. This is a proposed scope option,
not permission to change coverage silently after seeing outcomes.

## 2. Freeze a scientifically honest discrepancy contract

- Compare residual behavior and feasible parameter sensitivity, without using
  Sol success/failure to choose cutoffs.
- A public ceiling may be based on independently checked feasible fit loss plus
  prespecified sensitivity budgets. Label it an operational discrepancy set,
  not a likelihood-ratio confidence region or proof of global optimality.
- Do not let a poor submitted baseline enlarge its own admissible set.
- Freeze multiple budget values and exact arithmetic tolerances before model
  evaluation. Publish their provenance and units.
- Qualify fit/profile requirements that make an empty search fail while allowing
  genuine unresolved cases. If this cannot be done without a private recipe,
  simplify the question or do not release it.

## 3. Build and independently validate the reference evidence

- Export preprocessing-only contract; authenticate/rebuild the source cache.
- Refit with the reviewed domain. **Do not reuse old unconstrained fitted
  tensor parameters as physical ground truth.**
- Obtain independent candidates/witnesses, compare signal loss not coordinates
  in parameter space, and investigate material disagreement.
- Preserve all source rows and profile failures. Store both numerical evidence
  and limitations; do not prescribe a desired scientific conclusion.
- Verify a second implementation can pass under the public contract.

## 4. Turn the proposal into a benchmark, then measure difficulty

- Publish exact schema/scoring; replace rather than append incompatible legacy
  contract rules in a new task version.
- Implement source-bound semantic verifier and the negative controls listed
  in `verifier_design.md`.
- Run in-container oracle and adversarial tests. Freeze source/task/image/
  verifier versions and evidence receipts.
- Only then launch a fresh blinded frontier run with a reviewed model/resource
  contract. Keep previous raw scores as historical, incomparable task versions.
- Diagnose failures scientifically. A pass is evidence against the current
  hardness hypothesis; one run is not a pass-rate estimate. Further frozen,
  blinded trials may be needed. Neither a pass nor failure justifies hiding
  the contract or retuning accepted outcomes to the model's observed result.
