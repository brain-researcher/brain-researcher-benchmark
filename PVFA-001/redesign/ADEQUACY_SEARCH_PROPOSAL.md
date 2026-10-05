# Proposed next study: search limitations versus residual constraints

Status: design only; not implemented, launched, or authorized by phase-3 replay.
No passing cutoff, new exclusion, biological truth, or calibrated noise model
is selected. A separate scientific/resource contract, implementation review,
commit, and root GO are prerequisites.

Question: how much of the current empirical residual can a prespecified larger
search remove, and how much is unavoidable even under a relaxed version of the
same model? Neither question alone identifies a biological or acquisition cause.

## Fixed support and claim

Keep the same 16 coordinates, source snapshot, canonical preprocessing,
two protocols, forward model, loss denominator, domain, and arithmetic policy
after the replay resolves their numerical authority. This is further exploratory
work on an already examined sample, not a representative or confirmatory sample.
The scan is the acquisition unit; 16 voxels are not 16 independent participants.

The primary outputs are paired empirical loss changes and a mathematical lower
bound on empirical loss. Finite-search stability is not a global-optimum proof,
and a mathematical lower bound on fitting the observed noisy signals is not a
noise estimate or a biological adequacy criterion.

## A. No-optimizer model-constraint diagnostic

For the two-shell protocol, first authenticate exact direction correspondence
between b1000 and b2000. If paired released vectors are not identical, this
specific diagnostic stops as inapplicable; do not introduce an angular tolerance
or invent pairs. For each matched direction, the unchanged PSD tensor plus
nonnegative free-water mixture implies predicted S(b2000) <= S(b1000).

Relax the model by allowing each direction its own arbitrary nonincreasing
two-point prediction, with no tensor, shared S0, or fraction constraint. This
superset gives a lower bound on the original model's squared-error objective.
For observations y1 at b1000 and y2 at b2000, its contribution is

`max(0, y2-y1)^2 / 2`.

Sum across the 64 authenticated pairs, divide by measured b0 squared and by
129 (the existing two-shell mean-SSE denominator). Ignoring the b0 term and
other constraints only loosens the lower bound. Preserve every pair, both
shell values, and its contribution. Verify the formula and bound direction on
manufactured ordered, reversed, equal, and noisy model-generated examples.

Important arithmetic qualification: that formula is exact for the mathematical
PSD model. The existing numerical domain accepts very small negative
eigenvalues within its explicit roundoff allowance. Do not advertise the strict
monotonic bound as certified for every numerically accepted tensor. Before an
operational bound is used, independently certify a conservative eigenvalue floor
`-eta` including eigensolver roundoff. Then use the relaxed constraint
`p2 <= K*p1`, where `K = exp((b2-b1)*eta*||g||^2)`, and contribution
`max(0, y2-K*y1)^2/(1+K^2)`, with conservative arithmetic enclosure. The value
and certification of eta are unresolved design work, not an extra fitted
parameter or a scientific cutoff. If no certificate is implemented, report only
the ideal-PSD descriptive bound with that explicit limitation and do not compare
it as a rigorous bound on the accepted numerical candidate pool.

This is a model-derived necessary-condition calculation, not an assertion that
reverse-ordered observations are artifacts or that the model is wrong: noise
alone can reverse their order. A small bound is uninformative; a sizeable bound
only limits how far optimization of this exact objective can reduce the loss.
It does not supply a valid loss ceiling for scoring.

Proposed standalone envelope: 1 CPU, 2 GiB, 60 s, no GPU/network, 16 MiB artifacts,
zero fits, unchanged 16 two-shell rows. These are proposed, not executed caps.

## B. Fixed small search extension, only after separate approval

Use all 32 coordinate/protocol groups. For each group and each of the existing
two algorithms, run exactly two free-f starts:

1. the previously retained best feasible candidate for that same group;
2. one prospectively fixed isotropic tensor diag(0.0008,0.0008,0.0008), f=0.5,
   S0/measured-b0=1, with identity orientation where needed.

Total cap: 32 groups × 2 algorithms × 2 starts = **128 new fits**, no profiles,
adaptive restarts, outcome-based voxel selection, or retries. Warm starts use
the current pilot's candidates, never old Sol answers or legacy fitted arrays.
Representation conversion must preserve the retained tensor, with no clipping
or silent boundary repair. Unrepresentable initial points are explicit failed
slots, not substituted starts. The single new initialization is an operational
probe, not a published tissue or physiological assumption.

Proposed budgets: TRF max_nfev=600 and SLSQP maxiter=600, at most 7,500 objective
calls per fit, with all other respective numerical settings unchanged. A
fixed lexicographic group/algorithm/start schedule and hard global 900 s wall
cap determine partial completion; retain all planned missing/failed slots.
Resource envelope: 1 CPU, 2 GiB, offline/no GPU, at most 32 MiB new evidence.
These counts/settings require review before implementation or execution.

Report every candidate, feasibility, boundary flags, termination, calls and
available numerical optimality diagnostics, as well as each group's old and
new best-found feasible loss. Keep algorithm-specific diagnostics distinct:
they are not directly comparable certificates. Report absolute and relative
loss changes continuously, without declaring an improvement cutoff or calling
any numerical result a global optimum. Preserve the prior results unchanged.

## Interpretation and stopping

- Lower loss from feasible new candidates demonstrates a limitation of the
  earlier bounded search. It does not validate the new parameters biologically.
- Unchanged best-found loss after this finite extension does not prove model
  misspecification, nor exclude other optimization paths.
- A nonzero relaxed-model lower bound identifies an unavoidable component of
  the empirical objective under the specified model constraints, not its cause.
- Afterward, an adequacy claim still needs an independently defensible acquisition
  and discrepancy/noise contract. This scan has only one b0 and no independent
  repeat truth; do not manufacture noise calibration from the selected residuals.
- If that scientific contract cannot be justified, keep the task an honestly
  model-conditioned sensitivity/diagnosis case, or change the scientific target
  with explicit approval. Do not obtain difficulty by grading agreement with a
  secret optimizer, by demanding positive ambiguity, or by inventing a cutoff.

The forward model and diffusivity convention are grounded in
[Henriques et al. (2017), Eq. 1 and Eq. 8](https://samuelstjean.github.io/downloads/Henriques_et_al_2017.pdf).
The monotonic relaxation above is a direct mathematical consequence of that
fixed model, not a result claimed by the paper. Warnings about plausible free-water
maps not establishing specificity motivate the claim boundary; single-shell
results do not directly settle this two-shell scan's behavior.
[Golub et al.](https://arxiv.org/pdf/2007.06359).
