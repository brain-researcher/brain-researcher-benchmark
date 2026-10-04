# Source feasibility and verifier plan

## What is established, and what is not

The inherited source manifest contains 46 files, 124,132,750 total bytes, and
20 identities: `sub-pixar001` through `sub-pixar016` and `sub-pixar123` through
`sub-pixar126`. The inherited authenticated contract reports 16 children and
4 adults; the old loader-order halves have 4 and 0 adults. Therefore this draft
uses a metadata-only age-stratified split instead of treating those old halves
as independent replication samples.

The retained original Sol output reports all 8,000 participant-parcel geometry
supports as nonempty but only 7,999 active participant-parcels in both cleaning
arms. `sub-pixar124` has an inactive parcel. The old all-400/all-person rule
consequently left the full-group, band-pass and first-half embeddings undefined.
These are **read-only diagnostic observations from the old output**, consistent
with the prior source-checking audit, not a new source qualification receipt or
a reason to put that participant in a chosen split.

The proposed rule uses discovery-only common support, then scores held-out
participants separately. If the inactive participant is in evaluation, its
score can be undefined while the remaining nine are evaluated; if in discovery,
its source-inactive parcel is removed by the same declared rule. Neither case
allows modifying the split after inspecting the result. This avoids requiring
the entire held-out group to become undefined from one person-parcel.

Applying the single declared hash rule to the retained old cohort metadata
produces this provisional split (metadata source must still be independently
reauthenticated for the new version):

- Discovery: `001,003,005,006,009,010,012,013,123,125`.
- Evaluation: `002,004,007,008,011,014,015,016,124,126`.

All entries have the literal `sub-pixar` prefix. No alternative salt was tried.
Thus the existing diagnostic suggests one evaluation row will be source-invalid,
not a reason to change the split or learn support from evaluation. The defined
score mean estimates only the source-eligible evaluation subset; it is not
imputed as the mean of all ten, and source-related selection remains a limitation.

The adjacent #198 SOCIALBRAIN source contract lists all 155 people, 122 children
and 33 adults, with 168 frames each and 942,572,457 total bytes including its
own templates/provenance. The #199 DEVCONN manifest totals 940,543,951 bytes.
These are **metadata inventory evidence**, not a claim that this redesign has
loaded, anatomically qualified, or been authorized to use the larger cohort.

The 20-person data are sufficient in principle for a small conditional
held-out-person method test. They are not sufficient to claim HCP replication,
a population age effect, other-stimulus generalization, or pristine test data.
Support coverage and empirical endpoint behavior remain unmeasured for this
new split; a successful source pilot might still reveal that the question is
uninteresting or too easy. Do not change the score to force a desired result.

## Paper correspondence

[Margulies et al. (2016)](https://www.pnas.org/doi/10.1073/pnas.1608282113)
uses adult HCP resting-state connectivity. Figures 1A/D motivate a leading
connectivity axis; Figure 3A/B relates its values to canonical networks.
This draft tests a narrower, new held-out validation claim. Its signed top-row
selection/normalized-angle kernel and Schaefer parcels are disclosed adaptations.
Neither the movie cohort nor its kernel is presented as the original analysis.

## Reference answer is an evidence chain, not a required verdict

The reference must produce the authenticated metadata split, source-valid
discovery support, independently reconstructed operators, discovery eigenaxis
and gap, ten deletion diagnostics, ten held-out score/status rows, and the
separate sign/basis-invariant network statistics. The final interpretation can
be weak, negative or unresolved, but must follow those values. No minimum
Rayleigh fraction, positive configuration statistic or winning network is a
pass requirement. A small discovery spectral gap must not be disguised by
switching to the axis that best matches network labels.

## Proposed verifier layers

1. Authenticate the fixed manifest and recompute the metadata split. Reject
   missing/extra/duplicated people, old convenience-half substitution or any
   overlap. Do not trust the submission's partition labels.
2. Independently reconstruct raw/cleaned series and geometry/activity masks.
   Recompute discovery-only support and held-out validity; arbitrary nulls,
   outcome-selected exclusions, epsilon-filled inactive signals and using
   evaluation activity to reduce discovery support fail.
3. Recompute FC and operators; accept residual-certified eigenvectors and
   equivalent bases, not private array fingerprints. Verify stationary mode,
   ordering, positive denominator, gap and every undefined reason.
4. Recompute the frozen-axis projection, numerator, denominator, ratio and
   participant summaries. Any held-out axis substitution/alignment or selecting
   the best held-out direction must fail even if it looks more paper-like.
5. Recompute the network statistic or range; verify sign, scaling and basis
   invariance. Never count parcels or edges as independent observations.
6. Check interpretation against numerical claims, not prose keywords. Until a
   semantic claim checker is specified, machine grading can establish numeric
   and structured-claim correctness, while free-text scientific interpretation
   remains a manual review item. Do not claim a complete automatic oracle.

Mandatory positive controls: two independent equivalent implementations;
sign-flipped eigenvectors; rotation of a complete repeated-eigenvalue block;
coherent participant/parcel reorderings; real source-supported nulls.
Mandatory negative controls: empty, naive labels-only, fabricated scores,
all-null, held-out-informed support, overlapping splits, a copied test-optimal
axis (ratio=1), outcome-selected component, incorrect nuisance treatment,
unjustified source omission, false global-apex claim, and parcel-level SE.

The source-free tests in this folder cover **mathematical and contract plumbing
only**. They do not yet prove that a submitted program never read test data;
that requires a harness boundary: execute `fit` with only discovery files
mounted, hash/freeze the fit artifact, then execute `evaluate` with test data
read-only and the fit artifact immutable. The verifier reconstructs both stages.
The same staged boundary is required for the oracle, not just for agents.

## Concrete next steps and resources

Recommended scope is to retain the 20-person data, the inherited approximate spatial
mapping and no-band-pass preprocessing, with descriptive inference only. Before
activating the task, review those scientific defaults and the proposed pilot:
2 CPU, 8 GiB RAM, no GPU/network, 20-minute stop, at most 1 GiB new artifacts,
existing image/data read-only. This is **not launched** by this design package.

The pilot should authenticate metadata and source bytes, materialize the single
metadata-defined split, measure geometry/activity coverage, and test the staged
fit/evaluate boundary. It must not search splits, tune the operator by held-out
scores, add participants, or silently fetch a better template. Expanding to the
155-person package or changing spatial registration requires a separate scoped
scientific/resource decision. Once source-qualified, finalize schemas/tolerances,
implement independent source-backed verification, run the oracle and adversarial
controls, then lock a new task version for fresh Sol calibration. Its hardness
is determined only at that last step and subsequent trajectory review.
