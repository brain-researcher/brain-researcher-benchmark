# Native release qualification — 2026-10-04

Outcome: **in-container oracle reward1.0 and all13 fixed controls behave as
declared**. This qualifies the implementation and isolation boundaries, not
empirical task difficulty. Fresh model calibration is a separate next stage.

Implementation commit: `ac00521fcec81c99a2dacc4cc21cbb1ddcaa5155`.
Exact runnable task/evidence root:
`/home/zijiaochen/projects/brain_researcher_benchmark/tracking/scientific_release_2026-10-04/`.

## Evidence

- 29 new source-free release tests,5 host-adapter tests,11 fixture-uploader tests
  and10 cleanup-helper mock tests passed. These are not scientific replications.
- Clean agent and verifier image audits each authenticate26 source members and
  exclude the opposite partition. The old image is a build-stage runtime source,
  not the final image ancestor; only Ubuntu and an empty layer are shared.
- Native installed Harbor0.17.1 oracle-v3 completed in44s, reward1, no exception
  or retry. Discovery output was captured, its agent environment stopped, and a
  separate offline verifier certified the frozen discovery before running the
  evaluator as UID61616. Evaluation took7.731s; no child survived.
- Independent arithmetic, opposite axis sign and certified norm-roundoff all
  pass. No exact canonical eigenvector orientation is required.
- All33 explicit isolation probes passed: unprivileged identity/no extra groups,
  absent private/tests/proc/dev/socket/verifier-log paths and20 opposite-partition
  source paths, denied writes to fit/contract/Python, no inherited FD3..63, and
  active no-new-privileges. An independently orphaned setsid child was killed
  and reaped before grading.
- Eight invalid controls produce their intended ValueError, not an unrelated
  runtime zero: empty discovery; naive axis; held-out-informed support; fabricated
  transfer; held-out-optimal axis substitution; blanket unjustified null; missing
  participant; incorrect network interpretation. Invalid discovery never reaches
  submitted evaluator execution.

Actual receipts verify2CPU/8GiB per role, no extra swap/GPU, verifier networknone,
bounded64MiB scratch/16MiB output tmpfs, restricted trusted-parent capabilities,
no agent mount into verifier logs and unchanged captured submissions. The model
agent phase will allow only the three frozen OpenAI endpoint hosts; setup and
verification remain offline. This is one-shot held-out computation after coding,
not a second interactive model session.

The frozen scientific results remain10 evaluation slots,9 defined and one
source-inactive null (`sub-pixar124`,parcel119); mean Rayleigh fraction
0.5740165411839218. Negative/mixed network configurations remain valid. The task
is an honestly labelled fixed-cohort method-validation case, not the original
adult-HCP finding, spatial/anatomical validation or confirmed hard benchmark.

## Artifact identities

- Agent image: `sha256:c0f3c458aaa596ef682b942f309e0f861cdba82b05854bb235b3a34f5b53345d`.
- Verifier image: `sha256:c812c9837692a79758c769be5d942b1bac8aafc4eddebf572a44c480572a8532`.
- `qualification_result.json`: `4d998a35142b847dbd122f5ee8b96c783ce80b6c06c8f0d7d03971d58b3b9f07`.
- Oracle job `jobs/oracle-v3/result.json`: `25fe2d9cb8a247237ea2577db915c2f1792bd5a65072fa750d5ecdf1e1e63bdc`.
- Oracle verifier receipt: `87747b77fd8adfc988fbfd24cf04b656d3c6fc68681b13cbde12d637392f763f`.

Every job retains configuration, raw submissions, verifier stdout/reward,
container receipts and terminal result. Reviewed external host tools are
snapshotted in `authoring_runtime/`; they are never agent-visible image assets.

## Preserved failures and next gate

Initial image builds failed at raw-image-ID metadata resolution; using an
authenticated local tag fixed packaging without changing source. Oracle-v1
failed before scientific execution on duplicate Compose security options;
oracle-v2 failed before solving on Docker's NNP serialization. All failures are
retained. External-only runtime-v3 corrects these, with task/image/method/threshold
bytes unchanged. These setup failures are not model or scientific failures.

The conditional next run is exactly GPT-6.1 Sol/Max/CLI0.160.0,k1,zero retries,
agent3000s/verifier300s,2CPU8GiB,outer4500s/output256MiB/diskfloor50GiB. Its raw
trajectory must be reviewed before interpreting reward. No empirical hardness
claim is made by this qualification report; old tasks and Sol outputs/scores
remain unchanged. Local commits only; no GitHub push or merge.
