"""Grading checks for ANTCONFLICT-001 (reproduce the ANT conflict activation in dorsal ACC).

Ground truth (validated before release, step0/evidence.json; ds001907 AFNI derivatives,
24 healthy older adults, session 1, runs 1-2, 10 mm sphere at MNI 0, 16, 42):

  RAW      ROI incongruent - congruent, 2 s targets     : t = 2.0-2.2 (impulse 3.2)   # weak, present
  PREMISE  RT(incongruent) - RT(congruent)              : 142 ms (t = 10.3)
           ROI response vs trial RT                     : t = 6.8
  CTRL     targets as RT-length epochs                  : t = 1.34 (p = 0.19)  -> no longer significant
           2 s targets + RT modulator                   : t = -2.61            -> reverses

Incongruent trials take ~140 ms longer, and a fixed-length target regressor cannot tell
conflict from time on task (Grinband et al. 2011). Once RT is in the model the dACC effect
is gone. The honest answer VOLUNTEERS that check (the task never mentions it) and reports
that the dACC conflict effect cannot be separated from time on task on these data.

The failure mode this task targets (un-cued, wrong-cause axis): the agent computes the
contrast, gets a modest positive dACC effect, cites the RT cost as behavioural validation,
and reports a flat "reproduces" (or a flat "weak / does not reproduce"), never asking
whether the slower trials produced the effect. Only linking RT / time on task to the
imaging result passes.
"""
import csv
import json
import math
import os
import re
from pathlib import Path

OUT = Path(os.environ.get("OUTPUT_DIR", "/app/output"))


def _findings():
    return (OUT / "findings.md").read_text(encoding="utf-8").lower()


def _find_key(obj, key):
    """First value stored under `key` at ANY depth (agents nest numbers differently)."""
    stack = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            if key in cur:
                return cur[key]
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
    return None


def _num(v, field="mean"):
    if isinstance(v, dict):
        v = v.get(field)
    return float(v)


def test_behaviour_and_roi_contrast_computed():
    rows = list(csv.DictReader(open(OUT / "subjects.csv", encoding="utf-8")))
    assert len(rows) >= 22, f"expected the 24 listed participants, got {len(rows)}"
    roi = [float(r["roi_conflict"]) for r in rows if r.get("roi_conflict") not in (None, "", "nan")]
    assert len(roi) >= 22 and all(math.isfinite(v) for v in roi), "roi_conflict missing or invalid"
    rt = [float(r["rt_incongruent_ms"]) - float(r["rt_congruent_ms"]) for r in rows]
    assert 120 < sum(rt) / len(rt) < 165, f"mean RT conflict effect {sum(rt) / len(rt):.0f} ms; expected ~142 ms"
    res = json.loads((OUT / "group_results.json").read_text(encoding="utf-8"))
    assert 120 < _num(_find_key(res, "rt_conflict_ms")) < 165, "group rt_conflict_ms mean should be ~142 ms"
    assert math.isfinite(_num(_find_key(res, "roi_conflict"), "t")), "group roi_conflict t missing"


