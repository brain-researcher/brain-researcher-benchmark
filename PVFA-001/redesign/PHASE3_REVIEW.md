# Phase 3: replay the same candidates on two numerical substrates

Question: do unchanged candidate parameters reproduce the old feasibility and
metrics when evaluated on the exact original cached signal, while retaining the
separate outcome on the independently reconstructed signal?

This changes neither the model/domain nor its tolerances. The canonical input
is the authenticated numerical array used by phase 1, not newly established
biological truth. Both routes reuse the frozen independent phase-2 arithmetic
so that the only varying factor is the input signal representation. This is
not a third independent implementation or a new search.

The contract pins the prior 768 slots, 672 retained candidates, 16 coordinates,
32 best representatives, and 288 sensitivity rows. Missing candidates remain
missing. Prior metrics and phase-2 metrics are compared separately; no pool or
score is replaced. Endpoint and representative audits record membership only,
not new selection or a fresh scientific interpretation.

Only source-array keys are read from the bank. Phase-2 selected-source and raw
authentication receipts provide the reconstruction lineage; raw images are
not re-read. The replay cannot newly validate physical gradient orientation,
anatomy, noise, biological adequacy, or optimization quality.

Default execution is dry-run. A separate root approval binds the exact contract
and all four imported/executed code files. Root commits before source execution.
The isolated launch has one CPU, 2 GiB memory with no extra swap, a global 60 s
deadline including authentication, 16 MiB artifact cap, read-only inputs, and
no GPU/network. It refuses an existing output directory and retains logs,
container metadata, failure evidence, and exact-owned cleanup. Emergency cleanup
has its own bounded grace period after the analysis deadline.

Manufactured tests exercise both S0-boundary flips, strict canonical rejection
outside those bounds, interior points, absent candidates, metric disagreements,
full 768-slot bookkeeping, approval/resource gates, and immutable parameters.
These tests are engineering evidence only. The earlier phase-2 disagreement
status remains preserved even if this replay completes successfully.

The separate `ADEQUACY_SEARCH_PROPOSAL.md` is design-only. Its analysis/search
is not implemented or authorized by phase-3 replay approval.
