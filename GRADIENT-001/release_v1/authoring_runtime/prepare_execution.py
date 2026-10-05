"""Generate exact prospective receipts/configs; does not launch any job."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
OLD = ROOT.parent/'sol61_max_2026-10-03'
TASK = ROOT/'GRADIENT-HELDOUT-001'
HARBOR = Path('/home/zijiaochen/.local/share/uv/tools/harbor/lib/python3.13/site-packages/harbor')

def sha(path):
    assert path.is_file() and not path.is_symlink(), path
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')

def image(role):
    identity = (ROOT/(role+'_image.id')).read_text().strip()
    info = json.loads(subprocess.check_output(['docker','image','inspect', identity]))[0]
    assert info['Id'] == identity and info['Os'] == 'linux' and info['Architecture'] == 'amd64'
    return {'id':identity, 'layers':info['RootFS']['Layers']}

def prepare():
    package = json.loads((TASK/'preparation.json').read_text())
    assert all(sha(TASK/p) == h for p,h in package['files'].items())
    runtime = [ROOT/p for p in ('release_environment.py', 'release_agent.compose.json',
               'release_verifier.compose.json', 'fixture_agent.py', 'prepare_execution.py')]
    runtime += [OLD/p for p in ('offline_codex.py','network_hardening.py',
                  'network_hardening.compose.json','network_sidecar_identity.json')]
    runtime += [OLD/p for p in json.loads((OLD/'network_sidecar_identity.json').read_text())['source_sha256']]
    runtime += [p for p in HARBOR.rglob('*') if p.is_file() and p.suffix in ('.py','.yaml','.yml','.j2','.sh')]
    approval = {
        'approved':True, 'scope':'offline oracle and thirteen fixed qualification fixtures only; no model call',
        'task_path':str(TASK),
        'source_commit':'ac00521fcec81c99a2dacc4cc21cbb1ddcaa5155',
        'task_sha256':{str(p.relative_to(TASK)):sha(p) for p in sorted(TASK.rglob('*')) if p.is_file()},
        'runtime_sha256':{str(p):sha(p) for p in sorted(set(runtime))},
        'images':{role:image(role) for role in ('agent','verifier')},
        'resources':{'cpus_per_role':2,'memory_bytes':8*1024**3,'extra_swap_bytes':0,
                     'gpus':0,'network':'none','concurrent_trials':1,'retry':0},
        'scientific_scope':'No new dataset/estimator/fit search or tolerance changes; frozen phase2 science.'
    }
    write(ROOT/'execution_approval.json', approval)
    configs = ROOT/'configs'
    configs.mkdir()
    def config(name, agent):
        value = {'job_name':name, 'jobs_dir':str(ROOT/'jobs'), 'n_concurrent_trials':1,
                 'n_attempts':1,'retry':{'max_retries':0},
                 'environment':{'import_path':'release_environment:ReleaseDocker','force_build':False,
                 'delete':True,'kwargs':{'release_approval':str(ROOT/'execution_approval.json')}},
                 'agents':[agent], 'tasks':[{'path':str(TASK)}]}
        write(configs/(name+'.json'), value)
    config('oracle-v1', {'name':'oracle'})
    for case in json.loads((ROOT/'controls/cases.json').read_text())['cases']:
        config('control-'+case['case'], {'import_path':'fixture_agent:FixtureAgent', 'kwargs':{
            'fixture_dir':str(ROOT/'controls'/case['case']),
            'expected_sha256':{'discovery.json':case['discovery_sha256'],
                               'evaluate.py':case['program_sha256']}}})
    print(json.dumps({'status':'configured_not_launched','images':approval['images'],
                      'runtime_files_pinned':len(approval['runtime_sha256'])}))

if __name__ == '__main__':
    prepare()
