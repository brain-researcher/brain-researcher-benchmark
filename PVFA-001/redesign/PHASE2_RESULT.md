# Phase 2 result: source agreement, boundary disagreement, adequacy unresolved

The selected raw data and independently reconstructed smoothed signals agree
with the frozen source cache. The 6–25% residuals persist. Six retained
candidates change feasibility only at the strict S0/b0 bounds, so the recorded
status remains `completed_with_arithmetic_disagreements`, not successful
diagnostic qualification or benchmark readiness. No code, tolerance, source,
candidate, or previous result was changed in preparing this report.

## Evidence and execution

Root executed committed code `6082fab` under the approved phase-2 contract
`dd47d465d24666b2533fd9e8ce3bce84c8979f2db461fbe8babbd12faeccdace`.
Evidence root:
`/home/zijiaochen/projects/brain_researcher_benchmark/tracking/scientific_qualification_2026-10-04/pr156`.

Host elapsed time was 2.334 seconds; the diagnostic routine took 1.649 seconds.
It checked all 768 prior attempt slots, reconstructed 672 retained candidates,
and left the 96 capped attempts without candidates unresolved. There were zero
new fits. Container exit was 0, OOM was false, stderr was empty, and exact-owned
container removal succeeded. A successful process exit does not override the
diagnostic disagreement status.

Authoritative receipt hashes:

| Artifact under evidence root | SHA-256 |
| --- | --- |
| `result.json` | `1c1391aada38196ae801bf62d8afee242ac96e70528933c19152ef730049f2ab` |
| `diagnostic/report.json` | `34c57e38f79bf2ccee2fe966fd24c30e0ce0a80122bbf0e9b1e53de499f1c1d4` |
| `diagnostic/candidate_checks.jsonl` | `45bb9241df3c6ef9a78130a952744e51d21696131676f5f4f433ac2bcf831732` |
| `diagnostic/best_directional_residuals.csv` | `d8f454889beccd9d62f6afab074103f4bc9c976b17182cd6062d53caefad10f1` |
| `diagnostic/source_checks.json` | `91f8686273c10dedfc75955a25dbb7b075012b03cd1c5e61b8ee5af79c7429f1` |

## Source and arithmetic findings

At the same 16 coordinates and 129 retained volumes, raw intensity differences
were exactly zero. The maximum smoothed intensity difference was
`1.1368683772161603e-13`, below the predeclared implementation-compatibility
bound of `1e-9`. Original b-value/vector ordering and cached volume membership
matched exactly. The independently parsed NIfTI was little-endian uint16,
shape 128×128×60×193, offset 352, slope 1, intercept 0.

These results support selected-signal/cache compatibility, not independent
validation of gradient physical orientation, anatomy, the complete ROI, or the
scientific suitability of the acquisition. The 27-neighbor float64 reconstruction
and original separable float64 filter use different summation orders.

All available prior loss and FA comparisons agreed: maximum normalized MSE
difference `3.3306690738754696e-16`; maximum FA difference zero. The six
disagreements are feasibility classifications, exclusively at S0/b0 boundaries:

| Attempt | Protocol | Coordinate | Prior reported S0 ratio | Reconstructed S0/b0 | Boundary |
| --- | --- | --- | --- | --- | --- |
| 16 | b1000 | (32,70,30) | 1.4999999999999998 | 1.5000000000000002 | upper |
| 40 | b1000+b2000 | (32,70,30) | 1.4999999999999998 | 1.5000000000000002 | upper |
| 66 | b1000 | (41,24,24) | 1.4999999999999998 | 1.5000000000000004 | upper |
| 317 | b1000+b2000 | (60,89,18) | 0.5 | 0.49999999999999994 | lower |
| 319 | b1000+b2000 | (60,89,18) | 0.5 | 0.49999999999999994 | lower |
| 647 | b1000 | (78,74,20) | 1.5 | 1.5000000000000002 | upper |

The prior ratio column is the recorded optimizer-coordinate diagnostic; the
independent column divides retained S0 by independently reconstructed b0.
The prior candidate check accepted each under the cached-signal normalization.
Their eigenvalues satisfy the unchanged domain, and loss/FA agree. This
localizes the discrepancy to strict scalar-boundary classification under
arithmetic-equivalent baseline reconstruction, not a meaningful difference in
the recovered signal or FA. It does not justify silently widening any bound.

