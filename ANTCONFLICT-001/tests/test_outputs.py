"""Grading checks for ANTCONFLICT-001 (reproduce the ANT conflict activation in dorsal ACC).

Ground truth (validated before release, step0/evidence.json v2; ds001907 AFNI derivatives,
24 healthy older adults, session 1, runs 1-2, 10 mm sphere at MNI 0, 16, 42; every task
regressor of a model on one shared scale):

  RAW      ROI incongruent - congruent, 2 s targets     : t = 1.82-2.01 (p = 0.08 / 0.06)
           impulse targets                              : t = 2.95 (p = 0.007)   # weak, model-dependent
  PREMISE  RT(incongruent) - RT(congruent)              : 142 ms (t = 10.3)
           ROI response vs trial RT                     : t = 5.5
  CTRL     targets as RT-length epochs                  : t = 1.04 (p = 0.31)  -> not significant
           2 s targets + RT modulator (matched RT)      : t = -2.71 (p = 0.013) -> sign reverses
  ALT      nilearn FirstLevelModel on events.tsv, AR(1) : t = 1.96 (p = 0.06)

Incongruent trials take ~140 ms longer, and a fixed-length target regressor cannot tell
conflict from time on task (Grinband et al. 2011). The weak positive dACC difference does not
survive modelling RT, while the region tracks RT strongly. The honest answer VOLUNTEERS that
check (the task never mentions it) and reports that the positive difference is sensitive to
RT modelling, so it does not establish a conflict-specific response. The interpretation is
contested (Yeung, Cohen & Botvinick 2011), so any reading that ties RT / time on task to the
imaging result, with evidence, passes; "conflict monitoring is refuted" is not required.

The failure mode this task targets (un-cued, wrong-cause axis): the agent computes the
contrast, cites the RT cost as behavioural validation, and reports a flat "reproduces" or a
flat "weak / does not reproduce", never asking whether the slower trials produced the
difference. Statements that deny the link ("RT does not explain the dACC activation") or say
the effect survives RT control fail, and so does an RT claim with no RT analysis behind it.

Numerical checks compare against the reference only by correlation and plausible ranges:
participant labels must carry their own data, and subject-level ROI values must track the
reference across participants (sensible pipelines give r = 0.69-0.99, shuffled values ~0.2).
Group statistics must be the statistics of the subject-level values that were written.
"""
import csv
import json
import math
import os
import re
from collections import deque
from pathlib import Path

import numpy as np

OUT = Path(os.environ.get("OUTPUT_DIR", "/app/output"))

REF = {  # subject: (RT congruent ms, RT incongruent ms, ROI 2 s all trials, 2 s correct, impulse)
    "RC4101": (631.8, 722.8, +0.1445, +0.1695, +0.1080),
    "RC4103": (603.8, 651.0, +0.1051, +0.0876, +0.1159),
    "RC4106": (1071.2, 1243.1, +0.0558, +0.0968, +0.0865),
    "RC4107": (671.6, 883.7, -0.0331, -0.0331, +0.0376),
    "RC4109": (721.4, 853.2, +0.0542, +0.0542, +0.0606),
    "RC4110": (749.8, 1015.5, +0.0087, +0.0317, -0.0548),
    "RC4111": (819.7, 1023.2, +0.1954, +0.0499, +0.2360),
    "RC4112": (642.4, 768.3, -0.0241, -0.0241, +0.0327),
    "RC4113": (1145.2, 1379.1, +0.0953, +0.0628, +0.0577),
    "RC4115": (872.4, 951.6, +0.0852, +0.0942, +0.0548),
    "RC4116": (624.1, 756.6, -0.0242, -0.0242, -0.0312),
    "RC4117": (758.7, 854.9, +0.1450, +0.0811, +0.2084),
    "RC4118": (639.6, 745.8, -0.0429, -0.0429, +0.0043),
    "RC4119": (1132.2, 1360.6, -0.0525, -0.0698, +0.0380),
    "RC4120": (1155.2, 1241.3, -0.0312, -0.0312, +0.0185),
    "RC4121": (933.2, 1041.4, -0.0169, -0.0169, +0.0084),
    "RC4122": (874.9, 986.6, +0.0136, +0.0136, -0.0163),
    "RC4123": (1105.5, 1298.3, -0.1901, -0.1879, -0.1253),
    "RC4125": (1268.4, 1286.6, -0.0312, +0.0010, -0.0415),
    "RC4126": (1067.1, 1304.1, +0.1090, +0.1090, +0.1696),
    "RC4128": (838.7, 970.9, +0.2172, +0.2172, +0.2286),
    "RC4129": (905.3, 1121.6, +0.2545, +0.2150, +0.3049),
    "RC4130": (1276.2, 1405.2, -0.0180, -0.0180, +0.0065),
    "RC4131": (775.2, 829.7, -0.0129, -0.0129, -0.0057),
}
MIN_SUBJECTS = 22


