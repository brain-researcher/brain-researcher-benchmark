"""Manufactured arithmetic and adversarial controls; no source/image/Docker run."""
import copy
import gzip
import json
from pathlib import Path
import sys

import nibabel as nib
import numpy as np
import pytest
from scipy import linalg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"solution"))
import phase2_independent as independent
import phase2_production as production
from phase2_compare import audit_accounting, certificate, compare_arrays, compare_report, validate_fit_axis
from phase2_workflow import compute
from launch_phase2 import stage_command, validate_code

PHASE = json.loads(Path(__file__).with_name("phase2_contract.json").read_text())
BASE = json.loads(Path(__file__).with_name("pilot_contract.json").read_text())
ENVELOPES = PHASE["engineering_envelopes_not_final_scoring_tolerances"]


def test_reviewed_code_closure_and_base_contract_pins():
    validate_code(Path(__file__).resolve().parents[1], PHASE, BASE)


def synthetic_operator(values=(.6, .2, .1)):
    s = np.ones(len(values)+1)/np.sqrt(len(values)+1)
    q = linalg.qr(s[:, None], mode="full")[0][:, 1:]
    k = np.outer(s, s)+(q*np.array(values))@q.T
    return k, s, q


def test_independent_nifti_reader_calibrates_storage():
    image = nib.Nifti1Image(np.arange(24, dtype=np.int16).reshape(2, 3, 4), np.eye(4))
    image.header.set_slope_inter(2.5, -12)
    raw = gzip.compress(image.to_bytes())
    a, affine_a, _ = production.decode(raw, True, 3)
    b, affine_b, _ = independent.decode(raw, True, 3)
    assert np.array_equal(a, b) and np.array_equal(affine_a, affine_b)


@pytest.mark.parametrize("offset", [0., .49, .5, -.25, -1.])
def test_explicit_nearest_sampling_matches_declared_constant_boundary(offset):
    rng = np.random.default_rng(7)
    atlas = rng.integers(0, 7, size=(9, 8, 7))
    bold = rng.normal(size=(5, 4, 3, 6))
    affine = np.eye(4)
    affine[:3, 3] = offset
    ids = np.arange(1, 7)
    a, ca = production.extract(bold, affine, atlas, np.eye(4), ids)
    b, cb = independent.extract(bold, affine, atlas, np.eye(4), ids)
    assert np.array_equal(ca, cb)
    assert np.allclose(a, b, atol=1e-14, equal_nan=True)


def test_independent_projection_certifies_public_rank_and_handles_constant_signal():
    rng = np.random.default_rng(8)
    c = rng.normal(size=(168, 15))
    c[:, 1] = c[:, 0]  # Rank deficiency does not choose a different model.
    y = rng.normal(size=(168, 12))
    y[:, 0] = 7
    counts = np.ones(12, dtype=int)
    a, b = production.clean(y, c, counts), independent.clean(y, c, counts)
    assert a["rank"] == b["rank"] == 14
    assert b["nuisance_projector_error"] < 1e-8
    assert np.array_equal(a["active"], b["active"])
    assert not b["active"][0]
    assert np.allclose(a["clean"], b["clean"], atol=1e-12)


def test_svd_projector_mismatch_stops_instead_of_substituting_rank(monkeypatch):
    rng = np.random.default_rng(12)
    y, c = rng.normal(size=(168, 8)), rng.normal(size=(168, 15))
    original = np.linalg.svd
    def wrong_span(matrix, **kwargs):
        u, s, v = original(matrix, **kwargs)
        return np.roll(u, 1, axis=0), s, v
    monkeypatch.setattr(independent.np.linalg, "svd", wrong_span)
    with pytest.raises(ValueError, match="span ambiguity"):
        independent.clean(y, c, np.ones(8, int))


