# One-shot, discovery-only benchmark release

This version preserves the qualified fixed20 design and every earlier task and
qualification artifact. It is a paper-derived method-validation case, not an
original-paper replication or an empirically hard task until calibrated.

The installed Harbor 0.17.1 has a real separate-verifier lifecycle:
`SingleStepTrial._run` runs the agent, captures artifacts, stops the agent
environment, then calls `Trial._run_separate_verifier`. Task configuration uses
`[verifier].environment_mode = "separate"` and `[verifier.environment]`.
The verifier build context is `tests/`; its baked `/tests/test.sh` is executed
with `skip_tests_upload=True`. Artifact paths are transferred to their original
absolute paths. The ordinary convention artifact directory is also transferred
by Harbor, but it is not trusted or imported by our grader.

The coding-agent image starts from a clean pinned Ubuntu final stage and copies
only the scientific runtime from the old source image; the old image is a build
stage, not an ancestor of the final runtime image. Only authenticated discovery
files and a public contract enter the final image. No held-out image bytes,
private reference values, solution, grader, Docker socket, or source capture
are accessible, including to container root. The agent submits discovery.json
and evaluate.py. Evaluation is deliberately one-shot after coding terminates,
not a second interactive model session. A discovery self-test is possible.

The host must fail closed if stopping the coding environment fails. Its approved
runtime adapter must ensure no surviving agent can write the host verifier-log
mount during grading; stock Harbor's best-effort stop alone is insufficient for
this guarantee. Capture and source access probes are runtime qualification gates.

The fresh verifier validates a bounded, regular-file snapshot of discovery.json
against independently qualified source-backed receipts before executing any
submitted program. It accepts either sign of the certified discovery axis,
not an eigenvector fingerprint. Source-dependent nulls, all participant slots,
all ten deletion diagnostics and negative/mixed network results are checked.
Scalar envelopes are published and are numerical serialization allowances,
not scientific success thresholds.

Submitted evaluate.py is never imported in the trusted interpreter. A root-owned
chroot contains only a read-only Python/scientific runtime, evaluation capsule,
public contract, captured discovery.json, submitted program and writable output/
scratch. It has no /proc, device tree, inherited descriptors, host socket,
discovery images, grader, reference, or reward path. Before exec, the child
chroots, changes directory, drops supplementary groups/GID/UID, applies resource
limits and no_new_privs. The parent verifies all processes of the dedicated UID
are dead before parsing a bounded regular result. The fit bytes must remain
unchanged. Nonfinite values, duplicate JSON keys, symlinks, fake nulls and wrong
participant inventories fail. Chroot plus the outer Docker network/CPU/memory
boundary is the security boundary; arbitrary Python remains untrusted.

Private references are the already source-qualified, independently checked
phase2 receipts bound to exact source/contract hashes. The task grader does not
re-run a hidden estimator or choose a more favorable answer. These shared
qualified receipts are not a fully independent new scientific replication.

Prospective resources: agent 2 CPU, 8 GiB RAM, 3000 s; verifier 2 CPU, 8 GiB RAM,
300 s; untrusted evaluator 180 s CPU/wall, 1 MiB per output file, 16 processes,
8 GiB virtual memory, no network/GPU. Only the root authorizes builds and runs.
