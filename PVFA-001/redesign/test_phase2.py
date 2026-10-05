"""Manufactured independent-reader/arithmetic tests, never source analysis."""
import ast
import gzip
import json
import math
from pathlib import Path
import struct

import numpy as np
import pytest
from scipy.ndimage import gaussian_filter

import phase2_diagnostic as d
import launch_phase2 as launch


def nifti_fixture(path,data,endian="<",slope=1.,intercept=0.,datatype=512):
    header=bytearray(352)
    struct.pack_into(endian+"i",header,0,348)
    struct.pack_into(endian+"8h",header,40,4,*data.shape,1,1,1)
    struct.pack_into(endian+"2h",header,70,datatype,16)
    struct.pack_into(endian+"3f",header,108,352.,slope,intercept)
    header[344:348]=b"n+1\x00"
    with gzip.open(path,"wb") as stream:
        stream.write(header); stream.write(data.astype(endian+"u2").tobytes(order="F"))


@pytest.mark.parametrize("endian",["<",">"])
@pytest.mark.parametrize("slope,intercept",[(1.,0.),(2.,-3.),(0.,99.),(float("nan"),float("nan"))])
def test_independent_reader_endian_order_scaling_and_sparse_volume_indices(tmp_path,endian,slope,intercept):
    data=np.arange(4*5*3*4,dtype=np.uint16).reshape((4,5,3,4))
    file=tmp_path/"fixture.nii.gz"; nifti_fixture(file,data,endian,slope,intercept)
    coordinates=np.array([[0,0,0],[3,4,2],[2,1,1]])
    raw,smooth,meta=d.reconstruct_selected(file,coordinates,[0,2,3],data.shape)
    scaled=data.astype(float)*(slope if math.isfinite(slope) and slope!=0 else 1)+(intercept if math.isfinite(slope) and slope!=0 else 0)
    np.testing.assert_array_equal(raw,scaled[tuple(coordinates.T)][:,[0,2,3]])
    expected=np.stack([gaussian_filter(scaled[...,t],.625/math.sqrt(8*math.log(2)),mode="reflect",truncate=4)[tuple(coordinates.T)] for t in [0,2,3]],axis=1)
    np.testing.assert_allclose(smooth,expected,atol=1e-10,rtol=0)
    assert meta["endian"]==endian


def test_reflect_is_half_sample_symmetric():
    expected=np.pad(np.arange(4),(8,8),mode="symmetric")
    assert [d.reflect_index(i,4) for i in range(-8,12)]==expected.tolist()


@pytest.mark.parametrize("point",[[0,0,0],[4,5,6],[2,3,4]])
def test_direct_27_neighbor_kernel_matches_float64_separable_fixture(point):
    volume=np.random.default_rng(20).uniform(0,65535,(5,6,7)).astype(float)
    direct=d.gaussian_samples(volume,[point])[0]
    reference=gaussian_filter(volume,.625/math.sqrt(8*math.log(2)),mode="reflect",truncate=4)[tuple(point)]
    assert direct==pytest.approx(reference,abs=1e-9,rel=0)


@pytest.mark.parametrize("kind",["datatype","active_nan_intercept","bad_magic","truncated","coordinate","volume_order"])
def test_reader_fails_closed_on_unsupported_or_malformed_input(tmp_path,kind):
    data=np.ones((3,3,3,2),dtype=np.uint16); file=tmp_path/"bad.nii.gz"
    nifti_fixture(file,data,datatype=16 if kind=="datatype" else 512,intercept=float("nan") if kind=="active_nan_intercept" else 0.)
    if kind=="bad_magic":
        with gzip.open(file,"rb") as stream: content=bytearray(stream.read())
        content[344:348]=b"ni1\x00"
        with gzip.open(file,"wb") as stream: stream.write(content)
    if kind=="truncated":
        with gzip.open(file,"rb") as stream: content=stream.read()[:-2]
        with gzip.open(file,"wb") as stream: stream.write(content)
    coords=[[3,0,0]] if kind=="coordinate" else [[0,0,0]]
    volumes=[1,0] if kind=="volume_order" else [0,1]
    with pytest.raises(ValueError): d.reconstruct_selected(file,coords,volumes,data.shape)


