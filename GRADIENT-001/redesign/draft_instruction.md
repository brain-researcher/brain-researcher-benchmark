# Does a connectivity gradient transfer to held-out participants?

**Draft, not an active task.** Source qualification and the public artifact
schema must be completed before this replaces a runnable benchmark version.

Margulies et al. (2016), Figures 1A/D and 3A/B, relate a principal connectivity
gradient to a contrast between default-mode and primary sensory/motor systems.
The paper's adult HCP resting-state analysis is not the supplied dataset. Your
task is a **paper-derived, held-out-participant method validation** on the fixed
20-person developmental movie release, not an HCP replication, a developmental
effect test, or evidence of a universal cortical hierarchy.

The scientific question is whether the leading axis learned in discovery
participants is also a high-energy direction in held-out participants' diffusion
operators, and whether independent participant gradients place the default-mode
network on the same side of both visual and somatomotor network means. These are
two different measurements; neither guarantees the other or a global DMN apex.

## Discovery and locked evaluation

Use the authenticated 20-person ds000228-derived bundle and all 168 released
frames. Split participants with the public metadata-only age-pair rule: sort
within child/adult strata by `(age, participant_id)`, pair adjacent people, then
assign one member of every pair to discovery using the documented hash rule.
This yields 8 children and 2 adults in each partition. Do not try alternative
splits. This is a newly locked analysis split on previously used public data,
**not pristine participants unseen by the old agent or task authors**.

Apply the predeclared extraction and no-band-pass nuisance treatment independently
within each participant. Retain only parcels with valid geometry and active
residual signal in **every discovery participant**. Freeze this parcel support
before evaluating held-out signals. Preserve the original parcel identifiers,
network coverage, and every exclusion reason. No held-out measurement may alter
the support, preprocessing, sparsity, or choice of gradient. All seven networks
must remain represented; mathematical computability does not establish adequate
anatomical coverage.

Estimate the discovery group FC as the equal-person mean. Build its symmetric
diffusion operator using the public recipe: signed top `ceil(0.1 * P)` entries
per row, normalized-angle affinity, and alpha=0.5. This is a declared
BrainSpace-derived adaptation, not the original paper's exact kernel. The axis
is the **largest algebraic nontrivial eigenvector**, not the component with the
best DMN contrast. Do not rotate components to manufacture that contrast. Report
the spectral gap and leave-one-discovery-participant stability without using
stability to select another axis or split.

## Held-out measurement

Evaluate each held-out person separately on the frozen discovery support. A
person whose signals are inactive on that support remains in the cohort and has
a source-justified undefined score; that person does not invalidate otherwise
computable people. Do not drop new parcels or silently add epsilon to undefined
correlations.

Let `u_D` be the unit discovery axis, `K_i` the symmetric held-out operator,
`s_i` its unit stationary eigenvector, and `lambda1_i` its largest algebraic
nontrivial eigenvalue. Set `v_i = u_D - s_i (s_i' u_D)` and normalize `v_i` to
unit length when defined. Report:

- `R_i = v_i' K_i v_i`, the frozen-axis Rayleigh quotient;
- `lambda1_i`, its maximum possible nontrivial value;
- `T_i = R_i / lambda1_i`, with the stationary overlap and projection norm.

Also report the held-out leading eigengap, nontrivial spectral mean
`(trace(K_i)-1)/(P-1)`, and `R_i` minus that mean. This last difference is a
descriptive comparator, not a random-parcel null test. A flat nontrivial spectrum
can give ratio one for any axis; that is not selective gradient transfer.

Do not orient, select, rotate, or fit the discovery axis using held-out gradients.
Changing eigenvector signs must not change these scores. A high ratio with an
almost-zero eigenvalue is not strong evidence of structure. Undefined stationary
projection, non-simple stationary mode, unresolved discovery axis, or a leading
held-out eigenvalue at numerical zero produces an explicit reason, not a guessed
score. A small numerical gap is not a biological stability threshold.

As a separate network characterization, calculate the unitless statistic

`C_i = (mean_Default(g_i) - mean_Vis(g_i)) *
       (mean_Default(g_i) - mean_SomMot(g_i)) / variance_parcels(g_i)`.

Here `g_i` is the person's principal diffusion coordinate and network means use
the retained source labels. Positive values put the DMN mean in the same
direction from both sensory means; negative values put it between them. This
does **not** test whether DMN is the maximum of all seven networks. The statistic
is invariant to sign and nonzero scaling. For a numerically unresolved leading
eigenspace, report the attainable minimum and maximum over the whole certified
space, not the most favorable basis vector. The public range calculation and
column-equilibration/rank rules are in `protocol.py` and the scientific contract.
Invariance concerns numerically resolved certified spans, not transformations
that destroy information in floating point. Do not apply a test sign selected
from network labels.

## Answer and evidence

Return per-person source/QC records and measurements, the frozen discovery
support/axis and their source provenance, and the following summaries:

1. Training axis/gap and all ten discovery deletion diagnostics.
2. All ten held-out rows, including justified nulls. Give mean, minimum, maximum,
   and leave-one-valid-person mean range for defined transfer scores; show both
   expected and defined counts. These are descriptive summaries, **not p-values,
   confidence intervals, or ten-times-as-many parcel observations**.
3. All per-person network-configuration statistics/ranges, including discovery
   and held-out labels. Report measured agreement and disagreement between
   transfer and network characterization. Do not require a positive finding.
4. A short interpretation constrained to these selected people viewing this
   movie, conditional on the supplied preprocessing and spatial approximation.

Provide arrays sufficient to reconstruct FC/operators and these measurements;
the release will specify a small public keyed schema before scoring begins.
Source hashes, split membership, support, numerical definitions and null rules
are public. Actual values and a reference implementation are not hints to copy.

A correct negative or unresolved scientific answer is acceptable only when the
submitted calculations and source evidence justify it. Blank or fabricated
outputs, replacing every result with `inconclusive`, selecting the best test
axis, positive-orienting test network contrasts, using test activity to choose
training support, and treating parcels as participants are invalid.

The 4-mm release and the atlas have different template designations; their
inherited identity-world label transfer is an operational approximation, not a
verified nonlinear inter-template registration. This limits anatomical claims
even if held-out transfer is strong. Shared movie content also prevents a claim
of generalization to other stimuli or resting state.

Paper anchor: [Margulies et al. (2016)](https://www.pnas.org/doi/10.1073/pnas.1608282113).