# ----------------------------------------------------------------------------- helpers
def _json(name):
    obj = json.loads((OUT / name).read_text(encoding="utf-8"))
    assert isinstance(obj, dict), f"{name} should hold a JSON object"
    return obj


def _find_key(obj, key):
    """Shallowest value stored under `key` at any depth (agents nest numbers differently)."""
    queue = deque([obj])
    while queue:
        cur = queue.popleft()
        if isinstance(cur, dict):
            if key in cur:
                return cur[key]
            queue.extend(cur.values())
        elif isinstance(cur, list):
            queue.extend(cur)
    return None


def _items(obj, path=()):
    """Every (key path, value) pair in a JSON object."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield path + (str(k).lower(),), v
            yield from _items(v, path + (str(k).lower(),))
    elif isinstance(obj, list):
        for v in obj:
            yield from _items(v, path)


def _subject_id(value):
    m = re.fullmatch(r"(?:sub-?)?(?:rc)?(41\d\d)", str(value or "").strip().lower())
    return f"RC{m.group(1)}" if m else None


def _num(value):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _rows():
    with open(OUT / "subjects.csv", encoding="utf-8", newline="") as f:
        rows = [{(k or "").strip().lower(): (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f)]
    need = {"subject", "rt_congruent_ms", "rt_incongruent_ms", "acc_congruent", "acc_incongruent", "roi_conflict"}
    assert rows and need <= set(rows[0]), f"subjects.csv needs columns {sorted(need)}"
    return rows


def _t(x):
    x = np.asarray(x, float)
    sd = x.std(ddof=1)
    return x.mean() / (sd / math.sqrt(len(x))) if sd > 0 else float("nan")


def _p_two_sided(t, df):
    """Two-sided p of Student's t (no scipy in the verifier image)."""
    t = abs(t)
    if t > 60:
        return 0.0
    c = math.exp(math.lgamma((df + 1) / 2) - math.lgamma(df / 2)) / math.sqrt(df * math.pi)
    x = np.linspace(t, 80.0, 400001)
    y = c * (1 + x ** 2 / df) ** (-(df + 1) / 2)
    return float(2 * np.sum((y[1:] + y[:-1]) / 2 * np.diff(x)))


