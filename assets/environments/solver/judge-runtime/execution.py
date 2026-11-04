"""Execution boundary shared by the composed Online and Offline judges.

Only the audited build/solve calls are untrusted. Validation/decompression
commands retain the trusted checker identity. Unknown scoring calls fail
closed so new subprocess entry points require an explicit review.
"""
from __future__ import annotations
import builtins
import inspect
import io
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys

UNTRUSTED_FUNCTIONS = frozenset({'build_solver', 'compile_solver', 'run_solver', 'run_pool', 'run_instance'})
TRUSTED_FUNCTIONS = frozenset({'verify_edits', 'verify_fvs', 'verify_solution', 'materialize_instance',
    'run_validator', 'verify_cut', 'check_solution', 'materialize', 'verify_tour', 'verify_td', 'verify_vc', 'check_ctt'})
SUPERVISOR = Path(__file__).with_name('process_supervisor.py')
_ORIGINAL_POPEN = subprocess.Popen
_ORIGINAL_KILLPG = os.killpg
_ACTIVE = {}


def validate_tree(path):
    """Submission files must be ordinary private files, never links/devices."""
    path = Path(path)
    for item in [path, *path.rglob('*')]:
        info = item.lstat()
        if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
            raise ValueError(f'Unsupported submission file: {item.name}')
        if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
            raise ValueError(f'Hard-linked submission file: {item.name}')


def own_tree(path):
    path = Path(path)
    validate_tree(path)
    for item in [path, *path.rglob('*')]:
        info = item.lstat()
        os.chown(item, 65534, 65534, follow_symlinks=False)
        os.chmod(item, stat.S_IMODE(info.st_mode) & 0o777)
    # tempfile scratch parents are normally 0700. Permit traversal, while
    # preserving trusted ownership and denying writes to those parents.
    for parent in path.parents:
        if str(parent) in ('/', '/tmp', '/work', '/app'):
            break
        os.chmod(parent, stat.S_IMODE(parent.stat().st_mode) | 0o011)


def _writable(frame, keywords, task=None):
    values = frame.f_locals
    function = frame.f_code.co_name
    if function in ('build_solver', 'compile_solver'):
        directory = Path(keywords.get('cwd') or values.get('build_dir') or values.get('work_dir') or values['app_dir'])
        own_tree(directory)
        return {'directories': [str(directory)], 'files': [], 'symlinks': True}, directory
    policy = {'directories': ['/app'], 'files': []}
    if values.get('out_dir') or (task == 'jsplib-jssp' and values.get('out_path')):
        directory = Path(values['out_dir']) if values.get('out_dir') else Path(values['out_path']).parent
        if task == 'jsplib-jssp' and not directory.name.startswith('out-'):
            raise RuntimeError('JSSP requires a dedicated per-instance output directory')
        directory.mkdir(parents=True, exist_ok=True)
        own_tree(directory)
        policy['directories'].append(str(directory))
    else:
        # An explicit output pathname is writable; sibling instances and
        # checker files retain their ownership and Landlock protection.
        for key in ('out_path', 'proof_path'):
            value = values.get(key)
            if not value:
                continue
            output = Path(value)
            output.parent.mkdir(parents=True, exist_ok=True)
            if output.is_symlink():
                raise ValueError('Linked solver output')
            if not output.exists():
                output.touch()
            os.chown(output, 65534, 65534, follow_symlinks=False)
            policy['files'].append(str(output))
    return policy, None


def clean_environment(environment, cwd):
    result = {'PATH': '/opt/minizinc/bin:/opt/gp/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
              'HOME': str(cwd), 'TMPDIR': '/tmp', 'LANG': 'C.UTF-8'}
    # These are the numerical limits explicitly passed by the frozen scorers.
    for key, value in environment.items():
        if (re.fullmatch(r'[A-Z0-9_]+_(?:TIME_POOL|TIME_LIMIT|INSTANCE_SECONDS|TIMEOUT|BUDGET)', key)
                or key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')):
            if re.fullmatch(r'[0-9.]+', str(value)):
                result[key] = str(value)
    if 'QBF_PROOF_PATH' in environment:
        result['QBF_PROOF_PATH'] = environment['QBF_PROOF_PATH']
    return result


def _remove_output_links(directory):
    if directory is None or not directory.exists():
        return
    for parent, folders, files in os.walk(directory, followlinks=False):
        for name in folders + files:
            path = Path(parent) / name
            if path.is_symlink() and not path.resolve().is_relative_to(directory.resolve()):
                path.unlink()


def _seal_build_tree(directory):
    for path in [directory, *directory.rglob('*')]:
        os.chown(path, 0, 0, follow_symlinks=False)
        if not path.is_symlink():
            mode = stat.S_IMODE(path.stat().st_mode)
            # Preserve the builder's read/execute access after ownership
            # changes, including a legitimate umask 077 / mode 0700 output.
            os.chmod(path, (mode & ~0o022) | ((mode & 0o500) >> 6))


def _guard_writes():
    # Frozen Python scorers may open an output pathname as root after a solver
    # invocation. Deny both final and intermediate symlinks for every write.
    def wrap(original):
        def guarded(file, mode='r', *args, **kwargs):
            if isinstance(file, (str, bytes, os.PathLike)) and any(x in mode for x in 'wax+'):
                path = Path(os.fsdecode(file)).absolute()
                for parent in [path, *path.parents]:
                    if parent.is_symlink():
                        raise ValueError('Refusing judge write through a symlink')
                if kwargs.get('opener') is not None:
                    raise ValueError('Custom write opener is unsupported in a trusted checker')
                kwargs['opener'] = lambda name, flags: os.open(name, flags | os.O_NOFOLLOW, 0o666)
            return original(file, mode, *args, **kwargs)
        return guarded
    builtins.open = wrap(builtins.open)
    io.open = wrap(io.open)


def preflight():
    """Probe the actual image/kernel/seccomp/uid boundary before accepting work."""
    command = [sys.executable, '-I', str(SUPERVISOR), 'preflight']
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f'Judge isolation preflight failed: {exc}') from exc
    if result.returncode:
        raise RuntimeError('Judge isolation preflight failed: ' + result.stderr[-1000:])
    return json.loads(result.stdout)


