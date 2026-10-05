# Paired-shell diagnostic A: implementation review

Status: implementation and manufactured tests only, pending independent root
review and a hash-bound execution approval. No acquired-data diagnostic has
been run by this commit. This implements only part A of
`ADEQUACY_SEARCH_PROPOSAL.md`, without numerical-PSD certification. Part B's
128-fit extension remains unimplemented and unauthorized.

## Scientific and arithmetic contract

The fixed mathematical PSD tensor/nonnegative-mixture model predicts
`p_b1000 >= p_b2000` for identical released directions. Exact direction equality
is authenticated one-to-one without angular tolerance, antipodal substitution,
or normalization. Duplicate or unmatched vectors stop the study. Source vector
equality does not establish physically correct gradient orientation.

The least squared distance from observations `(y1,y2)` to the relaxed half-plane
`p1 >= p2` is zero if `y1 >= y2`. Otherwise the orthogonal projection is
`p1 = p2 = (y1+y2)/2`, so the summed squared error is `(y2-y1)^2/2`. Summing this
value over the 64 disjoint pairs and dividing by measured canonical b0 squared
and **129**, including the omitted b0 slot in the original denominator, gives
the ideal-PSD relaxation value. Dropping positivity, shared tensor/fraction/S0,
and b0-residual constraints enlarges the prediction set; it does not tighten it.

The implemented float64 value is descriptive, not a rigorous computational
certificate. It is **not certified for the existing roundoff-tolerant numerical
tensor domain**, which permits tiny negative eigenvalues. No operational
candidate-loss comparison or fraction-explained statement is made. No cutoff
is selected. Reversed observed order can arise from noise, so it cannot identify
artifacts, biological misspecification or acquisition errors.

The same 16 already examined voxels are retained, with all 1,024 signal pairs,
source volume indices, coordinates, observations and contributions. This is
exploratory, and the scan, not each voxel, is the acquisition unit. No candidate
parameters or old Sol outputs are read. Existing pools, scores and reports stay
unchanged. The source bank and generated evidence remain private.

## Runtime and checks

`paired_shell_contract.json` binds the bank, fixed selection, original pilot
contract, source-check receipt and canonical-replay receipt by SHA-256. Existing
runtime helpers are hash pinned. The launcher requires an external exact
root-approved code/contract manifest and a previously absent evidence root.

The retained immutable image is used with one CPU, 2 GiB RAM/no swap extension,
60-second host wall cap, no GPU/network, a read-only root, dropped capabilities,
unprivileged identity, read-only inputs, 16 MiB temporary space and a 16 MiB
evidence guard. Emergency cleanup checks the launch's ownership label and acts
only on its exact container. No optimizer is imported or invoked, no fits or
model calls occur, and no data are fetched.

Manufactured source-free tests check ordered/reversed/equal observations;
rational orthogonal projection and the direction of the bound; noisy predictions
from a fixed PSD mixture; pairing permutation, missing exact equality, duplicate,
antipodal, nonfinite and zero vectors; output row completeness and the per-voxel
mean-SSE denominator; approval/resource caps; and refusal to overwrite evidence.
They are engineering checks, not a result about this acquisition.

Dry run: `python3 -B PVFA-001/redesign/launch_paired_shell.py`.
Execute only after review:
`python3 -B PVFA-001/redesign/launch_paired_shell.py --execute --approval <root-approval.json>`.

Even completion leaves the scientific adequacy/noise contract and search
limitations unresolved; it does not release the task or authorize Sol.
