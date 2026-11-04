"""Exercise local image construction, caching and selection reuse."""
from argparse import Namespace
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
from subprocess import CompletedProcess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from tcsexam.build import ImageBuilder, build_selection, selection_artifact_path
from tcsexam.cli import main
from tcsexam.layout import selection
from tcsexam.resources import content_digest
from tcsexam.setup import artifacts


def image_id(reference):
    return 'sha256:' + hashlib.sha256(reference.encode()).hexdigest()


class Build(unittest.TestCase):
    def test_source_identity_survives_git_umask_but_tracks_executable_bit(self):
        from tcsexam.build import source_digest
        path = self.write('script.sh', '#!/bin/sh\ntrue\n')
        path.chmod(0o644)
        initial = source_digest(self.root, ['script.sh'])
        path.chmod(0o664)
        self.assertEqual(source_digest(self.root, ['script.sh']), initial)
        path.chmod(0o755)
        self.assertNotEqual(source_digest(self.root, ['script.sh']), initial)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'repo'
        self.cache = Path(self.temporary.name) / 'cache'
        self.task = 'tasks/theorem/sample'
        self.write('suites/tasks.json', {'tasks': [{'track': 'theorem', 'id': 'sample',
            'variants': {'default': {'path': self.task, 'readiness': 'ready'}}}]})
        self.write('suites/full.json', {'tasks': [{'track': 'theorem', 'id': 'sample'}]})
        self.write('suites/lite.json', {'tasks': [{'track': 'theorem', 'id': 'sample'}]})
        self.write(self.task + '/task.toml', '[environment]\n[verifier.environment]\n')
        self.write('assets/files.json', {'files': []})
        self.write('assets/data/Dockerfile', 'FROM scratch\n')
        self.write('src/tcsexam/resources.py', '# fixture source pin\n')
        self.write('src/tcsexam/build.py', '# fixture source pin\n')
        self.write(self.task + '/environment/Dockerfile',
                   'ARG FIXTURE_DATA\nFROM ${FIXTURE_DATA}\n')
        self.write(self.task + '/tests/Dockerfile',
                   'ARG DEVELOPMENT_IMAGE\nFROM ${DEVELOPMENT_IMAGE}\n')
        payload = b'fixture payload\n'
        payload_row = {'path': 'payload.txt', 'bytes': len(payload), 'mode': '0644',
                       'sha256': hashlib.sha256(payload).hexdigest()}
        self.write('assets/data/fixture-files.json', {'files': [payload_row]})
        archive = self.make_archive(payload)
        self.write('assets/data/fixture.json', {'recipe_format': 'fixed_tar',
            'source': {'id': 'fixture-source', 'url': None,
                       'bytes': archive.stat().st_size,
                       'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()}})
        manifest_path = self.root / 'assets/data/fixture-files.json'
        images = {'images': [
            {'id': 'fixture-data', 'type': 'data', 'recipe': 'assets/data/fixture.json',
             'recipe_format': 'fixed_tar', 'files_manifest': 'assets/data/fixture-files.json',
             'manifest_sha256': hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
             'content_version': 'v1', 'target_root': '/', 'distribution': 'local_prepare',
             'public_upload_allowed': False,
             'content_digest': content_digest([payload_row], '/'), 'dependencies': []},
            {'id': 'sample-development', 'type': 'runtime', 'runtime_role': 'development',
             'consumers': [self.task], 'dependencies': ['fixture-data'],
             'distribution': 'local_prepare',
             'build': {'dockerfile': self.task + '/environment/Dockerfile',
                       'context': self.task + '/environment',
                       'image_args': {'FIXTURE_DATA': 'fixture-data'}}},
            {'id': 'sample-verifier', 'type': 'runtime', 'runtime_role': 'verifier',
             'consumers': [self.task], 'dependencies': ['sample-development'],
             'distribution': 'local_prepare',
             'build': {'dockerfile': self.task + '/tests/Dockerfile',
                       'context': self.task + '/tests',
                       'image_args': {'DEVELOPMENT_IMAGE': 'sample-development'}}},
        ]}
        self.write('assets/images.json', images)
        _, self.rows = selection(self.root, 'full')
        self.args = Namespace(suite='full', track=None, task=['sample'], solver_protocol='offline',
                              artifacts=None, image_map=None, cache=self.cache, docker_context=None,
                              pull_policy='missing', output=None, judge_url=None, command='build')
        self.inputs = {'fixture-source': archive}
        self.commands = []
        self.missing = set()
        self.remote_present = set()
        for target in ('tcsexam.build.host_support_targets', 'tcsexam.setup.host_support_targets',
                       'tcsexam.diagnostics.host_support_targets'):
            patcher = patch(target, return_value=[])
            patcher.start()
            self.addCleanup(patcher.stop)
        for target in ('tcsexam.build.inspect_image', 'tcsexam.setup.inspect_image',
                       'tcsexam.diagnostics.inspect_image'):
            patcher = patch(target, side_effect=self.inspect)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch('tcsexam.build.inspect_tag_id', side_effect=lambda ref, args: image_id(ref))
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch('tcsexam.build.subprocess.run', side_effect=self.execute)
        self.execute_mock = patcher.start()
        self.addCleanup(patcher.stop)

    def write(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(value, str):
            path.write_text(value)
        else:
            path.write_text(json.dumps(value, indent=2) + '\n')
        return path

    def make_archive(self, payload):
        path = Path(self.temporary.name) / 'fixture.tar.gz'
        import gzip
        with path.open('wb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode='w|') as tar:
                info = tarfile.TarInfo('payload.txt')
                info.size = len(payload)
                info.mode = 0o644
                tar.addfile(info, io.BytesIO(payload))
        return path

    def inspect(self, reference, args, record=None):
        if reference in self.missing:
            return None
        if reference.startswith('registry.example/') and reference not in self.remote_present:
            return None
        actual = image_id(reference)
        if record and record.get('local') and record.get('image_id') != actual:
            return None
        return {'id': actual, 'platform': 'linux/amd64', 'reference': reference}

    def execute(self, command, **kwargs):
        self.commands.append(command)
        if 'pull' in command:
            self.remote_present.add(command[-1])
        return CompletedProcess(command, 0, stdout='', stderr='')

    def build(self):
        return build_selection(self.root, self.rows, self.args, inputs=self.inputs)

    def test_build_then_build_and_run_reuse_the_same_local_images(self):
        result = self.build()
        self.assertEqual(len(self.commands), 3)
        self.assertTrue(all(command[1] == 'build' for command in self.commands))
        self.assertTrue(all('push' not in command for command in self.commands))
        manifest_path = Path(result['manifest'])
        manifest = json.loads(manifest_path.read_text())
        self.assertEqual(len(manifest['images']), 3)
        self.assertTrue(all(row['local'] for row in manifest['images']))
        self.assertEqual(manifest['tasks'][self.task],
                         {'development': 'sample-development', 'verifier': 'sample-verifier'})
        _, evidence = artifacts(manifest_path, root=self.root)
        self.assertEqual(len(evidence), 3)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(['build', '--root', str(self.root), '--suite', 'full',
                                   '--task', 'sample', '--cache', str(self.cache)]), 0)
        self.assertEqual(len(self.commands), 3)
        with patch('tcsexam.cli.prepare', return_value={'tasks': []}) as prepare, \
                patch('tcsexam.cli.subprocess.call', return_value=0) as launch, \
                patch.dict(os.environ, {'TCSEXAM_API_KEY': 'fixture'}), redirect_stdout(io.StringIO()):
            self.assertEqual(main(['run', '--root', str(self.root), '--suite', 'full',
                                   '--task', 'sample', '--cache', str(self.cache),
                                   '--output', str(Path(self.temporary.name) / 'job.json')]), 0)
        self.assertEqual(prepare.call_args.args[0].artifacts, manifest_path)
        launch.assert_called_once()
        self.assertEqual(len(self.commands), 3)

    def test_build_and_run_do_not_open_private_oracle_backup(self):
        import builtins

        private = self.root / 'build/oracle-private-package/oracle-answers.tar.gz'
        private.parent.mkdir(parents=True)
        private.write_bytes(b'private backup sentinel')

        def checked(function):
            def open_file(path, *args, **kwargs):
                if isinstance(path, (str, bytes, os.PathLike)):
                    if Path(path).absolute() == private:
                        raise AssertionError('ordinary build/run opened the private oracle backup')
                return function(path, *args, **kwargs)
            return open_file

        with patch('builtins.open', new=checked(builtins.open)), \
                patch('io.open', new=checked(io.open)), \
                patch('os.open', new=checked(os.open)):
            result = self.build()
            manifest_path = Path(result['manifest'])
            with patch('tcsexam.cli.prepare', return_value={'tasks': []}), \
                    patch('tcsexam.cli.subprocess.call', return_value=0) as launch, \
                    patch.dict(os.environ, {'TCSEXAM_API_KEY': 'fixture'}), redirect_stdout(io.StringIO()):
                self.assertEqual(main(['run', '--root', str(self.root), '--suite', 'full',
                                       '--task', 'sample', '--cache', str(self.cache),
                                       '--output', str(Path(self.temporary.name) / 'job.json')]), 0)
            launch.assert_called_once()
        self.assertEqual(private.read_bytes(), b'private backup sentinel')

    def test_custom_output_also_updates_the_default_selection_cache(self):
        output = Path(self.temporary.name) / 'custom-artifacts.json'
        self.args.output = output
        self.build()
        with patch.dict(os.environ, {'TCSEXAM_API_KEY': 'fixture-model-key'}), \
                redirect_stdout(io.StringIO()):
            self.assertEqual(main(['doctor', '--root', str(self.root), '--suite', 'full',
                                   '--task', 'sample', '--cache', str(self.cache)]), 0)
        cached = selection_artifact_path(self.root, self.rows, self.args)
        self.assertNotEqual(output, cached)
        self.assertEqual(json.loads(output.read_text()), json.loads(cached.read_text()))

    def test_data_build_inputs_reject_old_manifests_and_rebuild(self):
        images = json.loads((self.root / 'assets/images.json').read_text())
        images['images'][0]['distribution_evidence'] = 'assets/data/source-evidence.json'
        self.write('assets/images.json', images)
        evidence = self.write('assets/data/source-evidence.json', {'source': 'original'})
        for changed in (self.root / 'assets/data/Dockerfile', evidence,
                        self.root / 'src/tcsexam/build.py'):
            with self.subTest(changed=changed.name):
                result = self.build()
                old = Path(self.temporary.name) / 'previous-artifacts.json'
                old.write_bytes(Path(result['manifest']).read_bytes())
                self.commands.clear()
                changed.write_text(changed.read_text() + '\n')
                with self.assertRaises(ValueError):
                    artifacts(old, root=self.root)
                self.build()
                self.assertEqual(len(self.commands), 3)

    def test_source_change_only_rebuilds_affected_products(self):
        result = self.build()
        old = json.loads(Path(result['manifest']).read_text())
        old_verifier = next(row for row in old['images'] if row['id'] == 'sample-verifier')['reference']
        self.commands.clear()
        dockerfile = self.root / self.task / 'tests/Dockerfile'
        dockerfile.write_text(dockerfile.read_text() + '# changed source\n')
        with redirect_stdout(io.StringIO()):
            main(['build', '--root', str(self.root), '--suite', 'full',
                  '--task', 'sample', '--cache', str(self.cache)])
        self.assertEqual(len(self.commands), 1)
        self.assertTrue(any(value.startswith('tcsexam/sample-verifier:')
                            for value in self.commands[0]))
        new = json.loads(Path(result['manifest']).read_text())
        new_verifier = next(row for row in new['images'] if row['id'] == 'sample-verifier')['reference']
        self.assertNotEqual(old_verifier, new_verifier)
        actions = {row['id']: row['action'] for row in new['actions']}
        self.assertEqual(actions, {'fixture-data': 'reused', 'sample-development': 'reused',
                                   'sample-verifier': 'built'})

    def test_failed_build_keeps_intermediates_but_not_a_complete_manifest(self):
        original = self.execute_mock.side_effect
        def fail_verifier(command, **kwargs):
            if any(value.startswith('tcsexam/sample-verifier:') for value in command):
                return CompletedProcess(command, 1)
            return original(command, **kwargs)
        self.execute_mock.side_effect = fail_verifier
        with self.assertRaisesRegex(ValueError, 'sample-verifier'):
            self.build()
        destination = selection_artifact_path(self.root, self.rows, self.args)
        self.assertFalse(destination.exists())
        self.assertTrue((self.cache / 'images/fixture-data.json').is_file())
        self.assertTrue((self.cache / 'images/sample-development.json').is_file())
        self.assertFalse((self.cache / 'images/sample-verifier.json').exists())
        self.execute_mock.side_effect = original
        self.build()
        self.assertTrue(destination.is_file())
        self.assertEqual(len(self.commands), 3)

    def test_published_products_are_pulled_without_local_docker_builds(self):
        path = self.root / 'assets/images.json'
        data = json.loads(path.read_text())
        for row in data['images']:
            reference = 'registry.example/' + row['id'] + '@sha256:' + hashlib.sha256(row['id'].encode()).hexdigest()
            row['public_image'] = reference
        path.write_text(json.dumps(data))
        builder = ImageBuilder(self.root, self.rows, self.args, inputs=self.inputs)
        tasks, _, images = builder.prepare(self.rows)
        self.assertEqual(len(self.commands), 2)
        self.assertTrue(all(command[1] == 'pull' for command in self.commands))
        self.assertEqual({row['id'] for row in images}, {'sample-development', 'sample-verifier'})
        self.assertEqual(set(tasks[self.task]), {'development', 'verifier'})
        self.assertTrue(all(not row['local'] for row in images))

    def test_public_product_is_derived_from_the_new_backend(self):
        self.write('src/tcsexam/public_image.py', '# fixture source pin\n')
        self.write('assets/public.json', {'schema_version': 1, 'task': self.task,
            'remove_paths': ['/tests'], 'allow_content_paths': ['/public'],
            'required_paths': ['/public']})
        path = self.root / 'assets/images.json'
        data = json.loads(path.read_text())
        data['images'].append({'id': 'sample-public-backend', 'type': 'runtime',
            'runtime_role': 'public_backend', 'consumers': [self.task],
            'dependencies': ['sample-verifier'], 'distribution': 'local_prepare',
            'build': {'kind': 'public_image', 'source_product': 'sample-verifier',
                      'manifest': 'assets/public.json'}})
        path.write_text(json.dumps(data))
        builder = ImageBuilder(self.root, self.rows, self.args, inputs=self.inputs)
        with patch('tcsexam.public_image.build_public_image', return_value={'rootfs_layers': 1}) as export:
            record = builder.prepare_product('sample-public-backend')
        source = export.call_args.args[0]
        self.assertEqual(source, builder.products['sample-verifier']['reference'])
        self.assertFalse(export.call_args.kwargs['pull'])
        self.assertFalse(export.call_args.kwargs['push'])
        self.assertTrue(record['local'])
        self.assertTrue(record['content_verified'])
        self.assertEqual(record['verification']['public_image']['rootfs_layers'], 1)

    def test_published_selection_does_not_read_unavailable_recipe_or_dependencies(self):
        path = self.root / 'assets/images.json'
        data = json.loads(path.read_text())
        row = data['images'][1]
        row['public_image'] = 'registry.example/complete@sha256:' + 'a' * 64
        row['dependencies'] = ['unavailable-intermediate']
        row['build']['dockerfile'] = 'unavailable/Dockerfile'
        path.write_text(json.dumps(data))
        record = ImageBuilder(self.root, self.rows, self.args).prepare_product('sample-development')
        self.assertFalse(record['local'])
        self.assertEqual(len(self.commands), 1)
        self.assertEqual(self.commands[0][1], 'pull')

    def test_local_build_preference_does_not_pull_optional_product(self):
        path = self.root / 'assets/images.json'
        data = json.loads(path.read_text())
        for row in data['images']:
            row['public_image'] = 'registry.example/' + row['id'] + '@sha256:' + 'a' * 64
            row['acquisition'] = {'preferred': 'local_build'}
        path.write_text(json.dumps(data))
        self.build()
        self.assertEqual(len(self.commands), 3)
        self.assertTrue(all(command[1] == 'build' for command in self.commands))

    def test_published_data_checks_payload_without_running_a_container(self):
        path = self.root / 'assets/images.json'
        data = json.loads(path.read_text())
        data['images'][0]['public_image'] = 'registry.example/data@sha256:' + 'a' * 64
        path.write_text(json.dumps(data))
        original = self.execute_mock.side_effect
        def populated(command, **kwargs):
            if command[1] == 'cp':
                target = Path(command[-1]) / 'payload.txt'
                target.write_bytes(b'fixture payload\n')
                target.chmod(0o644)
            return original(command, **kwargs)
        self.execute_mock.side_effect = populated
        builder = ImageBuilder(self.root, self.rows, self.args)
        record = builder.prepare_product('fixture-data')
        self.assertTrue(record['content_verified'])
        self.assertEqual([c[1] for c in self.commands], ['pull', 'create', 'cp', 'rm'])
        self.assertNotIn('start', [c[1] for c in self.commands])

    def test_corrupt_published_data_is_rejected_and_container_removed(self):
        path = self.root / 'assets/images.json'
        data = json.loads(path.read_text())
        data['images'][0]['public_image'] = 'registry.example/data@sha256:' + 'a' * 64
        path.write_text(json.dumps(data))
        original = self.execute_mock.side_effect
        def corrupted(command, **kwargs):
            if command[1] == 'cp':
                (Path(command[-1]) / 'payload.txt').write_bytes(b'wrong')
            return original(command, **kwargs)
        self.execute_mock.side_effect = corrupted
        builder = ImageBuilder(self.root, self.rows, self.args)
        with self.assertRaisesRegex(ValueError, 'Content differs'):
            builder.prepare_product('fixture-data')
        self.assertNotIn('fixture-data', builder.products)
        self.assertEqual(self.commands[-1][1], 'rm')

    def test_harbor_helper_build_uses_the_normalized_cached_context(self):
        self.write('src/tcsexam/harbor_support.py', '# fixture source pin\n')
        self.write('assets/environments/harbor/egress-control/Dockerfile', 'FROM scratch\n')
        path = self.root / 'assets/images.json'
        data = json.loads(path.read_text())
        data['images'].append({'id': 'harbor-helper', 'type': 'host_support',
            'support_kind': 'harbor_egress_control', 'harbor_context_hash': 'normalized-hash',
            'distribution': 'local_prepare', 'dependencies': [],
            'build': {'dockerfile': 'assets/environments/harbor/egress-control/Dockerfile',
                      'context': 'assets/environments/harbor/egress-control'}})
        path.write_text(json.dumps(data))
        normalized = self.root / 'normalized-helper'
        self.write('normalized-helper/Dockerfile', 'FROM scratch\n')
        builder = ImageBuilder(self.root, self.rows, self.args, inputs=self.inputs)
        with patch('tcsexam.harbor_support.normalized_context',
                   return_value=(normalized, 'normalized-hash')) as normalize:
            record = builder.prepare_product('harbor-helper')
        normalize.assert_called_once_with(self.cache)
        command = self.commands[-1]
        self.assertEqual(command[-1], str(normalized))
        self.assertEqual(Path(command[command.index('--file') + 1]), normalized / 'Dockerfile')
        self.assertEqual(record['harbor_context_hash'], 'normalized-hash')

    def test_official_resource_uses_the_acquired_side_loaded_builder(self):
        builder_ref = 'ubuntu:22.04@sha256:' + 'a' * 64
        path = self.root / 'assets/images.json'
        data = json.loads(path.read_text())
        resource = next(row for row in data['images'] if row['id'] == 'fixture-data')
        resource['recipe_format'] = 'official_build'
        path.write_text(json.dumps(data))
        recipe_path = self.root / resource['recipe']
        recipe = json.loads(recipe_path.read_text())
        recipe['build'] = {'builder_image': builder_ref, 'command': ['make', 'all'],
                           'cwd': '.', 'artifact': 'payload.txt', 'install': 'payload.txt'}
        recipe_path.write_text(json.dumps(recipe))
        rootfs = self.root / 'official-rootfs'
        self.write('official-rootfs/payload.txt', 'fixture payload\n').chmod(0o644)
        builder = ImageBuilder(self.root, self.rows, self.args, inputs=self.inputs)
        builder.references[builder_ref] = {'reference': builder_ref, 'local': False,
                                           'local_image': 'tcsexam/upstream-jammy'}
        with patch('tcsexam.build.prepare_resource', return_value=rootfs) as prepare:
            builder.prepare_product('fixture-data')
        self.assertIs(prepare.call_args.kwargs['args'], self.args)
        self.assertEqual(prepare.call_args.kwargs['builder_image'], 'tcsexam/upstream-jammy')

    def test_retag_archive_preserves_config_and_layer_bytes(self):
        archive = Path(self.temporary.name) / 'image.tar'
        manifest = [{'Config': 'config.json', 'RepoTags': ['old:latest'], 'Layers': ['layer.tar']}]
        with tarfile.open(archive, 'w') as tar:
            for name, payload in (('manifest.json', json.dumps(manifest).encode()),
                                  ('config.json', b'{"config":true}\n'), ('layer.tar', b'layer bytes')):
                info = tarfile.TarInfo(name)
                info.size = len(payload)
                tar.addfile(info, io.BytesIO(payload))
        ImageBuilder.retag_archive(archive, 'tcsexam/upstream-fixture')
        with tarfile.open(archive, 'r') as tar:
            updated = json.load(tar.extractfile('manifest.json'))
            self.assertEqual(updated[0]['RepoTags'], ['tcsexam/upstream-fixture:latest'])
            self.assertEqual(tar.extractfile('config.json').read(), b'{"config":true}\n')
            self.assertEqual(tar.extractfile('layer.tar').read(), b'layer bytes')

    def test_side_loaded_arg_base_uses_the_verified_local_image(self):
        upstream = 'registry.example/private@sha256:' + 'a' * 64
        local_image = 'tcsexam/upstream-fixture'
        builder = ImageBuilder(self.root, self.rows, self.args, inputs=self.inputs)
        record = {'reference': upstream, 'local': False, 'local_image': local_image}
        builder.products['fixture-data'] = record
        builder.references[upstream] = record
        builder.local_aliases.add(local_image)
        builder.prepare_product('sample-development')
        command = self.commands[-1]
        self.assertIn('FIXTURE_DATA=' + local_image, command)
        self.assertNotIn('FIXTURE_DATA=' + upstream, command)

    def test_literal_upstream_from_uses_the_verified_local_image(self):
        upstream = 'gogost/gost:3.2.7@sha256:' + 'a' * 64
        self.write(self.task + '/environment/Dockerfile',
                   'ARG FIXTURE_DATA\nFROM ${FIXTURE_DATA} AS fixture_data\n'
                   f'FROM {upstream}\nCOPY --from=fixture_data /payload/rootfs/ /\n')
        builder = ImageBuilder(self.root, self.rows, self.args, inputs=self.inputs)
        builder.references[upstream] = {'reference': upstream, 'local': False,
                                        'local_image': 'tcsexam/upstream-fixture'}
        original = self.execute_mock.side_effect
        captured = []
        def capture(command, **kwargs):
            if command[1] == 'build' and any('sample-development' in value for value in command):
                dockerfile = Path(command[command.index('--file') + 1])
                captured.append(dockerfile.read_text())
            return original(command, **kwargs)
        self.execute_mock.side_effect = capture
        builder.prepare_product('sample-development')
        self.assertEqual(len(captured), 1)
        self.assertIn('FROM tcsexam/upstream-fixture', captured[0])
        self.assertNotIn('FROM ' + upstream, captured[0])
        self.assertIn('FROM ${FIXTURE_DATA} AS fixture_data', captured[0])

    def test_proxy_environment_is_forwarded_safely(self):
        with patch.dict('os.environ', {
                'HTTP_PROXY': 'http://proxy.example:3128',
                'HTTPS_PROXY': 'https://proxy.example:3128',
                'NO_PROXY': 'localhost,example.org'}):
            builder = ImageBuilder(self.root, self.rows, self.args, inputs=self.inputs)
            builder.prepare_product('sample-development')
        command = self.commands[-1]
        self.assertIn('HTTP_PROXY=http://proxy.example:3128', command)
        self.assertIn('HTTPS_PROXY=https://proxy.example:3128', command)
        self.assertIn('NO_PROXY=localhost,example.org', command)
        self.assertEqual(command.count('--build-arg'), 4)
        from tcsexam.build import proxy_arguments
        with patch.dict('os.environ', {'HTTP_PROXY': 'http://user:secret@proxy.example'}):
            with self.assertRaisesRegex(ValueError, 'Proxy credentials'):
                proxy_arguments()

    def test_tampered_local_record_stops_run_before_model_launch(self):
        result = self.build()
        path = Path(result['manifest'])
        data = json.loads(path.read_text())
        development = next(row for row in data['images'] if row['id'] == 'sample-development')
        development['image_id'] = 'sha256:' + '0' * 64
        path.write_text(json.dumps(data))
        with patch('tcsexam.cli.prepare') as prepare, \
                patch('tcsexam.cli.subprocess.call') as launch, \
                patch.dict(os.environ, {'TCSEXAM_API_KEY': 'fixture'}), redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                main(['run', '--root', str(self.root), '--suite', 'full',
                      '--task', 'sample', '--cache', str(self.cache),
                      '--output', str(Path(self.temporary.name) / 'job.json')])
            self.assertEqual(error.exception.code, 2)
        prepare.assert_not_called()
        launch.assert_not_called()


if __name__ == '__main__':
    unittest.main()
