"""Root-only regression fixture for a disposable remote judge container.

Copy judge-runtime/*.py to /judge and the unchanged BPP scoring.py to
/opt/fixture/scoring.py. Run with TCSEXAM_ISOLATION_TEST_FIXTURE=1.
This script replaces /app and creates synthetic /tests and /work files.
It does not load benchmark data or run an optimization solver.
"""
import os
assert os.geteuid() == 0 and os.environ.get('TCSEXAM_ISOLATION_TEST_FIXTURE') == '1', 'Use a disposable remote fixture container'
import importlib.util,json,os,pathlib,shutil,sys,subprocess,time,ctypes
sys.path.insert(0,'/judge')
from execution import install,own_tree
P=pathlib.Path
shutil.rmtree('/app',ignore_errors=True);P('/work').mkdir(exist_ok=True);P('/app').mkdir(exist_ok=True);P('/tests').mkdir(exist_ok=True);P('/opt/fixture').mkdir(exist_ok=True)
P('/tests/sentinel').write_text('trusted');P('/tests/sentinel').chmod(0o666)
shutil.copy2('/usr/bin/id','/opt/fixture/suid-id');P('/opt/fixture/suid-id').chmod(0o4755)
P('/opt/fixture/solver.py').write_text('''#!/usr/bin/python3
import json,os,pathlib,subprocess,sys
p=pathlib.Path
report={'uid':os.getuid(),'gid':os.getgid(),'groups':os.getgroups(),'nnprivs':next(x.strip() for x in p('/proc/self/status').read_text().splitlines() if x.startswith('NoNewPrivs:')),'suid_uid':subprocess.check_output(['/opt/fixture/suid-id','-u'],text=True).strip(),'env':dict(os.environ)}
for name in ('/tests/sentinel','/app/../tests/sentinel'):
 try:p(name).write_text('corrupt');report[name]='WRITTEN'
 except PermissionError:report[name]='denied'
try:p('/proc/'+str(os.getppid())+'/environ').read_bytes();report['parent_env']='read'
except PermissionError:report['parent_env']='denied'
try:os.setuid(0);report['root_uid']='restored'
except PermissionError:report['root_uid']='denied'
with open('/tests/sentinel') as protected:
 try:p('/proc/self/fd/'+str(protected.fileno())).write_text('corrupt');report['fd_alias']='written'
 except PermissionError:report['fd_alias']='denied'
p('/app/legal-output').write_text('legal')
try:os.symlink('/tests/sentinel','/app/output-link');report['link']='created'
except PermissionError:report['link']='denied'
print(json.dumps(report))
''');P('/opt/fixture/solver.py').chmod(0o755)
P('/app/build.sh').write_text('#!/bin/bash\nset -eu\ncp /opt/fixture/solver.py /app/solver\nchmod +x /app/solver\n')
P('/app/input').write_text('synthetic')
own_tree('/app')
os.environ.update(TCSEXAM_TOKEN_SECRET='fixture-secret',LD_PRELOAD='',PYTHONPATH='/app',BPP_TIME_POOL='30.000')
# Use the real bpp scoring code, without real instances or optimization.
spec=importlib.util.spec_from_file_location('scoring','/opt/fixture/scoring.py');scoring=importlib.util.module_from_spec(spec);spec.loader.exec_module(scoring)
install({'relative_cpu_indices':True})
solver,error=scoring.build_solver('/app');assert error is None,error
elapsed,error=scoring.run_solver(solver,'/app/input','/work/output.json',1)
assert error is None,error
report=json.loads(P('/work/output.json').read_text());assert report['uid']==report['gid']==65534 and report['groups']==[]
assert report['parent_env']==report['root_uid']==report['fd_alias']=='denied'
assert report['suid_uid']=='65534' and report['nnprivs'].endswith('1')
assert report['/tests/sentinel']=='denied' and report['/app/../tests/sentinel']=='denied'
assert report['link']=='denied';assert P('/app/legal-output').read_text()=='legal'
assert 'TCSEXAM_TOKEN_SECRET' not in report['env'] and 'PYTHONPATH' not in report['env']
assert P('/tests/sentinel').read_text()=='trusted'
# A writable output file sharing a directory with a trusted input cannot
# confer write permission on that input (QBF's materialized-input layout).
P('/opt/fixture/scoring-other.py').write_text('')
code="""def run_solver(solver, instance_path, out_path, proof_path, budget):
 import subprocess
 return subprocess.run([solver, instance_path, proof_path],capture_output=True,text=True)
"""
ns={'__file__':'/opt/fixture/scoring.py'};exec(compile(code,'/opt/fixture/scoring.py','exec'),ns)
P('/work/materialized-input').write_text('original')
P('/app/input-test').write_text('#!/usr/bin/python3\nimport pathlib,sys\np=pathlib.Path\ntry:p(sys.argv[1]).write_text("corrupt");raise RuntimeError("input write escaped")\nexcept PermissionError:pass\np(sys.argv[2]).write_text("proof")\n')
P('/app/input-test').chmod(0o755)
r=ns['run_solver']('/app/input-test','/work/materialized-input','/work/answer','/work/proof',1)
assert r.returncode==0,(r.stdout,r.stderr);assert P('/work/materialized-input').read_text()=='original';assert P('/work/proof').read_text()=='proof'
# External validation remains trusted.
ns={};exec(compile('def verify_solution():\n import subprocess\n return subprocess.check_output(["id","-u"],text=True)\n','/opt/fixture/scoring.py','exec'),ns)
assert ns['verify_solution']().strip()=='0'
# Independent sessions and double fork are reaped on normal, error and timeout.
import judge_worker as worker
worker.WORK_DIR=P('/work/online');worker.APP_DIR='/app';worker.JUDGE_TIMEOUT=.4
shutil.rmtree(worker.WORK_DIR,ignore_errors=True);worker.WORK_DIR.mkdir(parents=True,exist_ok=True)
worker._STATE={'next_id':0,'submissions':[]}
P('/opt/fixture/checker.py').write_text('''import json,os,pathlib,subprocess,sys,time
p=pathlib.Path
subprocess.Popen([sys.executable,'-c','import os,time;pid=os.fork();time.sleep(20)'],start_new_session=True)
p('/work/checker-pid').write_text(str(os.getpid()))
if sys.argv[1]=='timeout':time.sleep(20)
if sys.argv[1]=='error':raise RuntimeError('synthetic')
p(os.environ['REWARD_PATH']).write_text(json.dumps({'per_instance':{'x':{'A':1,'B':2,'K':1,'status':'ok'}}}))
''')
checks=[]
for mode in ('timeout','normal','error','normal'):
 i=len(worker._STATE['submissions']);d=worker.WORK_DIR/'submissions'/str(i)/'app';d.mkdir(parents=True);(d/'ordinary').write_text('x')
 worker._STATE['submissions'].append({'submission':i,'status':'running','records':None})
 worker.JUDGE_CMD='/usr/bin/python3 /opt/fixture/checker.py '+mode
 worker._judge_one(i)
 entry=worker._STATE['submissions'][i];assert entry['status']=={'timeout':'timeout','normal':'ok','error':'judge_error'}[mode],entry
 # The supervisor has reaped every descendant; no process contains the
 # fixture's synthetic sleep script after each submission.
 leftovers=[]
 for d in P('/proc').iterdir():
  if not d.name.isdigit():continue
  try:
   cmd=(d/'cmdline').read_bytes()
   if b'import os,time;pid=os.fork();time.sleep(20)' in cmd:leftovers.append(d.name)
  except OSError:pass
 assert not leftovers,leftovers
 checks.append({'mode':mode,'status':entry['status'],'background_processes':leftovers})
