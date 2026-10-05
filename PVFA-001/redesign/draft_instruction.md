# How much tissue-FA information does this acquisition support?

> Draft only. Fields marked RELEASE BLOCKER in `scientific_contract.json` must
> be resolved before this becomes the public Harbor instruction.

Fit the provided Sherbrooke diffusion acquisition and investigate whether
substantially different tissue fractional anisotropy (FA) estimates remain
compatible with its observed signals. Supply numerical evidence, not only a
best-fit map or a warning that diffusion models have limitations.

## Data, scope and model

Use the original Sherbrooke image and the already orientation-corrected
b-vectors, verified against `/app/data/sherbrooke/data_manifest.json`. It is
one real example acquisition, not a population sample and not the original
cohort in the cited free-water studies. The acquisition has one b0 and 64
directions each at b=1000, 2000 and 3500 s/mm².

Keep the legacy source-defined proxy ROI and preprocessing fixed: the b0
brain mask, per-volume FWHM 0.625 **voxel** smoothing, low-b tensor seed and
dilated annulus are specified in the public preprocessing contract. Do not
rename the diffusion-defined mask a validated anatomical region, change its
thresholds after inspecting ambiguity, drop hard voxels, or treat voxels as
independent participants. The source NIfTI does not declare physical spatial
units; no verified millimeter smoothing length is claimed.

For each required voxel, use

`S_hat(b,g) = S0 * [(1-f)*exp(-b*g^T*D*g) + f*exp(-b*0.003)]`.

Here `f` is the free-water **signal fraction**, `D` is a symmetric
positive-semidefinite tissue tensor, and `S0` is fitted rather than silently
fixed to the single noisy b0 observation. Tissue FA is calculated directly from
the admissible tensor; clipping an indefinite tensor does not make it physical.
Follow the released parameter-domain bounds, not a private optimizer recipe.
Any solver, parameterization or initialization is acceptable.

The primary analysis uses b0+1000+2000. A proposed secondary analysis fits
b0+1000 on the **same** ROI, with the same model and domain. This is
protocol-specific operational sensitivity, not an equal-scan-time shell-design
experiment. Protocol-specific mean-SSE ceilings need not define nested sets;
independently found witness lower bounds cannot establish contraction of their
true FA ranges. Do not interpret a smaller found separation as proof of more
information. The direction or size of the difference is not predetermined.
The b=3500 data are not a required holdout:
tensor-model mismatch at higher b-values would confound that interpretation.

## Numerical question

For protocol `p` and voxel `v`, define the public discrepancy

`L_vp(theta) = mean(((S_hat(theta) - S_observed) / observed_b0)^2)`.

This is normalized signal-space mean squared error. It is **not** a calibrated
likelihood: one b0 observation and spatially smoothed data do not establish an
independent noise model. Each released budget defines an operational
admissible set `A_vp = {theta in domain: L_vp(theta) <= C_vp}`. The public
`C_vp` values are fixed by authoring qualification, not chosen by your output.

For every source voxel and released budget:

1. Produce a physically admissible low-loss fit, and document your search.
2. Search for two admissible parameter sets with different tissue FA. Retain
   both parameter sets, not just their scalar summaries. The verifier will
   reconstruct their signals and recompute their discrepancy and FA.
3. Report the largest FA separation you actually demonstrated. This is a
   **lower bound** on the FA range of `A_vp`, not its complete interval.
4. Report fraction-profile searches at the public profile points, including
   failed points and improved fits. A profile entry is a found candidate, not
   a proof that it is the global minimum. A search that finds no separated
   pair is `no_witness_found`, never `identified` or `unique`.

The release will specify public fit-quality and profile-coverage requirements.
An empty search or a caveat-only submission will not satisfy those numerical
requirements. A fully compliant low-loss/profile search may honestly find no
witness anywhere: this must remain acceptable evidence, not a forced-ambiguity
failure. The task will not be released unless independent solutions show the
public search-quality requirements are feasible.

## Evidence outputs

Write to `${OUTPUT_DIR:-/app/output}`:

- `candidates.csv`: `i,j,k,protocol,budget_id,candidate_id,Dxx,Dxy,Dyy,Dxz,Dyz,Dzz,S0,f`.
  Every cited fit/witness/profile candidate must have one unique row.
- `profiles.csv`: `i,j,k,protocol,profile_f,candidate_id,search_status`.
  A failed point retains its row with a blank candidate and nonempty reason.
  The release supplies the exact grid and permitted status meanings.
- `evidence.csv`: `i,j,k,protocol,budget_id,left_candidate,right_candidate,`
  `witness_status,fa_separation_lower_bound`.
  `witness_status` is `witness_found` or `no_witness_found`. Missing evidence
  is not encoded as zero ambiguity.
- `results.json`: source/contract hashes; protocol and budget identities;
  complete-support counts; validated witness counts; descriptive FA-range
  lower-bound summaries; and an explicit interpretation scope.
- `analysis.py` plus any local modules needed to reproduce outputs offline.
- `findings.md`: explain what the numerical evidence supports and what it
  leaves unresolved, tied to the output rows and paper's model assumptions.

All scalar summaries are recomputed from source-validated candidate rows.
No specific tissue-FA value, fraction, mean effect direction, solver trajectory,
or prose keyword is an answer key. Exact profile/scoring/output details remain
release blockers, not hidden requirements.

## Interpretation

A verified pair shows that two model parameterizations satisfy the stated
measurement-discrepancy criterion while disagreeing in FA. It does not show
that either is biologically correct or statistically indistinguishable under a
validated noise model. Conversely, a converged fit or an unsuccessful witness
search cannot establish unique tissue recovery. Report model-conditioned
evidence on this acquisition, not a clinical or population claim.
