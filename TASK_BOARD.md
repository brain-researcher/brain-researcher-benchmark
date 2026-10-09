# Task board

One row per paper in the pipeline. Stages: `1-assigned → 2-step0 → 3-v0+oracle →
4-agent-gate → 5-ratchet → 6-merge`. A paper dropped at Step-0 stays here with
`stage=dropped` and the reason — that's a logged success, not a deletion. See
`INTERN_GUIDE.md` for the contract, `ASSIGNMENT_QUEUE.md` for lanes.

| task_id | author | paper | lane | failure axis | lever | stage | step-0 result | oracle | agent verdict | updated |
|---|---|---|---|---|---|---|---|---|---|---|
| GRADIENT-001 | zjc | Vos de Wael 2020 / Margulies 2016 (gradients) | rest-conn (ds000228) | over-claim | none (rigor genre) | 6-merge | apex NOT robustly reproducible → rigor genre | 1.0 | GPT-5.5 FAIL 0.46; Claude FAIL 0.365 (un-cued overclaim) | 2026-06-24 |
| SOCIALBRAIN-001 | zjc | Richardson 2018 Nat Commun (ToM–pain anticorrelation) | rest-conn (ds000228) | confident-refutation | GSR | 6-merge | reproduces ONLY under GSR (−0.07 n.s. → −0.34) | 1.0 | GPT-5.5 FAIL; Claude FAIL (flat verdict, never try GSR) | 2026-06-24 |
| DEVCONN-001 | zjc | Fair 2009 PLoS CB (local→distributed developmental connectivity) | rest-conn (ds000228) | wrong-cause | head motion / QC-FC | 6-merge | dev effect real (seg child>adult p=0.030; age~short r_s=−0.205 p=0.011) → COLLAPSES under motion control (partial\|FD p=0.68; matched p=0.61); kids move 2× (FD 0.371 vs 0.187) | 1.0 | GPT-5.5 4/4 FAIL + Claude 3/3 FAIL (all compute it, none volunteer the motion check) | 2026-07-02 |
| ANTCONFLICT-001 | garrettl | Fan 2005 NeuroImage (ANT conflict → dACC) | task-fMRI (ds001907) | wrong-cause | time on task (RT in the GLM) | dropped | runs 1–2: after a regressor-scaling fix, face value n.s. (2 s targets p=.057/.081; independent pipeline p=.063) → gate not met; runs 1–6 under a pre-stated rule: RAW robust (correct-trial t=5.64, independent pipeline t=6.33, n=24) but the RT controls disagree (RT modulator t=−0.57 n.s.; RT-length epochs t=3.86 p=.0008) → no flip, and no fair fixed key for the wrong-cause verdict → archive | — (built then removed; kept in history at 9e77b1f) | — | 2026-10-08 |

<!-- add rows below; keep newest work at the bottom of its lane -->
