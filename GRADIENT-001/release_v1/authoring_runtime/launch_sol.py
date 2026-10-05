"""Frozen k=1 calibration, callable only after declared qualification passes.

No automatic retries or task edits. Runtime-only failed setups are retained.
This runner records an exclusive claim before invoking the exact approved model.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

from prepare_execution import ROOT,OLD,TASK,sha,write
from release_environment import authenticate
from run_controls import inspect
from audit_rejections import audit as audit_rejections
from job_cleanup import cleanup_job,terminate_process
sys.path.insert(0,str(OLD))
from offline_codex import runtime_identity,auth_metadata

NAME='pr200-heldout-v1-sol61-max-k1'

def main():
    approved=authenticate(ROOT/'execution_approval_v3.json')
    qualify=json.loads((ROOT/'qualification_result.json').read_text())
    assert qualify['status']=='oracle_and_all13_controls_passed'
    assert len(qualify['cases'])==13
    inspect('oracle-v3',1)
    cases=json.loads((ROOT/'controls/cases.json').read_text())['cases']
    assert {c['job'] for c in qualify['cases']}=={'control-'+c['case']+'-v3' for c in cases}
    for c in cases:inspect('control-'+c['case']+'-v3',c['expected_reward'])
    assert len(audit_rejections())==8
    for role in ('agent','verifier'):
        audit=json.loads((ROOT/(role+'_image_audit.json')).read_text())
        assert audit['exit_code']==0 and audit['image']==approved['images'][role]['id']
    runtime_identity();auth_metadata() # Metadata only; no credentials in receipts.
    assert shutil.disk_usage(ROOT).free>=50*1024**3
    assert not (ROOT/'jobs'/NAME).exists()
    model=copy.deepcopy(approved)
    model.update(scope='One fresh GPT-6.1 Sol Max k=1 after oracle and thirteen controls; no retries',
        model={'name':'openai/gpt-6.1-sol','reasoning_effort':'max','cli_version':'0.160.0','k':1},
        qualification_sha256=sha(ROOT/'qualification_result.json'),
        agent_timeout_seconds=3000,verifier_timeout_seconds=300,
        outer_wall_seconds=4500,host_job_output_cap_bytes=256*1024**2,
        network={'baseline':'none','agent_phase_only':['chatgpt.com','auth.openai.com','api.openai.com'],
                 'verifier':'none'},
        no_posthoc_changes=True)
    model['runtime_sha256'][str(Path(__file__).resolve())]=sha(Path(__file__).resolve())
    model['runtime_sha256'][str(ROOT/'run_controls.py')]=sha(ROOT/'run_controls.py')
    for name in ('audit_rejections.py','job_cleanup.py'):
        model['runtime_sha256'][str(ROOT/name)]=sha(ROOT/name)
    write(ROOT/'sol_approval.json',model)
    config={'job_name':NAME,'jobs_dir':str(ROOT/'jobs'),'n_concurrent_trials':1,'n_attempts':1,
        'retry':{'max_retries':0},'environment':{
            'import_path':'release_environment:ReleaseDocker','force_build':False,'delete':True,
            'kwargs':{'release_approval':str(ROOT/'sol_approval.json')}},
        'agents':[{'import_path':'offline_codex:OfflineCodex','model_name':'openai/gpt-6.1-sol',
            'extra_allowed_hosts':['chatgpt.com','auth.openai.com','api.openai.com'],
            'kwargs':{'version':'0.160.0','reasoning_effort':'max','web_search':'disabled','allow_host_auth':True}}],
        'tasks':[{'path':str(TASK)}]}
    write(ROOT/'sol_config.json',config)
    write(ROOT/'sol_launch_claim.json',{'pid':os.getpid(),'epoch':time.time(),
         'config_sha256':sha(ROOT/'sol_config.json'),'approval_sha256':sha(ROOT/'sol_approval.json'),'retries':0})
    env=os.environ.copy();env['PYTHONPATH']=str(ROOT)+':'+str(OLD)
    start=time.monotonic()
    termination=None;child=None;process_receipt=None;error_type=None
    try:
        with (ROOT/'sol.stdout.log').open('xb') as stream:
            child=subprocess.Popen(['/home/zijiaochen/.local/bin/harbor','run','--config',str(ROOT/'sol_config.json')],
                env=env,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
            write(ROOT/'sol_process.json',{'launcher_pid':os.getpid(),'harbor_pid':child.pid,'job':NAME})
            while child.poll() is None:
                output=(ROOT/'sol.stdout.log').stat().st_size+sum(p.stat().st_size for p in (ROOT/'jobs'/NAME).rglob('*') if p.is_file() and not p.is_symlink())
                if time.monotonic()-start>4500:termination='outer_wall_cap'
                if output>256*1024**2:termination='host_job_output_cap'
                if shutil.disk_usage(ROOT).free<50*1024**3:termination='host_disk_floor'
                if termination:break
                time.sleep(5)
    except BaseException as exc:
        error_type=type(exc).__name__;termination=termination or 'launcher_exception'
    finally:
        if child is not None:process_receipt=terminate_process(child)
        cleanup=cleanup_job(ROOT/'jobs'/NAME)
        write(ROOT/'sol_cleanup_receipt.json',{'process':process_receipt,'docker':cleanup})
        write(ROOT/'sol_launcher_result.json',{'exit_code':child.returncode if child else None,
              'wall_seconds':time.monotonic()-start,'termination':termination,
              'launcher_error_type':error_type,'cleanup_status':cleanup['status'],'no_retry':True})
    print(json.dumps({'exit_code':child.returncode if child else None,'termination':termination,'job':NAME}))

if __name__=='__main__':main()