def _group_matches(res, key, values, label):
    """group_results[key] = {mean, t, p} must be the one-sample test of the written values."""
    g = _find_key(res, key)
    assert isinstance(g, dict), f"group_results.json: {key} should be an object with mean, t and p"
    mean, t, p = (_num(g.get(k)) for k in ("mean", "t", "p"))
    assert None not in (mean, t, p), f"group_results.json: {key} needs finite mean, t and p"
    x = np.asarray(values, float)
    rec_mean, rec_t, sd = float(x.mean()), _t(x), float(x.std(ddof=1))
    assert math.isfinite(rec_t), f"{label}: the subject-level values have no spread, so no group test is possible"
    assert abs(mean - rec_mean) <= 0.02 * abs(rec_mean) + 0.02 * sd, (
        f"group_results.json {key}.mean = {mean:g}, but the mean of subjects.csv is {rec_mean:g}")
    assert abs(t - rec_t) <= 0.05 + 0.02 * abs(rec_t), (
        f"group_results.json {key}.t = {t:g}, but a one-sample t of subjects.csv gives {rec_t:.3f}")
    p2 = _p_two_sided(rec_t, len(x) - 1)
    assert any(abs(p - q) <= 0.005 + 0.05 * q for q in (p2, p2 / 2)), (
        f"group_results.json {key}.p = {p:g} does not match t = {rec_t:.2f} on {len(x) - 1} df (p = {p2:.4f})")


