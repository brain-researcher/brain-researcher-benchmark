# Phase 2: diagnose residuals before defining a grader

Question: do the previously observed 6–25% normalized residuals survive an
independent selected-source reconstruction and independent arithmetic, and
where do the remaining discrepancies occur? This is exploratory diagnosis on
the same 16 already-seen coordinates, not a new qualification sample.

The frozen prior pilot, its 768 attempt records, and original task/source files
are immutable inputs. No new optimization, exclusions, grading threshold,
noise estimate, or biological conclusion is authorized. The 96 capped attempts
without retained parameters remain unresolved; the other 672 candidates can
be reconstructed. The 32 existing best-feasible voxel/protocol representatives
receive full shell/direction diagnostics, without changing the selected support.

## Independent checks

`phase2_diagnostic.py` imports neither the old forward functions nor an
optimizer, SciPy, or nibabel. It expands the quadratic form independently and
recomputes MSE, FA, and the unchanged public domain. Source bytes, cache bytes,
volume membership, and original gradient ordering are authenticated.

A limited NIfTI-1 uint16 reader parses endian, shape, voxel offset, storage order,
and intensity scaling. It streams volumes 0–128 and evaluates the selected
Gaussian samples directly from 27 neighbors. Weights, products, and sums use
float64. Radius, voxel units, reflect convention, and scaling are explicit in
the contract; manufactured fixtures test these against a separate filter route.
The compatibility tolerances allow only declared summation-order differences;
they are not noise thresholds or scientific acceptance limits.

Matching gradient bytes does not establish physical gradient orientation.
The full ROI/mask is not reconstructed, and proxy anatomy is not validated.
Zero, negative, nonfinite, or above-baseline observations are descriptive QC,
not exclusion rules. Shell residuals use the measured b0 denominator and cannot
identify noise, artifacts, or model misspecification by themselves.

## Execution and interpretation

The default is dry-run. Explicit root approval binds the contract, diagnostic,
launcher, and unchanged isolation-helper hashes. The envelope is one CPU,
2 GiB memory with no additional swap, 900 seconds including authentication,
64 MiB outputs, no network/GPU, nonroot, and read-only inputs. The output root is
new and cannot overwrite prior evidence. Exact owned-container cleanup and
failure records are retained.

Source disagreement stops residual analysis. An arithmetic-disagreement result,
even with process exit 0, is failed/incomplete diagnostic qualification: do not
attribute residual causes until it is resolved. Successful agreement only
narrows implementation explanations; it does not validate biological adequacy,
identifiability, benchmark difficulty, or release readiness.

The independent reviewer read the contract, diagnostic, launcher and
manufactured tests and found no scientific blocker to this bounded diagnosis.
Root must still review final hashes, commit the exact allowlist, and authorize
execution. The tests are source-free engineering evidence only.
