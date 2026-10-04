"""Production numerical path. Authoring arrays are not agent deliverables."""
import math
import sys

import numpy as np
from scipy import linalg

sys.path.insert(0, "/legacy")
import core
import source_reader as reader
from protocol import configuration_range, transfer_score

GAP = 4e-8


def decode(raw, compressed, ndim):
    values, affine, metadata = reader.decode_image(raw, compressed, ndim)
    return values, affine, metadata


def extract(bold, affine, atlas, atlas_affine, parcel_ids):
    indices = reader.support(atlas, atlas_affine, bold.shape[:3], affine)
    indices = [indices[i-1] for i in parcel_ids]
    raw = np.full((bold.shape[-1], len(indices)), np.nan)
    for t in range(bold.shape[-1]):
        volume = bold[..., t].ravel(order="C")
        for p, idx in enumerate(indices):
            if len(idx):
                raw[t, p] = np.mean(np.ascontiguousarray(volume[idx]), dtype=np.float64)
    return raw, np.array([len(x) for x in indices], dtype=int)


def clean(raw, confounds, counts):
    geometry = counts > 0
    c = core.detrend(confounds)
    c -= c.mean(axis=0)
    sd = c.std(axis=0)
    sd[sd < core.EPS] = 1
    c /= sd
    q, r, _ = linalg.qr(c, mode="economic", pivoting=True)
    q = q[:, np.abs(np.diag(r)) > 100*core.EPS]
    y = core.detrend(raw[:, geometry])
    y -= q @ (q.T @ y)
    residual = np.full_like(raw, np.nan)
    residual[:, geometry] = y
    norms = np.full(raw.shape[1], np.nan)
    raw_sd = np.full(raw.shape[1], np.nan)
    threshold = np.full(raw.shape[1], np.nan)
    active = np.zeros(raw.shape[1], dtype=bool)
    for p in np.flatnonzero(geometry):
        raw_sd[p] = core.norm(core.centered(raw[:, p])) / math.sqrt(len(raw)-1)
        threshold[p] = 1e-12*math.sqrt(len(raw))*max(1, raw_sd[p])
        norms[p] = core.norm(core.centered(residual[:, p]))
        active[p] = norms[p] > threshold[p]
    return dict(clean=residual, active=active, counts=counts, raw_sd=raw_sd,
                residual_norm=norms, threshold=threshold, rank=q.shape[1])


def correlation(cleaned):
    fc = np.corrcoef(cleaned.T)
    return np.triu(fc, 1)+np.triu(fc, 1).T+np.eye(len(fc))


def operator(fc, parcel_ids):
    keep = math.ceil(.1*len(fc))
    chosen = np.zeros_like(fc, dtype=bool)
    for i in range(len(fc)):
        chosen[i, np.lexsort((parcel_ids, -fc[i]))[:keep]] = True
    k, stationary = core.operator(fc, parcel_ids, keep=keep)
    return k, stationary, chosen


def spectral(k, stationary):
    complement = linalg.qr(stationary[:, None], mode="full")[0][:, 1:]
    reduced = complement.T @ k @ complement
    reduced = np.triu(reduced)+np.triu(reduced, 1).T
    values, vectors = linalg.eigh(reduced, driver="evd")
    values, vectors = values[::-1], complement @ vectors[:, ::-1]
    block = 1
    while block < len(values) and values[block-1]-values[block] <= GAP:
        block += 1
    return dict(values=values, vectors=vectors, block=block,
                stationary_gap=float(1-values[0]), principal_gap=float(values[0]-values[1]))


def network_range(spec, stationary, labels):
    if spec["stationary_gap"] <= GAP:
        return dict(status="stationary_mode_unresolved", lower=None, upper=None)
    b = spec["block"]
    coordinate = spec["vectors"][:, :b] / stationary[:, None]
    coordinate *= spec["values"][:b] / (1-spec["values"][:b])
    return configuration_range(coordinate, labels)


def transfer(axis, k, stationary, spec, discovery_gap):
    value = transfer_score(axis, k, stationary, spec["values"][0],
                           discovery_gap=discovery_gap, stationary_gap=spec["stationary_gap"])
    value["heldout_leading_gap"] = spec["principal_gap"]
    return value