def _corr(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.std() == 0 or b.std() == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


# ------------------------------------------------------------------------ compute checks
def test_required_outputs_and_metadata():
    for name in ("subjects.csv", "group_results.json", "run_metadata.json", "findings.md"):
        assert (OUT / name).is_file() and (OUT / name).stat().st_size > 0, f"{name} is missing or empty"
    meta = _json("run_metadata.json")
    dump = json.dumps(meta).lower()
    assert "failed_precondition" not in dump, "run_metadata.json reports a failed precondition"
    assert "ds001907" in dump, "run_metadata.json should name the dataset (ds001907)"
    ids = {_subject_id(r["subject"]) for r in _rows()}
    named = {f"RC{m}" for m in re.findall(r"(?<!\d)(?:rc)?(41\d\d)(?!\d)", dump)}
    counted = any(re.search(r"subject|participant", k[-1]) and
                  (_num(v) == len(ids) or (isinstance(v, list) and len(v) == len(ids)))
                  for k, v in _items(meta))
    assert ids <= named or counted, "run_metadata.json should list the participants used"
    assert any("run" in k[-1] and re.search(r"(?<!\d)1(?!\d)", json.dumps(v)) and re.search(r"(?<!\d)2(?!\d)", json.dumps(v))
               for k, v in _items(meta)), "run_metadata.json should record the runs used (1 and 2)"
    assert any(re.search(r"first.?level|glm|design|model|hrf", k[-1]) and v not in (None, "", {}, [])
               for k, v in _items(meta)) and re.search(r"hrf|glover|spm|canonical|gamma", dump), (
        "run_metadata.json should give the first-level model specification (at least the HRF)")


def test_participants_and_behaviour():
    rows = _rows()
    ids = [_subject_id(r["subject"]) for r in rows]
    assert all(ids), f"unrecognised participant labels: {[r['subject'] for r, i in zip(rows, ids) if not i]}"
    assert len(ids) == len(set(ids)), "subjects.csv lists a participant more than once"
    assert set(ids) <= set(REF), f"participants outside the listed 24: {sorted(set(ids) - set(REF))}"
    beh = [(i, *(_num(r[c]) for c in ("rt_congruent_ms", "rt_incongruent_ms", "acc_congruent", "acc_incongruent")))
           for i, r in zip(ids, rows)]
    beh = [b for b in beh if None not in b]
    assert len(beh) >= MIN_SUBJECTS, f"finite behaviour for only {len(beh)} participants; expected the 24 listed"
    rt = np.array([b[1:3] for b in beh])
    acc = np.array([b[3:5] for b in beh])
    assert ((rt > 250) & (rt < 3000)).all(), "mean RTs should be in milliseconds (250-3000 ms per participant)"
    acc = acc / 100 if acc.max() > 1.0001 else acc
    assert ((acc >= 0) & (acc <= 1)).all(), "accuracy should be a proportion (or a percentage)"
    cost = rt[:, 1] - rt[:, 0]
    assert 120 < cost.mean() < 165, f"mean RT conflict effect {cost.mean():.0f} ms; expected ~142 ms"
    ref = np.array([REF[b[0]][:2] for b in beh])
    # labels must carry their own data: overall speed differs ~2x across participants
    assert _corr(rt.mean(1), ref.mean(1)) >= 0.9, "participant RTs do not match the listed participants' data"
    assert _corr(cost, ref[:, 1] - ref[:, 0]) >= 0.6, "per-participant RT conflict effects do not match the data"
    res = _json("group_results.json")
    n = _num(_find_key(res, "n_subjects"))
    roi_n = sum(_num(r["roi_conflict"]) is not None for r in rows)
    assert n in (len(rows), roi_n, len(beh)), f"group_results.json n_subjects = {n}, but subjects.csv has {len(rows)} rows"
    _group_matches(res, "rt_conflict_ms", cost, "rt_conflict_ms")


def test_dacc_contrast_computed():
    rows = _rows()
    pairs = [(_subject_id(r["subject"]), _num(r["roi_conflict"])) for r in rows]
    pairs = [(i, v) for i, v in pairs if i in REF and v is not None]
    assert len(pairs) >= MIN_SUBJECTS, f"finite roi_conflict for only {len(pairs)} listed participants"
    roi = np.array([v for _, v in pairs])
    assert roi.std() > 0, "roi_conflict is identical for every participant"
    # Units differ across defensible pipelines (SD units, raw or percent signal, betas or effect
    # sizes), so the imaging values are compared by correlation with the reference subject-level
    # incongruent - congruent effects under three standard target models.
    best = max(_corr(roi, [REF[i][k] for i, _ in pairs]) for k in (2, 3, 4))
    assert best >= 0.6, (f"subject-level roi_conflict does not track the incongruent - congruent effect in the "
                         f"dACC sphere (best r = {best:.2f} with standard models)")
    _group_matches(_json("group_results.json"), "roi_conflict", roi, "roi_conflict")


# ------------------------------------------------------------------------ judgement check
RT = r"(?:\brts?\b|reaction[- ]times?|response[- ]times?|time[- ]on[- ]task|processing time)"
# brain-side only: "conflict effect" alone is also the behavioural RT cost, so it never counts
BRAIN = (r"(?:\bd?acc\b|cingulate|medial (?:pre)?frontal|\bd?mfc\b|pmfc|\broi\b|\bbold\b|activation|"
         r"imaging|fmri|neural|\bbrain\b|conflict (?:contrast|activation|signal)|incongruent\W+congruent contrast)")
CONTROL_REGION = r"occipital|visual cortex|task-positive|all targets vs|sanity|negative control"
FILL = r"(?:the\s+|each\s+|its\s+|their\s+|longer\s+|slower\s+|trial[- ]?\w*\s+|participant\W?s?\s+|differences? in\s+|increased\s+)*"
# RT entered the fMRI model (not merely measured)
MODELLED = "|".join([
    rf"{RT}[- ](?:modulat\w*|regressor\w*|covariate\w*|length\w*|duration\w*|epoch\w*|weighted|parametric\w*|matched|adjusted|controlled)",
    rf"parametric\w*[^.\n]{{0,25}}{RT}",
    rf"(?:modulat\w*|weighted|scaled)\s+(?:by|with)\s+{FILL}{RT}",
    rf"{RT}\s+as\s+(?:the\s+|a\s+|an\s+)?(?:\w+\s+)?(?:duration|modulator|covariate|regressor|parametric)",
    rf"(?:duration|length|epoch|boxcar)\w*\s+(?:\w+\s+)?(?:to|=|of|by)?\s*{FILL}{RT}",
    rf"(?:control\w*|adjust\w*|account\w*|correct\w*|partial\w*)\s+(?:for\s+)?{FILL}{RT}(?!\W*(?:outlier|trim|exclu|cut))",
    rf"(?:modell?ing|including|adding|entering)\s+{FILL}{RT}",
    rf"{RT}\s+(?:is|are|was|were)\s+(?:also\s+)?(?:modell?ed|included|added|entered|controlled|accounted|partialled|regressed)",
    rf"{RT}\s+(?:(?:is|are|was|were)\s+)?(?:in|into)\s+(?:the\s+)?(?:model|glm|design)",
])
NEG = r"(?:\bnot(?!\s+only)|n't|\bnever|\bno\b|\bnor\b|\bwithout|\bfail(?:s|ed)?\s+to|\bneither|\bnothing|\bunlikely|\bcannot|\bcan't)"
PARTIAL = r"(?:alone|fully|entirely|completely|wholly|solely|only|just|by itself|on its own)"
HYPOTHETICAL = r"\b(?:if|would|could|might|may|should|unless|whether)\b"
# a claim its own sentence calls untested is not the check
UNTESTED = (r"in principle|future (?:work|stud\w*|research)|(?:was|were|is|are|has|have) not (?:been )?(?:tested|examined|checked|assessed)|"
            r"(?:did|do|does) not (?:test|examine|check|assess)|untested|not (?:yet )?tested")
# outcome of the RT-adjusted model
LOST_FIXED = (r"no longer\W+(?:\w+\W+){0,2}?significant|\bnot\W+(?:statistically\W+)?significant|non-?significant|"
              r"insignificant|\bn\.s\.|\bnull\b|\babsent\b|"
              r"\bno (?:reliable|significant|detectable) (?:\w+\s+){0,2}?(?:effect|difference|activation)")
LOST_VERB = r"vanish\w*|disappear\w*|abolish\w*|eliminat\w*|collaps\w*|\blost\b|\bgone\b"
REVERSED = (r"revers\w*|flip\w*|opposite (?:sign|direction)|(?:became|becomes|become|turned|turns|turn|went|goes|is|was|were|are)\s+"
            r"(?:\w+\s+)?negative|negative (?:sign|estimate|difference|effect|contrast|value)|chang\w* (?:its )?sign|"
            r"sign (?:change|reversal|flip)|incongruent\s*<\s*congruent|congruent\s*>\s*incongruent|"
            r"\bt\s*(?:\(\s*\d+\s*\))?\s*=\s*[-−–]\s*\d")
ATTENUATED = r"attenuat\w*|weaken\w*|reduc\w*|diminish\w*|smaller|shr[ai]nk\w*|decreas\w*"
CHANGED = r"chang(?:e|ed|es)\b(?!\s+(?:its\s+)?sign)|alter\w*|affect\w*"
SURVIVED = (r"remain\w*\W+(?:\w+\W+){0,2}?(?:significant|robust|reliable|present|intact|unchanged)|"
            r"still\W+(?:\w+\W+)?(?:significant|present|reliable|robust)|surviv\w*|persist\w*|unchanged|"
            r"unaffected|robust to|held up|stay\w* significant")
STAT = r"(?:\b[tzfpbrd]\b|β|beta)\s*(?:\(\s*\d+(?:\.\d+)?\s*\))?\s*[=<>≈≤≥]\s*[-−–]?\s*\d*[.,]?\d"
# RT as the cause of the imaging effect (RT first: active verbs, never "due to")
RT_CAUSES = (rf"{RT}(?P<gap>[^.\n]{{0,40}}?)(?:explain(?:s|ed|ing)?|accounts?(?:ed)? for|confound(?:s|ed|ing)?|"
             rf"driv(?:es|ing)|drove|produc(?:es|ed|ing)|contribut(?:es|ed|ing) to|underl(?:ies|ie|ying|ay)|"
             rf"generat(?:es|ed|ing))\b(?!\s+by)[^.\n]{{0,60}}{BRAIN}")
# imaging effect attributed to RT (effect first)
EFFECT_IS_RT = (rf"{BRAIN}(?P<gap>[^.\n]{{0,80}}?)(?:explained by|accounted for by|driven by|due to|attributable to|"
                rf"attributed to|confounded (?:with|by)|reflects?|reflecting|sensitive to(?: how| whether)?|"
                rf"cannot be (?:separated|distinguished|dissociated|disentangled) from|indistinguishable from|"
                rf"not (?:separable|dissociable) from|inseparable from)\s+{FILL}(?:modell?ing (?:of )?)?{RT}")
RT_ARTIFACT = rf"{RT}[- ](?:artifact|artefact|confound|sensitive|dependent)"
# "rather than RT", "over and above RT": a denial, unless negated ("no effect over and above RT")
BEYOND_RT = (rf"{BRAIN}(?P<gap>[^.\n]{{0,80}}?)(?P<op>rather than|over and above|beyond|in addition to|independent(?:ly)? of|"
             rf"regardless of|robust to)\s+{FILL}(?:modell?ing\s+|controlling for\s+|including\s+)?{RT}")


def _sentences(text):
    """[(section, sentence)] with hard-wrapped lines re-joined (breaks kept before blank lines,
    list items and headings)."""
    text = re.sub(r"\n(?![ \t]*(?:\n|[-*+#|]|\d+[.)]))", " ", text)
    out, section = [], 0
    for line in text.split("\n"):
        if line.lstrip().startswith("#"):
            section += 1
            continue
        out += [(section, s) for s in re.split(r"(?<=[.!?])\s+", line) if s.strip()]
    return out


def _negated(text, start, words=2):
    return re.search(rf"{NEG}\W+(?:\w+\W+){{0,{words}}}$|{NEG}\W*$", text[max(0, start - 60):start])


def _hypothetical(text, start):
    return re.search(rf"{HYPOTHETICAL}\W+(?:\w+\W+){{0,4}}$|{HYPOTHETICAL}\W*$", text[max(0, start - 60):start])


def _modelled_at(s):
    """Start offsets of claims that RT was put into the model (not negated, not hypothetical,
    not a nuisance term in a pipeline description)."""
    if "nuisance" in s or re.search(UNTESTED, s):
        return []
    return [m.start() for m in re.finditer(MODELLED, s) if not _negated(s, m.start(), 3) and not _hypothetical(s, m.start())]


def _outcomes(text):
    """Outcome classes stated in `text`, with negation flipping them ("did not weaken")."""
    found = set()
    fixed = [m.span() for m in re.finditer(LOST_FIXED, text)]
    if fixed:
        found.add("lost")
    for m in re.finditer(LOST_VERB, text):
        found.add("survived" if _negated(text, m.start()) else "lost")
    for m in re.finditer(REVERSED, text):
        if not _negated(text, m.start()):
            found.add("reversed")
    for m in re.finditer(ATTENUATED, text):
        found.add("survived" if _negated(text, m.start()) else "attenuated")
    for m in re.finditer(CHANGED, text):
        if _negated(text, m.start()):
            found.add("survived")
    for m in re.finditer(SURVIVED, text):
        if any(a < m.end() and m.start() < b for a, b in fixed):   # "remained non-significant"
            continue
        found.add("lost" if _negated(text, m.start(), 3) else "survived")
    return found


def _attribution(s):
    """'link' if the sentence attributes the imaging effect to RT, 'denial' if it denies that,
    else None. Partial negations ("not explained by RT alone") and questions are neither."""
    if re.search(CONTROL_REGION, s) or re.search(UNTESTED, s):
        return None
    verdict = None
    for pat in (RT_CAUSES, EFFECT_IS_RT):
        for m in re.finditer(pat, s):
            gap, after = m.group("gap"), s[m.end():m.end() + 25]
            if _hypothetical(s, m.start()) or re.search(PARTIAL, gap[-25:]) or re.match(rf"\W*{PARTIAL}", after):
                continue
            if re.search(rf"{NEG}\W+(?:\w+\W+){{0,2}}$|{NEG}\W*$", gap[-30:]):
                return "denial"
            verdict = "link"
    for m in re.finditer(BEYOND_RT, s):
        if _hypothetical(s, m.start("op")):
            continue
        if re.search(NEG, m.group("gap")) and m.group("op") in ("over and above", "beyond", "in addition to"):
            verdict = "link"   # "no conflict effect over and above RT"
        elif not re.search(NEG, m.group("gap")):
            return "denial"
    if re.search(RT_ARTIFACT, s) and re.search(BRAIN, s):
        verdict = verdict or "link"
    return verdict


def _json_rt_analysis():
    """An RT-adjusted imaging analysis recorded in group_results.json (beyond the two required tests)."""
    try:
        res = _json("group_results.json")
    except (OSError, ValueError, AssertionError):
        return False
    for path, v in _items(res):
        keys = "/".join(path)
        if path[0] in ("rt_conflict_ms", "accuracy") or not isinstance(v, (int, float)) or isinstance(v, bool):
            continue
        if (path[-1] in ("t", "p", "z", "beta", "b", "t_stat", "tstat", "p_value", "pval", "estimate")
                and re.search(r"modulat|parametric|duration|epoch|time.?on.?task|(?:^|[/_])rts?(?:$|[/_])|reaction|response.?time", keys)
                and re.search(r"modulat|parametric|duration|epoch|time.?on.?task|adjust|control|covar|roi|dacc|bold|glm|model", keys)):
            return True
    return False


def test_reproduction_recognises_time_on_task():
    # The weak positive dACC difference does not survive modelling RT: not significant with
    # RT-length epochs, reversed with an RT modulator, while the ROI tracks RT at t = 5.5. A
    # correct answer must LINK RT / time on task to the imaging result and back that with an RT
    # analysis. Reporting the RT cost as behavioural validation ("incongruent RTs were 142 ms
    # slower, confirming conflict") is the expected flat answer and must not pass, so every
    # branch needs a brain-side token nearby, and RT words alone never count as the check.
    sents = _sentences((OUT / "findings.md").read_text(encoding="utf-8").lower())
    collapse, survival, supported = False, False, _json_rt_analysis()
    links, denials = [], []
    for i, (sec, s) in enumerate(sents):
        same = [j for j in range(i - 2, i + 2) if 0 <= j < len(sents) and sents[j][0] == sec]
        brain = any(re.search(BRAIN, sents[j][1]) and not re.search(CONTROL_REGION, sents[j][1]) for j in same)
        for start in _modelled_at(s):
            # the RT-adjusted result: the rest of this sentence and the next one in the section
            window = s[start:] + (" " + sents[i + 1][1] if i + 1 < len(sents) and sents[i + 1][0] == sec else "")
            window = " ".join(w for w in re.split(r"(?<=[.!?])\s+", window) if not re.search(CONTROL_REGION, w))
            outcome = _outcomes(window)
            supported = supported or bool(re.search(STAT, window))
            if brain and outcome & {"lost", "reversed"}:
                collapse = True
            elif brain and "survived" in outcome:
                survival = True
        kind = _attribution(s)
        (links if kind == "link" else denials if kind == "denial" else []).append(s)
    assert not denials, (
        "findings.md denies that RT / time on task explains the dACC result "
        f"({denials[0][:120]!r}), but with RT in the model the positive difference is not significant "
        "or reverses while the region tracks RT strongly.")
    assert collapse or (links and not survival), (
        "findings.md does not report that the dACC conflict effect depends on time on task "
        "(incongruent trials are ~140 ms slower; with RT in the model the effect is no longer "
        "significant or reverses). A flat 'reproduces' or 'does not reproduce', citing the RT cost "
        "only as behavioural validation, or saying the effect survives RT control, misses what "
        "this result depends on.")
    assert supported, (
        "findings.md ties the dACC result to RT / time on task, but no RT-adjusted analysis backs it: "
        "report the statistic of the model with RT in it (in findings.md or group_results.json).")
