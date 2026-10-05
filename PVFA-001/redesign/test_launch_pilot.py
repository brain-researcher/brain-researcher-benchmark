"""Host launcher checks with no Docker/process/source-data execution."""
import json
from pathlib import Path
import subprocess
import time

import pytest

import launch_pilot as launch


@pytest.fixture
def contract():
    return json.loads(Path(__file__).with_name("pilot_contract.json").read_text())


def test_docker_envelope_and_readonly_inputs(contract,tmp_path):
    name,argv = launch.build_create(tmp_path/"task",tmp_path/"evidence",tmp_path/"approval.json",contract,"owned",1000,1000)
    assert name == "br-pr156-pilot-owned"
    for flag,value in [("--network","none"),("--runtime","runc"),("--memory","2147483648"),("--memory-swap","2147483648"),("--cpus","1"),("--user","1000:1000")]:
        assert argv[argv.index(flag)+1] == value
    assert "--gpus" not in argv
    mounts = [argv[i+1] for i,x in enumerate(argv) if x == "--mount"]
    assert len(mounts) == 8
    assert sum(x.endswith(",readonly") for x in mounts) == 7
    assert [x for x in mounts if not x.endswith(",readonly")][0].endswith("dst=/out")
    assert "--raw-source" in argv and "/app/data/sherbrooke" in argv


def test_root_runtime_forbidden(contract,tmp_path):
    with pytest.raises(ValueError,match="nonroot"):
        launch.build_create(tmp_path,tmp_path,tmp_path,contract,"t",0,0)


def test_approval_binds_launcher_and_contract(tmp_path):
    contract = tmp_path/"contract.json"; contract.write_text("{}")
    for name in launch.CODE_FILES: (tmp_path/name).write_text(name)
    approval = {"approved":True,"reviewer":"root","contract_sha256":launch.sha(contract),"code_sha256":launch.code_hashes(tmp_path)}
    launch.verify_approval(approval,contract,tmp_path)
    (tmp_path/"launch_pilot.py").write_text("changed")
    with pytest.raises(ValueError,match="code hashes"):
        launch.verify_approval(approval,contract,tmp_path)


def test_global_timeout_cannot_start_subprocess(monkeypatch):
    def forbidden(*args,**kwargs): raise AssertionError("must not start process")
    monkeypatch.setattr(subprocess,"run",forbidden)
    with pytest.raises(TimeoutError):
        launch.bounded(["docker","inspect","x"],time.monotonic()-1)


def test_cleanup_refuses_foreign_container(monkeypatch):
    calls = []
    def fake(argv,**kwargs):
        calls.append((argv,kwargs))
        return subprocess.CompletedProcess(argv,0,json.dumps([{"Id":"foreign-id","Config":{"Labels":{launch.OWNER_LABEL:"foreign"}}}]),"")
    monkeypatch.setattr(subprocess,"run",fake)
    result = launch.cleanup_owned("name","mine")
    assert result[0]["action"] == "refused"
    assert len(calls) == 1 and calls[0][1]["timeout"] == 3


def test_cleanup_only_removes_resolved_owned_id(monkeypatch):
    calls = []
    def fake(argv,**kwargs):
        calls.append((argv,kwargs))
        data = json.dumps([{"Id":"exact-owned-id","Config":{"Labels":{launch.OWNER_LABEL:"mine"}}}]) if argv[1] == "inspect" else ""
        return subprocess.CompletedProcess(argv,0,data,"")
    monkeypatch.setattr(subprocess,"run",fake)
    result = launch.cleanup_owned("name","mine")
    assert calls[1][0] == ["docker","rm","--force","exact-owned-id"]
    assert calls[1][1]["timeout"] == 5
    assert result[0]["id"] == "exact-owned-id"


def test_cleanup_timeout_is_evidence_not_unbounded_wait(monkeypatch):
    def fake(argv,**kwargs): raise subprocess.TimeoutExpired(argv,kwargs["timeout"])
    monkeypatch.setattr(subprocess,"run",fake)
    result = launch.cleanup_owned("name","mine")
    assert result[0]["action"] == "cleanup_failed"
