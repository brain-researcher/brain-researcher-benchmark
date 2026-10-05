"""Trusted, bounded artifact validation; never executes or imports a submission."""
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import numpy as np

LIMIT = 1024 * 1024


def require(test, message):
    if not test:
        raise ValueError(message)


def regular_bytes(path, limit=LIMIT):
    path = Path(path)
    for p in [*reversed(path.parents), path]:
        require(not p.is_symlink(), "symlink path refused")
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= limit, "bounded regular artifact required")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        after = os.fstat(stream.fileno())
        signature = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
        require(signature(before) == signature(after), "artifact changed before read")
        raw = stream.read(limit + 1)
        require(len(raw) == before.st_size and signature(before) == signature(os.fstat(stream.fileno())), "artifact changed during read")
    require(signature(before) == signature(path.lstat()), "artifact replaced after read")
    return raw


def strict_json(raw):
    def pairs(items):
        out = {}
        for k, v in items:
            require(k not in out, "duplicate JSON key")
            out[k] = v
        return out
    def bad(_):
        raise ValueError("nonfinite JSON")
    data = json.loads(raw, object_pairs_hook=pairs, parse_constant=bad)
    def walk(value, depth=0):
        require(depth <= 30, "JSON nesting limit")
        if isinstance(value, float):
            require(math.isfinite(value), "nonfinite JSON number")
        if isinstance(value, (dict, list)):
            for child in value.values() if isinstance(value, dict) else value:
                walk(child, depth+1)
    walk(data)
    return data


def compare(expected, submitted, path="answer"):
    if isinstance(expected, dict):
        require(isinstance(submitted, dict) and expected.keys() <= submitted.keys(), f"{path}: missing keys")
        # Person/deletion dictionaries are closed inventories, unlike harmless extra metadata.
        if path.endswith("people") or path.endswith("leave_one_out"):
            require(expected.keys() == submitted.keys(), f"{path}: participant inventory")
        for key, value in expected.items():
            compare(value, submitted[key], f"{path}.{key}")
    elif isinstance(expected, list):
        require(isinstance(submitted, list) and len(expected) == len(submitted), f"{path}: list dimensions")
        for i, (e, s) in enumerate(zip(expected, submitted)):
            compare(e, s, f"{path}[{i}]")
    elif type(expected) is float:
        require(type(submitted) in (float, int) and math.isfinite(submitted), f"{path}: finite number")
        require(abs(expected-submitted) <= 1e-6+1e-6*abs(expected), f"{path}: numerical disagreement")
    else:
        require(type(expected) is type(submitted) and expected == submitted, f"{path}: categorical/integer disagreement")


def validate_discovery(submitted, expected, arrays):
    require(isinstance(submitted, dict), "discovery JSON object required")
    reference = copy.deepcopy(expected)
    reference.pop("axis")
    compare(reference, submitted, "discovery")
    if expected["axis_status"] != "defined":
        require(submitted["axis"] is None, "undefined discovery axis must be null")
        return
    value = submitted.get("axis")
    require(isinstance(value, list) and all(type(x) in (int, float) for x in value), "numeric axis required")
    axis = np.asarray(value, dtype=float)
    k, stationary = arrays["discovery:operator"], arrays["discovery:stationary"]
    lead = float(arrays["discovery:eigenvalues"][0])
    require(axis.shape == (len(expected["support"]),) and np.isfinite(axis).all(), "axis dimensions/finiteness")
    require(abs(axis @ axis-1) <= 1e-7, "axis unit norm")
    require(abs(axis @ stationary) <= 1e-8, "axis stationary separation")
    require(np.linalg.norm(k @ axis-lead*axis) <= 1e-8, "axis source eigen-residual")


def evaluation_reference(reference, fit, arrays):
    """Recompute transfer on accepted axis, not a canonical orientation fingerprint."""
    result = copy.deepcopy(reference)
    axis = np.asarray(fit["axis"], dtype=float) if fit["axis_status"] == "defined" else None
    for pid, row in result["people"].items():
        if row["source_status"] != "defined":
            continue
        if axis is None:
            row["transfer"] = {"status": "discovery_axis_unresolved", "fraction": None}
            continue
        k, stationary = arrays[pid+":operator"], arrays[pid+":stationary"]
        values = arrays[pid+":eigenvalues"]
        coefficient = float(axis @ stationary)
        projected = axis-coefficient*stationary
        norm = float(np.linalg.norm(projected))
        lead, gap = float(values[0]), float(values[0]-values[1])
        mean = float((np.trace(k)-1)/(len(k)-1))
        out = dict(stationary_overlap_squared=coefficient**2, projected_norm=norm,
                   leading_eigenvalue=lead, nontrivial_spectral_mean=mean,
                   heldout_leading_gap=gap)
        reason = ("stationary_mode_unresolved" if 1-lead <= 4e-8 else
                  "stationary_projection_unresolved" if norm <= 1e-12 else
                  "leading_energy_unresolved" if lead <= 4e-8 else None)
        if reason:
            out.update(status=reason, fraction=None, rayleigh=None, rayleigh_minus_spectral_mean=None)
        else:
            rayleigh = float(projected @ k @ projected/(norm*norm))
            out.update(status="defined", rayleigh=rayleigh, fraction=rayleigh/lead,
                       rayleigh_minus_spectral_mean=rayleigh-mean)
        row["transfer"] = out
    scores = [row["transfer"]["fraction"] for row in result["people"].values()
              if row["transfer"]["status"] == "defined"]
    n = len(scores)
    means = [(math.fsum(scores)-v)/(n-1) for v in scores] if n > 1 else []
    result["summary"] = dict(n_expected=len(result["people"]), n_defined=n,
        mean_fraction=math.fsum(scores)/n if n else None,
        minimum_fraction=min(scores) if n else None, maximum_fraction=max(scores) if n else None,
        leave_one_valid_person_mean_range=[min(means), max(means)] if means else None)
    return result


def authenticate_capsule(root, manifest, ids):
    root = Path(root)
    expected = {r["path"]: r for r in manifest["files"]
                if r.get("participant_id") is None or r["participant_id"] in ids}
    members = list(root.rglob("*"))
    for p in members:
        require(not p.is_symlink(), "symlink in source capsule")
    observed = {p.relative_to(root).as_posix() for p in members if not p.is_dir()}
    require(observed == set(expected) | {"source_manifest.json"}, "capsule exact inventory")
    for name, row in expected.items():
        raw = regular_bytes(root/name, row["size_bytes"])
        require(len(raw) == row["size_bytes"] and hashlib.sha256(raw).hexdigest() == row["sha256"], "source authentication")
