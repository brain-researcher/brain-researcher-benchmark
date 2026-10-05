"""Bounded cleanup of one authenticated release job; no command runs on import.

Callers must persist the returned receipt, including refusal/error receipts.
Only exact Compose projects derived from authenticated immediate trial folders
are eligible. No image deletion, filesystem deletion, wildcard removal or prune.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess

ROOT = Path(__file__).resolve().parent
JOBS = ROOT / "jobs"
TASK = ROOT / "GRADIENT-HELDOUT-001"
LABEL = "com.docker.compose.project"
TRIAL = re.compile(r"GRADIENT-HELDOUT-001__[A-Za-z0-9_-]{1,32}\Z")
IDENTITY = re.compile(r"[0-9a-f]{64}\Z")
SERVICES = {"main", "harbor-docker-egress-control-sidecar"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_job_root(path):
    path = Path(path)
    require(path.is_absolute(), "absolute job root required")
    require(".." not in path.parts, "parent traversal refused")
    for part in (*reversed(path.parents), path):
        require(not part.is_symlink(), "symlink in job root")
    resolved = path.resolve()
    require(resolved.parent == JOBS.resolve(), "job root must be an immediate child of this release's jobs")
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", resolved.name), "unsafe job name")
    return resolved


def projects_for_trial(name):
    require(TRIAL.fullmatch(name), "unexpected release trial name")
    raw = name + "__verifier__trial"
    # Exact installed Harbor 0.17.1 _separate_verifier_session_id behavior.
    if len(raw) > 63:
        suffix = "__" + hashlib.sha1(raw.encode()).hexdigest()[:8]
        raw = raw[:63-len(suffix)].rstrip("-._") + suffix
    return [(name + "__env").lower(), raw.lower()]


def authenticate_trials(job):
    if not job.exists():
        return []
    require(job.is_dir(), "job is not a directory")
    projects = []
    for folder in sorted(job.iterdir()):
        if not folder.name.startswith("GRADIENT-HELDOUT-001__"):
            continue
        require(TRIAL.fullmatch(folder.name) and folder.is_dir() and not folder.is_symlink(), "unsafe trial folder")
        config = folder / "config.json"
        require(config.is_file() and not config.is_symlink() and config.stat().st_size <= 1024**2,
                "missing bounded regular trial config")
        value = json.loads(config.read_text())
        require(value.get("trial_name") == folder.name, "trial identity mismatch")
        require(Path(value["trials_dir"]).resolve() == job, "trial job-root mismatch")
        require(Path(value["task"]["path"]).resolve() == TASK.resolve(), "trial task mismatch")
        require(value.get("environment", {}).get("import_path") == "release_environment:ReleaseDocker",
                "trial is not owned by release adapter")
        projects.extend(projects_for_trial(folder.name))
    require(len(projects) == len(set(projects)), "ambiguous duplicate Compose project")
    return projects


def docker(args):
    return subprocess.run(["docker", *args], check=True, capture_output=True, text=True, timeout=20).stdout


def listed_ids(raw):
    values = raw.split()
    require(len(values) == len(set(values)) and all(IDENTITY.fullmatch(v) for v in values),
            "Docker query returned malformed/duplicate IDs")
    return values


def inspected(raw, expected):
    rows = json.loads(raw)
    require(isinstance(rows, list) and len(rows) == 1 and rows[0].get("Id") == expected,
            "Docker inspect identity mismatch")
    return rows[0]


def cleanup_job(job_root):
    """Return a terminal receipt even on refusal; caller persists it explicitly."""
    receipt = {"requested_job_root": str(job_root), "projects": [], "removed_containers": [],
               "removed_networks": [], "errors": [], "scope": "exact owned ephemeral Compose resources only"}
    try:
        job = safe_job_root(job_root)
        receipt["job_root"] = str(job)
        projects = authenticate_trials(job)
        receipt["projects"] = projects
        # Resolve and authenticate the complete allowlist before any mutation.
        containers, networks = [], []
        for project in projects:
            for identity in listed_ids(docker(["ps", "-aq", "--no-trunc", "--filter", "label=" + LABEL + "=" + project])):
                info = inspected(docker(["inspect", identity]), identity)
                labels = info.get("Config", {}).get("Labels") or {}
                require(labels.get(LABEL) == project, "container project-label mismatch")
                require(labels.get("com.docker.compose.service") in SERVICES, "unexpected project service")
                containers.append((identity, project))
            for identity in listed_ids(docker(["network", "ls", "-q", "--no-trunc", "--filter", "label=" + LABEL + "=" + project])):
                info = inspected(docker(["network", "inspect", identity]), identity)
                require((info.get("Labels") or {}).get(LABEL) == project, "network project-label mismatch")
                networks.append((identity, project, set((info.get("Containers") or {}).keys())))
        allowed_containers = {identity for identity, _ in containers}
        require(len(allowed_containers) == len(containers), "duplicate container ownership")
        for _, _, attached in networks:
            require(attached <= allowed_containers, "network has a non-owned attachment; no detach allowed")
        for identity, project in containers:
            # IDs are immutable; recheck the exact ownership immediately before rm.
            info = inspected(docker(["inspect", identity]), identity)
            require((info.get("Config", {}).get("Labels") or {}).get(LABEL) == project,
                    "container ownership changed")
            docker(["rm", "-f", identity])
            receipt["removed_containers"].append({"id": identity, "project": project})
        for identity, project, _ in networks:
            info = inspected(docker(["network", "inspect", identity]), identity)
            require((info.get("Labels") or {}).get(LABEL) == project, "network ownership changed")
            require(not info.get("Containers"), "network still has attachments; no force detach")
            docker(["network", "rm", identity])
            receipt["removed_networks"].append({"id": identity, "project": project})
        for project in projects:
            require(not listed_ids(docker(["ps", "-aq", "--no-trunc", "--filter", "label=" + LABEL + "=" + project])),
                    "owned containers remain")
            require(not listed_ids(docker(["network", "ls", "-q", "--no-trunc", "--filter", "label=" + LABEL + "=" + project])),
                    "owned networks remain")
        receipt["status"] = "cleaned" if projects else "no_authenticated_trials"
    except Exception as exc:
        receipt["status"] = "refused_or_failed"
        receipt["errors"].append({"type": type(exc).__name__, "message": str(exc)})
    return receipt


def terminate_process(child):
    """Escalate only a caller-owned fresh session: INT30s -> TERM15s -> KILL5s.

    The caller must create the child with start_new_session=True and retain its
    Popen instance. Even if Harbor exits promptly, call cleanup_job afterwards.
    """
    receipt = {"pid": child.pid, "signals": [], "errors": []}
    try:
        if child.poll() is not None:
            receipt.update(status="already_exited", returncode=child.returncode)
            return receipt
        require(child.pid > 1 and child.pid != os.getpid(), "unsafe child PID")
        require(os.getpgid(child.pid) == child.pid and os.getsid(child.pid) == child.pid,
                "child is not an isolated process-group/session leader")
        for sig, budget in ((signal.SIGINT, 30), (signal.SIGTERM, 15), (signal.SIGKILL, 5)):
            if child.poll() is not None:
                break
            try:
                os.killpg(child.pid, sig)
            except ProcessLookupError:
                pass
            receipt["signals"].append({"signal": sig.name, "wait_seconds": budget})
            try:
                child.wait(timeout=budget)
                break
            except subprocess.TimeoutExpired:
                continue
        require(child.poll() is not None, "process survived SIGKILL deadline")
        receipt.update(status="terminated", returncode=child.returncode)
    except Exception as exc:
        receipt["status"] = "refused_or_failed"
        receipt["errors"].append({"type": type(exc).__name__, "message": str(exc)})
    return receipt
