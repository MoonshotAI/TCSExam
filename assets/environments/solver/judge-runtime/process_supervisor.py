"""Linux subreaper for exactly one command and all of its descendants."""
from __future__ import annotations
import ctypes
import errno
import json
import os
import platform
import signal
import subprocess
import sys
import time
import tempfile
from pathlib import Path


def _prctl(option, value):
    if ctypes.CDLL(None, use_errno=True).prctl(option, value, 0, 0, 0):
        raise OSError(ctypes.get_errno(), 'prctl failed')


def _children():
    # A subreaper adopts orphaned grandchildren, even after setsid/double fork.
    found = []
    for entry in os.scandir('/proc'):
        if not entry.name.isdigit():
            continue
        try:
            stat = open(entry.path + '/stat').read().rsplit(')', 1)[1].split()
            if int(stat[1]) == os.getpid():
                found.append(int(entry.name))
        except (OSError, ValueError, IndexError):
            continue
    return found


CLEANUP_SECONDS = 5.0
FAILURE_ENV = 'TCSEXAM_EXECUTION_FAILURE_FILE'


class CleanupFailed(RuntimeError):
    pass


def _cleanup(timeout=CLEANUP_SECONDS):
    deadline = time.monotonic() + timeout
    while True:
        for pid in _children():
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except OSError as exc:
                raise CleanupFailed(f"Cannot terminate descendant {pid}: {exc}") from exc
        try:
            while os.waitpid(-1, os.WNOHANG)[0]:
                pass
        except ChildProcessError:
            return
        if time.monotonic() >= deadline:
            raise CleanupFailed("Descendants remain after the cleanup deadline")
        time.sleep(0.005)


def landlock_abi():
    if os.geteuid() != 0:
        raise RuntimeError('Judge isolation requires a root supervisor')
    libc = ctypes.CDLL(None, use_errno=True)
    abi = libc.syscall(444, 0, 0, 1)
    if abi < 0:
        error = ctypes.get_errno()
        raise RuntimeError(f'Landlock unavailable: errno={error} ({os.strerror(error)}); enable the LSM and allow its syscalls')
    if abi < 3:
        raise RuntimeError(f'Landlock ABI {abi} is unsupported; ABI >= 3 is required for truncate protection')
    return abi


def _landlock(policy):
    libc = ctypes.CDLL(None, use_errno=True)
    landlock_abi()
    # WRITE_FILE, REMOVE_*, MAKE_*, REFER and TRUNCATE. Reads/execute stay
    # available to the compiler and solver; only writes are confined.
    handled = 2 | sum(1 << bit for bit in range(4, 15))
    class Ruleset(ctypes.Structure):
        _fields_ = [('handled_access_fs', ctypes.c_uint64)]
    class Beneath(ctypes.Structure):
        _pack_ = 1
        _fields_ = [('allowed_access', ctypes.c_uint64), ('parent_fd', ctypes.c_int32)]
    rules = Ruleset(handled)
    rules_fd = libc.syscall(444, ctypes.byref(rules), ctypes.sizeof(rules), 0)
    if rules_fd < 0:
        raise OSError(ctypes.get_errno(), 'Cannot create Landlock ruleset')
    try:
        for kind in ('directories', 'files'):
            for path in policy[kind]:
                fd = os.open(path, os.O_PATH | os.O_NOFOLLOW)
                try:
                    # Only build directories permit symlink creation; output
                    # trees later read by the checker do not.
                    access = handled if kind == 'directories' else 2 | (1 << 14)
                    if not policy.get('symlinks'):
                        access &= ~(1 << 12)
                    rule = Beneath(access, fd)
                    if libc.syscall(445, rules_fd, 1, ctypes.byref(rule), 0):
                        raise OSError(ctypes.get_errno(), 'Cannot install Landlock path rule')
                finally:
                    os.close(fd)
        if libc.syscall(446, rules_fd, 0):
            raise OSError(ctypes.get_errno(), 'Cannot restrict untrusted filesystem writes')
    finally:
        os.close(rules_fd)