def test_signed_top_fraction_and_original_id_ties_are_exact():
    n = 20
    fc = np.full((n, n), .1)
    np.fill_diagonal(fc, 1)
    fc[0, 2] = fc[2, 0] = -.99
    ids = np.arange(20, 0, -1)
    ka, sa, ma = production.operator(fc, ids)
    kb, sb, mb = independent.operator(fc, ids)
    assert np.array_equal(ma, mb)
    assert not ma[0, 2] and ma[0, 19]
    assert np.all(ma.sum(axis=1) == 2)
    assert np.allclose(ka, kb, atol=1e-9)
    assert np.allclose(sa, sb, atol=1e-9)


def test_independent_pearson_preserves_public_unit_range_guard():
    x = np.linspace(-2, 3, 168)
    values = independent.correlation(np.column_stack([x, x, -x]))
    assert np.all(values <= 1) and np.all(values >= -1)
    assert np.allclose(values, production.correlation(np.column_stack([x, x, -x])))


def test_spectra_are_largest_algebraic_not_largest_magnitude():
    k, s, _ = synthetic_operator((.5, .1, -.7))
    for engine in (production, independent):
        spec = engine.spectral(k, s)
        assert np.allclose(spec["values"], [.5, .1, -.7])


def test_rotated_near_degenerate_complete_span_passes_but_wrong_span_fails():
    k, s, q = synthetic_operator((.6, .6-3e-8, .2))
    rotation = np.array([[1., -1], [1, 1]])/np.sqrt(2)
    span = q[:, :2]@rotation
    caps = ENVELOPES["spectral_certificate"]
    # Old columnwise matching would exceed1e-8 for this legitimate rotation.
    assert np.max(np.linalg.norm(k@span-span*np.array([.6, .6-3e-8]), axis=0)) > 1e-8
    assert certificate(k, s, np.array([.6, .6-3e-8, .2]), span, caps)["residual_l2_max"] < 1e-8
    with pytest.raises(ValueError, match="certificate"):
        certificate(k, s, np.array([.6, .6-3e-8, .2]), q[:, [0, 2]], caps)


def test_wrong_test_optimal_axis_cannot_replace_source_certified_discovery_axis():
    k, s, q = synthetic_operator()
    arrays = {"discovery:operator": k, "discovery:stationary": s,
              "discovery:eigenvalues": np.array([.6, .2, .1])}
    report = {"axis_status": "defined", "discovery_axis": q[:, 1].tolist()}
    with pytest.raises(ValueError, match="certificate"):
        validate_fit_axis(report, arrays, ENVELOPES["spectral_certificate"])


def test_flat_spectrum_ratio_one_is_not_selective_transfer():
    k, s, q = synthetic_operator((.3, .3, .3))
    for engine in (production, independent):
        spec = engine.spectral(k, s)
        score = engine.transfer(q[:, 0], k, s, spec, .1)
        assert score["fraction"] == pytest.approx(1)
        assert score["rayleigh_minus_spectral_mean"] == pytest.approx(0)


def test_network_range_uses_person_space_and_is_sign_basis_invariant():
    k, s, q = synthetic_operator((.6, .6-3e-8, .2))
    labels = ["Default", "Vis", "SomMot", "Default"]
    spec = production.spectral(k, s)
    a = production.network_range(spec, s, labels)
    changed = dict(spec, vectors=spec["vectors"].copy())
    changed["vectors"][:, :2] = changed["vectors"][:, :2]@np.array([[.6, -.8], [.8, .6]])
    b = independent.network_range(changed, s, labels)
    assert a["lower"] == pytest.approx(b["lower"])
    assert a["upper"] == pytest.approx(b["upper"])


@pytest.fixture(scope="module")
def manufactured_fit_evaluation():
    rng = np.random.default_rng(46)
    names = ["Vis", "SomMot", "DorsAttn", "SalVentAttn", "Limbic", "Cont", "Default"]
    labels = [{"parcel_id": i+1, "network": names[i%7]} for i in range(400)]
    loaded = {}
    for partition in ("discovery", "evaluation"):
        people = []
        for position, sid in enumerate(BASE["cohort"][partition]):
            raw = rng.normal(size=(50, 400))
            result = production.clean(raw, rng.normal(size=(50, 15)), np.ones(400, int))
            if partition == "evaluation" and position == 2:
                result["active"][19] = False
            result.update(participant_id=sid, raw=raw)
            people.append(result)
        loaded[partition] = people
    fit, fa = compute("fit", loaded["discovery"], labels, production)
    ev, ea = compute("evaluate", loaded["evaluation"], labels, production, fit)
    return fit, fa, ev, ea, loaded, labels


