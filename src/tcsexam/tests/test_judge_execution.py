"""Bounded filesystem/call-matrix checks; real uid/Landlock tests run remotely."""
import ast
import importlib.util
import os
from pathlib import Path
import pytest
from tcsexam.layout import repository

RUNTIME = repository() / 'assets/environments/solver/judge-runtime'
spec = importlib.util.spec_from_file_location('judge_execution_test', RUNTIME / 'execution.py')
execution = importlib.util.module_from_spec(spec)
spec.loader.exec_module(execution)


def test_every_scoring_subprocess_has_an_audited_classification():
    files = sorted((repository() / 'assets/environments/solver').glob('*/judge/scoring.py'))
    assert len(files) == 30
    count = 0
    for path in files:
        for function in ast.walk(ast.parse(path.read_text())):
            if not isinstance(function, ast.FunctionDef):
                continue
            for call in ast.walk(function):
                if (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                        and isinstance(call.func.value, ast.Name)
                        and call.func.value.id == 'subprocess'
                        and call.func.attr in ('run', 'Popen', 'call', 'check_call', 'check_output')):
                    assert function.name in execution.UNTRUSTED_FUNCTIONS | execution.TRUSTED_FUNCTIONS, (path, function.name)
                    count += 1
    assert count == 76


@pytest.mark.parametrize('kind', ['symlink', 'hardlink', 'fifo'])
def test_submission_links_and_special_files_are_rejected(tmp_path, kind):
    app = tmp_path / 'app'
    app.mkdir()
    source = app / 'ordinary'
    source.write_text('x')
    if kind == 'symlink':
        (app / 'link').symlink_to('/tests/reference.json')
    elif kind == 'hardlink':
        os.link(source, app / 'link')
    else:
        os.mkfifo(app / 'fifo')
    with pytest.raises(ValueError):
        execution.validate_tree(app)


def test_environment_keeps_only_required_numeric_solver_limits():
    env = execution.clean_environment({'TCSEXAM_TOKEN_SECRET': 'private', 'LD_PRELOAD': '/app/x.so',
        'PYTHONPATH': '/app', 'PATH': '/app', 'BPP_TIME_POOL': '30.000', 'QBF_PROOF_PATH': '/tmp/a.qrp',
        'MR_INSTANCE_SECONDS': '300', 'OTHER_TIME_LIMIT': 'secret'}, '/app')
    assert env['BPP_TIME_POOL'] == '30.000'
    assert env['QBF_PROOF_PATH'] == '/tmp/a.qrp'
    assert env['MR_INSTANCE_SECONDS'] == '300'
    assert not {'TCSEXAM_TOKEN_SECRET','LD_PRELOAD','PYTHONPATH','OTHER_TIME_LIMIT'} & env.keys()
    assert env['PATH'].startswith('/opt/minizinc/bin:/opt/gp/bin:/usr/local/')
    assert '/app' not in env['PATH']


@pytest.mark.parametrize('mode', ['normal', 'error', 'timeout'])
def test_supervisor_reaps_independent_sessions_and_double_fork(tmp_path, mode):
    import json
    import signal
    import subprocess
    import sys
    child = ('import os,pathlib,time; os.fork(); '
             'pathlib.Path("' + str(tmp_path) + '/pid-"+str(os.getpid())).touch(); time.sleep(20)')
    parent = tmp_path / 'parent.py'
    parent.write_text(
        'import pathlib,subprocess,sys,time\n'
        f'subprocess.Popen([sys.executable,"-c",{child!r}], start_new_session=True)\n'
        f'directory=pathlib.Path({str(tmp_path)!r})\n'
        'deadline=time.monotonic()+3\n'
        'while len(list(directory.glob("pid-*"))) < 2:\n'
        ' if time.monotonic()>deadline: raise RuntimeError("synthetic descendants did not start")\n'
        ' time.sleep(.005)\n'
        'print("ready",flush=True)\n'
        + ('time.sleep(20)\n' if mode == 'timeout' else 'sys.exit(' + ('7' if mode == 'error' else '0') + ')\n'))
    command = [sys.executable, '-I', str(RUNTIME / 'process_supervisor.py'), 'trusted',
               json.dumps([sys.executable, str(parent)])]
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as process:
        assert process.stdout.readline().strip() == 'ready'
        if mode == 'timeout':
            process.send_signal(signal.SIGTERM)
        # Allow the supervisor's five-second cleanup deadline plus process
        # scheduling and pipe teardown; the assertions below still require
        # successful cleanup and the exact exit status.
        stdout, stderr = process.communicate(timeout=15)
        assert process.returncode == {'normal': 0, 'error': 7, 'timeout': 137}[mode], (stdout, stderr)
    for pidfile in tmp_path.glob('pid-*'):
        assert not Path('/proc', pidfile.name.removeprefix('pid-')).exists()


