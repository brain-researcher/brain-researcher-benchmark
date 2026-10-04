"""Manufactured algebra/contract controls, not scientific source validation."""
import numpy as np
import pytest

from protocol import (configuration_range, discovery_support,
                      evaluation_eligibility, metadata_split, summarize_people,
                      transfer_score, validate_partitions)


def records():
    return [{"participant_id": f"s{i:02}", "age": 4+i/10,
             "child_adult": "child" if i < 16 else "adult"} for i in range(20)]


def test_split_is_order_invariant_and_stratified():
    rows = records()
    result = metadata_split(rows)
    assert result == metadata_split(rows[::-1])
    validate_partitions(result, [r["participant_id"] for r in rows])
    groups = {r["participant_id"]: r["child_adult"] for r in rows}
    for group in result.values():
        assert len(group) == 10
        assert sum(groups[x] == "adult" for x in group) == 2


def test_outcome_and_activity_fields_cannot_change_split():
    rows = records()
    result = metadata_split(rows)
    for row in rows:
        row.update(favorable_gradient=True, active=False, reward=0)
    assert metadata_split(rows) == result


@pytest.mark.parametrize("mutation", ["duplicate", "unknown", "overlap", "missing"])
def test_partition_errors_fail(mutation):
    result = metadata_split(records())
    if mutation == "duplicate":
        result["discovery"].append(result["discovery"][0])
    elif mutation == "unknown":
        result["evaluation"][0] = "not_source"
    elif mutation == "overlap":
        result["evaluation"][0] = result["discovery"][0]
    else:
        result["evaluation"].pop()
    with pytest.raises(ValueError):
        validate_partitions(result, [r["participant_id"] for r in records()])


def test_test_activity_cannot_shrink_discovery_support():
    train = np.ones((10, 8), dtype=bool)
    train[0, 7] = False
    support = discovery_support(train)
    test = np.ones((10, 8), dtype=bool)
    test[0, 3] = False
    eligible = evaluation_eligibility(test, support)
    assert eligible.sum() == 9
    assert np.array_equal(support, [True]*7+[False])
    assert np.array_equal(discovery_support(train), support)


def operator_fixture():
    s = np.ones(3)/np.sqrt(3)
    first = np.array([1., -1., 0.])/np.sqrt(2)
    second = np.cross(s, first)
    basis = np.column_stack([s, first, second])
    k = basis @ np.diag([1., .6, .2]) @ basis.T
    return k, s, first, second


def score(axis, **kw):
    k, s, _, _ = operator_fixture()
    values = dict(discovery_gap=.1, stationary_gap=.4)
    values.update(kw)
    return transfer_score(axis, k, s, .6, **values)


def test_score_sign_invariant_but_does_not_replace_frozen_axis():
    _, _, first, second = operator_fixture()
    assert score(second)["fraction"] == pytest.approx(1/3)
    assert score(-second)["fraction"] == pytest.approx(1/3)
    assert score(first)["fraction"] == pytest.approx(1)
    # Switching to the test-optimal first axis would change the result; final
    # verifier must compare the frozen discovery artifact, not trust this API.


def test_stationary_contamination_is_projected_and_reported():
    _, s, _, second = operator_fixture()
    result = score((s + second)/np.sqrt(2))
    assert result["fraction"] == pytest.approx(1/3)
    assert result["projected_norm"] == pytest.approx(1/np.sqrt(2))
    assert result["stationary_overlap_squared"] == pytest.approx(.5)


def test_isotropic_operator_high_ratio_is_not_selective_transfer():
    _, s, first, _ = operator_fixture()
    k = .3*np.eye(3) + .7*np.outer(s, s)
    result = transfer_score(first, k, s, .3, discovery_gap=.1, stationary_gap=.7)
    assert result["fraction"] == pytest.approx(1)
    assert result["nontrivial_spectral_mean"] == pytest.approx(.3)
    assert result["rayleigh_minus_spectral_mean"] == pytest.approx(0)


@pytest.mark.parametrize("reason,kwargs", [
    ("discovery_axis_unresolved", {"discovery_gap": 0}),
    ("stationary_mode_unresolved", {"stationary_gap": 0})])
def test_unresolved_spectrum_is_not_a_chosen_favorable_axis(reason, kwargs):
    _, _, _, second = operator_fixture()
    result = score(second, **kwargs)
    assert result["status"] == reason and result["fraction"] is None


def test_stationary_axis_and_zero_energy_are_undefined():
    k, s, first, _ = operator_fixture()
    assert score(s)["status"] == "stationary_projection_unresolved"
    result = transfer_score(first, np.outer(s, s), s, 0,
                            discovery_gap=.1, stationary_gap=1)
    assert result["status"] == "leading_energy_unresolved"