@pytest.fixture
def domain():
    return json.loads(Path(__file__).with_name("pilot_contract.json").read_text())["domain"]


def test_independent_forward_mse_fa_and_psd(domain):
    b=np.array([0,1000,2000,1000]); g=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1.]])
    parameters={"D":[.0016,0,.0005,0,0,.0003],"S0":100.,"f":.2}
    expected=100*(.8*np.exp(-b*np.array([0,.0016,.0005,.0003]))+.2*np.exp(-b*.003))
    prediction,metrics=d.prediction_and_metrics(parameters,expected,b,g,domain)
    np.testing.assert_allclose(prediction,expected,atol=1e-13,rtol=0)
    assert metrics["loss"]<1e-28 and metrics["feasible"]
    eig=np.array([1.6,.5,.3]); fa=np.sqrt(1.5*np.sum((eig-eig.mean())**2)/np.sum(eig**2))
    assert metrics["fa"]==pytest.approx(fa,abs=1e-14,rel=0)
    invalid=dict(parameters,D=[-1e-14,0,1e-14,0,0,1e-14])
    _,rejected=d.prediction_and_metrics(invalid,expected,b,g,domain)
    assert not rejected["feasible"]


def test_residual_denominator_and_shell_accounting():
    observed=np.array([100.,80.,60.,40.]); prediction=np.array([110.,70.,70.,30.]); b=np.array([0,1000,1000,2000])
    rows=d.shell_summaries(prediction,observed,b)
    assert [r["n"] for r in rows]==[1,2,1]
    assert sum(r["normalized_sse"] for r in rows)==pytest.approx(.04)
    assert sum(r["sse_fraction"] for r in rows)==pytest.approx(1)
    assert all(r["normalized_rmse"]==pytest.approx(.1) for r in rows)


def test_qc_counts_are_descriptive_not_exclusions():
    result=d.descriptive_qc(np.array([100.,0.,-1.,110.,float("nan")]),[0,1000,1000,2000,2000],100.,105.)
    assert result=={"n":5,"nonfinite":1,"negative":1,"zero":1,"diffusion_above_observed_b0":1,"diffusion_above_fitted_S0":1}


def test_diagnostic_does_not_import_optimization_or_prior_forward_modules():
    tree=ast.parse(Path(d.__file__).read_text())
    imports=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import): imports += [x.name for x in node.names]
        if isinstance(node,ast.ImportFrom): imports.append(node.module or "")
    assert not any(name.split('.')[0] in {"scipy","pilot","witness","nibabel"} for name in imports)


def test_phase2_launcher_binds_prior_readonly_and_zero_fit_scope(tmp_path):
    contract=json.loads(Path(__file__).with_name("phase2_contract.json").read_text())
    name,args=launch.build_command(tmp_path,tmp_path/"new",tmp_path/"approval",contract,"token",1000,1000)
    mounts=[args[i+1] for i,x in enumerate(args) if x=="--mount"]
    assert name=="br-pr156-phase2-token"
    assert len(mounts)==11 and sum(x.endswith(",readonly") for x in mounts)==10
    assert args[args.index("--memory-swap")+1]=="2147483648"
    assert contract["resources"]["fits"]==0
    assert args[-1]=="/out/diagnostic"


def test_global_deadline_starts_before_host_authentication(tmp_path,monkeypatch):
    events=[]
    def clock():
        events.append("clock")
        return 0.
    def reject(*args):
        events.append("verify")
        raise ValueError("expected rejection")
    monkeypatch.setattr(launch.time,"monotonic",clock)
    monkeypatch.setattr(launch,"verify",reject)
    with pytest.raises(ValueError,match="expected rejection"):
        launch.execute(tmp_path,tmp_path/"contract",tmp_path/"approval",{}, {"resources":{"global_wall_seconds":900}})
    assert events==["clock","verify"]