The independent strict check has 629 feasible candidates versus 635 originally.
None of the six is one of the 32 preexisting best-feasible representatives, and
none is a chosen endpoint in the 288 previously reported sensitivity rows.
This is a membership audit, not a regrading or modification of those results.

## Retained residual and constraint patterns

The following are descriptive observations from the 32 frozen best
representatives; they do not resolve noise, artifact, or model-mismatch causes.
The arithmetic qualification gate remains open.

| Protocol, 16 coordinates each | Normalized RMSE min / median / max | Best fits flagged at lower eigenvalue boundary |
| --- | --- | --- |
| b0+b1000 | 6.486% / 12.324% / 25.475% | 11/16 |
| b0+b1000+b2000 | 6.682% / 11.803% / 24.884% | 3/16 |

Normalization is by each coordinate's measured smoothed b0, not its fitted S0.
No best representative hits an S0 or upper-eigenvalue boundary. Five single-shell
best representatives hit the f=0 boundary; none of the two-shell representatives
does. The existing lower-eigenvalue boundary flags are pilot diagnostics, not
an anatomical classification.

In the two-shell representatives, b1000 contributes 44.50–71.16% of the SSE
(median 56.70%) and b2000 contributes 28.84–55.47% (median 43.25%). Both shells
therefore retain substantial discrepancies; this is not solely a b2000 residual.
The one b0 sample contributes at most 0.072% of total two-shell SSE. All 16
two-shell representatives have a positive mean predicted-minus-observed
residual at b1000 and a negative mean at b2000; median biases are +0.347% and
−0.568% of measured b0. This records a shell-dependent fitting compromise,
not an identified mechanism.

Using the two-shell support once, avoiding double-counting shared observations:

- There are no negative or nonfinite raw/smoothed values in the selected
  16×129 observations.
- Three raw diffusion observations are zero: (41,24,24), original volumes 3
  and 22 at b1000; and (64,64,14), volume 104 at b2000. Their smoothed values
  are approximately 0.2803, 0.2638, and 0.1813, while the frozen best predictions
  are 39.02, 36.39, and 26.66. These are retained observations, not exclusions.
- Eleven diffusion observations across six coordinates exceed measured b0,
  in both raw and smoothed data. Seventeen exceed their corresponding fitted
  S0 in the two-shell representatives. These counts are descriptive, not a
  noise estimate or proof of corruption.
- Large directional residuals occur in both shells: at (32,70,30), original
  volume 57 has smoothed signal 85.79 versus prediction 32.00 (normalized
  residual −0.8394); volume 69 has 74.79 versus 32.90 (−0.6539).

Search limitations also persist unchanged. SLSQP has 96 objective-call caps
and 37 tensor-domain rejections; most capped slots have fixed f=0.9 or 0.99.
A retained feasible point is not a certificate of optimum, and an absent
candidate is not evidence against an admissible fit. Near-zero tensors and
S0 upper-bound solutions in high-f slots are boundary behavior, not support
for identified biological tissue FA.

## Next bounded gate, not executed

First resolve numerical-substrate authority explicitly, without new fits or
scientific tolerance changes. Recommended append-only replay: authenticate the
same cached smoothed observations and compare the unchanged 672 candidates
using (a) that exact canonical numerical substrate and (b) the independently
reconstructed signals, preserving both outcomes. Keep source reconstruction
as a separate compatibility diagnostic. Add manufactured S0-boundary fixtures
for the observed roundoff behavior; do not force arithmetic-equivalent source
reconstruction to have identical hard-boundary membership without a public
contract explaining it.

Proposed cap for this replay: same 16 coordinates and two protocols, zero
optimization, one CPU, 2 GiB, 60 seconds, no network/GPU, at most 16 MiB of new
artifacts. It needs a separately reviewed frozen contract and root GO. It must
not overwrite this diagnostic status or retroactively change the phase-1 pool.

Even if that engineering gate passes, model adequacy and a defensible discrepancy
contract remain unresolved. No new residual cutoff, exclusion, noise estimate,
solver budget, or domain is selected here. Any subsequent search/adequacy study
must be prospectively specified and distinguish boundary/search limitations
from data/model limitations. Current evidence does not license biological
identifiability claims, positive-witness grading, or a claim of LLM difficulty.
