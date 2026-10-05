"""Pinned, separate-aware Harbor adapter. Importing this never starts a job.

The trusted host requires agent teardown before making the held-out verifier
available. Submission bytes are checked before native Harbor artifact upload.
No task/grading/model algorithm is changed here.
"""
import asyncio
import hashlib
import importlib.metadata
import json
from pathlib import Path
import re
import subprocess
import sys

PREVIOUS = Path('/home/zijiaochen/projects/brain_researcher_benchmark/tracking/sol61_max_2026-10-03')
sys.path.insert(0, str(PREVIOUS))
from network_hardening import HardenedNetwork
from harbor.environments.docker.docker import DockerEnvironment
from harbor.models.task.config import NetworkMode

STATE = {}
HERE = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'pin is not a regular file')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def authenticate(path):
    data = json.loads(Path(path).read_text())
    require(data.get('approved') is True, 'release execution has not been approved')
    require(importlib.metadata.version('harbor') == '0.17.1', 'unreviewed Harbor version')
    for name, expected in data['runtime_sha256'].items():
        require(digest(name) == expected, 'runtime pin changed: '+name)
    for relative, expected in data['task_sha256'].items():
        target = Path(data['task_path']) / relative
        require(target.resolve().is_relative_to(Path(data['task_path']).resolve()), 'task path escapes root')
        require(digest(target) == expected, 'task file changed: '+relative)
    return data


def project_name(session_id):
    name = session_id.lower()
    if not re.match(r'^[a-z0-9]', name):
        name = '0'+name
    return re.sub(r'[^a-z0-9_-]', '-', name)


def docker_metadata(argv):
    return subprocess.run(['docker', *argv], check=True, capture_output=True,
                          text=True, timeout=20).stdout.strip()


def require_stopped(project):
    require(not docker_metadata(['ps', '-q', '--filter',
                                 'label=com.docker.compose.project='+project]),
            'agent project still has a running container')


def authenticate_capture(root, limit=8*1024*1024):
    """Reject symlinks/devices before any host -> verifier file transfer."""
    root = Path(root)
    require(root.is_dir() and not root.is_symlink(), 'missing safe artifact root')
    total = 0
    for path in root.rglob('*'):
        require(not path.is_symlink(), 'symlink in captured artifacts')
        require(path.is_file() or path.is_dir(), 'special captured file')
        if path.is_file():
            total += path.stat().st_size
            require(total <= limit, 'captured artifacts exceed 8 MiB')
    return {str(p.relative_to(root)): digest(p) for p in sorted(root.rglob('*')) if p.is_file()}