def test_complete_manufactured_arithmetic_paths_agree(manufactured_fit_evaluation):
    fit, fa, ev, ea, loaded, labels = manufactured_fit_evaluation
    alternate_fit, alternate_fa = compute("fit", loaded["discovery"], labels, independent)
    compare_report(alternate_fit, fit, ENVELOPES["scalar"])
    compare_arrays(alternate_fa, fa, ENVELOPES)
    validate_fit_axis(fit, alternate_fa, ENVELOPES["spectral_certificate"])
    audit_accounting(fit, alternate_fa, BASE)
    alternate_ev, alternate_ea = compute("evaluate", loaded["evaluation"], labels, independent, fit)
    compare_report(alternate_ev, ev, ENVELOPES["scalar"])
    compare_arrays(alternate_ea, ea, ENVELOPES)
    audit_accounting(ev, alternate_ea, BASE, fit)
    assert ev["n_expected"] == 10 and ev["n_defined"] == 9


@pytest.mark.parametrize("mutation", ["all_null", "test_informed_mask", "missing_person", "parcel_mean", "missing_loo"])
def test_independent_accounting_rejects_contract_failures(manufactured_fit_evaluation, mutation):
    fit, fa, ev, ea, _, _ = manufactured_fit_evaluation
    bad = copy.deepcopy(fit if mutation == "missing_loo" else ev)
    if mutation == "all_null":
        for row in bad["people"]:
            row["transfer"] = {"status": "source_inactive", "fraction": None}
    elif mutation == "test_informed_mask":
        bad["frozen_support"][19] = False
    elif mutation == "missing_person":
        bad["people"].pop()
    elif mutation == "parcel_mean":
        bad["mean_fraction"] = 0.
    else:
        bad["leave_one_out"].pop()
    with pytest.raises(ValueError):
        audit_accounting(bad, fa if mutation == "missing_loo" else ea, BASE,
                         None if mutation == "missing_loo" else fit)


def test_discovery_degeneracy_does_not_null_independent_person_C(manufactured_fit_evaluation):
    fit, _, _, _, loaded, labels = manufactured_fit_evaluation
    unresolved = dict(fit, axis_status="discovery_axis_unresolved", discovery_axis=None)
    report, _ = compute("evaluate", loaded["evaluation"], labels, production, unresolved)
    valid = [r for r in report["people"] if r["source_status"] == "defined"]
    assert all(r["transfer"]["status"] == "discovery_axis_unresolved" for r in valid)
    assert all(r["network_C"]["status"] == "defined" for r in valid)


@pytest.mark.parametrize("stage", ["fit", "evaluate", "check_fit", "check_evaluate"])
def test_all_scientific_stage_commands_preserve_partition_isolation(stage):
    command = stage_command(stage, Path("/task"), Path("/evidence"), BASE, "owned-test", "a"*64)
    text = " ".join(command)
    partition = stage.removeprefix("check_")
    assert f"src=/evidence/capsules/{partition},dst=/source,readonly" in text
    assert "/app:rw,noexec,nosuid,size=1048576" in command
    assert "/opt/source_capture:rw,noexec,nosuid,size=1048576" in command
    if partition == "evaluate":
        assert "src=/evidence/fit/fit.json,dst=/frozen/fit.json,readonly" in text
        assert "src=/evidence/fit,dst=/frozen,readonly" not in text
    assert command[-2:] == ["/pilot/phase2_stage.py", stage]
    if stage.startswith("check_"):
        assert f"src=/evidence/{stage},dst=/out" in text
        assert f"src=/evidence/{partition},dst=/submitted,readonly" in text