print(json.dumps({'uid_isolation':report,'input_same_directory':'protected','trusted_validator_uid':0,'supervisor':checks,'landlock_abi':ctypes.CDLL(None).syscall(444,0,0,1),'sentinel':P('/tests/sentinel').read_text()}))

# Compile a tiny constant-output program, exercise make, the QBF mktemp
# template, and a generated internal library/executable symlink.
if P('/usr/bin/g++').exists():
 P('/app/hello.cpp').write_text('#include <iostream>\nint main(){std::cout << "42\\n";}\n')
 P('/app/Makefile').write_text('all:\n\tg++ hello.cpp -o solver-bin\n\tln -s solver-bin solver\n')
 P('/app/build.sh').write_text('#!/bin/bash\nset -eu\nmake\nln -s /tests/sentinel /app/external-link\nmktemp /tmp/qbf-input-XXXXXX.qdimacs > /app/tmp-path\n')
 solver,error=scoring.build_solver('/app');assert error is None,error
 assert not P('/app/external-link').is_symlink()
 assert P('/app/solver').is_symlink() and P('/app/solver').resolve()==P('/app/solver-bin')
 assert P('/app/tmp-path').read_text().startswith('/tmp/tcsexam-child-')
 r=scoring.run_solver(solver,'/app/ordinary','/work/compiled-output',1)
 assert r[1] is None,r
 assert P('/work/compiled-output').read_text().strip()=='42'
 print(json.dumps({'compiler_make_internal_symlink':'passed','qbf_explicit_tmp_template':'private'}))

print(json.dumps({'cgroup':{name:(P('/sys/fs/cgroup')/name).read_text().strip() for name in ('memory.max','pids.max','cpu.max','memory/memory.limit_in_bytes','pids/pids.max','cpu/cpu.cfs_quota_us','cpu/cpu.cfs_period_us') if (P('/sys/fs/cgroup')/name).exists()},'seccomp':next(line for line in P('/proc/self/status').read_text().splitlines() if line.startswith('Seccomp:'))}))

