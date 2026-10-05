"""Read-only clean-image audit. No scientific estimator or model is executed."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
PROBE = r'''
import hashlib,json,os
from pathlib import Path
role=os.environ['AUDIT_ROLE']
root=Path('/data' if role=='agent' else '/sandbox/data')
c=json.loads(Path('/public/contract.json').read_text())
raw=(root/'source_manifest.json').read_bytes()
assert hashlib.sha256(raw).hexdigest()==c['source_manifest_sha256']
m=json.loads(raw)
ids=c['discovery_ids' if role=='agent' else 'evaluation_ids']
expected={r['path']:r for r in m['files'] if r.get('participant_id') is None or r['participant_id'] in ids}
files={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
assert files==set(expected)|{'source_manifest.json'}
for name,r in expected.items():
    p=root/name
    assert not p.is_symlink() and p.stat().st_size==r['size_bytes']
    assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256']
for row in m['files']:
    if row.get('participant_id') and row['participant_id'] not in ids:
        assert not (root/row['path']).exists()
absent=['/solution','/opt/task','/app/solution','/var/run/docker.sock']
if role=='agent': absent+=['/private','/tests','/sandbox']
else: absent+=['/sandbox/private','/sandbox/tests','/sandbox/proc','/sandbox/dev','/sandbox/solution']
for name in absent: assert not Path(name).exists(),name
runtime_unexpected=[]
source_names={Path(r['path']).name for r in m['files'] if r.get('participant_id')}
for p in Path('/usr').rglob('*'):
    if p.name in source_names or 'sub-pixar' in p.name or p.name in ('oracle.pyz','calibration.md','fit_arrays.npz','evaluate_arrays.npz'):
        runtime_unexpected.append(str(p))
assert not runtime_unexpected,runtime_unexpected
import numpy,scipy
print(json.dumps({'role':role,'source_files_authenticated':len(expected),
    'participants':ids,'absent_paths':absent,'unexpected_runtime_source_paths':runtime_unexpected,
    'numpy':numpy.__version__,'scipy':scipy.__version__,'uid':os.getuid()}))
'''

def main(role):
    identity=(ROOT/(role+'_image.id')).read_text().strip()
    info=json.loads(subprocess.check_output(['docker','image','inspect',identity]))[0]
    old=json.loads(subprocess.check_output(['docker','image','inspect',
        'sha256:19be0cc27dd1c6a1250b318d32c1dd628d49f4d8426122513e0f0f55e41760ca']))[0]
    common=set(info['RootFS']['Layers']) & set(old['RootFS']['Layers'])
    empty_tar = 'sha256:'+hashlib.sha256(bytes(1024)).hexdigest()
    assert common <= {old['RootFS']['Layers'][0], empty_tar}, 'Inherited old task layer'
    name='br-release-image-audit-'+role+'-20261004'
    command=['docker','run','--rm','-i','--name',name,'--network','none','--read-only',
             '--cpus','2','--memory','2g','--memory-swap','2g','--pids-limit','32',
             '--cap-drop','ALL','--security-opt','no-new-privileges',
             '-e','AUDIT_ROLE='+role,'--entrypoint','python3',identity,'-B','-']
    try:
        run=subprocess.run(command,input=PROBE,text=True,capture_output=True,timeout=60)
        record={'image':identity,'common_old_layers':sorted(common),'command':command,
                'exit_code':run.returncode,'stdout':run.stdout,'stderr':run.stderr}
        with (ROOT/(role+'_image_audit.json')).open('x') as stream: json.dump(record,stream,indent=2)
        assert run.returncode==0,record
        print(run.stdout)
    finally:
        # Explicit exact ephemeral target; all logs are already retained on host.
        subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=15)

if __name__=='__main__': main(sys.argv[1])
