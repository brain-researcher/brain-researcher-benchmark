# Endpoint numerical qualification — 2026-10-04

The approved five-stage qualification completed successfully. The frozen
discovery axis is numerically resolved and stable under discovery-person
deletion; its mean held-out Rayleigh fraction is **0.5740**, with **9 defined
participants and one justified source null**. The network configuration is
negative in the discovery-group coordinate and mixed across held-out individual
coordinates. That is a permissible scientific result, not a reason to change
the split, remove a parcel using held-out data, or search for another component.

This establishes bounded source-backed numerical agreement and authoring-stage
isolation. It does **not** establish original-paper replication, anatomical
validity, a complete benchmark verifier, or empirical difficulty for Sol.

## Frozen run and source accounting

The root launched committed package `eb4da62` with approved contract SHA256
`17bdc4bddf02091c2bfcf64b76849f3334fa978765f92176b778446434f1cb96`.
The authoritative result status is
`completed_endpoint_numerical_qualification`. No scientific settings or
numerical comparison tolerances were changed after observing these results.

All 46 source/provenance files authenticated, and the metadata-derived split
remained the previously frozen 10 discovery / 10 evaluation participants.
All ten discovery participants supported all 400 parcels. Evaluation used this
unchanged discovery support; every evaluation slot remains in the report.

`sub-pixar124` has an explicit source null: parcel 119,
`7Networks_LH_Limbic_TempPole_1`, has constant extracted parcel-mean signal
(raw sample SD 0; cleaned centered L2 norm 0). Its 68-voxel geometric support
exists, so this is not an empty-atlas-support failure. The declared activity
threshold is approximately `1.29614814e-11`. Neither this person nor this parcel
was replaced or silently deleted. The other nine evaluation participants have
defined transfer and individual network-configuration measurements.

## Measured endpoints

The discovery group's largest nontrivial eigenvalue is `0.05576282066`, its
principal gap is `0.007613530104`, and the leading block is one-dimensional.
All ten leave-one-discovery-person fits are defined. Their squared axis overlaps
with the full discovery fit range from **0.9583164 to 0.9947488**; the principal
gaps range from `0.005939131` to `0.009765085`. These heavily overlapping fits
measure within-discovery deletion stability, not independent replication.

The primary held-out endpoint applies the frozen discovery axis to each
evaluation operator after stationary-mode projection. There is no held-out
axis alignment, component search, or network-driven orientation selection.

| Held-out descriptive quantity | Observed value |
| --- | --- |
| Fixed slots / defined transfers | 10 / 9 |
| Mean Rayleigh fraction, `R / lambda1` | 0.5740165412 |
| Individual fraction range | 0.3339446526–0.7355950115 |
| Leave-one-valid-person mean range | 0.5538192324–0.6040255273 |
| Raw Rayleigh quotient `R` range | 0.02843524334–0.03503048147 |
| Nontrivial spectral mean range | 0.002108040784–0.002181340032 |
| `R` minus spectral mean range | 0.02629118772–0.03289714047 |

The fraction is an operator-energy ratio, **not variance explained, prediction
accuracy, a benchmark pass rate, or statistical significance**. Its positive
excess over the nontrivial spectral mean is descriptive; that baseline is not
a calibrated random-parcel null. The deletion range is not a confidence
interval. Eigenvalues, gaps, projection norms and stationary overlaps remain in
the per-person receipts; the fraction alone would be insufficient, especially
for a nearly flat nontrivial spectrum.

The secondary configuration statistic uses each person's **own** principal
coordinate, not the projected discovery axis:

`C = (mean_Default(g) - mean_Vis(g)) * (mean_Default(g) - mean_SomMot(g)) / var(g)`.

The discovery-group coordinate has **C = −1.4012944324**: its DMN mean lies
between the visual and somatomotor means. Held-out individual coordinates have
**six positive and three negative C values**, plus the preserved source null.
Positive C only places the DMN mean on the same side of both sensory means; it
does not establish a global DMN apex. These individual descriptions are not
predictions of discovery-group C. A stable axis and measurable held-out
transfer therefore do not, by themselves, recover the named paper's DMN-pole
interpretation. The negative/mixed configuration should remain an acceptable
answer. This different cohort, acquisition and operator do not test a direct
refutation of the original result.

All source-defined leading blocks were one-dimensional. Sign/basis-equivalent
and near-degenerate complete-block behavior was exercised in manufactured
fixtures, not observed in a degenerate real-data leading block during this run.

## Independent arithmetic checks

Both checker stages report `independent_arithmetic_agrees`. Raw extracted
arrays, raw SDs and source activity thresholds agree exactly. Geometry/activity
masks and signed top-10% membership comparisons passed exactly before operator
agreement was accepted.

| Maximum absolute difference | Discovery checker | Evaluation checker |
| --- | ---: | ---: |
| Cleaned time series | 2.0002e-11 | 2.3235e-11 |
| Pearson connectivity | 2.2722e-14 | 3.3112e-14 |
| Symmetric diffusion operator | 1.3878e-17 | 2.0383e-17 |
| Eigenvalues | 1.5266e-16 | 1.6653e-16 |
| Compared scalar outputs | 9.6312e-15 | 9.4369e-15 |

