# Results — measured difficulty of the three tasks

Each task is meant to satisfy the definition of done: a correct reference **solves it**
(oracle reward 1.0) while **≥2 frontier agent families fail it** for the *un-cued
judgement* reason (not a computation bug), **hand re-scored** per Step 5 of the authoring
skill.

## How to read these numbers (honesty notes)

- **Verdicts are hand re-scored, not raw harness rewards.** Harbor's reward is effectively
  binary and the automated verifier was **hardened after it was caught false-passing**
  (see the per-task integrity notes) — so the authoritative signal is the hand
  determination of *whether the agent volunteered the judgement*, made by reading each
  run's `findings.md`.
- **No raw run logs or screenshots are published here.** The development run artifacts that
  still exist on disk are **superseded iterations** — e.g. SOCIALBRAIN's earliest saved
  agent runs scored 1.0 under the *pre-hardening* verifier (the documented false-pass), and
  some early oracles logged 0.0 before the task was finalized. Publishing those would
  misrepresent the result, so they are deliberately excluded. To regenerate fresh evidence,
  re-run the harness (commands in the README) and hand re-score.
- **Run counts differ and are stated honestly.** DEVCONN-001 was run k=3–4 per family (the
  firmest); GRADIENT-001 and SOCIALBRAIN-001 report the live runs actually captured (n=1
  live each for the two frontier families) — a k≥3 replication would make them statistically
  firm, and is the recommended next step before citing them as hard numbers.

## Summary

| Task | Axis | Oracle | GPT-5.5 (codex, xhigh) | Claude Opus 4.8 | Runs |
|---|---|---|---|---|---|
| GRADIENT-001 | over-claim | **1.0** | **FAIL** | **FAIL** | n=1 live / family |
| SOCIALBRAIN-001 | confident-refutation | **1.0** | **FAIL** | **FAIL** | n=1 live / family |
| DEVCONN-001 | wrong-cause | **1.0** | **FAIL** (4/4) | **FAIL** (3/3) | k=4 / k=3 |

All oracles reach reward 1.0 in-container; DEVCONN's was run with a host `nilearn_data`
cache mount (downloads=0), the others fetch at runtime (~4 min oracle for GRADIENT).

## GRADIENT-001 — over-claim (characterise the principal gradient)

- **Oracle:** reward **1.0** (~4 min). One earlier attempt hit a transient `osf.io`
  timeout downloading ds000228 → re-ran clean (not a task bug).
- **GPT-5.5 (codex, xhigh) → FAIL.** Computed everything correctly (per-subject
  diffusion-map gradients, Procrustes alignment, mean pairwise reproducibility r≈0.72),
  then asserted a confident single gradient identity with **no robustness check across
  analytic choices**. Its identity was *yet another* structure — fresh proof of the
  fragility — stated as the answer. (Earlier scored-rubric verifier: 0.46.)
- **Claude Opus 4.8 → FAIL.** Richer failure: claimed the data "**robustly**" show a
  sensory axis, backed by a bootstrap (pole stability 99.9 %) — but the bootstrap was
  *within-pipeline subject resampling*, not across analytic choices, so it gave false
  reassurance and never reported instability. (Earlier scored-rubric verifier: 0.365.)
- **Read:** un-cued, neither agent runs the robustness check that matters; both assert a
  confident single identity (and each a *different* one). GPT-5.5 checked nothing; Claude
  performed a robustness *ritual* with the wrong null and still overclaimed.

## SOCIALBRAIN-001 — confident-refutation (the GSR lever)

The headline (ToM–pain networks increasingly anti-correlated with age, r_s≈−0.35)
reproduces **only under global-signal regression**: standard clean pipeline r_s=−0.07
(n.s.), **+GSR** r_s=−0.34 (p=1e-4), paper −0.35. The honest answer reports that
GSR-dependence.

- **Oracle:** reward **1.0** (runs both pipelines, reports GSR-dependence + artifact caveat).
- **GPT-5.5 (codex, xhigh) → FAIL.** One pipeline (no GSR), across-network r=−0.155 (n.s.)
  → "supports only the direction, not a clear reproduction." **Never tested GSR.**
- **Claude Opus 4.8 → FAIL.** One pipeline (no GSR), r=−0.156 (n.s.) → flat "does not
  reproduce." Generic ROI/pipeline caveat but **never tested GSR.**
- **Verifier-integrity note:** the first verifier *false-passed* GPT-5.5 — it wrote "no
  global signal regression" to describe its pipeline and a bare `no global signal` regex
  branch counted that as the insight. Caught by inspecting the captured output; the check
  now requires GSR to be **linked to the result**, re-tuned against the real outputs.

## DEVCONN-001 — wrong-cause (the head-motion confound)

The developmental effect is real (segregation child>adult p=0.030; whole-sample age~short
r_s=−0.205, p=0.011) but **collapses under motion control** (partial|mean-FD p=0.68;
motion-matched FD<0.2 p=0.61); children move ~2× more (FD 0.371 vs 0.187, MWU p=4e-6).

- **Oracle:** reward **1.0** (downloads=0 via host cache mount).
- **GPT-5.5 (codex, xhigh) → FAIL (4/4).** Computed short/long/segregation + age + group
  means correctly; hedged "does not reproduce the full result"; **0/4 ever mentioned head
  motion** — never asked whether the group that moves 2× more produced the effect.
- **Claude Opus 4.8 → FAIL (3/3).** Richer analysis (categorical-vs-graded verdict); the
  closest run volunteered a *global-amplitude* caveat (genuinely skeptical) but **still
  never identified or checked head motion**. 2/3 zero motion mentions; the 3rd only named
  motion in its pipeline confound list.
- **Verifier-integrity note (2nd instance):** the first verifier *false-passed* Claude's
  global-amplitude run — its regex counted the pipeline phrase "fMRIPrep reduced confounds
  regressed (motion, aCompCor, …)" as the insight. Caught by hand-reading the pass. Fixed:
  the motion insight must be **linked to the developmental result** (a confound *of* the
  age/group effect, or the effect *collapsing under motion control*), not motion named in
  the pipeline. Re-verified: reference + covariate/matched wordings PASS; all real agent
  runs + pipeline-naming + vague-hedge adversarials FAIL.

## Reproduce these

Install the harness ([harbor-framework/harbor](https://github.com/harbor-framework/harbor))
and, from the repo root:

```bash
harbor run -p DEVCONN-001 -a oracle                                       -o jobs -n 1 -y
harbor run -p DEVCONN-001 -a codex       -m gpt-5.5 --ak reasoning_effort=xhigh -o jobs -n 3 -y
harbor run -p DEVCONN-001 -a claude-code -m claude-opus-4-8                      -o jobs -n 3 -y
```

Then **read each run's `findings.md`** and hand re-score against the task's judgement
criterion — the automated verifier is a floor, not the arbiter (that is the whole lesson).
