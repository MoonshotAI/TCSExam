"""Exercise complete-image acquisition and failure before any model launch."""
from argparse import Namespace
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
from subprocess import CompletedProcess
import tempfile
import sys
import unittest
from unittest.mock import patch

from tcsexam.cli import main
from tcsexam.layout import repository, selection
from tcsexam.setup import artifacts, host_support_targets, inspect_image, offline_host_capacity, setup_selection


class Setup(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.root = repository()
        _, self.rows = selection(self.root, 'full', task='dijkstra-universal')
        self.ref = 'registry.example/image@sha256:' + 'a'*64
        self.products = self.folder/'artifacts.json'
        self.products.write_text(json.dumps({'images': [{
            'id': 'complete-fixture', 'image': self.ref,
            'platform': 'linux/amd64', 'content_digest': 'sha256:'+'b'*64}],
            'tasks': {self.rows[0]['path']: {'development': 'complete-fixture',
                                          'verifier': 'complete-fixture'}}}))
        self.args = Namespace(artifacts=self.products, image_map=None,
                              cache=self.folder/'cache', pull_policy='missing', docker_context=None)
        self.support = patch('tcsexam.setup.host_support_targets', return_value=[])
        self.support.start()
        self.addCleanup(self.support.stop)

    def test_setup_needs_no_key_and_complete_images_bypass_source_inputs(self):
        output = self.folder/'setup.json'
        with patch.dict('os.environ', {}, clear=True), \
                patch('tcsexam.setup.inspect_image', return_value={
                    'id': 'sha256:fixture', 'reference': self.ref, 'platform': 'linux/amd64'}), \
                patch('tcsexam.setup.subprocess.run') as execute, redirect_stdout(io.StringIO()):
            self.assertEqual(main(['setup', '--root', str(self.root), '--suite', 'full',
                '--task', self.rows[0]['id'], '--artifacts', str(self.products),
                '--cache', str(self.args.cache), '--output', str(output)]), 0)
            execute.assert_not_called()
        report = json.loads(output.read_text())
        self.assertTrue(report['host_prepared'])
        self.assertFalse(report['model_started'])
        self.assertTrue(list(self.args.cache.glob('hosts/*.json')))

    def test_missing_image_is_pulled_then_its_digest_is_inspected(self):
        with patch('tcsexam.setup.inspect_image', side_effect=[None, {
                'id': 'sha256:fixture', 'reference': self.ref, 'platform': 'linux/amd64'}]), \
                patch('tcsexam.setup.subprocess.run', return_value=CompletedProcess([], 0)) as execute, \
                redirect_stdout(io.StringIO()):
            self.assertTrue(setup_selection(self.root, self.rows, self.args)['host_prepared'])
        self.assertEqual(execute.call_args.args[0], ['docker', 'pull', self.ref])

    def test_failed_acquisition_never_starts_harbor_or_writes_job(self):
        output = self.folder/'job.json'
        with patch('tcsexam.setup.inspect_image', return_value=None), \
                patch('tcsexam.setup.subprocess.run', return_value=CompletedProcess([], 1)), \
                patch('tcsexam.cli.subprocess.call') as launch, redirect_stdout(io.StringIO()), \
                patch('tcsexam.cli.argparse.ArgumentParser.exit', side_effect=ValueError('cli failure')):
            with self.assertRaises(ValueError):
                main(['run', '--root', str(self.root), '--suite', 'full', '--task', self.rows[0]['id'],
                      '--artifacts', str(self.products), '--output', str(output)])
        launch.assert_not_called()
        self.assertFalse(output.exists())

    def test_run_uses_the_same_python_and_harbor_package_as_setup(self):
        output = self.folder/'job.json'
        with patch('tcsexam.setup.setup_selection'), patch('tcsexam.cli.doctor', return_value=0), \
                patch('tcsexam.cli.prepare', return_value={'tasks': []}), \
                patch('tcsexam.cli.subprocess.call', return_value=0) as launch, \
                patch.dict('os.environ', {'TCSEXAM_API_KEY': 'fixture'}), redirect_stdout(io.StringIO()):
            self.assertEqual(main(['run', '--root', str(self.root), '--suite', 'full',
                '--task', self.rows[0]['id'], '--output', str(output)]), 0)
        self.assertEqual(launch.call_args.args[0], [sys.executable, '-m', 'tcsexam.harbor_launch',
                                                  'run', '--config', str(output.resolve())])

    def test_run_passes_the_side_loaded_probe_to_harbor(self):
        output = self.folder/'job.json'
        probe = 'tcsexam/upstream-alpine'
        preparation = {'host_support': [{'support_kind': 'harbor_kernel_probe',
                                        'image': self.ref, 'local_image': probe}]}
        with patch('tcsexam.setup.setup_selection', return_value=preparation), \
                patch('tcsexam.cli.doctor', return_value=0), \
                patch('tcsexam.cli.prepare', return_value={'tasks': []}), \
                patch('tcsexam.cli.subprocess.call', return_value=0) as launch, \
                patch.dict('os.environ', {'TCSEXAM_API_KEY': 'fixture'}), redirect_stdout(io.StringIO()):
            self.assertEqual(main(['run', '--root', str(self.root), '--suite', 'full',
                '--task', self.rows[0]['id'], '--cache', str(self.args.cache),
                '--output', str(output)]), 0)
        self.assertEqual(launch.call_args.kwargs['env']['TCSEXAM_HARBOR_KERNEL_PROBE_IMAGE'], probe)
        self.assertEqual(launch.call_args.kwargs['env']['TCSEXAM_CACHE'], str(self.args.cache))

    def test_harbor_launch_applies_the_verified_probe_and_normalized_context(self):
        from harbor.environments.docker.docker import DockerEnvironment
        from tcsexam.harbor_launch import configure_harbor
        original_probe = DockerEnvironment._EGRESS_CONTROL_KERNEL_PROBE_IMAGE
        original_context = DockerEnvironment._EGRESS_CONTROL_SIDECAR_CONTEXT_PATH
        helper = self.folder/'normalized-helper'
        try:
            with patch.dict('os.environ', {'TCSEXAM_HARBOR_KERNEL_PROBE_IMAGE': 'tcsexam/probe',
                                          'TCSEXAM_CACHE': str(self.args.cache)}), \
                    patch('tcsexam.harbor_launch.normalized_context',
                          return_value=(helper, 'b1e6760734a9e6f6')) as normalize:
                configure_harbor()
            self.assertEqual(DockerEnvironment._EGRESS_CONTROL_KERNEL_PROBE_IMAGE,
                             'tcsexam/probe')
            self.assertEqual(DockerEnvironment._EGRESS_CONTROL_SIDECAR_CONTEXT_PATH, helper)
            normalize.assert_called_once_with(self.args.cache)
        finally:
            DockerEnvironment._EGRESS_CONTROL_KERNEL_PROBE_IMAGE = original_probe
            DockerEnvironment._EGRESS_CONTROL_SIDECAR_CONTEXT_PATH = original_context

    def test_harbor_entrypoint_delegates_to_typer_app(self):
        from tcsexam import harbor_launch
        with patch('tcsexam.harbor_launch.configure_harbor'), \
                patch('harbor.cli.main.app') as app:
            harbor_launch.main()
        app.assert_called_once_with()

    def test_harbor_launch_reads_cached_host_support(self):
        import hashlib
        import os
        from tcsexam.harbor_launch import kernel_probe_reference
        from tcsexam.setup import save_record
        context = None
        endpoint = 'unix:///tmp/tcsexam-test.sock'
        key = hashlib.sha256(json.dumps([context, endpoint]).encode()).hexdigest()[:16]
        save_record(self.args.cache / 'hosts' / (key + '.json'), {'host_support': [{
            'support_kind': 'harbor_kernel_probe', 'image': self.ref,
            'local_image': 'tcsexam/probe-from-cache'}]})
        with patch.dict('os.environ', {'TCSEXAM_CACHE': str(self.args.cache),
                                      'DOCKER_HOST': endpoint, 'DOCKER_CONTEXT': ''}):
            os.environ.pop('TCSEXAM_HARBOR_KERNEL_PROBE_IMAGE', None)
            self.assertEqual(kernel_probe_reference(), 'tcsexam/probe-from-cache')

    def test_never_pull_and_platform_mismatch_fail_without_complete_record(self):
        self.args.pull_policy = 'never'
        with patch('tcsexam.setup.inspect_image', return_value=None), \
                patch('tcsexam.setup.subprocess.run') as execute:
            with self.assertRaisesRegex(ValueError, 'absent'):
                setup_selection(self.root, self.rows, self.args)
            execute.assert_not_called()
        self.args.pull_policy = 'missing'
        with patch('tcsexam.setup.inspect_image', return_value={'id': 'x', 'platform': 'linux/arm64'}):
            with self.assertRaisesRegex(ValueError, 'platform'):
                setup_selection(self.root, self.rows, self.args)
        self.assertFalse(self.args.cache.exists())

    def test_manifest_digest_mismatch_is_rejected(self):
        self.products.write_text(json.dumps({'images': [{'image': self.ref, 'digest': 'sha256:'+'b'*64}]}))
        with self.assertRaisesRegex(ValueError, 'conflicts'):
            artifacts(self.products)

    def test_missing_separate_verifier_blocks_before_pull_or_model_launch(self):
        from tcsexam.diagnostics import prerequisites
        _, rows = selection(self.root, 'full', task='jsplib-jssp', solver_protocol='offline')
        self.products.write_text(json.dumps({'images': [{'id': 'development-only', 'image': self.ref}],
            'tasks': {rows[0]['path']: {'development': 'development-only'}}}))
        with patch('tcsexam.setup.subprocess.run') as execute:
            with self.assertRaisesRegex(ValueError, 'No complete verifier image'):
                setup_selection(self.root, rows, self.args)
        execute.assert_not_called()
        with patch('tcsexam.diagnostics.host_support_targets', return_value=[]), \
                patch('tcsexam.diagnostics.inspect_image', return_value={'id': 'fixture'}):
            report = prerequisites(self.root, rows, self.args)
        self.assertFalse(report['ready'])
        self.assertTrue(any(r['kind'] == 'complete_verifier_image' for r in report['blockers']))

    def test_registry_port_is_preserved_when_resolving_a_digest(self):
        self.products.write_text(json.dumps({'images': [{'id': 'fixture',
            'image': 'registry.example:5000/image', 'digest': 'sha256:'+'a'*64}],
            'tasks': {'tasks/example': {'development': 'fixture'}}}))
        mapping, _ = artifacts(self.products)
        self.assertEqual(mapping['tasks/example']['development'],
                         'registry.example:5000/image@sha256:'+'a'*64)

    def test_side_loaded_upstream_checks_layers_config_and_local_id(self):
        layer = 'sha256:' + 'c' * 64
        identity = 'sha256:' + 'd' * 64
        config = {'Env': ['PATH=/usr/local/bin'], 'Cmd': ['python3'], 'WorkingDir': ''}
        upstream = {'os': 'linux', 'architecture': 'amd64',
                    'rootfs': {'diff_ids': [layer]}, 'config': config}
        record = {'side_loaded': True, 'local_image': 'tcsexam/upstream-fixture',
                  'image_id': identity, 'upstream_manifest_digest': self.ref.split('@')[1],
                  'upstream_config': upstream}
        inspected = {'Id': identity, 'Os': 'linux', 'Architecture': 'amd64',
                     'RootFS': {'Layers': [layer]}, 'Config': dict(config), 'RepoDigests': []}
        with patch('tcsexam.setup.subprocess.run', return_value=CompletedProcess(
                [], 0, stdout=json.dumps([inspected]))) as execute:
            self.assertEqual(inspect_image(self.ref, self.args, record)['id'], identity)
        self.assertEqual(execute.call_args.args[0][-1], record['local_image'])
        inspected['Config']['Cmd'] = ['different']
        with patch('tcsexam.setup.subprocess.run', return_value=CompletedProcess(
                [], 0, stdout=json.dumps([inspected]))):
            self.assertIsNone(inspect_image(self.ref, self.args, record))
        inspected['Config'] = dict(config)
        inspected['RootFS']['Layers'] = ['sha256:' + 'e' * 64]
        with patch('tcsexam.setup.subprocess.run', return_value=CompletedProcess(
                [], 0, stdout=json.dumps([inspected]))):
            self.assertIsNone(inspect_image(self.ref, self.args, record))

    def test_offline_minimum_accounts_for_original_model_limits_and_controller(self):
        _, rows = selection(self.root, 'full', task='jsplib-jssp', solver_protocol='offline')
        mapping = {rows[0]['path']: {'verifier': self.ref}}
        # Docker may advertise many CPUs while the enclosing host allows eight.
        limits = {'cpu_count': 8, 'memory_bytes': 64*1024**3, 'disk_free_bytes': 64*1024**3}
        with patch('tcsexam.setup.subprocess.run', return_value=CompletedProcess(
                [], 0, stdout=json.dumps(limits))) as execute:
            checks = offline_host_capacity(self.root, rows, mapping, self.args)
        self.assertFalse(checks[0]['ok'])
        self.assertEqual(checks[0]['minimum']['cpus'], 16)
        command = execute.call_args.args[0]
        self.assertIn('--pull=never', command)
        self.assertIn('--cgroupns', command)
        self.assertNotIn('/var/run/docker.sock', ' '.join(command))
        limits['cpu_count'] = 16
        with patch('tcsexam.setup.subprocess.run', return_value=CompletedProcess(
                [], 0, stdout=json.dumps(limits))):
            self.assertTrue(offline_host_capacity(self.root, rows, mapping, self.args)[0]['ok'])

    def test_insufficient_offline_host_stops_before_model_or_job_creation(self):
        output = self.folder/'blocked-job.json'
        _, rows = selection(self.root, 'full', task='jsplib-jssp', solver_protocol='offline')
        self.products.write_text(json.dumps({'images': [{'id': 'fixture', 'image': self.ref}],
            'tasks': {rows[0]['path']: {'development': 'fixture', 'verifier': 'fixture'}}}))
        limits = {'cpu_count': 8, 'memory_bytes': 64*1024**3, 'disk_free_bytes': 64*1024**3}
        with patch('tcsexam.setup.inspect_image', return_value={'id': 'fixture', 'platform': 'linux/amd64'}), \
                patch('tcsexam.setup.subprocess.run', return_value=CompletedProcess(
                    [], 0, stdout=json.dumps(limits))), \
                patch('tcsexam.cli.subprocess.call') as launch, redirect_stdout(io.StringIO()), \
                patch('tcsexam.cli.argparse.ArgumentParser.exit', side_effect=ValueError('cli failure')):
            with self.assertRaises(ValueError):
                main(['run', '--root', str(self.root), '--suite', 'full', '--task', rows[0]['id'],
                      '--solver-protocol', 'offline', '--artifacts', str(self.products),
                      '--output', str(output)])
        launch.assert_not_called()
        self.assertFalse(output.exists())

    def test_offline_capacity_probe_failure_is_not_treated_as_ready(self):
        _, rows = selection(self.root, 'full', task='jsplib-jssp', solver_protocol='offline')
        with patch('tcsexam.setup.subprocess.run', return_value=CompletedProcess([], 1)):
            with self.assertRaisesRegex(ValueError, 'capacity probe failed'):
                offline_host_capacity(self.root, rows, {rows[0]['path']: {'verifier': self.ref}}, self.args)

    def test_32_gib_worker_requires_the_controller_memory_reserve(self):
        _, rows = selection(self.root, 'full', task='maxsat-mse', solver_protocol='offline')
        mapping = {rows[0]['path']: {'verifier': self.ref}}
        for memory_mb, expected in [(32768, False), (33280, True)]:
            limits = {'cpu_count': 16, 'memory_bytes': memory_mb*1024**2,
                      'disk_free_bytes': 256*1024**3}
            with self.subTest(memory_mb=memory_mb), patch('tcsexam.setup.subprocess.run',
                    return_value=CompletedProcess([], 0, stdout=json.dumps(limits))):
                check = offline_host_capacity(self.root, rows, mapping, self.args)[0]
            self.assertEqual(check['minimum']['memory_mb'], 33280)
            self.assertEqual(check['ok'], expected)

    def test_host_support_is_tagged_before_any_model_starts(self):
        helper = {'id': 'helper-fixture', 'image': self.ref,
                  'support_kind': 'harbor_egress_control',
                  'local_tag': 'harbor-prebuilt:fixture--context'}
        with patch('tcsexam.setup.host_support_targets', return_value=[helper]), \
                patch('tcsexam.setup.inspect_image', return_value={
                    'id': 'sha256:fixture', 'reference': self.ref, 'platform': 'linux/amd64'}), \
                patch('tcsexam.setup.subprocess.run', return_value=CompletedProcess([], 0)) as execute:
            report = setup_selection(self.root, self.rows, self.args)
        self.assertFalse(report['model_started'])
        self.assertEqual(report['host_support'][0]['local_tag'], helper['local_tag'])
        self.assertEqual(execute.call_args.args[0], ['docker', 'tag', self.ref, helper['local_tag']])

    def test_unknown_host_context_stops_before_image_acquisition(self):
        with patch('tcsexam.setup.host_support_targets', side_effect=ValueError('Unknown host context')), \
                patch('tcsexam.setup.subprocess.run') as execute:
            with self.assertRaisesRegex(ValueError, 'Unknown host context'):
                setup_selection(self.root, self.rows, self.args)
        execute.assert_not_called()

    def test_missing_host_support_is_an_explicit_failure(self):
        self.support.stop()
        with self.assertRaisesRegex(ValueError, 'must include the prebuilt Harbor helper'):
            host_support_targets({}, self.args)

    def test_remote_endpoint_is_rejected_before_pull_or_model_launch(self):
        self.support.stop()
        self.args.docker_context = 'remote-host'
        with patch('tcsexam.setup.subprocess.run', return_value=CompletedProcess(
                [], 0, stdout='ssh://worker.example', stderr='')) as execute:
            with self.assertRaisesRegex(ValueError, 'local Unix socket'):
                host_support_targets({'fixture': {'type': 'host_support'}}, self.args)
        self.assertEqual(execute.call_count, 1)

    def test_doctor_reports_the_same_host_context_failure(self):
        from tcsexam.diagnostics import prerequisites
        with patch('tcsexam.diagnostics.host_support_targets', side_effect=ValueError('Unknown host context')), \
                patch('tcsexam.diagnostics.inspect_image', return_value={'id': 'sha256:fixture'}):
            report = prerequisites(self.root, self.rows, self.args)
        self.assertFalse(report['ready'])
        self.assertFalse(report['host_prepared'])
        self.assertEqual(report['host_support'][0]['reason'], 'Unknown host context')

    def test_tagged_artifact_evidence_uses_the_normalized_digest(self):
        self.products.write_text(json.dumps({'images': [{'id': 'helper',
            'image': 'registry.example/image:mutable', 'manifest_digest': 'sha256:'+'a'*64}]}))
        _, evidence = artifacts(self.products)
        self.assertEqual(evidence[self.ref]['image'], self.ref)

    def test_repeated_preparation_creates_distinct_harbor_job_names(self):
        output = self.folder/'job.json'
        names = []
        with redirect_stdout(io.StringIO()):
            for _ in range(2):
                self.assertEqual(main(['prepare', '--root', str(self.root), '--suite', 'full',
                    '--task', self.rows[0]['id'], '--artifacts', str(self.products),
                    '--base-url', 'https://provider.example.invalid/v1', '--output', str(output)]), 0)
                names.append(json.loads(output.read_text())['job_name'])
        self.assertNotEqual(names[0], names[1])
