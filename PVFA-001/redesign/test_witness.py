"""Manufactured arithmetic fixtures only; not pilot evidence or a task answer."""

import copy
import json
from pathlib import Path

import numpy as np
import pytest

from witness import Domain, EvidenceError, candidate_metrics, require_release_contract, validate_witness


@pytest.fixture
def fixture():
    # Axis sampling deliberately makes closed-form arithmetic inspectable.
    # This is not a scientifically sufficient diffusion acquisition.
    b = np.array([0, 1000, 1000, 1000, 2000, 2000, 2000], dtype=float)
    g = np.vstack([np.zeros(3), np.eye(3), np.eye(3)])
    left = {"D": [0.0016, 0, 0.0005, 0, 0, 0.0003], "S0": 100.0, "f": 0.2}
    right = {"D": [0.0013, 0, 0.00065, 0, 0, 0.00045], "S0": 100.0, "f": 0.15}
    # Bounds and budgets are test-only constants, not proposed scientific cutoffs.
    domain = Domain(0, 0.003, 0.5, 1.5, 0, 0.99, 1e-15, 1e-12, 1e-6)
    expected = 100 * (0.8 * np.exp(-b * np.array([0, .0016, .0005, .0003, .0016, .0005, .0003])) + 0.2 * np.exp(-b * .003))
    right_loss = candidate_metrics(expected, b, g, right, domain)["loss"]
    return expected, b, g, left, right, domain, right_loss + 1e-12


def test_forward_model_matches_independent_axis_formula(fixture):
    y, b, g, left, _, domain, _ = fixture
    result = candidate_metrics(y, b, g, left, domain)
    np.testing.assert_allclose(result["prediction"], y, atol=1e-13, rtol=0)
    assert result["loss"] < 1e-28
    expected_fa = np.sqrt(1.5 * ((.0016-.0008)**2 + (.0005-.0008)**2 + (.0003-.0008)**2) / (.0016**2+.0005**2+.0003**2))
    assert result["fa"] == pytest.approx(expected_fa)


def test_verified_pair_is_only_lower_bound(fixture):
    y, b, g, left, right, domain, ceiling = fixture
    result = validate_witness(y, b, g, left, right, domain, loss_ceiling=ceiling, minimum_fa_gap=0.01)
    assert result["fa_separation_lower_bound"] > 0.01
    assert result["interpretation"] == "model_and_budget_conditioned_lower_bound"
    assert "identified" not in result


def test_common_signal_scale_does_not_change_discrepancy(fixture):
    y, b, g, left, right, domain, ceiling = fixture
    before = validate_witness(y, b, g, left, right, domain, loss_ceiling=ceiling, minimum_fa_gap=.01)
    left, right = copy.deepcopy(left), copy.deepcopy(right)
    left["S0"] *= 17
    right["S0"] *= 17
    after = validate_witness(y*17, b, g, left, right, domain, loss_ceiling=ceiling, minimum_fa_gap=.01)
    assert before["right_loss"] == pytest.approx(after["right_loss"])
    assert before["fa_separation_lower_bound"] == pytest.approx(after["fa_separation_lower_bound"])


def test_joint_rotation_invariance(fixture):
    y, b, g, left, _, domain, _ = fixture
    angle = .31
    R = np.array([[np.cos(angle), -np.sin(angle), 0], [np.sin(angle), np.cos(angle), 0], [0, 0, 1]])
    D = R @ np.diag([.0016, .0005, .0003]) @ R.T
    rotated = dict(left, D=[D[0,0], D[0,1], D[1,1], D[0,2], D[1,2], D[2,2]])
    original = candidate_metrics(y, b, g, left, domain)
    result = candidate_metrics(y, b, g @ R.T, rotated, domain)
    np.testing.assert_allclose(result["prediction"], original["prediction"], atol=1e-13, rtol=0)
    assert result["fa"] == pytest.approx(original["fa"])


def test_volume_order_invariance(fixture):
    y, b, g, left, _, domain, _ = fixture
    p = [3, 6, 0, 1, 5, 2, 4]
    assert candidate_metrics(y[p], b[p], g[p], left, domain)["loss"] < 1e-28


def test_rank_deficient_tensor_uses_explicit_roundoff_tolerance(fixture):
    y, b, g, left, _, domain, _ = fixture
    # Exact rank-one all-ones tensor can have a tiny negative eigvalsh result.
    rank_one = dict(left, D=[.001] * 6)
    result = candidate_metrics(y, b, g, rank_one, domain)
    assert result["fa"] == pytest.approx(1.0)
    assert result["minimum_raw_eigenvalue"] >= -domain.eigenvalue_arithmetic_atol


@pytest.mark.parametrize("scale", [1e-14, 1e-100, 1e-200])
def test_absolute_tolerance_cannot_hide_tiny_indefinite_tensor(fixture, scale):
    y, b, g, left, _, _, _ = fixture
    permissive_absolute = Domain(0, .003, .5, 1.5, 0, .99, 1e-12, 1e-12, 1e-6)
    invalid = dict(left, D=[-scale, 0, scale, 0, 0, scale])
    with pytest.raises(EvidenceError, match="tensor eigenvalues"):
        candidate_metrics(y, b, g, invalid, permissive_absolute)