def install(config):
    preflight()
    allowed = sorted(os.sched_getaffinity(0))
    class JudgeProcess(_ORIGINAL_POPEN):
        def __init__(self, args, *positional, **keywords):
            if (config.get('relative_cpu_indices', True) and isinstance(args, (list, tuple))
                    and len(args) >= 4 and Path(str(args[0])).name == 'taskset' and args[1] == '-c'):
                indices = str(args[2]).split(',')
                if not all(x.isdigit() and int(x) < len(allowed) for x in indices):
                    raise RuntimeError('Checker CPU index exceeds the allocated worker CPUs')
                args = list(args)
                args[2] = ','.join(str(allowed[int(x)]) for x in indices)
            frame = inspect.currentframe().f_back
            while frame and Path(frame.f_code.co_filename).name not in ('scoring.py', 'verify_qbf.py', 'sygus_check.py'):
                frame = frame.f_back
            self._untrusted = False
            self._output_directory = None
            if frame and Path(frame.f_code.co_filename).name == 'scoring.py':
                function = frame.f_code.co_name
                # The gp scorer's bunzip2 input stream is trusted preparation.
                preparation = isinstance(args, (list, tuple)) and args[0] == 'bunzip2'
                if function in UNTRUSTED_FUNCTIONS and not preparation:
                    if positional or keywords.get('shell') or keywords.get('preexec_fn'):
                        raise RuntimeError('Unsupported untrusted subprocess options')
                    policy, self._output_directory = _writable(frame, keywords, config.get("task"))
                    cwd = keywords.get('cwd') or '/app'
                    keywords['cwd'] = cwd
                    keywords['env'] = clean_environment(keywords.get('env') or os.environ, cwd)
                    if os.environ.get('TCSEXAM_EXECUTION_FAILURE_FILE'):
                        keywords['env']['TCSEXAM_EXECUTION_FAILURE_FILE'] = os.environ['TCSEXAM_EXECUTION_FAILURE_FILE']
                    for key in ('user', 'group', 'extra_groups'):
                        keywords.pop(key, None)  # legacy Offline kwargs; helper owns the identity change
                    args = [sys.executable, '-I', str(SUPERVISOR), 'untrusted', json.dumps(list(args)), json.dumps(policy)]
                    keywords['start_new_session'] = True
                    self._untrusted = True
                elif function not in TRUSTED_FUNCTIONS and not preparation:
                    raise RuntimeError(f'Unaudited scoring subprocess: {function}')
            super().__init__(args, *positional, **keywords)
            if self._untrusted:
                _ACTIVE[self.pid] = self
        def send_signal(self, sig):
            # The supervisor must survive long enough to reap independent
            # sessions, including when subprocess.run calls kill() on timeout.
            super().send_signal(signal.SIGUSR1 if self._untrusted and sig == signal.SIGKILL else sig)
        def wait(self, timeout=None):
            result = super().wait(timeout)
            if self._untrusted:
                _ACTIVE.pop(self.pid, None)
                _remove_output_links(self._output_directory)
                if self._output_directory and str(self._output_directory) != "/app":
                    _seal_build_tree(self._output_directory)
            return result
    def kill_group(pid, sig):
        if pid in _ACTIVE:
            _ACTIVE[pid].send_signal(sig)
        else:
            _ORIGINAL_KILLPG(pid, sig)
    subprocess.Popen = JudgeProcess
    os.killpg = kill_group
    _guard_writes()


def supervise_script(script, main, *, failure_path=None):
    """An Offline unit cannot absorb a descendant cleanup failure as a score."""
    if os.environ.pop('TCSEXAM_SUPERVISED', '') == '1':
        main()
        return
    failure_path = Path(failure_path or '/work/execution-failure.json')
    failure_path.parent.mkdir(parents=True, exist_ok=True)
    if failure_path.exists():
        raise RuntimeError('Offline worker has a persisted execution failure')
    environment = dict(os.environ, TCSEXAM_SUPERVISED='1',
                       TCSEXAM_EXECUTION_FAILURE_FILE=str(failure_path))
    command = [sys.executable, '-I', str(SUPERVISOR), 'trusted',
               json.dumps([sys.executable, '-I', str(Path(script).resolve())])]
    process = _ORIGINAL_POPEN(command, env=environment)
    while True:
        if failure_path.exists():
            process.send_signal(signal.SIGUSR1)
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    pass
            raise SystemExit(125)
        try:
            result = process.wait(timeout=0.2)
            break
        except subprocess.TimeoutExpired:
            continue
    raise SystemExit(125 if failure_path.exists() else result)
