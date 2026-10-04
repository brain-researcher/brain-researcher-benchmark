"""Source-free contract prototype, not the MRI oracle or final verifier.

Scientific algebra only. Caller/harness must authenticate data, solve certified
operators, and enforce discovery-only file access. No function reads source data.
"""
from __future__ import annotations

import hashlib
import math
from collections import defaultdict

import numpy as np


def metadata_split(records, salt="GRADIENT-HELDOUT-v1"):
    """Deterministic age-paired split; outcome/FC/activity never enter the API."""
    strata = defaultdict(list)
    seen = set()
    for row in records:
        sid, group, age = row["participant_id"], row["child_adult"], row["age"]
        if not isinstance(sid, str) or not sid or sid in seen:
            raise ValueError("unique nonempty participant IDs required")
        if group not in {"child", "adult"} or not math.isfinite(float(age)):
            raise ValueError("finite age and explicit child/adult stratum required")
        seen.add(sid)
        strata[group].append((float(age), sid))
    if set(strata) != {"child", "adult"}:
        raise ValueError("both strata required")
    discovery, evaluation = [], []
    for group in sorted(strata):
        ordered = sorted(strata[group])
        if len(ordered) % 2:
            raise ValueError("predeclared paired design requires even strata")
        for left, right in zip(ordered[::2], ordered[1::2]):
            ids = [left[1], right[1]]
            token = "|".join((salt, group, *ids)).encode("utf-8")
            choose = hashlib.sha256(token).digest()[0] % 2
            discovery.append(ids[choose])
            evaluation.append(ids[1 - choose])
    return {"discovery": sorted(discovery), "evaluation": sorted(evaluation)}


def validate_partitions(split, expected_ids):
    expected = list(expected_ids)
    d, e = list(split["discovery"]), list(split["evaluation"])
    if len(set(expected)) != len(expected):
        raise ValueError("duplicate expected identity")
    if len(set(d)) != len(d) or len(set(e)) != len(e) or set(d) & set(e):
        raise ValueError("duplicate or overlapping partition")
    if not d or not e or set(d) | set(e) != set(expected):
        raise ValueError("partition must exactly cover fixed cohort")


def discovery_support(discovery_activity):
    """Only discovery masks accepted: no optional test mask to leak selection."""
    active = np.asarray(discovery_activity)
    if active.dtype != bool or active.ndim != 2 or not active.shape[0]:
        raise ValueError("nonempty Boolean person-by-parcel masks required")
    return active.all(axis=0)


def evaluation_eligibility(evaluation_activity, frozen_support):
    active, support = np.asarray(evaluation_activity), np.asarray(frozen_support)
    if active.dtype != bool or support.dtype != bool or active.ndim != 2:
        raise ValueError("Boolean masks required")
    if support.shape != (active.shape[1],) or not support.any():
        raise ValueError("nonempty matching frozen support required")
    return active[:, support].all(axis=1)


def transfer_score(discovery_axis, operator, stationary, leading_eigenvalue,
                   *, discovery_gap, stationary_gap, spectral_tol=4e-8,
                   norm_tol=1e-12):
    """Frozen-axis Rayleigh fraction. No test eigenvector/alignment argument.

    Gaps/lambda must ultimately come from independently certified operators;
    this prototype validates basic algebra, not eigenvalue provenance.
    """
    u, k, s = map(lambda x: np.asarray(x, dtype=float),
                  (discovery_axis, operator, stationary))
    if u.ndim != 1 or k.shape != (len(u), len(u)) or s.shape != u.shape:
        raise ValueError("dimension mismatch")
    if not all(np.isfinite(x).all() for x in (u, k, s)):
        raise ValueError("finite arrays required")
    if not all(math.isfinite(float(x)) for x in
               (leading_eigenvalue, discovery_gap, stationary_gap)):
        raise ValueError("finite certified spectrum required")
    if not np.allclose(k, k.T, atol=1e-10, rtol=0):
        raise ValueError("symmetric operator required")
    if not np.isclose(np.linalg.norm(u), 1, atol=1e-8, rtol=0):
        raise ValueError("unit frozen discovery axis required")
    if not np.isclose(np.linalg.norm(s), 1, atol=1e-8, rtol=0):
        raise ValueError("unit stationary vector required")
    if not np.allclose(k @ s, s, atol=1e-8, rtol=0):
        raise ValueError("stationary certificate invalid")
    if len(u) < 2:
        raise ValueError("at least two parcels required")
    overlap = float(s @ u)
    projected = u - s * overlap
    norm = float(np.linalg.norm(projected))
    nontrivial_mean = float((np.trace(k) - 1) / (len(u) - 1))
    base = {"stationary_overlap_squared": overlap**2, "projected_norm": norm,
            "leading_eigenvalue": float(leading_eigenvalue),
            "nontrivial_spectral_mean": nontrivial_mean}
    reason = None
    if discovery_gap <= spectral_tol:
        reason = "discovery_axis_unresolved"
    elif stationary_gap <= spectral_tol:
        reason = "stationary_mode_unresolved"
    elif norm <= norm_tol:
        reason = "stationary_projection_unresolved"
    elif leading_eigenvalue <= spectral_tol:
        reason = "leading_energy_unresolved"
    if reason:
        return dict(base, status=reason, rayleigh=None, fraction=None,
                    rayleigh_minus_spectral_mean=None)
    v = projected / norm
    rayleigh = float(v @ k @ v)
    if rayleigh > leading_eigenvalue + 1e-8:
        raise ValueError("Rayleigh quotient exceeds supplied leading eigenvalue")
    return dict(base, status="defined", rayleigh=rayleigh,
                rayleigh_minus_spectral_mean=rayleigh-nontrivial_mean,
                fraction=rayleigh / leading_eigenvalue)


