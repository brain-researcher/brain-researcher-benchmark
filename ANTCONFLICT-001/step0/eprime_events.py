"""Rebuild BIDS-style ANT events (with trial-level RT and accuracy) from the ds001907 E-Prime export.

OpenNeuro ds001907 ships trial-level RT/accuracy in derivatives/*_events.tsv for only six
healthy subjects (RC4101/03/06/07/09/10). Everyone else's behaviour is in
derivatives/ANT-eprime-export.zip (E-Prime 2 text exports, UTF-16). Mapping, validated
against all 12 derivative events files that exist for ses-1 runs 1-2 (see validate()):

  * ANT_fMRI_Session1-<NNN>-1.txt is sub-RC4<NNN> ses-1.
  * Each scanned block is a Run<L>Proc frame; BIDS run-N is block letter "ABCDEF"[N-1]
    (NOT presentation order). Its TrigTest.RTTime is the scanner trigger (t = 0).
  * A block logs 38 TrialProc frames; the first two are lead-in trials absent from
    events.tsv. Cue = SlideWarning (0.2 s), target = SlideTarget (2 s).
  * RT/accuracy are the script-level ReactionTime/Accuracy fields, which count a late
    response made during the following ITI (SlideTarget.RT is 0 for those).
  * The raw BIDS events (sub-*/ses-1/func/*_events.tsv: onset, duration, trial_type) are the
    same events with every error trial relabelled: target -> TargetErr, its cue -> CueErr.

    python step0/eprime_events.py <eprime_dir> <ds001907_dir>    # validate against derivatives
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def _frames(path):
    text = Path(path).read_text(encoding="utf-16")
    head, _, body = text.partition("*** Header End ***")
    hdr = dict(re.findall(r"^\s*([\w.]+): (.*)$", head, re.M))
    return hdr, [dict(re.findall(r"^\s*([\w.\[\]]+): (.*)$", fr, re.M))
                 for fr in body.split("*** LogFrame Start ***")[1:]]


def session_events(path):
    """{run_number: events DataFrame} for one E-Prime session file."""
    hdr, frames = _frames(path)
    out = {}
    for kv in frames:
        m = re.fullmatch(r"Run([A-F])Proc", kv.get("Procedure", ""))
        if not m:
            continue
        trig = float(kv["TrigTest.RTTime"])
        trials = [f for f in frames if f.get("Running") == f"Run{m.group(1)}TrialList"][2:]
        rows = []
        for tr in trials:
            rows.append({"onset": (float(tr["SlideWarning.OnsetTime"]) - trig) / 1000, "duration": 0.2,
                         "trial_type": tr["CueType"]})
            rows.append({"onset": (float(tr["SlideTarget.OnsetTime"]) - trig) / 1000, "duration": 2.0,
                         "trial_type": tr["FlankerType"], "cue": tr["CueType"],
                         "response_time": float(tr["ReactionTime"]), "accuracy": int(tr["Accuracy"])})
        out["ABCDEF".index(m.group(1)) + 1] = pd.DataFrame(rows).sort_values("onset", ignore_index=True)
    return out


def subject_events(eprime_dir, sub, session=1):
    f = Path(eprime_dir) / f"ANT_fMRI_Session{session}-{sub.removeprefix('RC4')}-{session}.txt"
    return session_events(f)


def validate(eprime_dir, ds_dir):
    n = 0
    for evf in sorted(Path(ds_dir).glob("derivatives/sub-*/ses-1/func/sub-*_ses-1_run-*_events.tsv")):
        sub, run = re.search(r"sub-(\w+?)_ses-1_run-(\d)", evf.name).groups()
        b = pd.read_csv(evf, sep="\t")
        e = subject_events(eprime_dir, sub)[int(run)]
        assert len(b) == len(e) and (b.trial_type.values == e.trial_type.values).all(), evf.name
        assert np.abs(b.onset.values - e.onset.values).max() < 0.01, evf.name
        tb, te = b[b.duration == 2], e[e.duration == 2]
        assert np.allclose(pd.to_numeric(tb.response_time).values, te.response_time.values), evf.name
        assert np.allclose(pd.to_numeric(tb.accuracy).values, te.accuracy.values), evf.name
        n += 1
    print(f"E-Prime events match derivative events.tsv exactly for {n} runs")
    m, unlabelled = 0, []
    for evf in sorted(Path(ds_dir).glob("sub-*/ses-1/func/sub-*_ses-1_task-ANT_run-*_events.tsv")):
        sub, run = re.search(r"sub-(\w+?)_ses-1_task-ANT_run-(\d)", evf.name).groups()
        if not (Path(eprime_dir) / f"ANT_fMRI_Session1-{sub.removeprefix('RC4')}-1.txt").is_file():
            continue
        b, e = pd.read_csv(evf, sep="\t"), subject_events(eprime_dir, sub)[int(run)]
        err_t = (e.duration == 2) & (e.accuracy == 0)
        expect = e.trial_type.where(~err_t, "TargetErr").where(~err_t.shift(-1, fill_value=False), "CueErr")
        assert len(b) == len(e), evf.name
        assert np.abs(b.onset.values - e.onset.values).max() < 0.01, evf.name
        # The only tolerated difference: an E-Prime error (Accuracy 0, which the derivative events
        # agree with) that the raw file leaves under its condition label. Seen in RC4110 runs 5-6.
        off = b.trial_type.values != expect.values
        assert (b.trial_type.values[off] == e.trial_type.values[off]).all(), evf.name
        if off.any():
            unlabelled.append(f"{evf.name}: {int((off & err_t.values).sum())} error targets")
        m += 1
    print(f"E-Prime events match raw BIDS events.tsv (errors relabelled) for {m} runs")
    for u in unlabelled:
        print(f"  raw events.tsv leaves E-Prime errors unrelabelled in {u}")
    return n + m


if __name__ == "__main__":
    validate(sys.argv[1], sys.argv[2])
