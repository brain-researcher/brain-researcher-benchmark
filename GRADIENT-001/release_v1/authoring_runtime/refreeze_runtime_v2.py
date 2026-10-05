"""Record reviewed runtime-only repair; prior approvals/jobs remain untouched."""
import copy
import json
from pathlib import Path
from prepare_execution import sha, write, ROOT, TASK

old=json.loads((ROOT/'execution_approval.json').read_text())
assert all(sha(TASK/p)==h for p,h in old['task_sha256'].items())
changed={str(ROOT/p) for p in ('release_environment.py','release_agent.compose.json','release_verifier.compose.json')}
new=copy.deepcopy(old)
for p,h in old['runtime_sha256'].items():
    observed=sha(Path(p))
    assert p in changed or observed==h,p
    new['runtime_sha256'][p]=observed
new['runtime_sha256'][str(Path(__file__).resolve())]=sha(Path(__file__).resolve())
new['supersedes_runtime_only']='execution_approval.json'
new['repair']='Duplicate Compose security option removed; inherited hardened overlay required. Verifier main forced network none; trusted launcher FOWNER for native log chmod. No task/source/image/scoring change.'
write(ROOT/'execution_approval_v2.json',new)
folder=ROOT/'configs2';folder.mkdir()
for p in sorted((ROOT/'configs').glob('*.json')):
    c=json.loads(p.read_text())
    c['job_name']='oracle-v2' if c['job_name']=='oracle-v1' else c['job_name']+'-v2'
    c['environment']['kwargs']['release_approval']=str(ROOT/'execution_approval_v2.json')
    write(folder/(c['job_name']+'.json'),c)
print('Runtime v2 pinned; no job launched.')