# Preserve a real candidate's TERM handler and force cleanup only on request.
from execution import SUPERVISOR, clean_environment, _writable
P('/app/term.py').write_text('import os,signal,time\ndef stop(a,b):\n os.write(1,b"saved-at-term\\n")\n raise SystemExit(0)\nsignal.signal(signal.SIGTERM,stop)\nos.write(1,b"ready\\n")\ntime.sleep(20)\n')
environment=clean_environment({},'/app')
command=[sys.executable,'-I',str(SUPERVISOR),'untrusted',json.dumps([sys.executable,'/app/term.py']),json.dumps({'directories':['/app'],'files':[]})]
with subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=environment) as process:
 assert process.stdout.readline().strip()=='ready'
 process.terminate()
 output,error=process.communicate(timeout=3)
 assert process.returncode==0 and output.strip()=='saved-at-term',(process.returncode,output,error)

# Atomic rename is confined to JSSP's existing per-instance output directory.
from types import SimpleNamespace
private=P('/work/jssp-private');private.mkdir(exist_ok=True);private.chmod(0o700)
protected=private/'instance.txt';protected.write_text('trusted');protected.chmod(0o666)
output=private/'out-fixture'/'answer.sol'
frame=SimpleNamespace(f_code=SimpleNamespace(co_name='run_solver'),f_locals={'out_path':str(output)})
policy,_=_writable(frame,{},'jsplib-jssp')
code="""import os,pathlib,tempfile,sys
fd,name=tempfile.mkstemp(dir=sys.argv[1])
os.write(fd,b'atomic');os.close(fd);os.replace(name,sys.argv[2])
try:
    pathlib.Path(sys.argv[3]).write_text('bad')
except PermissionError:
    pass
else:
    raise RuntimeError('input writable')
"""
command=[sys.executable,'-I',str(SUPERVISOR),'untrusted',json.dumps([sys.executable,'-I','-c',code,str(output.parent),str(output),str(protected)]),json.dumps(policy)]
result=subprocess.run(command,env=environment,capture_output=True,text=True,timeout=5)
assert result.returncode==0,result.stderr
assert output.read_text()=='atomic' and protected.read_text()=='trusted'

# A root-owned sealed build created with umask 077 remains executable by 65534.
build=P('/work/private-build');shutil.rmtree(build,ignore_errors=True);build.mkdir(mode=0o700)
P('/opt/fixture/private-program.py').write_text('#!/usr/bin/python3\nprint("private700")\n')
script=build/'build.sh';script.write_text('umask 077\ncp /opt/fixture/private-program.py solver\nchmod 700 solver\n')
ns={};exec(compile('def build_solver(build_dir):\n import subprocess\n return subprocess.run(["bash","build.sh"],cwd=build_dir,capture_output=True,text=True)\n','/opt/fixture/scoring.py','exec'),ns)
assert ns['build_solver'](str(build)).returncode==0
assert build.stat().st_uid==0 and (build/'solver').stat().st_uid==0
command=[sys.executable,'-I',str(SUPERVISOR),'untrusted',json.dumps([str(build/'solver')]),json.dumps({'directories':['/app'],'files':[]})]
result=subprocess.run(command,env=environment,capture_output=True,text=True,timeout=5)
assert result.returncode==0 and result.stdout.strip()=='private700',result.stderr

# Inject a cleanup failure after a real restricted child exits. The checker
# deliberately absorbs rc=125; the trusted marker must still disable Online.
P('/opt/fixture/forced-cleanup.py').write_text('import sys\nsys.path.insert(0,"/judge")\nimport process_supervisor as s\ndef fail(*a,**k):raise s.CleanupFailed("injected cleanup failure")\ns._cleanup=fail\nraise SystemExit(s.main())\n')
P('/opt/fixture/absorb-checker.py').write_text('''import json,os,pathlib,subprocess,sys
code='import os;assert "TCSEXAM_EXECUTION_FAILURE_FILE" not in os.environ'
command=[sys.executable,'-I','/opt/fixture/forced-cleanup.py','untrusted',json.dumps([sys.executable,'-I','-c',code]),json.dumps({'directories':['/app'],'files':[]})]
r=subprocess.run(command);assert r.returncode==125
pathlib.Path(os.environ['REWARD_PATH']).write_text(json.dumps({'build_error':'absorbed child failure'}))
''')
i=len(worker._STATE['submissions']);d=worker.WORK_DIR/'submissions'/str(i)/'app';d.mkdir(parents=True);(d/'ordinary').write_text('x')
worker._STATE['submissions'].append({'submission':i,'status':'running','records':None})
worker.JUDGE_TIMEOUT=3
worker.JUDGE_CMD='/usr/bin/python3 /opt/fixture/absorb-checker.py'
worker._judge_one(i)
assert worker._WORKER_ERROR and worker._STATE['submissions'][i]['status']=='judge_error'
assert (worker.WORK_DIR/'worker-error.json').exists()
print(json.dumps({'term_grace':'preserved','jssp_atomic_rename':'passed','jssp_input':'protected','private_build_0700':'executable_as_65534','inner_cleanup_failure':'judge_error_and_worker_disabled'}))