def _deny_network():
    """Restrict submission networking, preserving private local IPC.

    The trusted worker retains its HTTP service and tunnel. This filter is
    inherited by the submission's children across fork and exec.
    """
    if sys.platform != 'linux' or platform.machine() != 'x86_64':
        raise RuntimeError('Judge network isolation requires Linux x86-64')

    class Instruction(ctypes.Structure):
        _fields_ = [('code', ctypes.c_ushort), ('jt', ctypes.c_ubyte),
                    ('jf', ctypes.c_ubyte), ('k', ctypes.c_uint32)]

    class Program(ctypes.Structure):
        _fields_ = [('length', ctypes.c_ushort), ('filter', ctypes.POINTER(Instruction))]

    deny = 0x00050000 | errno.EPERM  # SECCOMP_RET_ERRNO
    allow = 0x7fff0000
    rules = [
        (0x20, 0, 0, 4),             # load seccomp_data.arch
        (0x15, 1, 0, 0xc000003e),    # AUDIT_ARCH_X86_64
        (0x06, 0, 0, 0x80000000),    # kill a different syscall ABI (e.g. int 0x80)
        (0x20, 0, 0, 0),             # load seccomp_data.nr
        (0x35, 0, 1, 512),           # reject x32, including its old 512..547 range
        (0x06, 0, 0, deny),
        (0x15, 0, 4, 53),            # socketpair: permit AF_UNIX only
        (0x20, 0, 0, 16),            # load args[0] (socket domain)
        (0x15, 0, 1, 1),
        (0x06, 0, 0, allow),
        (0x06, 0, 0, deny),
    ]
    # socket, connect, accept, bind, listen, accept4; io_uring can otherwise
    # perform networking without invoking the corresponding socket syscalls.
    for number in (41, 42, 43, 49, 50, 288, 425, 426, 427):
        rules.extend([(0x15, 0, 1, number), (0x06, 0, 0, deny)])
    rules.append((0x06, 0, 0, allow))
    instructions = (Instruction * len(rules))(*(Instruction(*rule) for rule in rules))
    program = Program(len(rules), instructions)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(22, 2, ctypes.byref(program), 0, 0):  # PR_SET_SECCOMP, FILTER
        raise OSError(ctypes.get_errno(), 'Cannot restrict submission network access')


def _drop_privileges(policy):
    _prctl(38, 1)  # PR_SET_NO_NEW_PRIVS: disables setuid/file capabilities.
    _landlock(policy)
    _deny_network()
    os.setgroups([])
    os.setgid(65534)
    os.setuid(65534)
    os.umask(0o022)


def preflight():
    abi = landlock_abi()
    _prctl(36, 1)
    with tempfile.TemporaryDirectory(prefix='tcsexam-preflight-') as temporary:
        root = Path(temporary)
        root.chmod(0o755)
        allowed = root / 'allowed'
        allowed.mkdir()
        os.chown(allowed, 65534, 65534)
        sentinel = root / 'protected'
        sentinel.write_text('trusted')
        sentinel.chmod(0o666)
        policy = {'directories': [str(allowed)], 'files': ['/dev/null']}
        code = """import errno,json,os,pathlib,socket,subprocess,sys
pathlib.Path(sys.argv[1]).write_text('ok')
try:
    pathlib.Path(sys.argv[2]).write_text('corrupt')
except PermissionError:
    pass
else:
    raise RuntimeError('Landlock write protection failed')
assert os.getuid()==os.getgid()==65534 and not os.getgroups()
probe = '''import errno,socket
for family,kind in ((socket.AF_INET,socket.SOCK_STREAM),(socket.AF_INET6,socket.SOCK_STREAM),(socket.AF_INET,socket.SOCK_DGRAM),(socket.AF_UNIX,socket.SOCK_STREAM)):
    try:
        socket.socket(family,kind)
    except OSError as exc:
        assert exc.errno==errno.EPERM, exc
    else:
        raise RuntimeError('Submission network isolation failed')
'''
exec(probe)
subprocess.run([sys.executable,'-I','-c',probe],check=True,timeout=1)
left,right=socket.socketpair()
left.sendall(b'ipc')
assert right.recv(3)==b'ipc'
left.close();right.close()
print(json.dumps({'uid':os.getuid(),'gid':os.getgid(),'groups':os.getgroups(),'network_denied':True,'descendant_network_denied':True}))
"""
        result = subprocess.run([sys.executable, '-I', '-c', code,
                                 str(allowed / 'output'), str(sentinel)],
                                preexec_fn=lambda: _drop_privileges(policy),
                                capture_output=True, text=True, timeout=3)
        if result.returncode or sentinel.read_text() != 'trusted':
            raise RuntimeError('Judge isolation enforcement probe failed: ' + result.stderr[-500:])
        print(json.dumps({'ok': True, 'landlock_abi': abi, **json.loads(result.stdout)}))
    return 0