Separate accounting checks reconstructed all fixed participant slots, support
and null decisions, and participant-summary arithmetic. The checker uses
alternative cleaning, connectivity, operator and endpoint arithmetic; it does
not call the production numerical routines or legacy numerical core. Its SVD
projection certifies the publicly fixed QR-kept nuisance span, rather than
substituting an unrelated rank cutoff.

This is not a fully independent complete verifier. Both paths share immutable
source/capsule authentication, fixed metadata/LUT parsing, high-level recipe
orchestration including aggregation/null dispatch, numerical libraries, and
the public contract. The independent accounting audit mitigates the shared
orchestration risk but does not remove those common dependencies.

## Isolation and resource receipts

The production and checker fit/evaluation stages each denied all **40** tested
opposite-partition reads: **160 denied probes** total. Baked `/app` and
`/opt/source_capture` were covered; each process received only its own read-only
source capsule. Both evaluation stages denied attempts to write the frozen
discovery JSON. Its SHA256 remained:

`b61ec1b9297d951ce0e441d6b9340993c793071372f8414b114d400519c96d43`.

Evaluation checking also required a successful discovery-check certificate
bound to that exact fit JSON. These are actual authoring-process access probes,
not merely a promise in a configuration file. They do **not yet demonstrate
isolation for an interactive coding agent** with its full task environment;
that separate runtime boundary still needs implementation and testing.

All five stages exited zero, with no cleanup errors. Container receipts confirm
2 CPU, 8 GiB RAM, no network, a read-only root filesystem, nonroot UID 1004 and
dropped capabilities. Recorded stage times were approximately 2.24 s for
authentication, 9.25 s for fit, 7.45 s for evaluation, 6.65 s for fit checking,
and 6.25 s for evaluation checking. The run recorded 190,157,577 bytes of new
artifacts, below the 1 GiB cap; the global wall budget was 1,200 s. There were
**zero model runs**, no Harbor/oracle run, no regrade and no reward computation.
The frozen source-free test suite passed 61 tests before launch; those tests
are engineering evidence, not a difficulty measurement.

## Evidence and remaining limits

Authoritative artifacts are under:

`/home/zijiaochen/projects/brain_researcher_benchmark/tracking/scientific_qualification_2026-10-04/pr200/`

- `result.json`: completion status, defined-slot accounting and scope.
- `authentication.json`: authenticated source and fixed split.
- `fit/fit.json`: frozen discovery axis, support, spectra, individual C and LOO.
- `evaluate/evaluate.json`: all ten evaluation slots and descriptive endpoints.
- `check_fit/check_fit.json` and `check_evaluate/check_evaluate.json`: numerical
  comparisons, source spectral certificates and independent accounting.
- Stage provenance and `*.launch.json` files: access probes, exact commands,
  observed container settings, wall times and exit status.
- Stage `*.stdout.log` files: complete combined stdout/stderr.

The cohort remains 16 children and four adults watching a shared movie, not
the adult resting-state HCP sample of Margulies et al. The declared signed
top-k angle-kernel recipe is a paper-derived adaptation. The atlas/BOLD
template mismatch remains an **identity-world approximation**, not validated
nonlinear registration. These results support only the stated conditional
method-validation analysis, not population, age, other-stimulus, resting-state
or original-paper replication claims. The participant is the independent unit,
not a parcel or edge. Previously inspected public data are not pristine unseen
data merely because this analysis now has a locked procedure-level split.

## Exact next gates

1. Preserve the fixed 20-person cohort, split and permissible negative/mixed
   outcome. Freeze a concise public estimator/undefined-value contract and
   minimal submission interface: an immutable discovery artifact and keyed
   person-level results. Private full-matrix QA receipts must not become
   agent-facing housekeeping requirements.
2. Convert these authoring checks into a task verifier: hardened artifact
   parsing, source-supported null validation, complete participant accounting,
   equivalent sign/basis acceptance and an enforced agent-level fit/evaluate
   boundary. Publish numerical acceptance rules without inventing a positive
   scientific-success threshold.
3. Run a complete in-container oracle and source-backed adversarial submissions
   (empty, naive, fabricated, all-null, held-out-informed support, test-optimal
   axis and incorrect configuration interpretation). Source-free tests and
   authoring receipts alone do not close this gate. Review scientific meaning
   rather than grading prose keywords.
4. Lock the new task version, then obtain approval for a fresh blinded Sol
   calibration and raw-trajectory review. Preserve old task versions and raw
   grades; this qualification neither regrades them nor proves the new task is
   hard enough.

If direct original-paper reproduction is required instead of this explicitly
labeled method-validation case, a justified data/spatial-model redesign remains
a separate decision. No additional source execution or endpoint search is
needed to report the present result honestly.
