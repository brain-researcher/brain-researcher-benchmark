"""One serial pass over13predeclared fixtures, no retries/model calls."""
import json
import os
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'sol61_max_2026-10-03'
HARBOR='/home/zijiaochen/.local/bin/harbor'

def trial(job):
    rows=list((ROOT/'jobs'/job).glob('*/result.json'))
    assert len(rows)==1,rows
    result=json.loads(rows[0].read_text())
    assert result.get('finished_at') and result.get('exception_info') is None,result.get('exception_info')
    assert result.get('agent_execution',{}).get('finished_at'), 'agent did not finish'
    return rows[0].parent,result

def inspect(job,expected):
    folder,result=trial(job)
    reward=result['verifier_result']['rewards']['reward']
    assert reward==expected,(job,reward,expected)
    receipt=json.loads((folder/'release_verifier_receipt.json').read_text())
    assert receipt['agent_state']['stopped'] and receipt['host_config']['NetworkMode']=='none'
    assert receipt['host_config']['Memory']==receipt['host_config']['MemorySwap']==8*1024**3
    assert receipt['host_config']['NanoCpus']==2000000000
    assert receipt['host_config']['Privileged'] is False
    assert set(receipt['host_config']['Tmpfs'])=={'/sandbox/tmp','/sandbox/out'}
    assert set(m['Destination'] for m in receipt['mounts'] if m['Type']=='bind')=={'/logs/verifier'}
    assert set(receipt['host_config']['CapAdd'])=={'SYS_CHROOT','SETUID','SETGID','KILL','DAC_OVERRIDE','FOWNER'}
    assert {'ALL','NET_RAW','NET_ADMIN'}<=set(receipt['host_config']['CapDrop'])
    agent=json.loads((folder/'release_agent_receipt.json').read_text())
    assert '/logs/verifier' not in {m['Destination'] for m in agent['mounts']}
    grade=json.loads((folder/'verifier/receipt.json').read_text())
    if expected==1:
        assert grade['all_candidate_processes_dead'] and grade['candidate_uid']==61616
    if 'sandbox_denied' in job:
        probes=json.loads((folder/'verifier/evaluation.json').read_text())['isolation_probes']
        assert len(probes)>20 and all(v is True for v in probes.values())
    if 'orphaned' in job:
        child=json.loads((folder/'verifier/evaluation.json').read_text())['surviving_child_created']
        assert child in grade['terminated_descendant_pids']
    return {'job':job,'trial_path':str(folder),'reward':reward,'expected_reward':expected,
            'grader_receipt':grade}

def main():
    oracle=inspect('oracle-v3',1)
    env=os.environ.copy()
    env['PYTHONPATH']=str(ROOT)+':'+str(OLD)
    output={'oracle':oracle,'cases':[],'scope':'grader/isolation qualification, not model difficulty'}
    # Exclusive claim prevents accidental reruns. Failures retain all evidence.
    with (ROOT/'controls_launch_claim.json').open('x') as stream:
        json.dump({'pid':os.getpid(),'started_epoch':time.time(),'retries':0},stream)
    for row in json.loads((ROOT/'controls/cases.json').read_text())['cases']:
        name='control-'+row['case']+'-v3'
        config=ROOT/'configs3'/(name+'.json')
        assert not (ROOT/'jobs'/name).exists(),name
        print('START '+name,flush=True)
        with (ROOT/(name+'.stdout.log')).open('xb') as log:
            subprocess.run([HARBOR,'run','--config',str(config)],stdout=log,stderr=subprocess.STDOUT,
                           env=env,cwd=ROOT,timeout=700,check=True)
        outcome=inspect(name,row['expected_reward'])
        output['cases'].append(outcome)
        with (ROOT/(name+'.qualification.json')).open('x') as stream:json.dump(outcome,stream,indent=2)
        print('PASS '+name+' expected='+str(row['expected_reward']),flush=True)
    output['status']='oracle_and_all13_controls_passed'
    with (ROOT/'qualification_result.json').open('x') as stream:json.dump(output,stream,indent=2)
    print(output['status'],flush=True)

if __name__=='__main__':main()
