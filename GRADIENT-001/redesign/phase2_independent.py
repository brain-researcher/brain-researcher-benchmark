"""Independent arithmetic. No production, protocol, or legacy-core imports.

Same authenticated source and NumPy/SciPy/NiBabel libraries, independently
composed extraction, projection, kernel, spectral and endpoint calculations.
"""
import gzip
import math

import nibabel as nib
import numpy as np
from scipy import linalg

GAP = 4e-8


def require(value, message):
    if not value:
        raise ValueError(message)


def decode(raw, compressed, ndim):
    logical = gzip.decompress(raw) if compressed else raw
    image = nib.Nifti1Image.from_bytes(logical)
    require(len(image.shape) == ndim, "image dimensions")
    stored = np.asarray(image.dataobj.get_unscaled(), dtype=np.float64)
    values = stored*float(image.dataobj.slope)+float(image.dataobj.inter)
    require(np.isfinite(values).all(), "nonfinite calibrated source")
    return values, np.asarray(image.affine), dict(shape=list(values.shape),
            effective_scaling_slope=float(image.dataobj.slope),
            effective_scaling_intercept=float(image.dataobj.inter))


def extract(bold, affine, atlas, atlas_affine, parcel_ids):
    shape = bold.shape[:3]
    grid = np.indices(shape).reshape(3, -1)
    transform = np.linalg.solve(atlas_affine, affine)
    coords = transform[:3, :3] @ grid + transform[:3, 3, None]
    # ndimage constant mode considers coordinates outside [0,n-1] out of bounds
    # before nearest-integer rounding; this matters near half-voxel edges.
    valid = np.all((coords >= 0) & (coords <= np.array(atlas.shape)[:, None]-1), axis=0)
    nearest = np.floor(coords[:, valid]+.5).astype(int)
    labels = np.zeros(grid.shape[1], dtype=int)
    labels[valid] = atlas[tuple(nearest)].astype(int)
    counts_all = np.bincount(labels, minlength=int(max(parcel_ids))+1)
    counts = counts_all[parcel_ids]
    means = np.full((bold.shape[-1], len(parcel_ids)), np.nan)
    for t in range(bold.shape[-1]):
        sums = np.bincount(labels, weights=bold[..., t].ravel(order="C"), minlength=len(counts_all))
        means[t, counts > 0] = sums[parcel_ids[counts > 0]]/counts[counts > 0]
    return means, counts


def stable_norm(x):
    scale = float(np.max(np.abs(x)))
    return 0. if scale == 0 else scale*math.sqrt(math.fsum(float(z)**2 for z in x/scale))


def center(x):
    if np.max(x) == np.min(x):
        return np.zeros_like(x)
    return x-math.fsum(float(v) for v in x)/len(x)


def detrend_by_projection(x):
    x = np.asarray(x, float)
    design = np.column_stack([np.ones(len(x)), np.arange(len(x))-(len(x)-1)/2])
    design /= np.linalg.norm(design, axis=0)
    result = x-design@(design.T@x)
    result[:, np.all(x == x[0], axis=0)] = 0
    return result


def clean(raw, confounds, counts):
    geometry = counts > 0
    c = detrend_by_projection(confounds)
    c -= c.mean(axis=0)
    sigma = np.sqrt(np.mean(c*c, axis=0))
    c /= np.where(sigma < np.finfo(float).eps, 1, sigma)
    # QR is used only to certify the PUBLIC rank definition. Projection is SVD.
    public_q, r, _ = linalg.qr(c, mode="economic", pivoting=True)
    kept = np.abs(np.diag(r)) > 100*np.finfo(float).eps
    public_rank = int(np.count_nonzero(kept))
    public_q = public_q[:, kept]
    u, singular, _ = np.linalg.svd(c, full_matrices=False)
    q = u[:, :public_rank]
    projector_error = float(np.linalg.norm(q@q.T-public_q@public_q.T, ord="fro"))
    require(projector_error <= 1e-8, "nuisance SVD/QR span ambiguity; no rank substitution")
    y = detrend_by_projection(raw[:, geometry])
    y = y-q@(q.T@y)
    residual = np.full_like(raw, np.nan)
    residual[:, geometry] = y
    norms, raw_sd, thresholds = (np.full(raw.shape[1], np.nan) for _ in range(3))
    active = np.zeros(raw.shape[1], dtype=bool)
    for p in np.flatnonzero(geometry):
        raw_sd[p] = stable_norm(center(raw[:, p]))/math.sqrt(len(raw)-1)
        thresholds[p] = 1e-12*math.sqrt(len(raw))*max(1, raw_sd[p])
        norms[p] = stable_norm(center(residual[:, p]))
        active[p] = norms[p] > thresholds[p]
    return dict(clean=residual, active=active, counts=counts, raw_sd=raw_sd,
                residual_norm=norms, threshold=thresholds, rank=public_rank,
                nuisance_projector_error=projector_error)


def correlation(cleaned):
    y = cleaned-np.mean(cleaned, axis=0)
    y /= np.sqrt(np.sum(y*y, axis=0))
    matrix = y.T@y
    # np.corrcoef's public real-valued range guard is also part of the declared
    # Pearson output; do not let roundoff above1 change signed top-k ordering.
    np.clip(matrix, -1, 1, out=matrix)
    np.fill_diagonal(matrix, 1)
    return (matrix+matrix.T)/2


