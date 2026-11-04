"""Small syscall probes; compiler and full uid/Landlock checks run on the judge host."""
import platform
import subprocess
import sys

import pytest

from tcsexam.layout import repository

RUNTIME = repository() / 'assets/environments/solver/judge-runtime'
pytestmark = pytest.mark.skipif(
    sys.platform != 'linux' or platform.machine() != 'x86_64',
    reason='Judge syscall policy targets Linux x86-64',
)
BOOT = f"import sys; sys.path.insert(0,{str(RUNTIME)!r}); import process_supervisor as s\n"
RESTRICT = 's._prctl(38,1); s._deny_network()\n'


def run_probe(code):
    result = subprocess.run([sys.executable, '-I', '-c', BOOT + code],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_socket_denial_including_direct_syscalls_and_alternate_abi():
    run_probe(RESTRICT + '''
import ctypes,errno,socket
libc=ctypes.CDLL(None,use_errno=True)
for family,kind in ((socket.AF_INET,socket.SOCK_STREAM),(socket.AF_INET6,socket.SOCK_STREAM),
                    (socket.AF_INET,socket.SOCK_DGRAM),(socket.AF_UNIX,socket.SOCK_STREAM),
                    (socket.AF_NETLINK,socket.SOCK_RAW)):
    try:
        socket.socket(family,kind)
    except OSError as exc:
        assert exc.errno==errno.EPERM,exc
    else:
        raise AssertionError((family,kind))
# Invalid arguments deliberately distinguish policy rejection from EBADF/EINVAL.
for nr in (41,42,43,49,50,288,425,426,427,512,547,0x40000029):
    ctypes.set_errno(0)
    assert libc.syscall(nr,-1,0,0,0,0,0)==-1
    assert ctypes.get_errno()==errno.EPERM,(nr,ctypes.get_errno())
''')


def test_inherited_filter_and_local_ipc_files_threads(tmp_path):
    child = '''import errno,socket
try:
    socket.socket()
except PermissionError as exc:
    assert exc.errno==errno.EPERM
else:
    raise AssertionError('child networking escaped')
'''
    run_probe(RESTRICT + f'''
import os,pathlib,socket,subprocess,threading
subprocess.run([sys.executable,'-I','-c',{child!r}],check=True)
pid=os.fork()
if pid==0:
    exec({child!r})
    os._exit(0)
assert os.waitpid(pid,0)[1]==0
results=[]
thread=threading.Thread(target=lambda:results.append(42))
thread.start();thread.join();assert results==[42]
left,right=socket.socketpair()
left.sendall(b'local');assert right.recv(5)==b'local'
left.close();right.close()
r,w=os.pipe();os.write(w,b'pipe');assert os.read(r,4)==b'pipe'
os.close(r);os.close(w)
p=pathlib.Path({str(tmp_path / 'output')!r});p.write_text('ok');assert p.read_text()=='ok'
''')


def test_connect_on_existing_socket_is_denied_and_parent_keeps_network():
    # A local listener confirms that the same otherwise-reachable route works
    # for trusted code and is rejected after the submission filter is installed.
    run_probe('''
import socket,subprocess
listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1)
address=listener.getsockname()
client=socket.create_connection(address);accepted,_=listener.accept()
client.close();accepted.close()
code="import sys;sys.path.insert(0,"+repr(str(s.Path(s.__file__).parent))+");import process_supervisor as s;import socket,errno\\n"
code+="client=socket.socket();s._prctl(38,1);s._deny_network()\\n"
code+="try: client.connect("+repr(address)+")\\nexcept PermissionError as exc: assert exc.errno==errno.EPERM\\nelse: raise AssertionError('connect succeeded')\\n"
subprocess.run([sys.executable,'-I','-c',code],check=True)
client=socket.create_connection(address);accepted,_=listener.accept()
client.close();accepted.close();listener.close()
''')


def test_filter_installation_failure_never_executes_submission(tmp_path):
    marker = tmp_path / 'executed'
    run_probe(f'''
import subprocess
def fail(policy):
    s._prctl(38,1)
    s.platform.machine=lambda:'unsupported'
    s._deny_network()
try:
    subprocess.run([sys.executable,'-c',"from pathlib import Path;Path({str(marker)!r}).touch()"],
                   preexec_fn=lambda:fail({{}}),check=True)
except subprocess.SubprocessError:
    pass
else:
    raise AssertionError('unsupported filter accepted')
assert not s.Path({str(marker)!r}).exists()
''')
