"""Keep every offline Docker client on the same API negotiation path."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tcsexam.layout import repository


def load_module():
    path = repository() / 'assets/environments/solver/offline-runtime/docker_api.py'
    spec = importlib.util.spec_from_file_location('tcsexam_offline_docker_api', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_admission():
    import sys
    path = repository() / 'assets/environments/solver/offline-runtime/admission.py'
    spec = importlib.util.spec_from_file_location('tcsexam_offline_admission', path)
    module = importlib.util.module_from_spec(spec)
    original_path = sys.path.copy()
    try:
        sys.path.insert(0, str(path.parent))
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = original_path
    return module


class OfflineDockerAPI(unittest.TestCase):
    def test_minimum_version_is_negotiated_and_reused(self):
        module = load_module()
        calls = []
        class Connection:
            def __init__(self, path, timeout):
                self.path = path
                self.response = None
            def request(self, method, path, body, headers):
                calls.append(path)
                if path.startswith('/v1.41/'):
                    payload = {'message': 'Minimum supported API version is 1.44, please upgrade your client'}
                    self.response = (400, json.dumps(payload).encode())
                else:
                    self.response = (200, b'{"ok":true}')
            def getresponse(self):
                status, data = self.response
                class Response:
                    def read(self):
                        return data
                response = Response()
                response.status = status
                return response
            def close(self):
                pass
        module.UnixHTTP = Connection
        client = module.Docker()
        self.assertEqual(client.call('GET', '/info'), {'ok': True})
        self.assertEqual(client.call('GET', '/info'), {'ok': True})
        self.assertEqual(calls, ['/v1.41/info', '/v1.44/info', '/v1.44/info'])

    def test_controller_identification_skips_unrelated_containers(self):
        module = load_admission()
        own_id = 'a' * 64
        other_id = 'b' * 64
        own = '0::/docker/' + own_id
        calls = []
        class FakeDocker:
            def containers(self):
                return [{'Id': other_id, 'Labels': {'org.tcsexam.public-judge.controller': '1'},
                         'State': 'running'},
                        {'Id': own_id, 'Labels': {'org.tcsexam.public-judge.controller': '1'},
                         'State': 'running'}]
            def inspect(self, identity):
                calls.append(identity)
                if identity != own_id:
                    raise TimeoutError('unrelated controller must not be inspected')
                return {'Id': identity, 'State': {'Pid': 4242}}
        with patch.object(module.Path, 'read_text', return_value=own):
            result = module.identify_controller(FakeDocker())
        self.assertEqual(result['Id'], own_id)
        self.assertEqual(calls, [own_id])

    def test_resource_usage_does_not_inspect_other_controllers(self):
        module = load_admission()
        calls = []
        class FakeDocker:
            def containers(self):
                return [{'Id': 'old-controller', 'State': 'running',
                         'Labels': {'org.tcsexam.public-judge.controller': '1'}},
                        {'Id': 'unit-id', 'State': 'running',
                         'Labels': {'org.tcsexam.public-judge.unit': 'bpp',
                                    'org.tcsexam.public-judge.disk_mb': '8192'}}]
            def inspect(self, identity):
                calls.append(identity)
                if identity != 'unit-id':
                    raise TimeoutError('unrelated controller must not be inspected')
                return {'Id': identity, 'HostConfig': {'NanoCpus': 4_000_000_000,
                        'Memory': 8192*1024**2, 'CpusetCpus': '0-3'}}
        with patch.object(module.Path, 'read_text', return_value='0::/docker/self'):
            used_cpu, _, pinned, _, _ = module.usage(FakeDocker(), {'Id': 'self'})
        self.assertEqual(used_cpu, 5)
        self.assertEqual(pinned, {0, 1, 2, 3})
        self.assertEqual(calls, ['unit-id'])

    def test_all_offline_variants_share_the_implementation(self):
        root = repository()
        shared_users = 0
        for name in ('docker_api.py', 'admission.py'):
            expected = (root / 'assets/environments/solver/offline-runtime' / name).read_bytes()
            paths = [task / 'tests/runtime' / name
                     for task in (root / 'tasks/solver/offline').iterdir() if task.is_dir()]
            self.assertEqual(len(paths), 30)
            for path in paths:
                with self.subTest(task=path.parts[-4], file=name):
                    if path.is_file():
                        self.assertEqual(path.read_bytes(), expected)
                    else:
                        dockerfile = path.parent.parent / 'Dockerfile'
                        self.assertIn('assets/environments/solver/offline-runtime',
                                      dockerfile.read_text())
                        shared_users += 1
        self.assertEqual(shared_users, 50)


if __name__ == '__main__':
    unittest.main()
