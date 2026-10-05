"""Offline Harbor 0.17.1 control: copy two authenticated fixtures, never solve.

Use import path ``fixture_agent:FixtureAgent`` with this directory on PYTHONPATH.
Agent kwargs require an absolute ``fixture_dir`` and ``expected_sha256`` mapping
with exactly ``discovery.json`` and ``evaluate.py``. There is no import/setup I/O
from this module; construction only authenticates bounded files into memory.
Only run() stages/uploads bytes. The evaluator is never imported or executed.
"""
from importlib.metadata import version as distribution_version
import hashlib
import os
from pathlib import Path
import re
import stat
import tempfile
from collections.abc import Mapping

from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext


FILENAMES = ("discovery.json", "evaluate.py")
MAX_FILE_BYTES = 1024 * 1024
AGENT_VERSION = "1.0.0"
HARBOR_VERSION = "0.17.1"
PREPARE_COMMAND = (
    "test ! -L /submission && mkdir -p /submission && test -d /submission"
    " && test ! -e /submission/discovery.json && test ! -L /submission/discovery.json"
    " && test ! -e /submission/evaluate.py && test ! -L /submission/evaluate.py"
)
VERIFY_COMMAND = (
    "test ! -L /submission && test -d /submission"
    " && test -f /submission/discovery.json && test ! -L /submission/discovery.json"
    " && test -f /submission/evaluate.py && test ! -L /submission/evaluate.py"
    " && sha256sum /submission/discovery.json /submission/evaluate.py"
)


def _read_frozen_files(fixture_dir, expected_sha256):
    if not isinstance(expected_sha256, Mapping) or set(expected_sha256) != set(FILENAMES):
        raise ValueError("SHA256 pins must name exactly discovery.json and evaluate.py")
    pins = dict(expected_sha256)
    if any(not isinstance(value,str) or re.fullmatch(r"[0-9a-f]{64}",value) is None for value in pins.values()):
        raise ValueError("SHA256 pins must be lowercase 64-character hexadecimal strings")
    directory = Path(fixture_dir)
    if not directory.is_absolute() or ".." in directory.parts:
        raise ValueError("fixture_dir must be absolute without parent traversal")
    # Open every directory component without following a symlink. Do not resolve
    # the path first, which would hide symlink traversal from the checks.
    fd = os.open("/",os.O_RDONLY | os.O_DIRECTORY)
    payloads = []
    try:
        for part in directory.parts[1:]:
            next_fd = os.open(part,os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,dir_fd=fd)
            os.close(fd); fd = next_fd
        for name in FILENAMES:
            file_fd = os.open(name,os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,dir_fd=fd)
            try:
                before = os.fstat(file_fd)
                if not stat.S_ISREG(before.st_mode) or not 0 <= before.st_size <= MAX_FILE_BYTES:
                    raise ValueError("fixture must be a regular file no larger than 1 MiB: "+name)
                chunks = []; remaining = MAX_FILE_BYTES+1
                while remaining:
                    chunk = os.read(file_fd,min(65536,remaining))
                    if not chunk: break
                    chunks.append(chunk); remaining -= len(chunk)
                payload = b"".join(chunks)
                after = os.fstat(file_fd)
                fields = ("st_dev","st_ino","st_size","st_mtime_ns","st_ctime_ns")
                if len(payload) != before.st_size or len(payload) > MAX_FILE_BYTES or any(getattr(before,k) != getattr(after,k) for k in fields):
                    raise ValueError("fixture changed during bounded read: "+name)
                if hashlib.sha256(payload).hexdigest() != pins[name]:
                    raise ValueError("fixture SHA256 mismatch: "+name)
                payloads.append((name,payload,pins[name]))
            finally:
                os.close(file_fd)
    finally:
        os.close(fd)
    return tuple(payloads)


class FixtureAgent(BaseAgent):
    """Native lifecycle control, not a model or an alternative reference solver."""

    @staticmethod
    def name() -> str:
        return "frozen-fixture-control"

    def version(self) -> str:
        return AGENT_VERSION

    def __init__(self, logs_dir: Path, fixture_dir: str | Path,
                 expected_sha256: Mapping[str,str], model_name: str | None = None,
                 **kwargs):
        if distribution_version("harbor") != HARBOR_VERSION:
            raise RuntimeError("this control was reviewed only for Harbor "+HARBOR_VERSION)
        payloads = _read_frozen_files(fixture_dir,expected_sha256)
        # Deliberately discard model_name: no provider, credentials, or model
        # process participates in fixture controls.
        super().__init__(logs_dir=logs_dir,model_name=None,**kwargs)
        self._payloads = payloads

    async def setup(self, environment: BaseEnvironment) -> None:
        return

    async def run(self, instruction: str, environment: BaseEnvironment,
                  context: AgentContext) -> None:
        context.n_input_tokens = 0
        context.n_cache_tokens = 0
        context.n_output_tokens = 0
        context.cost_usd = 0.0
        receipt = {"agent_version":AGENT_VERSION,"harbor_version":HARBOR_VERSION,
            "status":"preparing","analysis_executed":False,"model_used":False,
            "sha256":{name:digest for name,_,digest in self._payloads},
            "bytes":{name:len(payload) for name,payload,_ in self._payloads}}
        context.metadata = {**(context.metadata or {}),"fixture_control":receipt}
        try:
            prepared = await environment.exec(command=PREPARE_COMMAND,timeout_sec=10)
            if prepared.return_code != 0:
                raise RuntimeError("unsafe or nonempty fixture destination; refusing overwrite")
            # Authenticated immutable snapshots prevent source-file mutation
            # between construction and upload from changing submitted bytes.
            with tempfile.TemporaryDirectory(prefix="br-harbor-fixture-") as staging:
                for name,payload,_ in self._payloads:
                    path = Path(staging)/name
                    with path.open("xb") as stream:
                        stream.write(payload)
                    await environment.upload_file(source_path=path,target_path="/submission/"+name)
            checked = await environment.exec(command=VERIFY_COMMAND,timeout_sec=10)
            if checked.return_code != 0:
                raise RuntimeError("uploaded fixture regular-file/hash verification failed")
            observed = {}
            for line in checked.stdout.splitlines():
                fields = line.split()
                if len(fields) != 2 or fields[1] in observed:
                    raise RuntimeError("unexpected destination SHA256 receipt")
                observed[fields[1]] = fields[0]
            expected = {"/submission/"+name:digest for name,_,digest in self._payloads}
            if observed != expected:
                raise RuntimeError("destination SHA256 differs from frozen fixture")
            receipt["status"] = "uploaded_and_verified"
        except BaseException as exc:
            receipt["status"] = "failed"
            receipt["error_type"] = type(exc).__name__
            raise
        finally:
            context.metadata = {**(context.metadata or {}),"fixture_control":receipt}
