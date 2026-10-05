"""Source-free schema/security/numerical controls. Not empirical task difficulty."""
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import zipfile
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent))
from grading import (authenticate_capsule, compare, evaluation_reference, regular_bytes,
                     strict_json, validate_discovery)
from format import expand_fit, interpretation
from prepare_release import oracle_zip


@pytest.fixture
def certified():
    s = np.ones(3)/np.sqrt(3)
    u = np.array([1., -1., 0.])/np.sqrt(2)
    v = np.cross(s, u)
    k = np.outer(s, s)+.5*np.outer(u, u)+.2*np.outer(v, v)
    arrays = {"discovery:operator": k, "discovery:stationary": s,
              "discovery:eigenvalues": np.array([.5, .2]),
              "held:operator": k, "held:stationary": s, "held:eigenvalues": np.array([.5, .2])}
    fit = dict(support=[1, 2, 3], axis_status="defined", axis=u.tolist(),
               spectrum={"leading_eigenvalue": .5, "principal_gap": .3}, people={"train": {"rank": 2}},
               network_C={"status": "defined", "lower": -2., "upper": -2., "rank": 1},
               configuration="between", leave_one_out={"train": {"status": "defined", "overlap": 1.}})
    evaluation = {"people": {"held": {"source_status": "defined", "transfer": {}}}}
    return fit, evaluation, arrays


def test_either_axis_sign_and_extra_metadata(certified):
    fit, _, arrays = certified
    candidate = copy.deepcopy(fit)
    candidate["axis"] = (-np.array(fit["axis"])).tolist()
    candidate["note"] = "harmless metadata"
    validate_discovery(candidate, fit, arrays)


def test_certified_norm_roundoff_can_enter_oracle(certified):
    fit, _, arrays = certified
    candidate = copy.deepcopy(fit)
    candidate["axis"] = (np.array(fit["axis"])*(1+4e-8)).tolist()
    validate_discovery(candidate, fit, arrays)
    normalized = expand_fit(candidate)["discovery_axis"]
    assert abs(np.linalg.norm(normalized)-1) < 1e-14


@pytest.mark.parametrize("mutation", ["empty", "missing_person", "extra_person", "all_null", "drop_support", "wrong_axis", "positive_C", "missing_loo", "bool_integer"])
def test_discovery_negative_controls(certified, mutation):
    fit, _, arrays = certified
    bad = copy.deepcopy(fit)
    if mutation == "empty": bad = {}
    elif mutation == "missing_person": bad["people"] = {}
    elif mutation == "extra_person": bad["people"]["other"] = {}
    elif mutation == "all_null": bad["axis_status"] = "discovery_axis_unresolved"; bad["axis"] = None
    elif mutation == "drop_support": bad["support"] = [1, 2]
    elif mutation == "wrong_axis": bad["axis"] = [1., 0., 0.]
    elif mutation == "positive_C": bad["configuration"] = "same_side"
    elif mutation == "missing_loo": bad["leave_one_out"] = {}
    elif mutation == "bool_integer": bad["support"][0] = True
    with pytest.raises(ValueError): validate_discovery(bad, fit, arrays)


def test_transfer_sign_invariance_and_actual_accepted_axis(certified):
    fit, evaluation, arrays = certified
    a = evaluation_reference(evaluation, fit, arrays)
    flipped = copy.deepcopy(fit)
    flipped["axis"] = (-np.array(fit["axis"])).tolist()
    b = evaluation_reference(evaluation, flipped, arrays)
    compare(a, b)
    assert a["people"]["held"]["transfer"]["fraction"] == pytest.approx(1)
    changed = copy.deepcopy(fit)
    changed["axis"] = [1., 0., 0.]
    c = evaluation_reference(evaluation, changed, arrays)
    assert c["people"]["held"]["transfer"]["fraction"] != pytest.approx(1)


@pytest.mark.parametrize("value,expected", [
    ({"status": "defined", "lower": 1., "upper": 2.}, "same_side"),
    ({"status": "defined", "lower": -2., "upper": -1.}, "between"),
    ({"status": "defined", "lower": -2., "upper": 1.}, "unresolved"),
    ({"status": "source_inactive", "lower": None, "upper": None}, "undefined")])