def test_fabricated_stationary_or_leading_eigenvalue_fails():
    k, s, first, _ = operator_fixture()
    with pytest.raises(ValueError, match="stationary"):
        transfer_score(first, k, first, .6, discovery_gap=.1, stationary_gap=.4)
    with pytest.raises(ValueError, match="exceeds"):
        transfer_score(first, k, s, .2, discovery_gap=.1, stationary_gap=.4)


def test_network_statistic_sign_scale_and_offset_invariance():
    labels = ["Default", "Default", "Vis", "Vis", "SomMot", "SomMot"]
    g = np.array([2., 1., -1., -2., -.5, -1.5])
    result = configuration_range(g, labels)
    changed = configuration_range(-3*g+100, labels)
    assert result["lower"] == pytest.approx(changed["lower"])
    expected = (g[:2].mean()-g[2:4].mean())*(g[:2].mean()-g[4:].mean())/g.var()
    assert result["lower"] == pytest.approx(expected)
    assert result["upper"] == pytest.approx(expected)


@pytest.mark.parametrize("scale", [1e-200, -1e-150, 1e150, -1e200])
def test_network_statistic_resolved_extreme_nonzero_scale_invariance(scale):
    labels = ["Default"]*2+["Vis"]*2+["SomMot"]*2
    g = np.array([2., 1., -1., -2., -.5, -1.5])
    a, b = configuration_range(g, labels), configuration_range(g*scale, labels)
    assert a["status"] == b["status"] == "defined"
    assert a["lower"] == pytest.approx(b["lower"])
    assert a["upper"] == pytest.approx(b["upper"])


def test_span_very_different_column_scales_are_equilibrated():
    labels = ["Default"]*2+["Vis"]*2+["SomMot"]*2
    g = np.array([[2, 0], [1, 1], [-2, 0], [-1, 1], [0, -1], [0, -2.]])
    a = configuration_range(g, labels)
    b = configuration_range(g * [1e-200, 1e200], labels)
    assert a["rank"] == b["rank"] == 2
    assert a["lower"] == pytest.approx(b["lower"])
    assert a["upper"] == pytest.approx(b["upper"])


def test_negative_configuration_is_valid_not_forced_positive():
    result = configuration_range([0, 0, -1, -1, 1, 1],
                                 ["Default"]*2+["Vis"]*2+["SomMot"]*2)
    assert result["lower"] < 0 and result["upper"] < 0


def test_full_repeated_span_range_is_basis_invariant():
    labels = ["Default"]*2+["Vis"]*2+["SomMot"]*2
    g = np.array([[2, 0], [1, 1], [-2, 0], [-1, 1], [0, -1], [0, -2.]])
    mixed = g @ np.array([[2., -1], [1, 3]]) + 4
    a, b = configuration_range(g, labels), configuration_range(mixed, labels)
    assert a["lower"] == pytest.approx(b["lower"])
    assert a["upper"] == pytest.approx(b["upper"])
    # A single favorably selected column is not the whole-space range.
    assert configuration_range(g[:, 0], labels)["lower"] > a["lower"]


def test_constant_and_missing_network_do_not_produce_fake_scores():
    labels = ["Default", "Vis", "SomMot"]
    assert configuration_range(np.ones(3), labels)["status"] == "constant_coordinate"
    with pytest.raises(ValueError, match="networks"):
        configuration_range([1, 2, 3], ["Vis"]*3)


def test_person_summary_keeps_undefined_person_and_is_not_parcel_inference():
    rows = [{"participant_id": "a", "status": "defined", "fraction": .2},
            {"participant_id": "b", "status": "defined", "fraction": .8},
            {"participant_id": "c", "status": "source_inactive", "fraction": None}]
    result = summarize_people(rows, ["c", "a", "b"])
    assert result["n_expected"] == 3 and result["n_defined"] == 2
    assert result["mean"] == pytest.approx(.5)
    assert result["leave_one_valid_person_mean_range"] == pytest.approx([.2, .8])
    assert not {"p_value", "confidence_interval", "n_parcels"} & result.keys()
    with pytest.raises(ValueError):
        summarize_people(rows[:-1], ["a", "b", "c"])


def test_all_null_summary_does_not_claim_source_validation_or_success():
    result = summarize_people([
        {"participant_id": "a", "status": "unproven_reason", "fraction": None}], ["a"])
    assert result["n_expected"] == 1 and result["n_defined"] == 0
    assert result["mean"] is None
    # This prototype is deliberately not the final verifier: source-backed
    # checks, not a reason string or this summary, must reject invented nulls.