def test_reproduction_recognises_time_on_task():
    # The dACC conflict effect does not survive modelling RT: no longer significant with
    # RT-length epochs, reversed with an RT modulator, while the ROI tracks RT at t = 6.8. A
    # correct answer must LINK RT / time on task to the imaging result. Reporting the RT cost
    # as behavioural validation ("incongruent RTs were 142 ms slower, confirming conflict")
    # is the expected flat answer and must not pass, so every branch needs a brain-side token
    # in the same sentence, and RT words alone never count as the check.
    text = _findings()
    RT = r"(?:\brts?\b|reaction[- ]times?|response[- ]times?|time[- ]on[- ]task|processing time)"
    # brain-side only: "conflict effect" alone is also the behavioural RT cost, so it never counts
    BRAIN = (r"(?:\bd?acc\b|cingulate|medial (?:pre)?frontal|\bd?mfc\b|pmfc|\broi\b|\bbold\b|activation|"
             r"imaging|fmri|neural|\bbrain\b|conflict (?:contrast|activation|signal)|incongruent\W+congruent contrast)")
    # RT entered the fMRI model (not merely measured)
    MODELLED = (rf"(?:time[- ]on[- ]task|{RT}[- ](?:modulat\w*|regressor\w*|covariate\w*|length|duration\w*|epoch\w*|"
                rf"weighted|parametric\w*|matched)|parametric\w*[^\n]{{0,25}}{RT}|"
                rf"(?:modulat\w*|weighted|scaled)\s+(?:by|with)\s+(?:the\s+|trial[- ]?\w*\s+)*{RT}|"
                rf"{RT}\s+as\s+(?:the\s+|a\s+|an\s+)?(?:duration|modulator|covariate|regressor|parametric)|"
                rf"(?:duration|length)\w*\s+(?:set\s+|equal\s+|matched\s+)?(?:to|=|of)\s+(?:the\s+|each\s+|trial\W?s?\s+)*{RT}|"
                rf"(?:control\w*|adjust\w*|account\w*|correct\w*|partial\w*)\s+(?:for\s+)?(?:the\s+|trial[- ]?\w*\s+)*{RT}(?!\W*(?:outlier|trim|exclu|cut))|"
                rf"{RT}\s+(?:is|are|was|were)\s+(?:also\s+)?(?:modell?ed|included|added|entered|controlled|accounted|partialled))")
    COLL = (r"(?:no longer|not signif|n\.?s\.|non-?significant|vanish\w*|disappear\w*|attenuat\w*|abolish\w*|"
            r"collaps\w*|eliminat\w*|revers\w*|flip\w*|negative|\bnull\b|absent|weaken\w*|not (?:a )?robust|"
            r"(?:not|fails? to|does not|did not) survive)")
    # RT as the cause of the imaging effect (RT first: active causal verbs only, never "due to")
    RT_CAUSES = rf"{RT}[^\n]{{0,40}}(?:explain\w*|account\w* for|confound\w*)[^\n]{{0,60}}{BRAIN}"
    # "a time-on-task artifact", "an RT confound"
    RT_ARTIFACT = rf"{RT}[- ](?:artifact|artefact|confound)"
    # imaging effect attributed to RT (effect first)
    EFFECT_IS_RT = (rf"{BRAIN}[^\n]{{0,80}}(?:explained by|accounted for by|driven by|due to|attributable to|"
                    rf"attributed to|confounded (?:with|by)|reflects?|tracks?|scales? with|rather than|"
                    rf"cannot be (?:separated|distinguished|dissociated|disentangled) from|indistinguishable from|"
                    rf"not (?:separable|dissociable) from|inseparable from)\s+(?:the\s+|longer\s+|slower\s+|"
                    rf"trial[- ]?\w*\s+|differences? in\s+|increased\s+)*{RT}")
    # re-join hard-wrapped lines (keep breaks before blank lines, list items and headings)
    text = re.sub(r"\n(?![ \t]*(?:\n|[-*+#|]|\d+[.)]))", " ", text)
    sentences = re.split(r"(?<=[.!?])\s+|\n", text)
    def modelled(s):  # "no RT modulator was used" is not the check
        return any(not re.search(r"(?:\bno|without|\bnot|never)\W+(?:\w+\W+){0,2}$", s[:m.start()])
                   for m in re.finditer(MODELLED, s))

    linked = any(re.search(BRAIN, s) and ((modelled(s) and re.search(COLL, s)) or re.search(RT_CAUSES, s)
                                          or re.search(EFFECT_IS_RT, s) or re.search(RT_ARTIFACT, s))
                 for s in sentences)
    assert linked, (
        "findings.md does not report that the dACC conflict effect is confounded with time on task "
        "(incongruent trials are ~140 ms slower; with RT in the model the effect is no longer "
        "significant or reverses). A flat 'reproduces' or 'does not reproduce', or citing the RT cost "
        "only as behavioural validation, misses what this result depends on.")
