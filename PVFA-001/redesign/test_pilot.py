"""Source-free pilot engineering checks. No Sherbrooke fitting is run here."""
import copy
import json
from pathlib import Path
import time

import numpy as np
import pytest

import pilot


@pytest.fixture
def contract():
    return json.loads(Path(__file__).with_name("pilot_contract.json").read_text())


def test_selection_is_coordinate_only_and_permutation_invariant():
    ijk = np.c_[np.arange(4083),np.zeros((4083,2),dtype=int)].astype(int)
    expected = ((2*np.arange(16)+1)*4083)//32
    np.testing.assert_array_equal(pilot.select_indices(ijk,16),expected)
    order = np.arange(4083)[::-1]
    np.testing.assert_array_equal(ijk[order][pilot.select_indices(ijk[order],16)],ijk[expected])


def test_contract_budget_and_prospectively_fixed_views(contract):
    search = contract["search"]
    fits = contract["selection"]["n_voxels"]*len(contract["protocols"])*len(search["algorithms"])*len(search["starts"])*(1+len(search["profile_f"]))
    assert fits == search["max_fits"] == 768
    assert contract["resources"]["wall_seconds"] == 900
    assert set(contract["sensitivity"]["fraction_views"].values()) == {.7,.9,.999}
    assert "ref_stats" not in contract["source"]["allowed_bank_keys"]


def test_approval_denied_without_explicit_binding(tmp_path):
    p = tmp_path/"contract.json"; p.write_text("{}")
    with pytest.raises(ValueError,match="root review"):
        pilot.verify_approval({},p)
    with pytest.raises(ValueError,match="contract"):
        pilot.verify_approval({"approved":True,"reviewer":"root","contract_sha256":"wrong"},p)
    with pytest.raises(ValueError,match="pilot.py"):
        pilot.verify_approval({"approved":True,"reviewer":"root","contract_sha256":pilot.sha256(p)},p)


def test_distinct_forward_paths_agree_for_equivalent_parameters(contract):
    g = np.vstack([np.zeros(3), np.eye(3),np.ones(3)/np.sqrt(3)])
    b = np.array([0,1000,1000,1000,2000.])
    x = np.array([1.6,.5,.3,.2,-.1,.3,1.1,.25])
    D, ratio, f = pilot.unpack_eigensystem(x,None)
    direct = np.r_[np.array(pilot.tensor6(D))*1000,ratio,f]
    a = pilot.forward_eigensystem(x,b,g,None,.003)
    z = pilot.forward_direct(direct,b,g,None,.003)
    np.testing.assert_allclose(a,z,atol=1e-14,rtol=0)


@pytest.mark.parametrize("algorithm", ["trf_eigensystem","slsqp_direct_tensor"])
@pytest.mark.parametrize("fixed_f", [None,.25])
def test_solver_engineering_smoke_on_manufactured_signal_only(contract,algorithm,fixed_f):
    rng = np.random.default_rng(15)
    g = rng.normal(size=(18,3)); g /= np.linalg.norm(g,axis=1)[:,None]
    g = np.vstack([np.zeros(3),g])
    b = np.r_[0,np.repeat([1000.,2000.],9)]
    start = copy.deepcopy(contract["search"]["starts"][0])
    start["free_f"] = .25
    x = np.r_[np.array(start["eigenvalues"])*1000,start["rotvec"],1.,.25]
    y = 100*pilot.forward_eigensystem(x,b,g,None,.003)
    row = pilot.fit_once(y,b,g,algorithm,fixed_f,start,contract,time.monotonic()+5)
    assert row["admissible"]
    assert row["loss"] < 1e-12
    assert row["objective_calls"] <= 1500
    assert set(row["boundary_diagnostics"]) >= {"f_lower","f_upper","eigenvalue_lower","eigenvalue_upper","S0_lower","S0_upper"}


def test_wall_cap_prevents_any_objective(contract):
    with pytest.raises(pilot.PilotStop,match="wall_cap"):
        pilot.fit_once(np.array([100,60,50]),np.array([0,1000,1000]),np.array([[0,0,0],[1,0,0],[0,1,0]]),"trf_eigensystem",None,contract["search"]["starts"][0],contract,time.monotonic()-1)


def test_candidate_pool_filter_has_common_ceiling_and_retains_failed_feasible(contract):
    rows = [
        {"ijk":[1,2,3],"protocol":"b1000","admissible":True,"optimizer_success":False,"loss":.001,"fa":.2,"parameters":{"f":.5},"attempt_id":0},
        {"ijk":[1,2,3],"protocol":"b1000","admissible":True,"optimizer_success":True,"loss":.00101,"fa":.8,"parameters":{"f":.99},"attempt_id":1},
        {"ijk":[1,2,3],"protocol":"b1000","admissible":False,"loss":0,"fa":1,"parameters":{"f":.2},"attempt_id":2},
    ]
    out = pilot.sensitivity_summary(rows,contract)
    assert len(out) == 9
    first = out[:3]
    assert len(set(x["loss_ceiling"] for x in first)) == 1
    assert first[0]["fa_separation_lower_bound"] == pytest.approx(.6)
    assert first[1]["fa_separation_lower_bound"] == 0
    assert all(x["best_found_loss_full_pool"] == .001 for x in out)


