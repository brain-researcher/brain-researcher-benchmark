"""Source-free engineering prototype: validate model-conditioned FA witnesses.

This is not a Harbor grader, optimizer, uncertainty estimator, or source reader.
The caller must authenticate observations/protocol/domain/budgets independently.
Manufactured tests establish arithmetic behavior, not real-data validity.
"""

from dataclasses import dataclass
from numbers import Real
from typing import Mapping

import numpy as np


class EvidenceError(ValueError):
    """A proposed numerical certificate violates its public contract."""


def _number(value, name):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise EvidenceError(f"{name} must be a real number, not boolean/string")
    value = float(value)
    if not np.isfinite(value):
        raise EvidenceError(f"{name} must be finite")
    return value


def _array(values, shape, name):
    raw = np.asarray(values)
    if raw.dtype.kind not in "iuf" or raw.shape != shape:
        raise EvidenceError(f"{name} must have numeric shape {shape}")
    values = np.asarray(values, dtype=np.float64)
    if not np.all(np.isfinite(values)):
        raise EvidenceError(f"{name} must be finite")
    return values


@dataclass(frozen=True)
class Domain:
    """Explicit caller-supplied bounds; these are not calibrated defaults."""

    eigenvalue_min: float
    eigenvalue_max: float
    s0_ratio_min: float
    s0_ratio_max: float
    fraction_min: float
    fraction_max: float
    eigenvalue_arithmetic_atol: float
    eigenvalue_arithmetic_rtol: float
    gradient_norm_atol: float

    def __post_init__(self):
        values = {name: _number(value, name) for name, value in vars(self).items()}
        if not 0 <= values["eigenvalue_min"] < values["eigenvalue_max"]:
            raise EvidenceError("invalid eigenvalue bounds")
        if not 0 < values["s0_ratio_min"] < values["s0_ratio_max"]:
            raise EvidenceError("invalid S0 ratio bounds")
        if not 0 <= values["fraction_min"] < values["fraction_max"] < 1:
            raise EvidenceError("fraction bounds must exclude absent tissue f=1")
        if values["eigenvalue_arithmetic_atol"] < 0 or values["gradient_norm_atol"] < 0:
            raise EvidenceError("public arithmetic tolerances must be nonnegative")
        if not 0 <= values["eigenvalue_arithmetic_rtol"] < 1:
            raise EvidenceError("relative eigenvalue roundoff cap must be in [0,1)")


def require_release_contract(contract):
    """Fail closed; schema completeness is necessary, not scientific approval."""
    if contract.get("status") != "qualified_release" or contract.get("runnable") is not True:
        raise EvidenceError("design is not a qualified runnable release")
    required = {
        "discrepancy": ("public_loss_ceilings_artifact", "public_budgets", "calibration_rule"),
        "parameter_domain": ("tensor_eigenvalue_bounds_mm2_per_s", "S0_over_observed_b0_bounds", "f_bounds", "eigenvalue_arithmetic_atol", "eigenvalue_arithmetic_rtol", "gradient_norm_atol"),
        "search_requirements": ("public_fraction_profile_grid", "fit_quality_ceilings", "profile_quality_ceilings", "required_profile_coverage", "minimum_witness_fa_separation", "witness_completeness_rule"),
        "scoring": ("public_component_weights",),
    }
    for section, keys in required.items():
        for key in keys:
            if contract.get(section, {}).get(key) is None:
                raise EvidenceError(f"unresolved release field: {section}.{key}")
    if contract.get("release_blockers") != []:
        raise EvidenceError("unresolved release blockers")


def _protocol(bvals, bvecs, norm_atol):
    raw = np.asarray(bvals)
    if raw.ndim != 1 or len(raw) < 2:
        raise EvidenceError("b-values require a nonempty acquisition")
    b = _array(bvals, raw.shape, "bvals")
    g = _array(bvecs, (len(b), 3), "bvecs")
    if np.any(b < 0) or not np.any(b == 0) or not np.any(b > 0):
        raise EvidenceError("protocol requires nonnegative b, a b0 and diffusion observations")
    if not np.allclose(np.linalg.norm(g[b > 0], axis=1), 1.0, atol=norm_atol, rtol=0):
        raise EvidenceError("gradient norm outside public arithmetic tolerance")
    # Preserve released rounded vectors exactly; never silently normalize.
    return b, g


