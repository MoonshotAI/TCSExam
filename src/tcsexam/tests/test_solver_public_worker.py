"""Public worker startup honors split isolation across both shipped layouts."""
import importlib.util
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from tcsexam.layout import repository

@pytest.mark.parametrize('available,explicit,expected', [
    ({'/tests-public/instances'}, None, '/tests-public/instances'),
    ({'/tests/instances_public'}, None, '/tests/instances_public'),
    ({'/custom/public'}, '/custom/public', '/custom/public'),
])
def test_public_startup_selects_only_public_instance_tree(available, explicit, expected, tmp_path):
    path = repository() / 'assets/environments/solver/judge-runtime/judge_worker.py'
    spec = importlib.util.spec_from_file_location('public_runtime_worker', path)
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    worker.INSTANCE_SET = 'public'
    environment = {} if explicit is None else {'INSTANCES_PUBLIC_DIR': explicit}
    server = MagicMock()
    with patch.dict(worker.os.environ, environment, clear=True), \
         patch.object(worker.os.path, 'isdir', side_effect=lambda p: p in available), \
         patch.object(worker, 'WORK_DIR', tmp_path / 'work'), \
         patch.object(worker, 'ThreadingHTTPServer', return_value=server), \
         patch.object(worker.threading, 'Thread'), \
         patch.object(worker, 'preflight'):
        assert worker.main() == 0
        assert worker.os.environ['INSTANCES_DIR'] == expected
        server.serve_forever.assert_called_once()
        assert (tmp_path / 'work').is_dir()


def test_public_startup_rejects_missing_explicit_directory():
    path = repository() / 'assets/environments/solver/judge-runtime/judge_worker.py'
    spec = importlib.util.spec_from_file_location('public_runtime_worker', path)
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    worker.INSTANCE_SET = 'public'
    with patch.dict(worker.os.environ, {'INSTANCES_PUBLIC_DIR':'/missing'}, clear=True), \
         patch.object(worker.os.path, 'isdir', side_effect=lambda p: p == '/tests-public/instances'), \
         patch.object(worker, 'ThreadingHTTPServer') as server:
        assert worker.main() == 2
        server.assert_not_called()
