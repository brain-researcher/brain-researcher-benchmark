"""Source-free support and launch-isolation controls. No Docker/source run."""
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import time

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"solution"))
import core
import launch_support_pilot as launcher
from pilot_support import allowed_rows, authenticate_capsule, no_bandpass_activity
from launch_support_pilot import docker_args, verify_reviewed_files


def contract():
    return json.loads(Path(__file__).with_name("pilot_contract.json").read_text())


def test_frozen_pins_match_actual_public_files():
    c, task = contract(), Path(__file__).resolve().parents[1]
    verify_reviewed_files(task, c)
    for key, name in (("method_sha256", "method_contract.json"), ("schema_sha256", "output_schema.json"),
                      ("source_manifest_sha256", "source_manifest.json")):
        assert hashlib.sha256((task/"environment"/name).read_bytes()).hexdigest() == c[key]
    for name, digest in c["legacy_code_sha256"].items():
        assert hashlib.sha256((task/"solution"/name).read_bytes()).hexdigest() == digest
    assert hashlib.sha256(Path(__file__).with_name("protocol.py").read_bytes()).hexdigest() == c["protocol_sha256"]


def test_no_bandpass_support_matches_inherited_branch_but_calls_no_fc(monkeypatch):
    rng = np.random.default_rng(2)
    raw = rng.normal(size=(168, 400))
    raw[:, 8] = 6
    confounds = rng.normal(size=(168, 15))
    geometry = np.ones(400, dtype=bool)
    expected = core.preprocess(raw, confounds, geometry)
    monkeypatch.setattr(core, "canonical_fc", lambda *_: (_ for _ in ()).throw(AssertionError("FC forbidden")))
    rows, active, rank = no_bandpass_activity(raw, confounds, geometry)
    assert np.array_equal(active, expected["person_parcel_active"][0])
    assert rank == expected["nuisance_rank"]
    assert not rows[8]["active"]
    assert np.allclose([r["residual_centered_l2"] for r in rows], expected["clean_centered_l2"][0])


def test_missing_geometry_and_nonfinite_source_handled_explicitly():
    raw = np.zeros((168, 400))
    geometry = np.ones(400, dtype=bool)
    geometry[0] = False
    raw[:, 0] = np.nan
    rows, active, _ = no_bandpass_activity(raw, np.zeros((168, 15)), geometry)
    assert not active.any() and rows[0]["geometry"] is False
    assert rows[0]["raw_sample_sd"] is None
    raw[0, 1] = np.nan
    with pytest.raises(ValueError, match="finite"):
        no_bandpass_activity(raw, np.zeros((168, 15)), geometry)


def test_partition_allowlist_contains_common_and_only_own_people():
    manifest = {"files": [{"participant_id": None, "path": "atlas"},
                          {"participant_id": "train", "path": "train_bold"},
                          {"participant_id": "test", "path": "test_bold"}]}
    assert [r["path"] for r in allowed_rows(manifest, ["train"])] == ["atlas", "train_bold"]


def test_source_capsule_rejects_opposite_file_before_parsing(tmp_path):
    (tmp_path/"source_manifest.json").write_text("{}")
    (tmp_path/"unexpected_test_bold").write_bytes(b"forbidden")
    with pytest.raises(ValueError, match="allowlist"):
        authenticate_capsule(tmp_path, {"files": []}, ["train"])


@pytest.mark.parametrize("stage", ["fit", "evaluate"])
def test_stage_launch_covers_baked_sources_and_limits_mounts(stage):
    command = docker_args(stage, Path("/task"), Path("/evidence"), contract(), "test-name", 1000, 1000, "a"*64)
    text = " ".join(command)
    assert "/app:rw,noexec,nosuid,size=1048576" in command
    assert "/opt/source_capture:rw,noexec,nosuid,size=1048576" in command
    assert f"src=/evidence/capsules/{stage},dst=/source,readonly" in text
    assert "--cap-drop ALL" in text and "--network none" in text
    assert "--read-only" in command and "--user 1000:1000" in text
    assert "src=/evidence,dst=/out" not in text
    assert "docker.sock" not in text and "--privileged" not in text
    if stage == "fit":
        assert "dst=/frozen" not in text and "capsules/evaluate" not in text
    else:
        assert "src=/evidence/fit,dst=/frozen,readonly" in text
        assert "capsules/fit" not in text


def test_root_stage_is_rejected():
    with pytest.raises(ValueError, match="nonroot"):
        docker_args("fit", Path("/task"), Path("/evidence"), contract(), "test", 0, 0)


def test_daemon_cleanup_timeout_does_not_hide_original_limit_or_receipt(tmp_path, monkeypatch):
    class Client:
        returncode = None
        terminated = False

        def poll(self):
            return self.returncode

        def terminate(self):
            self.terminated = True
            self.returncode = -15

        def wait(self, timeout):
            return self.returncode

    client = Client()
    monkeypatch.setattr(launcher.subprocess, "Popen", lambda *a, **kw: client)
    def stalled(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])
    monkeypatch.setattr(launcher.subprocess, "run", stalled)
    with pytest.raises(TimeoutError, match="global"):
        launcher.run_stage("fit", ["docker", "run", "--name", "owned-exact"],
                           tmp_path, time.monotonic()-1, 1024**2)
    receipt = json.loads((tmp_path/"fit.launch.json").read_text())
    assert client.terminated and receipt["returncode"] == -15
    assert receipt["cleanup_errors"] == ["exact-container-stop: TimeoutExpired"]
