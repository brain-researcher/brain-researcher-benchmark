# Does a discovery connectivity gradient transfer to other participants?

Margulies et al. (2016), Figures 1A/D and 3A/B
(https://doi.org/10.1073/pnas.1608282113), motivates two distinct questions:
does a discovery connectivity axis remain a high-energy direction in held-out
participants, and do individual gradients place the default-mode network on
the same side of both visual and somatomotor means?

This is a **paper-derived method-validation case**, not the paper's adult HCP
resting-state reproduction. The fixed ds000228-derived release contains 16
children and four adults watching the same movie. The identity-world transfer
between differently designated atlas/BOLD templates is an operational spatial
approximation, not validated nonlinear registration. No population, age,
other-stimulus, resting-state or global cortical-hierarchy inference follows.
Negative/mixed numerical findings are as acceptable as positive ones.

## Discovery and one-shot evaluation

`/data` contains only the ten discovery participants and common metadata/atlas.
`/public/contract.json` lists the fixed 10/10 metadata-only split and selected
nuisance columns. `/data/source_manifest.json` identifies all original source
files and their hashes, but the evaluation images/confounds are not available
while you code. This is a procedure-level locked split of previously public,
previously inspected data, not a claim that these participants are pristine.

Submit **two files** (each at most 1 MiB):

- `/submission/discovery.json`: your completed discovery analysis.
- `/submission/evaluate.py`: a self-contained Python program (source or zipapp).

After your coding session ends, a fresh offline environment certifies and freezes
your discovery artifact and executes your program once:

```
python3 evaluate.py --data /data --fit /input/discovery.json \
  --output /out/evaluation.json --contract /public/contract.json
```

Here `/data` contains only the ten evaluation participants plus common files;
the fit is read-only. Your program must produce the evaluation JSON below.
There is no interactive feedback or opportunity to refit after seeing held-out
data. You may develop a discovery self-test, but must not require discovery
images at evaluation time. NumPy 2.1.3, SciPy 1.14.1 and NiBabel 5.3.2 are
installed; arbitrary extra dependencies/network access are unavailable. The
program has 180 seconds, 8 GiB virtual memory, 16 processes, 1 MiB per output
file, `/tmp` scratch (64 MiB), and `/out` (16 MiB). No GPU is available.

## Public estimator

Use float64. Decode original NIfTI storage with its effective slope/intercept.
Use all 168 frames. Resample **atlas labels**, not BOLD, to each BOLD grid with
`inv(atlas_affine) @ bold_affine`, nearest neighbour (`order=0`, constant outside
zero, `prefilter=False`); parcel means use all matching voxel centres, ascending
C-flat index, no smoothing or extra brain mask. Original LUT IDs are 1–400.

For each signal and selected nuisance column: remove temporal mean and linear
trend using the centred unit-norm frame index; exact constants become exact
zero. Centre the detrended nuisances again, divide each by population SD (replace
SD below machine epsilon by 1). Pivoted economic QR keeps Q columns with
`abs(diag(R)) > 100*eps64`. Subtract their projection from detrended signals;
no band-pass, censoring, imputation or final z-score. A parcel is active iff it
has voxels and its centred cleaned L2 norm exceeds
`1e-12*sqrt(168)*max(1, raw_sample_SD)`, with raw SD using ddof=1. Use accurate
centering/summation and exact-constant guards. Never add epsilon to correlations.

Discovery support is the intersection of all ten discovery activity masks;
freeze it, retain original ascending IDs, and retain every network. Evaluation
inactivity invalidates that person's dependent measurements, **not another
parcel/person selection**. Keep every participant slot and identify inactive
parcel IDs. The participant, not parcel or edge, is the independent unit.

Compute each active participant's Pearson FC, mirror the upper triangle and set
diagonal 1. The discovery-group FC is the equal-person arithmetic mean. For any
FC on P retained parcels:

1. Keep `ceil(.1*P)` largest **signed** entries per row; diagonal is eligible,
   exact ties choose smaller original parcel ID. Set all others to zero.
2. Unit-normalize these sparse rows. Set
   `W = 1-arccos(clip(row_dot,-1,1))/pi`, mirrored and diagonal 1.
3. `q=W.sum(1)`; `A=W/sqrt(outer(q,q))`; `d=A.sum(1)`;
   `K=A/sqrt(outer(d,d))`; stationary unit vector `s=sqrt(d/sum(d))`.
4. Solve symmetric K on the orthogonal complement of s; sort **largest
   algebraic** nontrivial eigenvalues, not magnitude. The leading block is the
   complete initial block with successive eigenvalue gaps <=4e-8. Report its
   dimension, leading eigenvalue, `principal_gap=lambda1-lambda2` and
   `stationary_gap=1-lambda1`.

The discovery axis is its unit leading nontrivial eigenvector, either sign,
provided both gaps exceed 4e-8; otherwise it is null with
`axis_status="discovery_axis_unresolved"`. Refit all ten leave-one-discovery-person
group FCs on unchanged support; report both gaps and squared overlap with the
full axis. If either axis is unresolved, overlap is null/status `axis_unresolved`.
No label-driven component selection, alignment or rotation is allowed.

For each evaluation person, project the frozen discovery axis u away from their
stationary mode: `w=u-s*(s@u)`, `v=w/||w||`. Report `R=v@K@v`, `lambda1`,
`fraction=R/lambda1`, `(s@u)^2`, `||w||`, the leading gap,
`spectral_mean=(trace(K)-1)/(P-1)`, and `R-spectral_mean`.
The fraction is not variance explained or significance. A flat spectrum may
give one for arbitrary axes; spectral excess is descriptive, not a calibrated
null test. Summarize defined participants only but show both total and defined
counts. The leave-one-valid-person mean range is not a confidence interval.

Separately for each discovery/evaluation person and discovery group, use their
**own** principal diffusion coordinate
`g=(eigenvector/s)*lambda/(1-lambda)` and compute
`C=(mean_Default(g)-mean_Vis(g))*(mean_Default(g)-mean_SomMot(g))/mean((g-mean(g))^2)`.
This sign/scale-invariant statistic is positive for the same side of both
sensory means and negative for a DMN mean between them; neither is a global
DMN-apex test. For an unresolved leading block, report the exact attainable
minimum/maximum over the whole coordinate span, not a favourable basis vector:
max-absolute-normalize columns, centre, remove exact constants, max-absolute
equilibrate remaining columns then unit-L2-normalize; SVD rank uses
`singular > 1e-10*largest`. In the resulting orthonormal centred span Z, let
`a=mean_Default(Z)-mean_Vis(Z)`, `b=mean_Default(Z)-mean_SomMot(Z)`; extrema
are min/max eigenvalues of `P*(outer(a,b)+outer(b,a))/2`. Any equivalent complete
span is acceptable. A non-simple stationary mode makes C undefined.

## JSON schema and undefined values

Objects `people` and `leave_one_out` are keyed by exact participant ID (order
irrelevant). All required fields below are explicit. Numbers must be finite;
undefined numbers use JSON null, never NaN. Harmless additional metadata is
ignored. No full source arrays, hashes, operators or private QA receipts are
required. The schema describes measurements, not expected values.

`discovery.json` has:

```
support: [ascending original parcel IDs]
axis_status: "defined" | "discovery_axis_unresolved"
axis: [unit vector on support] | null
spectrum: {leading_eigenvalue, principal_gap, stationary_gap, leading_block_dimension}
network_C: {status, lower, upper, rank (only when defined)}
configuration: "same_side" | "between" | "unresolved" | "undefined"
people: {discovery_ID: PERSON}
leave_one_out: {omitted_ID: {principal_gap, stationary_gap,
                           squared_axis_overlap, status}}
```

`PERSON` has `nuisance_rank` (integer), `inactive_on_frozen_support` (ascending
IDs), `source_status` (`defined` or `source_inactive`), `spectrum`, `network_C`,
and `configuration`. C has `status="defined"`, finite `lower/upper`, integer
`rank`; otherwise lower/upper are null and status is `source_inactive`,
`stationary_mode_unresolved` or `constant_coordinate`. Configuration follows
the whole interval: lower>0 `same_side`; upper<0 `between`; contains zero
`unresolved`; undefined C `undefined`. Source-inactive spectrum is null.

`evaluation.json` has `people: {evaluation_ID: PERSON}` and `summary`.
Each evaluation PERSON also has `transfer`:

```
status, rayleigh, fraction, leading_eigenvalue, stationary_overlap_squared,
projected_norm, heldout_leading_gap, nontrivial_spectral_mean,
rayleigh_minus_spectral_mean
```

For source inactivity or unresolved discovery axis, transfer needs only
`{status: "source_inactive" | "discovery_axis_unresolved", fraction: null}`.
Otherwise diagnostics remain present. Null rayleigh/fraction/excess with reason
`stationary_mode_unresolved` (stationary gap<=4e-8),
`stationary_projection_unresolved` (projected norm<=1e-12), or
`leading_energy_unresolved` (lambda1<=4e-8) replace defined transfer, in that
precedence. No blanket nulls: source/numerical reasons must hold independently.
An unresolved discovery axis does not invalidate a person's own C.

Summary fields are `n_expected`, `n_defined`, `mean_fraction`,
`minimum_fraction`, `maximum_fraction`, and
`leave_one_valid_person_mean_range: [min,max]`. With no defined scores, scalar
summaries are null; with fewer than two, the deletion range is null.

Scalar acceptance is `abs(error)<=1e-6+1e-6*abs(reference)`, integer inventories
and categories are exact. Axis certification uses unit-squared-norm error<=1e-7,
stationary dot<=1e-8, source eigen-residual L2<=1e-8, accepting either sign.
Held-out expectations use your accepted certified axis. These are numerical
allowances for serialization: discovery C and deletion diagnostics describe the
source-estimated eigensystems, not a redefinition using rounded axis entries.
You may unit-renormalize the serialized discovery axis for evaluation; the
published scalar envelope accommodates its certified norm roundoff. These are
not effect-size thresholds. Reward is 1 only when the complete
discovery artifact and blind evaluation are valid; otherwise 0. There is no
partial-credit promise or requirement to recover a positive paper finding.
