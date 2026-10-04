"""Source-backed arithmetic/certificate comparison; authoring QA only."""
import math

import numpy as np


def require(value, message):
    if not value:
        raise ValueError(message)


def compare_report(expected, observed, envelope, path="report", diagnostics=None):
    diagnostics = {} if diagnostics is None else diagnostics
    if isinstance(expected, dict):
        require(isinstance(observed, dict) and set(observed) == set(expected), f"{path}: exact private QA field set")
        for key in expected:
            if key == "discovery_axis":
                # Verified against independent source operator, not sign-matched.
                require((expected[key] is None) == (observed[key] is None), f"{path}: axis null mismatch")
                continue
            compare_report(expected[key], observed[key], envelope, f"{path}.{key}", diagnostics)
    elif isinstance(expected, list):
        require(isinstance(observed, list) and len(observed) == len(expected), f"{path}: all fixed rows required")
        for i, (x, y) in enumerate(zip(expected, observed)):
            compare_report(x, y, envelope, f"{path}[{i}]", diagnostics)
    elif isinstance(expected, float):
        require(isinstance(observed, (int, float)) and not isinstance(observed, bool) and math.isfinite(observed),
                f"{path}: finite numerical value required")
        difference = abs(expected-observed)
        diagnostics["max_scalar_abs_difference"] = max(difference, diagnostics.get("max_scalar_abs_difference", 0))
        require(np.isclose(expected, observed, **envelope), f"{path}: numerical discrepancy {difference}")
    else:
        require(type(expected) is type(observed) and expected == observed, f"{path}: source-derived identity/status mismatch")
    return diagnostics


def certificate(k, stationary, values, basis, caps):
    require(basis.ndim == 2 and basis.shape[0] == len(k) and basis.shape[1] > 0, "leading basis shape")
    n = basis.shape[1]
    if n == 1:
        residual = float(np.max(np.linalg.norm(k@basis-basis*values[:n], axis=0)))
        ritz_error = abs(float(basis[:, 0]@k@basis[:, 0])-float(values[0]))
    else:
        restriction = basis.T@k@basis
        residual = float(np.max(np.linalg.norm(k@basis-basis@restriction, axis=0)))
        ritz = np.linalg.eigvalsh((restriction+restriction.T)/2)[::-1]
        ritz_error = float(np.max(np.abs(ritz-values[:n])))
    orthogonal = float(np.max(np.abs(basis.T@basis-np.eye(n))))
    stationary_dot = float(np.max(np.abs(stationary@basis)))
    require(residual <= caps["residual_l2"] and orthogonal <= caps["orthogonality"] and
            stationary_dot <= caps["stationary_dot"] and ritz_error <= caps["residual_l2"],
            "source-reconstructed spectral certificate failure")
    return {"residual_l2_max": residual, "orthogonality_max": orthogonal,
            "stationary_dot_max": stationary_dot, "ritz_spectrum_error": ritz_error}


def compare_arrays(expected, submitted, envelopes):
    require(set(expected) == set(submitted), "private QA array inventory mismatch")
    metrics, certificates = {}, {}
    for key, reference in expected.items():
        value = np.asarray(submitted[key])
        require(value.shape == reference.shape, f"{key}: shape mismatch")
        quantity = key.split(":")[-1]
        if quantity in {"active", "counts", "sparsity"}:
            require(np.array_equal(reference, value), f"{key}: source support/signed sparsity mismatch")
            continue
        if quantity == "leading_basis":
            continue
        category = {"raw": "raw_means", "clean": "cleaned_series", "fc": "FC",
                    "operator": "operator", "stationary": "operator",
                    "raw_sd": "scalar", "residual_norm": "scalar", "threshold": "scalar",
                    "eigenvalues": "operator"}[quantity]
        require(np.array_equal(np.isnan(reference), np.isnan(value)), f"{key}: fabricated null mask")
        mask = np.isfinite(reference)
        require(np.isfinite(value[mask]).all(), f"{key}: nonfinite receipt")
        diff = float(np.max(np.abs(reference[mask]-value[mask]))) if mask.any() else 0.
        metrics[quantity] = max(diff, metrics.get(quantity, 0))
        require(np.allclose(reference[mask], value[mask], **envelopes[category]), f"{key}: engineering envelope exceeded ({diff})")
    for key, reference in expected.items():
        if not key.endswith(":leading_basis"):
            continue
        prefix = key[:-len("leading_basis")]
        basis = np.asarray(submitted[key])
        # Expected basis width certifies completeness of the source-derived block;
        # residual+orthogonality, not matching its individual columns, grades it.
        certificates[prefix] = certificate(expected[prefix+"operator"], expected[prefix+"stationary"],
                                           expected[prefix+"eigenvalues"], basis, envelopes["spectral_certificate"])
    return {"max_abs_differences": metrics, "source_spectral_certificates": certificates}