def configuration_range(coordinate_basis, network_labels):
    """Exact C range over all nonconstant coordinates in a supplied span.

    Input columns are diffusion coordinates (eigenvectors divided by stationary
    vector), not raw symmetric-operator eigenvectors. Scale and well-resolved
    invertible basis changes do not alter the result. Range boundaries are
    descriptive, not confidence bounds or a parcel-randomization null.

    Normalize each finite column before centering, then equilibrate centered
    column norms before SVD. Discard exact-constant columns; numerical rank uses
    singular values > 1e-10 times the largest. Invariance requires the represented
    span remain resolved under that public criterion. No guarantee applies when
    a transform/offset loses signal in floating-point representation or makes a
    span unresolved. Such a span needs source/certificate adjudication, not
    scientific reinterpretation as a constant gradient.
    """
    g = np.asarray(coordinate_basis, dtype=float)
    labels = np.asarray(network_labels)
    if g.ndim == 1:
        g = g[:, None]
    if g.ndim != 2 or labels.shape != (g.shape[0],) or not np.isfinite(g).all():
        raise ValueError("finite parcel-by-component basis and labels required")
    n = g.shape[0]
    indicators = {}
    for label in ("Default", "Vis", "SomMot"):
        mask = labels == label
        if not mask.any():
            raise ValueError("all three endpoint networks must be represented")
        indicators[label] = mask.astype(float) / mask.sum()
    if g.shape[1] == 0:
        raise ValueError("at least one coordinate column required")
    column_scale = np.max(np.abs(g), axis=0)
    scaled = g / np.where(column_scale > 0, column_scale, 1)
    centered = scaled - scaled.mean(axis=0)
    centered_scale = np.max(np.abs(centered), axis=0)
    nonconstant = centered_scale > 0
    if not nonconstant.any():
        return {"status": "constant_coordinate", "lower": None, "upper": None}
    centered = centered[:, nonconstant] / centered_scale[nonconstant]
    centered /= np.linalg.norm(centered, axis=0)
    u, values, _ = np.linalg.svd(centered, full_matrices=False)
    rank = int(np.sum(values > values[0] * 1e-10))
    q = u[:, :rank]
    a = q.T @ (indicators["Default"] - indicators["Vis"])
    b = q.T @ (indicators["Default"] - indicators["SomMot"])
    form = n * (np.outer(a, b) + np.outer(b, a)) / 2
    endpoints = np.linalg.eigvalsh(form)
    return {"status": "defined", "lower": float(endpoints[0]),
            "upper": float(endpoints[-1]), "rank": rank}


def summarize_people(rows, expected_ids):
    """Descriptive person-level summary; no array of parcel observations."""
    expected = list(expected_ids)
    ids = [row["participant_id"] for row in rows]
    if len(set(expected)) != len(expected) or len(set(ids)) != len(ids):
        raise ValueError("duplicate participant")
    if set(ids) != set(expected):
        raise ValueError("missing or unexpected participant")
    values = []
    for row in rows:
        value = row["fraction"]
        if row["status"] == "defined":
            if value is None or isinstance(value, bool) or not math.isfinite(value):
                raise ValueError("defined score must be a finite number")
            values.append(float(value))
        elif value is not None or not row["status"]:
            raise ValueError("undefined score needs reason and null")
    out = {"n_expected": len(expected), "n_defined": len(values),
           "mean": None, "minimum": None, "maximum": None,
           "leave_one_valid_person_mean_range": None}
    if values:
        out.update(mean=math.fsum(values)/len(values), minimum=min(values),
                   maximum=max(values))
    if len(values) > 1:
        loo = [(math.fsum(values)-x)/(len(values)-1) for x in values]
        out["leave_one_valid_person_mean_range"] = [min(loo), max(loo)]
    return out
