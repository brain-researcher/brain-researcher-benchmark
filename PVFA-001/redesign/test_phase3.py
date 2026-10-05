"""Source-free engineering fixtures; no retained candidate/source replay."""
import copy
import json
from pathlib import Path

import numpy as np
import pytest

import phase3_replay as replay
import launch_phase3 as launch


@pytest.fixture
def contract():
    return json.loads(Path(__file__).with_name("phase3_contract.json").read_text())


@pytest.fixture
def domain():
    return json.loads(Path(__file__).with_name("pilot_contract.json").read_text())["domain"]


def manufactured(s0,canonical_b0,reconstructed_b0,domain):
    b=np.array([0,1000,1000]); g=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]])
    canonical=np.array([canonical_b0,40.,30.]); reconstructed=canonical.copy(); reconstructed[0]=reconstructed_b0
    params={"D":[.001,0,.0005,0,0,.0002],"S0":s0,"f":.2}
    _,left=replay.arithmetic.prediction_and_metrics(params,canonical,b,g,domain)
    _,right=replay.arithmetic.prediction_and_metrics(params,reconstructed,b,g,domain)
    attempt={"attempt_id":0,"ijk":[1,2,3],"protocol":"fixture","algorithm":"none","parameters":params,"admissible":left["feasible"],"loss":left["loss"],"fa":left["fa"]}
    row=replay.compare_candidate(attempt,right,canonical,reconstructed,b,g,domain,{"normalized_mse_atol":1e-10,"fa_atol":1e-10})
    return row,attempt


@pytest.mark.parametrize("s0,new_b0",[(150.,np.nextafter(100.,0.)),(50.,np.nextafter(100.,np.inf))])
def test_strict_boundary_reconstruction_difference_is_retained_not_repaired(domain,s0,new_b0):
    row,_=manufactured(s0,100.,new_b0,domain)
    assert row["canonical"]["feasible"]
    assert not row["reconstructed"]["feasible"]
    assert row["substrate_feasibility_difference"]
    assert row["canonical_comparison"]["feasibility_agrees"]
    assert row["reconstructed_comparison"]["feasibility_agrees"]
    assert row["canonical"]["fa"]==row["reconstructed"]["fa"]


@pytest.mark.parametrize("s0",[np.nextafter(150.,np.inf),np.nextafter(50.,0.)])
def test_materially_exact_canonical_bound_is_not_silently_relaxed(domain,s0):
    row,_=manufactured(s0,100.,100.,domain)
    assert not row["canonical"]["feasible"] and not row["reconstructed"]["feasible"]


def test_interior_candidate_and_parameters_are_unchanged(domain):
    row,attempt=manufactured(100.,100.,np.nextafter(100.,np.inf),domain)
    before=copy.deepcopy(attempt)
    b=np.array([0,1000,1000]); g=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]])
    replay.compare_candidate(attempt,row["reconstructed"],np.array([100.,40.,30.]),
        np.array([np.nextafter(100.,np.inf),40.,30.]),b,g,domain,{"normalized_mse_atol":1e-10,"fa_atol":1e-10})
    assert row["canonical"]["feasible"] and row["reconstructed"]["feasible"]
    assert not row["substrate_feasibility_difference"]
    assert len(row["parameters_sha256"])==64
    assert attempt==before


def test_missing_candidate_is_preserved_without_invented_metrics(domain):
    attempt={"attempt_id":17,"ijk":[1,2,3],"protocol":"fixture","algorithm":"none","admissible":False,"error":"objective_call_cap"}
    row=replay.compare_candidate(attempt,{},None,None,None,None,domain,{})
    assert row["status"]=="no_retained_candidate" and "canonical" not in row


def test_prior_false_accept_and_changed_metric_are_detected(domain):
    row,_=manufactured(100.,100.,100.,domain)
    changed=dict(row["canonical"],feasible=False,loss=row["canonical"]["loss"]+.01)
    comparison=replay.compare_metrics(row["canonical"],changed,{"normalized_mse_atol":1e-10,"fa_atol":1e-10},"feasible")
    assert comparison["feasibility_agrees"] is False and comparison["loss_agrees"] is False


def test_approval_requires_exact_code_and_contract(tmp_path,contract,monkeypatch):
    monkeypatch.setattr(replay.arithmetic,"sha",lambda path:"h")
    monkeypatch.setattr(replay,"code_hashes",lambda path:{"x":"h"})
    contract=dict(contract,immutable_code_sha256={"old":"h"})
    good={"approved":True,"reviewer":"root","contract_sha256":"h","code_sha256":{"x":"h"}}
    replay.verify_approval(good,tmp_path/"contract",tmp_path,contract)
    with pytest.raises(ValueError): replay.verify_approval(dict(good,code_sha256={"x":"stale"}),tmp_path/"contract",tmp_path,contract)