class ReleaseDocker(HardenedNetwork, DockerEnvironment):
    @property
    def _docker_compose_paths(self):
        paths = (super()._docker_compose_paths if self._enable_egress_control else
                 DockerEnvironment._docker_compose_paths.fget(self))
        return [*paths, HERE/('release_'+self._role+'.compose.json')]

    def __init__(self, environment_dir, environment_name, session_id, trial_paths,
                 task_env_config, *, release_approval, **kwargs):
        self._approval_path = Path(release_approval)
        self._release = authenticate(self._approval_path)
        root = Path(self._release['task_path']).resolve()
        directory = Path(environment_dir).resolve()
        require(directory in (root/'environment', root/'tests'), 'unapproved build context')
        self._role = 'agent' if directory == root/'environment' else 'verifier'
        require(not (directory/'docker-compose.yaml').exists(), 'task compose override forbidden')
        require(not kwargs.get('extra_docker_compose') and not kwargs.get('persistent_env'),
                'extra environment injection forbidden')
        for name in ('cpus', 'memory_mb', 'storage_mb', 'gpus', 'tpu'):
            require(kwargs.get('override_'+name) is None, 'resource override forbidden')
        expected = self._release['images'][self._role]
        require(task_env_config.cpus == 2 and task_env_config.memory_mb == 8192
                and task_env_config.gpus == 0, 'unreviewed resource settings')
        policy = kwargs.get('network_policy')
        require(policy is not None and policy.network_mode == NetworkMode.NO_NETWORK
                and not policy.allowed_hosts, 'baseline must be offline')
        checked_mounts = []
        self._trial = Path(trial_paths.trial_dir).resolve()
        for item in kwargs.get('mounts') or []:
            target = item.get('target')
            require(item.get('type') == 'bind' and target in (
                '/logs/agent', '/logs/verifier', '/logs/artifacts'), 'unreviewed mount')
            suffix = {'/logs/agent':'agent', '/logs/verifier':'verifier',
                      '/logs/artifacts':'artifacts/logs/artifacts'}[target]
            require(Path(item['source']).resolve() == self._trial/suffix, 'non-trial mount')
            if self._role == 'verifier':
                require(target == '/logs/verifier', 'verifier received non-log host mount')
            # Agent has no write channel into later trusted verifier receipts.
            if not (self._role == 'agent' and target == '/logs/verifier'):
                checked_mounts.append(item)
        kwargs['mounts'] = checked_mounts
        config = task_env_config.model_copy(deep=True, update={'docker_image':expected['id']})
        self._image = expected
        self._capture = None
        super().__init__(environment_dir=environment_dir, environment_name=environment_name,
                         session_id=session_id, trial_paths=trial_paths,
                         task_env_config=config, **kwargs)
        require(self._enable_egress_control, 'required hardened overlay is unavailable')
        if self._role == 'agent':
            require(str(self._trial) not in STATE, 'agent lifecycle reused')
            STATE[str(self._trial)] = {'project':project_name(session_id), 'stopped':False}

    async def start(self, force_build):
        require(force_build is False, 'release images must be prebuilt and frozen')
        authenticate(self._approval_path)
        info = json.loads(docker_metadata(['image', 'inspect', '--format',
             '{"id":{{json .Id}},"layers":{{json .RootFS.Layers}}}', self._image['id']]))
        require(info == self._image, 'release image identity changed')
        if self._role == 'verifier':
            state = STATE.get(str(self._trial))
            require(state and state['stopped'], 'agent teardown not successfully certified')
            require_stopped(state['project'])
            self._capture = authenticate_capture(self._trial/'artifacts')
        try:
            await super().start(force_build=False)
            self._certify_started()
        except BaseException:
            # Native Harbor's verifier context does not enter its finally until
            # start returns; clean our exact project even if certification fails.
            try:
                await asyncio.shield(DockerEnvironment.stop(self, delete=True))
            except BaseException as cleanup_error:
                self._trial.mkdir(parents=True, exist_ok=True)
                with (self._trial/('release_'+self._role+'_startup_cleanup.json')).open('w') as stream:
                    json.dump({'cleanup_error_type':type(cleanup_error).__name__}, stream)
            raise

    def _certify_started(self):
        ids = docker_metadata(['ps', '-q', '--filter',
              'label=com.docker.compose.project='+project_name(self.session_id),
              '--filter', 'label=com.docker.compose.service=main']).split()
        require(len(ids) == 1, 'cannot identify exact runtime main container')
        actual = json.loads(docker_metadata(['inspect', ids[0]]))[0]
        host = actual['HostConfig']
        with (self._trial/('release_'+self._role+'_observed.json')).open('x') as stream:
            json.dump({'container_id':actual['Id'], 'host_config':host, 'mounts':actual['Mounts']},stream,indent=2)
        require(actual['Image'] == self._image['id'] and host['Memory'] == 8*1024**3
                and host['MemorySwap'] == 8*1024**3 and host['NanoCpus'] == 2_000_000_000
                and not host.get('DeviceRequests') and not host['Privileged'],
                'actual runtime image/resource isolation mismatch')
        require(any(x in ('no-new-privileges','no-new-privileges:true') for x in host['SecurityOpt'])
                and {'NET_RAW','NET_ADMIN'} <= set(host['CapDrop']),
                'required no-new-privileges or network capability restrictions missing')
        if self._role == 'verifier':
            require(host['NetworkMode'] == 'none', 'heldout verifier has network access')
            require(set(host['Tmpfs']) == {'/sandbox/tmp', '/sandbox/out'},
                    'heldout evaluator scratch mounts changed')
        # Host-owned receipt lives outside all agent-writable mounted paths.
        record = {'role':self._role, 'image':self._image,
                  'capture_sha256':self._capture, 'agent_state':STATE[str(self._trial)],
                  'container_id':actual['Id'], 'host_config':host, 'mounts':actual['Mounts']}
        path = self._trial/('release_'+self._role+'_receipt.json')
        with path.open('x') as stream:
            json.dump(record, stream, indent=2)

    async def stop(self, delete):
        await super().stop(delete=delete)
        if self._role == 'agent':
            state = STATE[str(self._trial)]
            require_stopped(state['project'])
            state['stopped'] = True
        elif self._capture is not None:
            require(authenticate_capture(self._trial/'artifacts') == self._capture,
                    'captured submissions changed during verifier phase')