def operator(fc, parcel_ids):
    p = len(fc)
    keep = (p+9)//10
    selected = np.zeros((p, p), dtype=bool)
    sparse = np.zeros((p, p))
    for i in range(p):
        indices = sorted(range(p), key=lambda j: (-float(fc[i, j]), int(parcel_ids[j])))[:keep]
        selected[i, indices] = True
        sparse[i, indices] = fc[i, indices]
    norms = np.sqrt(np.einsum("ij,ij->i", sparse, sparse))
    require(np.all(norms > 0), "zero sparse profile")
    cosine = (sparse@sparse.T)/np.outer(norms, norms)
    w = 1-np.arccos(np.clip(cosine, -1, 1))/math.pi
    np.fill_diagonal(w, 1)
    w = np.triu(w)+np.triu(w, 1).T
    degree = w.sum(axis=1)
    anisotropic = w/np.sqrt(np.outer(degree, degree))
    d = anisotropic.sum(axis=1)
    k = anisotropic/np.sqrt(np.outer(d, d))
    stationary = np.sqrt(d/d.sum())
    return k, stationary, selected


def spectral(k, stationary):
    values, vectors = np.linalg.eigh((k+k.T)/2)
    values, vectors = values[::-1], vectors[:, ::-1]
    require(abs(values[0]-1) <= 1e-8, "stationary eigenvalue certificate")
    # For a simple stationary mode, full eigensolve and projected solve agree.
    # For a multiple stationary mode the entire leading nontrivial space is
    # unresolved; explicitly reconstruct stationary complement via SVD.
    if 1-values[1] <= GAP:
        _, _, right = np.linalg.svd(stationary[None, :], full_matrices=True)
        basis = right[1:].T
        values, reduced = np.linalg.eigh(basis.T@k@basis)
        values, vectors = values[::-1], basis@reduced[:, ::-1]
    else:
        require(abs(abs(vectors[:, 0]@stationary)-1) <= 1e-8, "stationary mode mismatch")
        values, vectors = values[1:], vectors[:, 1:]
    block = 1
    while block < len(values) and values[block-1]-values[block] <= GAP:
        block += 1
    return dict(values=values, vectors=vectors, block=block,
                stationary_gap=float(1-values[0]), principal_gap=float(values[0]-values[1]))


def network_range(spec, stationary, labels):
    if spec["stationary_gap"] <= GAP:
        return dict(status="stationary_mode_unresolved", lower=None, upper=None)
    b = spec["block"]
    g = spec["vectors"][:, :b]/stationary[:, None]
    g *= spec["values"][:b]/(1-spec["values"][:b])
    scale = np.max(np.abs(g), axis=0)
    g = g/np.where(scale > 0, scale, 1)
    g -= g.mean(axis=0)
    magnitude = np.max(np.abs(g), axis=0)
    keep = magnitude > 0
    if not keep.any():
        return dict(status="constant_coordinate", lower=None, upper=None)
    g = g[:, keep]/magnitude[keep]
    g /= np.linalg.norm(g, axis=0)
    # Right singular vectors whiten the Gram matrix, a separately composed
    # generalized Rayleigh-quotient solution (not the production left basis).
    _, singular, right = np.linalg.svd(g, full_matrices=False)
    rank = int(np.sum(singular > singular[0]*1e-10))
    z = (g@right[:rank].T)/singular[:rank]
    labels = np.asarray(labels)
    means = {name: z[labels == name].mean(axis=0) for name in ("Default", "Vis", "SomMot")}
    require(all(np.any(labels == name) for name in means), "missing endpoint network")
    a, b = means["Default"]-means["Vis"], means["Default"]-means["SomMot"]
    form = len(g)*(np.outer(a, b)+np.outer(b, a))/2
    eig = np.linalg.eigvalsh(form)
    return dict(status="defined", lower=float(eig[0]), upper=float(eig[-1]), rank=rank)


def transfer(axis, k, stationary, spec, discovery_gap):
    coefficient = float(np.dot(axis, stationary))
    perpendicular = axis-coefficient*stationary
    length = stable_norm(perpendicular)
    lead = float(spec["values"][0])
    spectral_mean = float((np.trace(k)-1)/(len(k)-1))
    out = dict(stationary_overlap_squared=coefficient**2, projected_norm=length,
               leading_eigenvalue=lead, nontrivial_spectral_mean=spectral_mean,
               heldout_leading_gap=spec["principal_gap"])
    reason = ("discovery_axis_unresolved" if discovery_gap <= GAP else
              "stationary_mode_unresolved" if spec["stationary_gap"] <= GAP else
              "stationary_projection_unresolved" if length <= 1e-12 else
              "leading_energy_unresolved" if lead <= GAP else None)
    if reason:
        return dict(out, status=reason, rayleigh=None, fraction=None, rayleigh_minus_spectral_mean=None)
    rayleigh = float(np.einsum("i,ij,j->", perpendicular, k, perpendicular)/(length*length))
    return dict(out, status="defined", rayleigh=rayleigh, fraction=rayleigh/lead,
                rayleigh_minus_spectral_mean=rayleigh-spectral_mean)
