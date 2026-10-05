# #156 bounded real-data pilot: feasible, not benchmark-qualified

The approved pilot completed all **768 attempts** in **14.03 seconds** wall
time (12.54 seconds in the fitting routine), producing **635 feasible
candidates**. It shows that this question can be investigated cheaply on the
existing authenticated data. It does **not** yet establish a scientifically
adequate identifiability benchmark or model difficulty.

The main concern is absolute fit adequacy: the best-found normalized RMSE
across the 32 voxel/protocol slots ranges from **6.49% to 25.47% of measured
b0**, with median **11.80%**. A large FA separation around an imperfect fit is
conditional sensitivity, not proof that two biologically plausible tissue
states are indistinguishable at the acquisition's noise level.

## Execution and evidence

- Frozen implementation commit: `6f6387c`; approved contract SHA256
  `d3048bd54b1becdff368a9f60718c50b65fd93e1719c64f20a8fb08579794036`.
- 16 coordinate-bin-selected voxels; two protocols; two starts; free-f fit and
  five fixed-f profiles; two solver routes. No outcome-based reselection.
- 1 CPU, 2 GiB memory and equal memory+swap cap, no GPU/network, nonroot
  read-only container inputs, one BLAS thread. Global deadline included source
  authentication; no wall/memory/overall-fit cap was hit.
- Container exited 0, `OOMKilled=false`, stderr empty. Exact owned container
  removal succeeded. A stale-approval preflight was rejected before this run;
  it did not produce fits and is not part of the numerical results below.
- Current raw image/b-value/b-vector bytes were stream-hashed. Cached signals
  were authenticated through pinned bank/manifest/receipt and historical
  complete-source reconstruction checks. This was **not a fresh preprocessing
  reconstruction**. No old fitted parameter arrays or Sol outputs were read.
- Source-free engineering tests: 69 passed before launch. These tests and the
  runtime success are not scientific validation or difficulty evidence.

Authoritative artifacts are under
`/home/zijiaochen/projects/brain_researcher_benchmark/tracking/scientific_pilots_2026-10-04/pr156/`:
`result.json`, `launch.json`, `container.before.json`, `container.after.json`,
`cleanup.json`, `pilot/selection.json`, `pilot/attempts.jsonl`, and
`pilot/report.json`. Original artifacts remain unchanged; this note derives
descriptive summaries from them without rerunning any fit.

## Fit adequacy before ambiguity

The normalization is measured b0. Percentages below are `100*sqrt(loss)`;
they are not percent error against ground-truth tissue or a calibrated noise
standard. Best-found means the lowest independently feasible candidate loss
across both routes and all attempted fractions, not a proven global optimum.

| Protocol | Minimum normalized RMSE | Median | Maximum | Best tensor at lower-eigenvalue boundary |
| --- | ---: | ---: | ---: | ---: |
| b0+1000 | 6.49% | 12.32% | 25.47% | 11/16 |
| b0+1000+2000 | 6.68% | 11.80% | 24.88% | 3/16 |

No best-found candidate hit the prespecified S0 or upper-eigenvalue boundary
flags. Best S0/b0 ranges were 1.0000–1.0137 and 0.9243–0.9980 respectively.
The worst-fit coordinate was `(32,70,30)` under both protocols. Tensor-boundary
frequency and appreciable residuals both deserve investigation; neither proves
a particular cause such as noise, model mismatch or preprocessing error.

## Solver behavior

Feasibility is the independent parameter-domain/forward-arithmetic check;
optimizer success is only its termination report.

| Route | Attempts | Feasible candidates | Successful termination | Feasible despite unsuccessful termination |
| --- | ---: | ---: | ---: | ---: |
| TRF, eigensystem | 384 | 384 | 383 | 1 |
| SLSQP, direct tensor | 384 | 251 | 253 | 1 |

SLSQP's 133 missing feasible candidates comprise **96 objective-call-cap
aborts** and **37 tensor-domain rejections**. Three optimizer-success rows
were nevertheless infeasible. These are fitting/constraint limitations, not
failed benchmark questions. Every attempt slot is retained; objective-cap
aborts have no completed candidate, so their profiles remain incomplete.

Most cap aborts occurred at f=.9/.99: 41 of 45 single-shell aborts and 46 of
51 two-shell aborts. Profile completeness cannot be inferred from overall
run completion. Both algorithms had at least one feasible candidate in every
voxel/protocol slot, but their joint source/library dependencies remain.