def candidate_metrics(observed, bvals, bvecs, params: Mapping, domain: Domain):
    """Recompute predictions, discrepancy and FA without clipping or refitting.

    Uses the sole observed b0 for normalization. This restriction corresponds
    to the source acquisition; extra b0 images would require a revised contract.
    Parameter order: Dxx,Dxy,Dyy,Dxz,Dyz,Dzz. S0 and f are scalars.
    """
    b, g = _protocol(bvals, bvecs, domain.gradient_norm_atol)
    if np.count_nonzero(b == 0) != 1:
        raise EvidenceError("this prototype requires exactly one b0")
    y = _array(observed, b.shape, "observed signal")
    if np.any(y < 0):
        raise EvidenceError("magnitude observations cannot be negative")
    scale = float(y[b == 0][0])
    if scale <= 0:
        raise EvidenceError("b0 normalization must be positive")
    try:
        d = _array(params["D"], (6,), "D coefficients")
        s0 = _number(params["S0"], "S0")
        f = _number(params["f"], "f")
    except KeyError as exc:
        raise EvidenceError(f"missing parameter {exc.args[0]}") from exc
    D = np.array([[d[0], d[1], d[3]], [d[1], d[2], d[4]], [d[3], d[4], d[5]]])
    eigenvalues = np.linalg.eigvalsh(D)
    # Arithmetic tolerance is explicit, caller supplied and release-blocking
    # until qualified. No eigenvalue clipping or hidden tensor repair occurs.
    # An absolute tolerance alone would admit materially indefinite tiny tensors.
    # Bound it by tensor-relative roundoff at every tensor scale.
    eigenvalue_scale = float(np.max(np.abs(eigenvalues)))
    if eigenvalue_scale == 0:
        raise EvidenceError("zero tensor has undefined tissue FA")
    eig_atol = min(domain.eigenvalue_arithmetic_atol,
                   domain.eigenvalue_arithmetic_rtol * eigenvalue_scale)
    if np.any(eigenvalues < domain.eigenvalue_min - eig_atol) or np.any(eigenvalues > domain.eigenvalue_max + eig_atol):
        raise EvidenceError("tensor eigenvalues outside public domain")
    if not domain.s0_ratio_min <= s0 / scale <= domain.s0_ratio_max:
        raise EvidenceError("S0 outside public normalized domain")
    if not domain.fraction_min <= f <= domain.fraction_max:
        raise EvidenceError("fraction outside public domain")
    tissue = np.exp(-b * np.einsum("ni,ij,nj->n", g, D, g))
    prediction = s0 * ((1 - f) * tissue + f * np.exp(-b * 0.003))
    loss = float(np.mean(((prediction - y) / scale) ** 2))
    scaled_eigenvalues = eigenvalues / eigenvalue_scale
    fa = float(np.sqrt(1.5 * np.sum((scaled_eigenvalues - np.mean(scaled_eigenvalues)) ** 2) / np.sum(scaled_eigenvalues ** 2)))
    if not np.isfinite(loss) or not np.isfinite(fa):
        raise EvidenceError("nonfinite reconstructed metrics")
    return {"prediction": prediction, "loss": loss, "fa": fa,
            "minimum_raw_eigenvalue": float(eigenvalues.min()),
            "effective_eigenvalue_arithmetic_atol": eig_atol}


def validate_witness(observed, bvals, bvecs, left, right, domain, *, loss_ceiling, minimum_fa_gap):
    """Accept only two domain-valid candidates meeting a trusted public budget.

    A positive gap certifies a lower bound on an operational admissible-set
    range. It is not statistical indistinguishability or global nonuniqueness.
    Neither budget may be taken from the participant's self-reported output.
    """
    ceiling = _number(loss_ceiling, "loss_ceiling")
    gap_min = _number(minimum_fa_gap, "minimum_fa_gap")
    if ceiling < 0 or not 0 < gap_min <= 1:
        raise EvidenceError("invalid public loss ceiling or FA gap")
    a = candidate_metrics(observed, bvals, bvecs, left, domain)
    z = candidate_metrics(observed, bvals, bvecs, right, domain)
    if a["loss"] > ceiling or z["loss"] > ceiling:
        raise EvidenceError("candidate does not explain observations within public budget")
    gap = abs(a["fa"] - z["fa"])
    if gap < gap_min:
        raise EvidenceError("pair does not demonstrate the required FA separation")
    return {
        "status": "witness_found",
        "fa_separation_lower_bound": gap,
        "left_loss": a["loss"],
        "right_loss": z["loss"],
        "left_fa": a["fa"],
        "right_fa": z["fa"],
        "interpretation": "model_and_budget_conditioned_lower_bound",
    }
