"""Check the recovered public judging worker without starting a service."""
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

from tcsexam.layout import repository


def load_worker():
    path = repository() / 'assets/environments/solver/bpp-bpplib/judge/judge_worker.py'
    spec = importlib.util.spec_from_file_location('tcsexam_bpp_judge_worker', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class JudgeWorker(unittest.TestCase):
    def test_raw_records_preserve_results_and_error_classes(self):
        worker = load_worker()
        output = {'per_instance': {
            'better': {'A': 4, 'B': 8, 'K': 5, 'status': 'ok'},
            'invalid': {'A': None, 'B': 8, 'K': 5, 'status': 'timeout'},
            'equal': {'A': 5, 'B': 5, 'K': 5, 'status': 'ok'},
            'unsolved_baseline': {'A': 6, 'B': None, 'K': 5, 'status': 'ok',
                                  'anchor_baseline_unsolved': True},
        }}
        records, excluded, excluded_records, note = worker._build_records(output)
        self.assertEqual(excluded, ['equal'])
        self.assertEqual(note, '')
        self.assertEqual(excluded_records[0]['instance'], 'equal')
        self.assertEqual(excluded_records[0]['A'], 5)
        self.assertEqual(excluded_records[0]['reason'], 'b_equals_k')
        by_name = {row['instance']: row for row in records}
        self.assertEqual(by_name['better']['A'], 4)
        self.assertEqual(by_name['better']['status'], 'ok')
        self.assertIsNone(by_name['invalid']['A'])
        self.assertEqual(by_name['invalid']['status'], 'invalid')
        self.assertEqual(by_name['unsolved_baseline']['A'], 6)
        self.assertEqual(by_name['unsolved_baseline']['status'], 'ok')
        records, _, _, _ = worker._build_records({'per_instance': {
            'broken': {'A': 1, 'B': None, 'K': 2, 'status': 'ok'}}})
        self.assertEqual(records[0]['status'], 'error')
        records, excluded, excluded_records, note = worker._build_records({'reward': 0})
        self.assertIsNone(records)
        self.assertEqual(excluded, [])
        self.assertIn('no per-instance', note)

    def test_submission_unpack_rejects_path_escape(self):
        worker = load_worker()
        for name in ('../escape', '/absolute'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as folder:
                stream = io.BytesIO()
                with tarfile.open(fileobj=stream, mode='w:gz') as tar:
                    info = tarfile.TarInfo(name)
                    info.size = 1
                    tar.addfile(info, io.BytesIO(b'x'))
                with self.assertRaises((tarfile.TarError, ValueError)):
                    worker._safe_unpack(stream.getvalue(), Path(folder) / 'app')
                self.assertFalse((Path(folder) / 'escape').exists())

    def test_missing_public_instances_stop_worker_startup(self):
        worker = load_worker()
        worker.INSTANCE_SET = 'public'
        with tempfile.TemporaryDirectory() as folder:
            worker.TESTS_DIR = folder
            self.assertEqual(worker.main(), 2)


if __name__ == '__main__':
    unittest.main()
