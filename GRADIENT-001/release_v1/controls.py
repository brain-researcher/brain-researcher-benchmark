"""Generate source-backed adversarial submissions; root runs them separately.

Fixtures deliberately contain author-known reference values. They never enter
the model image or oracle bundle, and are not an empirical difficulty test.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np
from grading import evaluation_reference, require, strict_json


def script_for(answer, probe=False, surviving_fork=False):
    prelude = '''import argparse, json, os
from pathlib import Path
p=argparse.ArgumentParser()
for n in ('data','fit','output','contract'): p.add_argument('--'+n, required=True)
a=p.parse_args()
'''
    if probe:
        prelude += '''probes={}
assert os.getuid()==61616 and os.geteuid()==61616
assert os.getgroups()==[]
probes['unprivileged_identity']=True
for name in ['/private', '/tests', '/proc/self/root', '/proc', '/dev', '/var/run/docker.sock', '/logs/verifier']:
    assert not Path(name).exists(), name
    probes['absent:'+name]=True
contract=json.loads(Path(a.contract).read_text())
manifest=json.loads((Path(a.data)/'source_manifest.json').read_text())
for row in manifest['files']:
    if row.get('participant_id') in contract['discovery_ids']:
        assert not (Path(a.data)/row['path']).exists()
        probes['opposite_denied:'+row['path']]=True
for name in [a.fit, a.contract, '/usr/bin/python3']:
    try:
        with open(name, 'wb'): pass
    except PermissionError: probes['write_denied:'+name]=True
    else: raise AssertionError('immutable path writable: '+name)
for fd in range(3,64):
    try: os.fstat(fd)
    except OSError: pass
    else: raise AssertionError('extra inherited descriptor:'+str(fd))
probes['extra_inherited_fds_absent']=True
import ctypes
assert ctypes.CDLL(None).prctl(39,0,0,0,0)==1
probes['no_new_privs']=True
'''
    if surviving_fork:
        prelude += '''import time
child=os.fork()
if child==0:
    os.setsid()
    time.sleep(120)
    os._exit(0)
os.kill(child,0)
'''
    tail = "answer=json.loads("+repr(json.dumps(answer, allow_nan=False))+")\n"
    if probe:
        tail += "answer['isolation_probes']=probes\n"
    if surviving_fork:
        tail += "answer['surviving_child_created']=child\n"
    return prelude+tail+"Path(a.output).write_text(json.dumps(answer,allow_nan=False))\n"


def generate(task, destination):
    require(not destination.exists(), "new controls destination required")
    private = task/"tests/private"
    fit = strict_json((private/"discovery.json").read_bytes())
    evaluation = strict_json((private/"evaluation.json").read_bytes())
    with np.load(private/"operators.npz", allow_pickle=False) as archive:
        arrays = {k: archive[k] for k in archive.files}
    destination.mkdir(parents=True)
    records = []
    def save(name, expected, f, answer=None, program=None, probe=False, surviving_fork=False):
        folder = destination/name
        folder.mkdir()
        (folder/"discovery.json").write_text(json.dumps(f, allow_nan=False))
        raw = program if program is not None else script_for(answer, probe, surviving_fork).encode()
        (folder/"evaluate.py").write_bytes(raw)
        records.append({"case": name, "expected_reward": float(expected),
            "discovery_sha256": hashlib.sha256((folder/"discovery.json").read_bytes()).hexdigest(),
            "program_sha256": hashlib.sha256(raw).hexdigest()})
    independent = (task/"solution/oracle_independent.pyz").read_bytes()
    save("independent_numerical_evaluator", 1, fit, program=independent)
    sign = copy.deepcopy(fit)
    sign["axis"] = (-np.array(sign["axis"])).tolist()
    save("sign_equivalent_independent", 1, sign, program=independent)
    rounded = copy.deepcopy(fit)
    rounded["axis"] = (np.array(rounded["axis"])*(1+4e-8)).tolist()
    save("certified_norm_roundoff", 1, rounded, program=independent)
    answer = evaluation_reference(evaluation, fit, arrays)
    save("sandbox_denied_reads_and_writes", 1, fit, answer, probe=True)
    save("sandbox_orphaned_setsid_child_reaped", 1, fit, answer, surviving_fork=True)
    save("empty", 0, {}, answer)
    naive = copy.deepcopy(fit)
    naive["axis"] = [1.] + [0.]*(len(fit["axis"])-1)
    save("naive_axis", 0, naive, answer)
    support = copy.deepcopy(fit)
    null_row = next(row for row in evaluation["people"].values() if row["source_status"] == "source_inactive")
    excluded = set(null_row["inactive_on_frozen_support"])
    support["support"] = [p for p in support["support"] if p not in excluded]
    support["axis"] = [v for p, v in zip(fit["support"], fit["axis"]) if p not in excluded]
    save("heldout_informed_support", 0, support, answer)
    fabricated = copy.deepcopy(answer)
    for row in fabricated["people"].values():
        if row["transfer"]["status"] == "defined":
            row["transfer"]["fraction"] = .99
    save("fabricated_high_transfer", 0, fit, fabricated)
    optimal = copy.deepcopy(answer)
    for row in optimal["people"].values():
        t = row["transfer"]
        if t["status"] == "defined":
            t["fraction"] = 1.
            t["rayleigh"] = t["leading_eigenvalue"]
            t["rayleigh_minus_spectral_mean"] = t["rayleigh"]-t["nontrivial_spectral_mean"]
    save("heldout_optimal_axis_substitution", 0, fit, optimal)
    allnull = copy.deepcopy(answer)
    for row in allnull["people"].values():
        row["transfer"] = {"status": "source_inactive", "fraction": None}
    save("blanket_unjustified_null", 0, fit, allnull)
    missing = copy.deepcopy(answer)
    del missing["people"][next(iter(missing["people"]))]
    save("missing_person", 0, fit, missing)
    wrong = copy.deepcopy(fit)
    wrong["configuration"] = "same_side" if fit["configuration"] != "same_side" else "between"
    save("incorrect_network_interpretation", 0, wrong, answer)
    (destination/"cases.json").write_text(json.dumps({"cases": records,
        "scope": "source-backed grader fixtures; not model calibration or hardness evidence"}, indent=2)+"\n")
    print(json.dumps({"controls": len(records), "destination": str(destination)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    a = parser.parse_args()
    generate(a.task, a.destination)