@pytest.mark.parametrize('link_type', ['symlink', 'hardlink'])
def test_online_archive_rejects_links_before_extraction(tmp_path, link_type):
    import io
    import sys
    import tarfile
    from unittest.mock import patch
    with patch.object(sys, 'path', [str(RUNTIME), *sys.path]):
        worker_spec = importlib.util.spec_from_file_location('isolated_archive_worker', RUNTIME / 'judge_worker.py')
        worker = importlib.util.module_from_spec(worker_spec)
        worker_spec.loader.exec_module(worker)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w') as archive:
        member = tarfile.TarInfo('link')
        member.type = tarfile.SYMTYPE if link_type == 'symlink' else tarfile.LNKTYPE
        member.linkname = '/tests/reference.json'
        archive.addfile(member)
    with pytest.raises(ValueError):
        worker._safe_unpack(buffer.getvalue(), tmp_path / 'app')
    assert not (tmp_path / 'app/link').is_symlink()


def load_runtime(name):
    path = RUNTIME / (name + '.py')
    spec = importlib.util.spec_from_file_location('execution_regression_' + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cleanup_deadline_and_kill_failure_are_explicit():
    import errno
    import time
    from unittest.mock import patch
    supervisor = load_runtime('process_supervisor')
    started = time.monotonic()
    with patch.object(supervisor, '_children', return_value=[123456789]), \
         patch.object(supervisor.os, 'kill'), \
         patch.object(supervisor.os, 'waitpid', return_value=(0, 0)):
        with pytest.raises(supervisor.CleanupFailed, match='deadline'):
            supervisor._cleanup(timeout=0.01)
    assert time.monotonic() - started < 1
    with patch.object(supervisor, '_children', return_value=[123456789]), \
         patch.object(supervisor.os, 'kill', side_effect=PermissionError(errno.EPERM, 'denied')):
        with pytest.raises(supervisor.CleanupFailed, match='Cannot terminate'):
            supervisor._cleanup(timeout=0.01)


def test_jssp_atomic_output_directory_excludes_materialized_input(tmp_path):
    from types import SimpleNamespace
    from unittest.mock import patch
    output = tmp_path / 'out-fixture' / 'answer.sol'
    materialized = tmp_path / 'fixture.txt'
    materialized.write_text('trusted')
    frame = SimpleNamespace(f_code=SimpleNamespace(co_name='run_solver'),
                            f_locals={'out_path': str(output)})
    with patch.object(execution, 'own_tree') as own:
        policy, directory = execution._writable(frame, {}, 'jsplib-jssp')
    assert directory is None
    assert set(policy['directories']) == {'/app', str(output.parent)}
    assert str(tmp_path) not in policy['directories']
    assert not policy['files']
    own.assert_called_once_with(output.parent)
    assert materialized.read_text() == 'trusted'


def test_sealed_private_build_retains_read_execute_access(tmp_path):
    from unittest.mock import patch
    build = tmp_path / 'build'
    build.mkdir(mode=0o700)
    program = build / 'solver'
    program.write_text('synthetic')
    program.chmod(0o700)
    with patch.object(execution.os, 'chown'):
        execution._seal_build_tree(build)
    assert build.stat().st_mode & 0o777 == 0o705
    assert program.stat().st_mode & 0o777 == 0o705
    assert not program.stat().st_mode & 0o022


def test_trusted_supervisor_preserves_inner_failure_marker(tmp_path):
    import json
    import subprocess
    import sys
    environment = dict(os.environ, TCSEXAM_EXECUTION_FAILURE_FILE=str(tmp_path / 'failure.json'))
    command = [sys.executable, '-I', str(RUNTIME / 'process_supervisor.py'), 'trusted',
               json.dumps([sys.executable, '-c', 'import os; print(os.getenv("TCSEXAM_EXECUTION_FAILURE_FILE"))'])]
    result = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == environment['TCSEXAM_EXECUTION_FAILURE_FILE']


def test_candidate_sigterm_grace_matches_direct_execution(tmp_path):
    import json
    import subprocess
    import sys
    candidate = tmp_path / 'candidate.py'
    candidate.write_text('import os,signal,time\n'
                         'def save(signum, frame):\n os.write(1,b"saved-at-term\\n")\n raise SystemExit(0)\n'
                         'signal.signal(signal.SIGTERM,save)\nos.write(1,b"ready\\n")\ntime.sleep(20)\n')
    # Signal forwarding itself needs no privileged identity change. The
    # separate root fixture verifies the real uid/Landlock boundary.
    wrapper = tmp_path / 'signal_supervisor.py'
    wrapper.write_text('import sys\nsys.path.insert(0,' + repr(str(RUNTIME)) + ')\n'
                       'import process_supervisor as s\ns._drop_privileges=lambda policy:None\n'
                       's.os.chown=lambda *a,**k:None\nraise SystemExit(s.main())\n')
    commands = [[sys.executable, str(candidate)],
                [sys.executable, str(wrapper), 'untrusted', json.dumps([sys.executable, str(candidate)]),
                 json.dumps({'directories': [str(tmp_path)], 'files': []})]]
    for command in commands:
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as process:
            assert process.stdout.readline().strip() == 'ready'
            process.terminate()
            output, error = process.communicate(timeout=5)
            assert process.returncode == 0, error
            assert output.strip() == 'saved-at-term'


def test_startup_preflight_failure_prevents_listener(tmp_path):
    from unittest.mock import patch
    worker = load_runtime('judge_worker')
    worker.WORK_DIR = tmp_path
    worker.INSTANCE_SET = 'hidden'
    with patch.object(worker, 'preflight', side_effect=RuntimeError('Landlock unavailable')), \
         patch.object(worker, 'ThreadingHTTPServer') as server:
        assert worker.main() == 2
    server.assert_not_called()
    assert 'Isolation startup failed' in worker._WORKER_ERROR
    assert (tmp_path / 'worker-error.json').exists()


def test_cleanup_failure_disables_worker_and_preserves_error_history(tmp_path):
    import json
    import subprocess
    from unittest.mock import MagicMock, patch
    worker = load_runtime('judge_worker')
    worker.WORK_DIR = tmp_path
    worker.APP_DIR = str(tmp_path / 'app')
    worker._STATE = {'next_id': 2, 'submissions': [
        {'submission': 0, 'status': 'running', 'records': None},
        {'submission': 1, 'status': 'running', 'records': None}]}
    (tmp_path / 'submissions/0/app').mkdir(parents=True)
    process = MagicMock()
    process.wait.side_effect = subprocess.TimeoutExpired('synthetic', .01)
    worker.CLEANUP_WAIT = .01
    with patch.object(worker, 'own_tree'), patch.object(worker.subprocess, 'Popen', return_value=process), \
         patch.object(worker, '_wait_pipeline', side_effect=subprocess.TimeoutExpired('synthetic', 1)):
        worker._judge_one(0)
    assert process.kill.called
    assert worker._WORKER_ERROR
    assert all(entry['status'] == 'judge_error' for entry in worker._STATE['submissions'])
    assert all(entry['status'] == 'judge_error' for entry in json.loads((tmp_path / 'submissions.json').read_text()))
    assert (tmp_path / 'worker-error.json').exists()
    # Later queued submissions do not launch another process.
    with patch.object(worker.subprocess, 'Popen') as launch:
        worker._judge_one(1)
    launch.assert_not_called()


def test_failed_worker_http_rejects_submissions_and_keeps_history(tmp_path):
    import http.client
    import json
    import threading
    worker = load_runtime('judge_worker')
    worker.WORK_DIR = tmp_path
    worker._STATE = {'next_id': 1, 'submissions': [{'submission': 0, 'status': 'running', 'records': None}]}
    worker._disable_worker('synthetic cleanup failure')
    server = worker.ThreadingHTTPServer(('127.0.0.1', 0), worker.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        for method, path, expected in [('GET', '/health', 503), ('POST', '/submit', 503),
                                       ('GET', '/submissions', 200)]:
            connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
            connection.request(method, path)
            response = connection.getresponse()
            body = json.loads(response.read())
            assert response.status == expected
            if path == '/submissions':
                assert body['worker_error'] == 'synthetic cleanup failure'
                assert body['submissions'][0]['status'] == 'judge_error'
            connection.close()
        assert worker._STATE['next_id'] == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_offline_supervision_rejects_absorbed_inner_failure(tmp_path):
    import subprocess
    import sys
    marker = tmp_path / 'execution-failure.json'
    script = tmp_path / 'offline.py'
    script.write_text('import os,pathlib,sys\nsys.path.insert(0,' + repr(str(RUNTIME)) + ')\n'
                      'from execution import supervise_script\n'
                      'def swallowed_error():\n'
                      ' pathlib.Path(os.environ["TCSEXAM_EXECUTION_FAILURE_FILE"]).write_text("cleanup failed")\n'
                      ' print("candidate build failure absorbed by the scorer",flush=True)\n'
                      'supervise_script(__file__, swallowed_error, failure_path=' + repr(str(marker)) + ')\n')
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=5)
    assert result.returncode == 125, result.stderr
    assert marker.read_text() == 'cleanup failed'