def test_configuration_is_quantitative_not_positive_requirement(value, expected):
    assert interpretation(value) == expected


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}'])
def test_strict_json_rejects_ambiguity_nonfinite(raw):
    with pytest.raises(ValueError): strict_json(raw)


def test_symlink_empty_and_oversized_refused(tmp_path):
    original = tmp_path/"real"
    original.write_bytes(b"abc")
    linked = tmp_path/"linked"
    linked.symlink_to(original)
    with pytest.raises(ValueError): regular_bytes(linked)
    with pytest.raises(ValueError): regular_bytes(original, 2)
    original.write_bytes(b"")
    with pytest.raises(ValueError): regular_bytes(original)


def test_capsule_cannot_hide_opposite_participant(tmp_path):
    raw = b"signal"
    manifest = {"files": [{"path": "train", "participant_id": "train", "size_bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}]}
    (tmp_path/"source_manifest.json").write_text(json.dumps(manifest))
    (tmp_path/"train").write_bytes(raw)
    authenticate_capsule(tmp_path, manifest, ["train"])
    (tmp_path/"heldout").write_bytes(raw)
    with pytest.raises(ValueError): authenticate_capsule(tmp_path, manifest, ["train"])


def test_capsule_cannot_hide_symlink_directory(tmp_path):
    capsule = tmp_path/"capsule"
    capsule.mkdir()
    (capsule/"source_manifest.json").write_text('{}')
    (capsule/"outside").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError): authenticate_capsule(capsule, {"files": []}, [])


def test_control_programs_compile():
    from controls import script_for
    for probe in (False, True):
        for orphan in (False, True):
            compile(script_for({}, probe, orphan), "control", "exec")


def test_every_new_python_module_compiles():
    for path in Path(__file__).parent.glob("*.py"):
        compile(path.read_text(), str(path), "exec")


def test_evaluation_fabrication_and_blanket_null_fail(certified):
    fit, evaluation, arrays = certified
    expected = evaluation_reference(evaluation, fit, arrays)
    fabricated = copy.deepcopy(expected)
    fabricated["people"]["held"]["transfer"]["fraction"] = .1
    with pytest.raises(ValueError): compare(expected, fabricated)
    fabricated["people"]["held"]["transfer"] = {"status": "source_inactive", "fraction": None}
    with pytest.raises(ValueError): compare(expected, fabricated)


def test_source_null_is_preserved_not_dropped(certified):
    fit, evaluation, arrays = certified
    evaluation["people"]["null"] = {"source_status": "source_inactive", "transfer": {"status": "source_inactive", "fraction": None}}
    result = evaluation_reference(evaluation, fit, arrays)
    assert result["summary"]["n_expected"] == 2
    assert result["summary"]["n_defined"] == 1
    assert result["summary"]["leave_one_valid_person_mean_range"] is None


def test_oracle_bundles_have_no_qualified_answers():
    release = Path(__file__).parent
    for independent in (False, True):
        raw = oracle_zip(release.parent, release, independent)
        assert len(raw) < 1024**2
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            assert set(archive.namelist()) == {"__main__.py", "format.py", "core.py", "source_reader.py", "protocol.py", "phase2_production.py", "phase2_workflow.py", "pilot_support.py"}
            assert not any(name.endswith(".json") for name in archive.namelist())


def test_static_trust_boundary():
    root = Path(__file__).parent
    verify = (root/"verify.py").read_text()
    assert verify.index("validate_discovery(fit") < verify.index("run_candidate(fit_raw")
    sandbox = (root/"sandbox.py").read_text()
    for fragment in ("os.chroot", "os.setgroups([])", "os.setgid(UID)", "os.setuid(UID)", "close_fds=True", "libc.prctl(38", "kill_owned()"):
        assert fragment in sandbox
    docker = (root/"environment/Dockerfile").read_text()
    assert "FROM ubuntu:" in docker
    assert "COPY --from=qualified_runtime /app" not in docker
    assert "COPY --from=qualified_runtime /opt" not in docker
    task = (root/"task.toml").read_text()
    assert 'environment_mode = "separate"' in task
