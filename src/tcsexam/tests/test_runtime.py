"""Validate actual Harbor schemas and per-attempt credential boundaries."""
from argparse import Namespace
import json
import os
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch

from harbor.models.job.config import JobConfig
from tcsexam.layout import repository, selection
from tcsexam.runtime import KIMI_INSTALL_HOSTS, image_map, materialize, native_config, prepare_agent_install_network, resource_image_ids


class Runtime(unittest.TestCase):
    def test_new_offline_variant_retains_original_data_provenance(self):
        from tcsexam.layout import load
        root = repository()
        _, online = selection(root, 'full', task='ahc058-atcoder', solver_protocol='online')
        _, offline = selection(root, 'full', task='ahc058-atcoder', solver_protocol='offline')
        images = load(root / 'assets/images.json')['images']
        expected = resource_image_ids(root, online[0], images)
        self.assertIn('solver-ahc058-atcoder-development-data', expected)
        self.assertEqual(resource_image_ids(root, offline[0], images), expected)

    def test_install_network_preserves_native_phase_policies_for_all_task_variants(self):
        from harbor.models.task.config import TaskConfig
        from harbor.models.task.verifier_mode import resolve_task_verifier_mode
        from harbor.models.trial.config import AgentConfig, EnvironmentConfig
        from harbor.trial.network_policy import resolve_trial_network_plan
        files = sorted((repository() / 'tasks').rglob('task.toml'))
        self.assertEqual(len(files), 130)
        agent = AgentConfig(name='kimi-code', extra_allowed_hosts=['provider.example.invalid'])
        environment = EnvironmentConfig(type='docker')
        for path in files:
            with self.subTest(task=str(path)):
                data = tomllib.loads(path.read_text())
                original = TaskConfig.model_validate(data)
                before = resolve_trial_network_plan(original, agent, environment, None,
                    verifier_mode=resolve_task_verifier_mode(original))
                prepare_agent_install_network(data)
                _, prepared = native_config(data)
                after = resolve_trial_network_plan(prepared, agent, environment, None,
                    verifier_mode=resolve_task_verifier_mode(prepared))
                self.assertEqual(after.agent_phase, before.agent_phase)
                self.assertEqual(after.verifier_phase, before.verifier_phase)
                self.assertEqual(after.verifier_env_baseline, before.verifier_env_baseline)
                self.assertEqual(after.agent_env_baseline.network_mode.value, 'allowlist')
                self.assertEqual(set(after.agent_env_baseline.allowed_hosts), set(KIMI_INSTALL_HOSTS))
                self.assertEqual(prepared.agent.timeout_sec, 43200)
                self.assertIn('/app', prepared.artifacts)

    def test_unique_identity_phase_credentials_network_and_native_schema(self):
        root = repository()
        _, rows = selection(root, 'full', task='ahc058-atcoder', solver_protocol='online')
        with tempfile.TemporaryDirectory() as folder:
            args = Namespace(output=Path(folder)/'job.json', attempts=2, suite='full',
                             cache=Path(folder)/'cache', judge_url='https://judge.example.invalid/v1',
                             image_map=None)
            sentinel = 'secret-must-never-be-serialized'
            with patch.dict(os.environ, {'TCSEXAM_ARCHIVE_TOKEN': sentinel,
                                         'TCSEXAM_TOKEN_SECRET': sentinel}):
                tasks, records = materialize(root, rows, args)
            self.assertEqual(len({r['run_id'] for r in records}), 2)
            JobConfig.model_validate({'tasks': tasks})
            for task, record in zip(tasks, records):
                text = (Path(task['path'])/'task.toml').read_text()
                self.assertNotIn(sentinel, text)
                data = tomllib.loads(text)
                self.assertEqual(data['environment']['env']['TCSEXAM_RUN_ID'], record['run_id'])
                self.assertEqual(data['verifier']['env']['TCSEXAM_RUN_ID'], record['run_id'])
                self.assertNotIn('TCSEXAM_ARCHIVE_TOKEN', data['environment']['env'])
                self.assertEqual(data['verifier']['env']['TCSEXAM_ARCHIVE_TOKEN'], '${TCSEXAM_ARCHIVE_TOKEN}')
                for phase in ('agent', 'verifier'):
                    self.assertEqual(data[phase]['network_mode'], 'allowlist')
                    self.assertIn('judge.example.invalid', data[phase]['allowed_hosts'])
                    self.assertTrue(set(KIMI_INSTALL_HOSTS).isdisjoint(data[phase]['allowed_hosts']))
                self.assertEqual(set(data['environment']['allowed_hosts']), set(KIMI_INSTALL_HOSTS))
                self.assertEqual(data['agent']['timeout_sec'], 43200)
                self.assertIn('/app', data['artifacts'])
                native_config(data)
            again, reruns = materialize(root, rows, args)
            self.assertTrue(set(r['run_id'] for r in reruns).isdisjoint(r['run_id'] for r in records))

    def test_unknown_harbor_fields_and_unpinned_overrides_fail(self):
        with self.assertRaisesRegex(ValueError, 'Unknown Harbor task field'):
            native_config({'per_task_env': {}})
        with self.assertRaisesRegex(ValueError, 'Unknown Harbor agent field'):
            native_config({'agent': {'env': {'SECRET': 'x'}}})
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/'images.json'
            p.write_text(json.dumps({'tasks/example': {'development': 'example/image:latest'}}))
            with self.assertRaisesRegex(ValueError, 'Pin'):
                image_map(p)

    def test_prebuilt_environment_does_not_require_local_copy_inputs(self):
        from tcsexam.diagnostics import prerequisites
        root = repository()
        _, rows = selection(root, 'full', task='ahc058-atcoder', solver_protocol='online')
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder)/'images.json'
            p.write_text(json.dumps({rows[0]['path']: {
                'development': 'registry.example/image@sha256:'+'a'*64,
                'backend': 'registry.example/judge@sha256:'+'b'*64}}))
            args = Namespace(image_map=p, cache=Path(folder)/'cache', judge_url='https://judge.example.invalid')
            with patch.dict(os.environ, {'TCSEXAM_TOKEN_ID': 'fixture', 'TCSEXAM_TOKEN_SECRET': 'fixture',
                                         'TCSEXAM_ARCHIVE_TOKEN': 'fixture'}), \
                    patch('tcsexam.diagnostics.inspect_image', return_value={'id': 'fixture'}):
                with patch('tcsexam.diagnostics.host_support_targets', return_value=[]):
                    report = prerequisites(root, rows, args)
            self.assertTrue(report['host_prepared'], report['blockers'])
            self.assertFalse(report['runtime_acceptance_complete'])
            self.assertFalse(any(c['kind']=='build_inputs' for c in report['tasks'][0]['checks']))
