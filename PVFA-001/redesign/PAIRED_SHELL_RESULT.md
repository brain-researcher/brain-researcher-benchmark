# Paired-shell diagnostic A: completed, scientific adequacy still unresolved

The exact released-vector pairing succeeded. In the unchanged 16 selected
voxels, **227 of 1,024 observed pairs** had b2000 signal greater than b1000 signal.
All 16 voxels had at least one such pair. The descriptive ideal-PSD relaxation
normalized RMSE ranged from **0.002691 to 0.115310** (about 0.27–11.53% of each
voxel's measured canonical b0, using the original 129-observation denominator).
These are not model fits, estimated noise levels, biological effect sizes or
new scoring thresholds.

## Retained execution and verification

Root ran committed code at `0f440bd886cd55c29cb89a9dcf62e58e76ca496b` once under
contract SHA-256
`366940fba9b8e6b84837d84f101df67c8f9154b640a196c0f9c41ccfe58de329`.
Evidence root:
`/home/zijiaochen/projects/brain_researcher_benchmark/tracking/scientific_release_2026-10-04/pr156_paired_shell`.

- Status: `completed_ideal_psd_descriptive_diagnostic`; scientific release false.
- 16/16 original coordinates, 64/64 matched directions per coordinate, and all
  1,024 pairs retained with observations and source-volume mapping.
- No angular tolerance, vector normalization, antipodal replacement or exclusions.
- Zero fits and zero model runs; no old-output regrade or domain/tolerance change.
- Host elapsed 0.583 s; diagnostic routine 0.041 s; exit 0, no OOM, empty stderr.
- Runtime inspection confirms offline, one CPU, 2 GiB RAM/no swap extension,
  unprivileged user, read-only root and input mounts. The exact owned container
  was removed successfully. Retained evidence totals 476,049 bytes, within 16 MiB.
- 134 source-free engineering tests passed, including 24 diagnostic tests.

An independent receipt audit recomputed all pair distances by rational
orthogonal projection of the recorded float64 observations, rather than calling
the diagnostic's gap formula. The maximum absolute SSE difference from the
float64 formula was `4.547473508864641e-13`; all pairs agreed within floating
arithmetic precision. All 16 aggregate denominators and pair membership counts
were also checked. This is an arithmetic audit, **not an interval-arithmetic or
numerical-PSD certificate** and not independent acquired data.

Artifact SHA-256:

- `result.json`: `dd34bbce2e708c72e5bc045342c38d609c7764da0b00947f380a3794d04a3c88`
- `diagnostic/pairs.jsonl`: `cd838144e2fbc4a7a2c72b6f75955799a9d586b8a041ca0693ab6ebef4b05988`
- `diagnostic/voxels.json`: `3e26b0be6e5c877dbd1e824419c9bd621aa3bfb46dcf9d224f7ecc5694689932`

Raw source-specific pair/voxel evidence is retained privately, not added to the
public source/report export. Prior pools, reports and historical scores are
unchanged. The original `ADEQUACY_SEARCH_PROPOSAL.md` remains a dated design
artifact; this report records execution of A only. Its B search extension was
not implemented, run or authorized.

## What this does and does not establish

The fixed *ideal mathematical PSD* mixture model predicts nonincreasing signal
between exactly paired b1000/b2000 directions. The calculation measures distance
to a much larger prediction set that imposes only that ordering. It therefore
has a clear model-derived interpretation, without using a secret optimizer.

However, the existing operational numerical domain tolerates tiny negative
tensor eigenvalues. No conservative eigenvalue/rounding certificate was added.
These values must **not** be presented as certified bounds for that accepted
numerical candidate pool, compared as a rigorous fraction of its residual, or
used to set a pass/fail ceiling.

Observed reversals do not diagnose their cause: noise alone can reverse order.
This scan has one b0 and lacks independent repeat truth for this purpose. Vector
equality authenticates the released pairing, not physical gradient orientation.
The 16 already examined voxels form an exploratory within-scan sample, not 16
independent subjects or a representative validation sample. Consequently this
result does not settle noise, acquisition validity, biological adequacy,
identifiability, optimizer completeness or task hardness.

## Practical next decision

Keep #156 an explicitly **model-conditioned sensitivity/diagnosis case** until
an acquisition and discrepancy/noise contract can be independently justified.
Do not tune a cutoff to these residuals or require agreement with a hidden
reference optimizer. If the intended claim requires biological adequacy rather
than conditional sensitivity, that missing contract is a release blocker.

A separately reviewed fixed search extension could probe the earlier search's
limitations, but would not itself supply noise calibration or biological truth.
No further fits or Sol calibration are authorized by this diagnostic. Existing
public instruction/oracle/verifier and historical score are not replaced by it.
