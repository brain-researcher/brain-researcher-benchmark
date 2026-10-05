"""Linux verifier-only subprocess boundary; no candidate import in parent."""
import ctypes
import hashlib
import os
from pathlib import Path
import resource
import signal
import subprocess
import time
from grading import regular_bytes, require

UID = 61616


def owned_processes():
    found = []
    for item in Path("/proc").iterdir():
        if not item.name.isdigit():
            continue
        try:
            lines = (item/"status").read_text().splitlines()
            ids = next(s for s in lines if s.startswith("Uid:")).split()[1:]
            if str(UID) in ids:
                found.append(int(item.name))
        except (FileNotFoundError, ProcessLookupError):
            pass
    return found


def kill_owned():
    terminated = set()
    for _ in range(20):
        while True:
            try:
                pid, _ = os.waitpid(-1, os.WNOHANG)
            except ChildProcessError:
                break
            if pid == 0:
                break
        pids = owned_processes()
        if not pids:
            return sorted(terminated)
        for pid in pids:
            try:
                os.kill(pid, signal.SIGKILL)
                terminated.add(pid)
            except ProcessLookupError:
                pass
        time.sleep(.025)
    require(not owned_processes(), "candidate processes survived termination")


def confinement(root):
    os.setsid()
    os.chdir(root)
    os.chroot(".")
    os.chdir("/tmp")
    resource.setrlimit(resource.RLIMIT_CPU, (180, 180))
    resource.setrlimit(resource.RLIMIT_AS, (8*1024**3, 8*1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024**2, 1024**2))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    resource.setrlimit(resource.RLIMIT_NPROC, (16, 16))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    libc = ctypes.CDLL(None, use_errno=True)
    require(libc.prctl(38, 1, 0, 0, 0) == 0, "no_new_privs failed")
    os.setgroups([])
    os.setgid(UID)
    os.setuid(UID)
    require(os.getuid() == UID and os.geteuid() == UID, "UID drop failed")


def run_candidate(fit_raw, code_raw, root=Path("/sandbox"), logs=Path("/logs/verifier")):
    require(os.geteuid() == 0, "trusted sandbox launcher requires root")
    require(not owned_processes(), "candidate UID already in use")
    # Adopt and reap deliberately orphaned grandchildren; Docker PID1 may not
    # reap them, and a setsid() child must not survive merely by leaving a group.
    libc = ctypes.CDLL(None, use_errno=True)
    require(libc.prctl(36, 1, 0, 0, 0) == 0, "child subreaper setup failed")
    # Parent root owns all immutable paths. Only dedicated tmpfs scratch/output
    # are writable to the candidate. Root adapter certifies mounts and limits.
    for name, raw in (("discovery.json", fit_raw), ("evaluate.py", code_raw)):
        path = root/"input"/name
        require(not path.exists(), "sandbox input already exists")
        path.write_bytes(raw)
        path.chmod(0o444)
    before = hashlib.sha256(fit_raw).hexdigest()
    args = ["/usr/bin/python3", "-B", "/input/evaluate.py", "--data", "/data",
            "--fit", "/input/discovery.json", "--output", "/out/evaluation.json",
            "--contract", "/public/contract.json"]
    env = {"PATH": "/usr/bin:/bin", "HOME": "/tmp", "TMPDIR": "/tmp",
           "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1",
           "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
    start = time.monotonic()
    with (logs/"candidate-stdout.txt").open("wb") as stdout:
        child = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=stdout, stderr=subprocess.STDOUT,
            close_fds=True, env=env, preexec_fn=lambda: confinement(root))
        try:
            code = child.wait(timeout=180)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)
            raise ValueError("candidate wall timeout")
        finally:
            terminated = kill_owned()
    require(code == 0, f"candidate exit status {code}")
    require(hashlib.sha256(regular_bytes(root/"input/discovery.json")).hexdigest() == before, "frozen discovery modified")
    result = regular_bytes(root/"out/evaluation.json")
    return result, {"candidate_uid": UID, "exit_code": code, "wall_seconds": time.monotonic()-start,
        "fit_sha256": before, "program_sha256": hashlib.sha256(code_raw).hexdigest(),
        "all_candidate_processes_dead": not owned_processes(), "network": "outer container disabled",
        "terminated_descendant_pids": terminated,
        "boundary": "unprivileged chroot, no proc/dev/socket, immutable root-owned inputs"}
