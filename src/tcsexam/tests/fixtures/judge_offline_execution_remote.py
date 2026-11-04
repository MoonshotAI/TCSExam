"""Root-only Offline entry regression fixture; run in a disposable remote container.
Requires the companion remote fixture and staged worker sources under /source.
"""
import os
assert os.geteuid()==0 and os.environ.get('TCSEXAM_ISOLATION_TEST_FIXTURE')=='1'
import json,os,pathlib,shutil,subprocess,sys
P=pathlib.Path
base=P('/opt/public_judge');base.mkdir(parents=True,exist_ok=True)
P('/tests/instances').mkdir(parents=True,exist_ok=True);P('/tests/instances/fixture').write_text('synthetic')
P('/logs/verifier').mkdir(parents=True,exist_ok=True)
config={'task':'fixture','pool':False,'seconds':1,'build_seconds':2,'check_seconds':1,'module_dir':'/opt/fixture','instances_dir':'/tests/instances','judge_env':{},'relative_cpu_indices':True}
(base/'task.json').write_text(json.dumps(config));P('/judge/task.json').write_text(json.dumps(config))
P('/tests/reference.json').write_text(json.dumps({'instances':{'fixture':{'B':2,'K':1}}}))
# Delegate the security-relevant calls to the unchanged BPP build/run code.
(base/'scoring.py').write_text('''import importlib.util,json,pathlib
spec=importlib.util.spec_from_file_location('bpp_original','/opt/fixture/scoring.py');real=importlib.util.module_from_spec(spec);spec.loader.exec_module(real)
def main(argv):
 solver,error=real.build_solver('/app');assert error is None,error
 elapsed,error=real.run_solver(solver,'/tests/instances/fixture','/work/offline-result.json',1);assert error is None,error
 report=json.loads(pathlib.Path('/work/offline-result.json').read_text());assert report['uid']==65534 and report['groups']==[] and report['/tests/sentinel']=='denied'
 return {'per_instance':{'fixture':{'A':1,'B':2,'K':1,'status':'ok'}}}
''')
P('/tests/checker.py').write_text('''import importlib.util,json,os,pathlib
spec=importlib.util.spec_from_file_location('fixture_delegate','/opt/public_judge/scoring.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
pathlib.Path(os.environ['REWARD_PATH']).write_text(json.dumps(module.main([])))
''')
(base/'frozen-test.sh').write_text('#!/bin/bash\nset -eu\npython3 /judge/run_checker.py\n')
(base/'bin').mkdir(exist_ok=True);shutil.copyfile('/source/python-shim.sh',base/'bin/python3');(base/'bin/python3').chmod(0o755)
results=[]
for name in ('generic','bpp-bpplib','curriculum-itc2007','maxcut-mqlib','mr-roadef2012','qbf-qbfeval'):
 shutil.rmtree('/submission',ignore_errors=True);P('/submission/app').mkdir(parents=True)
 P('/submission/app/build.sh').write_text('#!/bin/bash\nset -eu\ncp /opt/fixture/solver.py /app/solver\nchmod +x /app/solver\n')
 shutil.copyfile('/source/'+name+'.py',base/'worker.py')
 r=subprocess.run([sys.executable,str(base/'worker.py')],env=dict(os.environ,TCS_UNIT_KEYS='["fixture"]'),capture_output=True,text=True,timeout=10)
 assert r.returncode==0,(name,r.stdout,r.stderr)
 unit=json.loads(P('/logs/verifier/unit.json').read_text());assert unit['per_instance']['fixture']['A']==1
 assert P('/tests/sentinel').read_text()=='trusted'
 results.append({'entry':name,'returncode':r.returncode,'uid':json.loads(P('/work/offline-result.json').read_text())['uid'],'sentinel':'trusted'})
print(json.dumps({'offline_entrypoints':results}))

# A scorer can absorb a child return code, but the Offline supervisor must
# still return an infrastructure failure when that child's cleanup failed.
(base/'scoring.py').write_text('''import importlib.util,pathlib,execution
spec=importlib.util.spec_from_file_location('bpp_original','/opt/fixture/scoring.py');real=importlib.util.module_from_spec(spec);spec.loader.exec_module(real)
def main(argv):
 execution.SUPERVISOR=pathlib.Path('/opt/fixture/forced-cleanup.py')
 real.build_solver('/app')
 return {'build_error':'inner cleanup failure absorbed'}
''')
failures=[]
for name in ('generic','bpp-bpplib','curriculum-itc2007','maxcut-mqlib','mr-roadef2012','qbf-qbfeval'):
 P('/work/execution-failure.json').unlink(missing_ok=True)
 shutil.rmtree('/submission',ignore_errors=True);P('/submission/app').mkdir(parents=True)
 P('/submission/app/build.sh').write_text('#!/bin/bash\nset -eu\ncp /opt/fixture/solver.py /app/solver\nchmod +x /app/solver\n')
 shutil.copyfile('/source/'+name+'.py',base/'worker.py')
 r=subprocess.run([sys.executable,str(base/'worker.py')],env=dict(os.environ,TCS_UNIT_KEYS='["fixture"]'),capture_output=True,text=True,timeout=10)
 assert r.returncode==125,(name,r.returncode,r.stdout,r.stderr)
 assert P('/work/execution-failure.json').exists()
 failures.append({'entry':name,'returncode':r.returncode,'cleanup_failure':'infrastructure_failure'})
print(json.dumps({'offline_injected_cleanup_failures':failures}))