def test_zero_feasible_and_unattempted_groups_remain_visible(contract):
    row = {"ijk":[1,2,3],"protocol":"b1000","admissible":False}
    planned = [((1,2,3),"b1000"),((1,2,3),"b1000_b2000")]
    out = pilot.sensitivity_summary([row],contract,planned)
    assert len(out) == 18
    assert {x["status"] for x in out} == {"not_attempted","no_feasible_candidate"}
    assert all(x["fa_separation_lower_bound"] is None and x["loss_ceiling"] is None for x in out)


def test_aborted_slot_is_retained_and_existing_output_is_not_overwritten(tmp_path,contract,monkeypatch):
    contract = copy.deepcopy(contract); contract["selection"]["n_voxels"] = 1
    arrays = {"ref_roi_ijk":np.array([[1,2,3]]),"ref_bvals":np.array([0,1000]),"ref_bvecs":np.array([[0.,0,0],[1,0,0]]),"ref_signal":np.array([[100.,50.]])}
    def stop(*args,**kwargs): raise pilot.PilotStop("wall_cap")
    monkeypatch.setattr(pilot,"fit_once",stop)
    report = pilot.run_pilot(arrays,contract,tmp_path/"new")
    assert report["status"] == "partial_wall_cap"
    assert report["n_attempts"] == 1
    assert len(report["sensitivity"]) == 18
    assert {x["status"] for x in report["sensitivity"]} == {"not_attempted","no_feasible_candidate"}
    row = json.loads((tmp_path/"new"/"attempts.jsonl").read_text())
    assert row["attempt_aborted"] is True
    with pytest.raises(FileExistsError):
        pilot.run_pilot(arrays,contract,tmp_path/"new")


@pytest.fixture
def authenticated_manufactured_cache(tmp_path,contract):
    contract = copy.deepcopy(contract)
    paths = {name:tmp_path/(name+".json") for name in ("receipt","report","manifest","preprocessing")}
    paths["bank"] = tmp_path/"manufactured.npz"
    paths["raw_source"] = tmp_path/"raw"; paths["raw_source"].mkdir()
    raw = paths["raw_source"]/"manufactured.txt"; raw.write_text("fixture, not Sherbrooke")
    manifest = {"files":[{"path":raw.name,"size_bytes":raw.stat().st_size,"sha256":pilot.sha256(raw)}]}
    paths["manifest"].write_text(json.dumps(manifest))
    paths["preprocessing"].write_text("{}")
    n = 4
    np.savez(paths["bank"],ref_roi_ijk=np.c_[np.arange(n),np.ones((n,2),dtype=int)],ref_signal=np.ones((n,129))*100,ref_bvals=np.r_[0,np.repeat([1000.,2000.],64)],ref_bvecs=np.tile([1.,0,0],(129,1)),forbidden_old_fit=np.array([999.]))
    report = {"status":"passed","mode":"complete_source_check","source_manifest_sha256":pilot.sha256(paths["manifest"]),"source_roi_count":n,"source_sha256":{raw.name:pilot.sha256(raw)},"checks":[{"name":key,"passed":True,"detail":{"max_abs_difference":0}} for key in contract["source"]["required_report_checks"]]}
    receipt = {"reference":{"sha256":pilot.sha256(paths["bank"])},"source":{"manifest_sha256":pilot.sha256(paths["manifest"])}}
    paths["report"].write_text(json.dumps(report)); paths["receipt"].write_text(json.dumps(receipt))
    for role,key in {"bank":"bank_sha256","receipt":"receipt_sha256","report":"independent_report_sha256","manifest":"manifest_sha256","preprocessing":"preprocessing_contract_sha256"}.items():
        contract["source"][key] = pilot.sha256(paths[role])
    contract["source"].update(n_roi=n,signal_shape=[n,129])
    return paths,contract


def test_only_authenticated_source_arrays_are_loaded(authenticated_manufactured_cache):
    paths,contract = authenticated_manufactured_cache
    arrays = pilot.authenticate_source(paths,contract)
    assert set(arrays) == set(contract["source"]["allowed_bank_keys"])
    assert "forbidden_old_fit" not in arrays


@pytest.mark.parametrize("changed", ["bank","raw"])
def test_changed_source_bytes_fail_closed(authenticated_manufactured_cache,changed):
    paths,contract = authenticated_manufactured_cache
    target = paths["bank"] if changed == "bank" else paths["raw_source"]/"manufactured.txt"
    with target.open("ab") as stream: stream.write(b"changed")
    with pytest.raises(ValueError,match="mismatch"):
        pilot.authenticate_source(paths,contract)


def test_failed_historical_source_check_cannot_be_bypassed_by_fresh_hash(authenticated_manufactured_cache):
    paths,contract = authenticated_manufactured_cache
    report = json.loads(paths["report"].read_text()); report["checks"][0]["passed"] = False
    paths["report"].write_text(json.dumps(report))
    contract["source"]["independent_report_sha256"] = pilot.sha256(paths["report"])
    with pytest.raises(ValueError,match="source check"):
        pilot.authenticate_source(paths,contract)