def validate_fit_axis(fit, independent_arrays, caps):
    if fit["axis_status"] != "defined":
        require(fit["discovery_axis"] is None, "unresolved fit axis must be null")
        return None
    axis = np.asarray(fit["discovery_axis"], dtype=float)
    require(axis.shape == independent_arrays["discovery:stationary"].shape, "frozen axis shape")
    return certificate(independent_arrays["discovery:operator"], independent_arrays["discovery:stationary"],
                       independent_arrays["discovery:eigenvalues"], axis[:, None], caps)


def audit_accounting(report, independent_arrays, base, frozen=None):
    """Independently crosscheck shared orchestration's slots, nulls and means."""
    fit = report["schema_version"] == "gradient-phase2-fit-v1"
    people = base["cohort"]["discovery" if fit else "evaluation"]
    require([r["participant_id"] for r in report["people"]] == people, "fixed person slot inventory")
    require(report["n_expected"] == len(people), "expected denominator")
    support = (np.logical_and.reduce([independent_arrays[f"{p}:active"] for p in people]) if fit
               else np.asarray(frozen["frozen_support"], bool))
    require(np.array_equal(report["frozen_support"], support), "withheld-informed or fabricated support")
    values = []
    for row in report["people"]:
        sid = row["participant_id"]
        invalid = (np.flatnonzero(support & ~independent_arrays[f"{sid}:active"])+1).tolist()
        require(row["inactive_on_frozen_support"] == invalid, "invented or omitted source null")
        require(row["source_status"] == ("source_inactive" if invalid else "defined"), "source status")
        if invalid:
            require(not fit and row["transfer"] == {"status": "source_inactive", "fraction": None},
                    "invalid source must retain explicit null")
        if not fit and not invalid:
            if frozen["axis_status"] != "defined":
                require(row["transfer"] == {"status": "discovery_axis_unresolved", "fraction": None},
                        "discovery axis null must not invent test transfer")
            else:
                eigen = independent_arrays[f"{sid}:eigenvalues"]
                stationary = independent_arrays[f"{sid}:stationary"]
                axis = np.asarray(frozen["discovery_axis"])
                norm = np.linalg.norm(axis-stationary*np.dot(stationary, axis))
                status = ("stationary_mode_unresolved" if 1-eigen[0] <= 4e-8 else
                          "stationary_projection_unresolved" if norm <= 1e-12 else
                          "leading_energy_unresolved" if eigen[0] <= 4e-8 else "defined")
                require(row["transfer"]["status"] == status, "fabricated numerical null")
            if row["transfer"]["status"] == "defined":
                values.append(float(row["transfer"]["fraction"]))
    if fit:
        require([r["omitted_participant"] for r in report["leave_one_out"]] == people,
                "all ten discovery deletion diagnostics required")
    else:
        require(report["n_defined"] == len(values), "defined denominator")
        mean = math.fsum(values)/len(values) if values else None
        require(report["mean_fraction"] is None if mean is None else
                math.isclose(report["mean_fraction"], mean, rel_tol=1e-12, abs_tol=1e-12),
                "participant-weighted mean mismatch")
        require(report["minimum_fraction"] == (min(values) if values else None), "minimum")
        require(report["maximum_fraction"] == (max(values) if values else None), "maximum")
        loo = [(math.fsum(values)-v)/(len(values)-1) for v in values] if len(values)>1 else []
        require(report["leave_one_valid_person_mean_range"] is None if not loo else
                np.allclose(report["leave_one_valid_person_mean_range"], [min(loo), max(loo)], atol=1e-12, rtol=1e-12),
                "participant deletion summary mismatch")
    return {"fixed_slots": len(people), "source_nulls": sum(bool(r["inactive_on_frozen_support"]) for r in report["people"]),
            "summary_scope": "person-level descriptive; independent recount and arithmetic"}