def main():
    if sys.argv[1] == 'preflight':
        return preflight()
    _prctl(36, 1)  # PR_SET_CHILD_SUBREAPER, before launching any descendants.
    # Command arguments, never shell interpolation; the caller selects bash
    # explicitly where the frozen judge command is a shell string.
    failure_file = os.environ.get(FAILURE_ENV, '')
    restricted = sys.argv[1] == 'untrusted'
    if restricted:
        os.environ.pop(FAILURE_ENV, None)
    command = json.loads(sys.argv[2])
    policy = json.loads(sys.argv[3]) if restricted else {}
    scratch = None
    if restricted:
        scratch = tempfile.TemporaryDirectory(prefix='tcsexam-child-')
        os.chown(scratch.name, 65534, 65534)
        policy['directories'].append(scratch.name)
        policy['files'].append('/dev/null')
        os.environ['TMPDIR'] = scratch.name
        # The shipped QBF wrapper supplies an explicit /tmp template to
        # mktemp. Keep that interface within this invocation's private tmp.
        bin_dir = Path(scratch.name) / 'bin'
        bin_dir.mkdir()
        shim = bin_dir / 'mktemp'
        shim.write_text('#!' + sys.executable + '\nimport os,sys\n'
            'args=[os.environ["TMPDIR"]+x[4:] if x.startswith("/tmp/") else x for x in sys.argv[1:]]\n'
            'os.execv("/usr/bin/mktemp",["mktemp",*args])\n')
        shim.chmod(0o755)
        os.environ['PATH'] = str(bin_dir) + ':' + os.environ['PATH']
    stopped = [False]
    process = None
    def stop(signum, _frame):
        if signum == signal.SIGUSR1 or not restricted:
            stopped[0] = True
        elif process is not None:
            # A scorer's first TERM preserves its original grace period.
            # Only explicit force-cleanup terminates the supervisor's wait.
            try:
                os.killpg(process.pid, signum)
            except ProcessLookupError:
                pass
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGUSR1, stop)
    try:
        if restricted:
            # This helper is single-threaded. Only this fork uses preexec_fn.
            process = subprocess.Popen(command, preexec_fn=lambda: _drop_privileges(policy),
                                       start_new_session=True)
        else:
            process = subprocess.Popen(command, start_new_session=True)
        while process.poll() is None and not stopped[0]:
            time.sleep(0.005)
        result = process.returncode if process.returncode is not None else -signal.SIGKILL
    finally:
        try:
            _cleanup()
        except CleanupFailed as exc:
            if failure_file:
                Path(failure_file).write_text(json.dumps({'error': str(exc), 'supervisor_pid': os.getpid()}))
            # Do not remove a live process's filesystem or report completion.
            print(str(exc), file=sys.stderr, flush=True)
            return 125
        if scratch:
            scratch.cleanup()
    return result if result >= 0 else 128 - result


if __name__ == '__main__':
    sys.exit(main())