@pytest.mark.parametrize("scale", [1e-14, 1e-100, 1e-200])
def test_tiny_positive_tensor_has_scale_stable_fa(fixture, scale):
    y, b, g, left, _, domain, _ = fixture
    tiny = dict(left, D=[scale, 0, .5*scale, 0, 0, .3*scale])
    ordinary = dict(left, D=[.001, 0, .0005, 0, 0, .0003])
    a = candidate_metrics(y, b, g, tiny, domain)
    z = candidate_metrics(y, b, g, ordinary, domain)
    assert a["fa"] == pytest.approx(z["fa"], abs=1e-14, rel=0)
    assert a["effective_eigenvalue_arithmetic_atol"] <= domain.eigenvalue_arithmetic_rtol * scale * (1+1e-14)


@pytest.mark.parametrize("scale", [1e-3, 1e-14, 1e-100, 1e-200])
def test_rotated_rank_one_tensor_is_stable_across_scales(fixture, scale):
    y, b, g, left, _, domain, _ = fixture
    u = np.array([1., 2., 3.]) / np.sqrt(14.)
    D = scale * np.outer(u, u)
    params = dict(left, D=[D[0,0], D[0,1], D[1,1], D[0,2], D[1,2], D[2,2]])
    result = candidate_metrics(y, b, g, params, domain)
    assert result["fa"] == pytest.approx(1., abs=1e-14, rel=0)
    assert result["minimum_raw_eigenvalue"] >= -result["effective_eigenvalue_arithmetic_atol"]


def test_rounded_source_style_vector_is_preserved_not_normalized(fixture):
    y, b, g, left, _, domain, _ = fixture
    g = g.copy()
    g[1] = [-.999979, -.00504001, -.00402795]
    result = candidate_metrics(y, b, g, left, domain)
    q = np.sum(g[1] ** 2 * [.0016, .0005, .0003])
    expected = 100 * (.8 * np.exp(-1000*q) + .2 * np.exp(-3))
    assert result["prediction"][1] == pytest.approx(expected, abs=1e-13, rel=0)
    strict = Domain(0, .003, .5, 1.5, 0, .99, 1e-15, 1e-12, 1e-8)
    with pytest.raises(EvidenceError, match="gradient norm"):
        candidate_metrics(y, b, g, left, strict)


def test_duplicate_fit_is_not_a_witness(fixture):
    y, b, g, left, _, domain, ceiling = fixture
    with pytest.raises(EvidenceError, match="FA separation"):
        validate_witness(y, b, g, left, left, domain, loss_ceiling=ceiling, minimum_fa_gap=.01)


def test_different_bad_fits_do_not_pass(fixture):
    y, b, g, left, right, domain, _ = fixture
    with pytest.raises(EvidenceError, match="public budget"):
        validate_witness(y, b, g, left, right, domain, loss_ceiling=1e-20, minimum_fa_gap=.01)


@pytest.mark.parametrize("field,value", [("S0", 0), ("S0", 1000), ("S0", np.nan), ("S0", True), ("f", 1), ("f", -.1), ("f", np.inf), ("f", "0.2"), ("D", [-.001,0,.0005,0,0,.0003]), ("D", [0]*6), ("D", [.004,0,.0005,0,0,.0003]), ("D", [np.nan]*6), ("D", [True]*6), ("D", [0]*5)])
def test_rejects_invalid_parameters_without_clipping(fixture, field, value):
    y, b, g, left, _, domain, _ = fixture
    with pytest.raises(EvidenceError):
        candidate_metrics(y, b, g, dict(left, **{field: value}), domain)


@pytest.mark.parametrize("kind", ["zero_b0", "negative", "nan", "wrong_shape", "nonunit", "two_b0"])
def test_rejects_invalid_observations_or_protocol(fixture, kind):
    y, b, g, left, _, domain, _ = fixture
    y, b, g = y.copy(), b.copy(), g.copy()
    if kind == "zero_b0": y[0] = 0
    if kind == "negative": y[1] = -1
    if kind == "nan": y[2] = np.nan
    if kind == "wrong_shape": y = y[:-1]
    if kind == "nonunit": g[1] *= 2
    if kind == "two_b0": b[1] = 0
    with pytest.raises(EvidenceError):
        candidate_metrics(y, b, g, left, domain)


@pytest.mark.parametrize("ceiling,gap", [(np.inf,.1), (-1,.1), (.1,0), (.1,2), (True,.1), (.1,False)])
def test_rejects_vacuous_or_nonfinite_public_budgets(fixture, ceiling, gap):
    y, b, g, left, right, domain, _ = fixture
    with pytest.raises(EvidenceError):
        validate_witness(y, b, g, left, right, domain, loss_ceiling=ceiling, minimum_fa_gap=gap)


def test_design_contract_cannot_be_used_as_release():
    contract = json.loads(Path(__file__).with_name("scientific_contract.json").read_text())
    with pytest.raises(EvidenceError, match="not a qualified"):
        require_release_contract(contract)
    contract.update(status="qualified_release", runnable=True)
    with pytest.raises(EvidenceError, match="unresolved release field"):
        require_release_contract(contract)