For best feasible candidates, the maximum cross-route loss difference was
`6.75e-12` for b0+1000 and `3.45e-4` for b0+1000+2000. Maximum corresponding
FA differences were `4.80e-6` and `0.05167`. The two-shell outlier was
`(32,70,30)`: SLSQP's best feasible candidate came from f=.25 while TRF found
a lower-loss free-f candidate at f=.43171. This is a search-quality issue,
not evidence for matching either route's parameter coordinates as ground truth.

## Found FA separation by the predeclared budgets

Each cell summarizes the **demonstrated lower bound** on the FA range in the
found feasible candidate pool. Ceilings were best-found loss plus the listed
increment. None is a confidence interval, a complete feasible-set range,
or a calibrated benchmark acceptance threshold.

| Protocol | Added normalized MSE | Minimum FA separation | Median | Maximum |
| --- | ---: | ---: | ---: | ---: |
| b0+1000 | 0.000025 | 0.00000046 | 0.36770 | 0.62920 |
| b0+1000 | 0.000100 | 0.08637 | 0.44135 | 0.62920 |
| b0+1000 | 0.000400 | 0.09234 | 0.44194 | 0.62920 |
| b0+1000+2000 | 0.000025 | 0 | 0.00115 | 0.01530 |
| b0+1000+2000 | 0.000100 | 0 | 0.00422 | 0.04762 |
| b0+1000+2000 | 0.000400 | 0.00078 | 0.04965 | 0.16874 |

Each row has 16 source locations. The f≤.7, f≤.9 and full f≤.999 **found-pool
views give identical separation summaries** for every protocol/budget. Thus
these particular demonstrated gaps are not created solely by keeping
near-f=1 candidates. This does not validate the chosen domain: the views
are sparse candidate filters, not new restricted-domain fits or complete
profiles. Several witness endpoints lie on the lower tensor boundary.

The visibly smaller two-shell found gaps do **not** demonstrate true interval
contraction: protocol-specific mean-loss feasible sets need not nest, and
independent search lower bounds need not reflect their actual range ordering.

Two inspectable examples:

- `(52,67,17)`, b0+1000, increment .000025: attempts **144/157** give
  FA **.29136/.92056**, f approximately **0/.5**, losses
  **.01068309/.01068865**. The second tensor is at the PSD boundary within
  declared roundoff tolerance. Their gap .62920 is numerically supported
  under this operational ceiling, around normalized RMSE of roughly 10.3%.
- `(60,89,18)`, b0+1000+2000, increment .0004: attempts **324/312** give
  FA **.72142/.89016**, f **.5/.60624**, losses
  **.03918555/.03895497**. The higher-FA endpoint is at the lower tensor
  boundary; both residuals are about 19.7–19.8% of measured b0.

## Decision and next work

**Continue scientific qualification, not Sol calibration yet.** The pilot
establishes practical execution and concrete source-bound sensitivity evidence.
It does not justify declaring the task hard, uniquely answerable, or ready for
benchmark scoring.

Before another approved pilot:

1. Inspect the absolute residual pattern and source/QC/preprocessing assumptions
   on the fixed sample. Separate model inadequacy from fitting failure; do not
   call a small loss increment around a poor fit observational equivalence.
2. Choose a defensible adequacy/noise or explicitly nonstatistical discrepancy
   contract prospectively. One b0 and spatial smoothing do not supply a
   validated independent-noise model. Do not select cutoffs now merely to
   preserve the largest observed FA gaps.
3. Resolve PSD-boundary interpretation and improve/qualify the constrained
   profile search while preserving finite failed candidates and complete
   coverage. The current SLSQP cap failures make an exhaustive profile claim
   untenable; no additional runs or new thresholds were introduced here.
4. Only after independent source-bound reference evidence and public grading
   semantics are qualified should a new frozen task receive in-container
   oracle/negative controls and fresh blinded model calibration.

Artifact hashes:

- `pilot/report.json`: `93aa728a70eeee486307fd2a4df0878993759d76ef6981d7b69386bd41d1308f`
- `pilot/attempts.jsonl`: `bc067da6dfd3bc6a08407f960cba015d5692c0fc95a0aeaba722cfdee2d3ca77`
- `pilot/selection.json`: `e285ada92e94f21f964ca751b0cfafcdaeae172ff4c646ed9f1e1cb4a5746b6e`
