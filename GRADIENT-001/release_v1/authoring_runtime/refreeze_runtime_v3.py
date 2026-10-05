"""Normalize Docker's observed NNP representation; no security/science changes."""
import copy,json
from pathlib import Path
from prepare_execution import ROOT,TASK,sha,write
old=json.loads((ROOT/'execution_approval_v2.json').read_text())
new=copy.deepcopy(old)
assert all(sha(TASK/p)==h for p,h in old['task_sha256'].items())
for p,h in old['runtime_sha256'].items():
    observed=sha(Path(p))
    assert p==str(ROOT/'release_environment.py') or observed==h,p
    new['runtime_sha256'][p]=observed
new['runtime_sha256'][str(Path(__file__).resolve())]=sha(Path(__file__).resolve())
new['supersedes_runtime_only']='execution_approval_v2.json'
new['repair']='Accept observed Docker no-new-privileges:true serialization as well as bare true flag; record actual metadata before assertions. No security setting or scientific change.'
write(ROOT/'execution_approval_v3.json',new)
folder=ROOT/'configs3';folder.mkdir()
for p in sorted((ROOT/'configs2').glob('*.json')):
    c=json.loads(p.read_text());c['job_name']=c['job_name'][:-2]+'v3'
    c['environment']['kwargs']['release_approval']=str(ROOT/'execution_approval_v3.json')
    write(folder/(c['job_name']+'.json'),c)
print('Runtime v3 pinned; no job launched.')