def test_launcher_is_readonly_offline_bounded_and_has_no_raw_mount(tmp_path,contract):
    name,args=launch.build_command(tmp_path,tmp_path/"out",tmp_path/"approval",contract,"owned",1000,1000)
    mounts=[args[i+1] for i,x in enumerate(args) if x=="--mount"]
    assert name=="br-pr156-replay-owned" and len(mounts)==13
    assert sum(m.endswith(",readonly") for m in mounts)==12
    assert args[args.index("--network")+1]=="none"
    assert args[args.index("--memory-swap")+1]=="2147483648"
    assert args[-1]=="/out/replay"
    assert not any("/app/data" in m for m in mounts)


@pytest.mark.parametrize("key,value",[("fits",1),("global_wall_seconds",61),("network",True),("gpu",True),("max_output_bytes",33554432)])
def test_launcher_rejects_scope_expansion(tmp_path,contract,key,value):
    contract["resources"][key]=value
    with pytest.raises(ValueError): launch.build_command(tmp_path,tmp_path/"out",tmp_path/"approval",contract,"owned",1000,1000)


def test_global_clock_precedes_authentication(tmp_path,contract,monkeypatch):
    events=[]
    def clock(): events.append("clock"); return 0.
    def reject(*args): events.append("verify"); raise ValueError("expected")
    monkeypatch.setattr(launch.time,"monotonic",clock); monkeypatch.setattr(replay,"verify_approval",reject)
    with pytest.raises(ValueError,match="expected"): launch.execute(tmp_path,tmp_path/"contract",tmp_path/"approval",{},contract)
    assert events==["clock","verify"]


def test_host_authentication_refuses_changed_file(tmp_path,monkeypatch):
    file=tmp_path/"input"; file.write_text("fixture")
    monkeypatch.setattr(launch.infra,"remaining",lambda deadline:1)
    with pytest.raises(ValueError,match="hash mismatch"):
        launch.authenticate_host({"bank":file},{"input_sha256":{"bank":"wrong"}},1)


def test_full_replay_bookkeeping_with_manufactured_receipts(tmp_path,domain,contract,monkeypatch):
    # All support is manufactured here; authenticate is replaced, never run.
    canonical=np.tile([100.,40.,30.],(16,1)); reconstructed=canonical.copy()
    reconstructed[0,0]=np.nextafter(100.,0.)
    b=np.array([0,1000,2000]); g=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]])
    selection={"coordinates":[[i,0,0] for i in range(16)]}
    rebuilt={"smoothed":reconstructed,"bvalues":b,"directions":g}
    prior={"domain":domain,"protocols":{"p":[0,1000,2000]}}
    comparison={"arithmetic_checks":{"normalized_mse_atol":1e-10,"fa_atol":1e-10}}
    attempts=[]; checks=[]
    for i in range(768):
        coordinate=i//48
        attempt={"attempt_id":i,"ijk":[coordinate,0,0],"protocol":"p","algorithm":"manufactured","admissible":False}
        check={"status":"no_retained_candidate"}
        if i%48<42:
            parameters={"D":[.001,0,.0005,0,0,.0002],"S0":150. if i==0 else 100.,"f":.2}
            _,left=replay.arithmetic.prediction_and_metrics(parameters,canonical[coordinate],b,g,domain)
            _,right=replay.arithmetic.prediction_and_metrics(parameters,reconstructed[coordinate],b,g,domain)
            attempt.update(parameters=parameters,admissible=left["feasible"],loss=left["loss"],fa=left["fa"])
            check=dict(right,status="reconstructed")
        else: attempt["error"]="objective_call_cap"
        attempts.append(attempt); checks.append(check)
    representatives=[{"ijk":[i,0,0],"protocol":"p","attempt_id":i*48+1+j,"normalized_rmse":.1} for i in range(16) for j in range(2)]
    sensitivity=[{"ijk":[i,0,0],"protocol":"p","budget":.0001,"view":"fixture","left_candidate":i*48+1,"right_candidate":i*48+2} for i in range(16) for _ in range(18)]
    historical={"status":"completed_with_arithmetic_disagreements","best_residual_summaries":representatives}
    contract["arithmetic"]["expected_historical_difference_ids"]=[0]
    frozen=copy.deepcopy(attempts)
    monkeypatch.setattr(replay,"authenticate",lambda paths,c:(canonical,rebuilt,prior,comparison,selection,attempts,checks,{"sensitivity":sensitivity},historical,1e-14))
    output=tmp_path/"new"
    result=replay.replay({},contract,output)
    assert result["status"]=="completed_canonical_substrate_replay"
    assert result["n_attempt_slots"]==768 and result["n_retained_candidates"]==672 and result["n_without_candidate"]==96
    assert result["canonical_feasible_count"]==672 and result["reconstructed_feasible_count"]==671
    assert result["substrate_feasibility_difference_ids"]==[0]
    assert result["representative_difference_ids"]==[] and result["n_endpoint_rows_with_membership_difference"]==0
    assert result["prior_phase2_status_preserved"]==historical["status"]
    assert len((output/"candidate_replay.jsonl").read_text().splitlines())==768
    assert len(json.loads((output/"representative_audit.json").read_text()))==32
    assert len(json.loads((output/"endpoint_membership_audit.json").read_text()))==288
    assert attempts==frozen
    with pytest.raises(FileExistsError): replay.replay({},contract,output)
