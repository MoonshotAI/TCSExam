"""Check pinned data preparation, cache atomicity and data-only image contexts."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import lzma
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from tcsexam.resources import (build_data_image, content_digest, digest, extract_tar,
    make_archive, prepare_resource, resource_by_id, stage_data_context)


class Resources(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.payload = self.root / 'payload'
        self.payload.mkdir()
        (self.payload / 'build.sh').write_bytes(b'#!/bin/sh\nexit 0\n')
        (self.payload / 'build.sh').chmod(0o755)
        self.rows = [{'path': 'build.sh', 'bytes': 17, 'mode': '0755',
                      'sha256': digest(self.payload / 'build.sh')}]
        self.rows[0]['bytes'] = (self.payload / 'build.sh').stat().st_size
        self.archive = self.root / 'source.tar.gz'
        source = make_archive(self.payload, self.rows, self.archive)
        source.update(id='fixture-source', url='https://example.invalid/source.tar.gz')
        assets = self.root / 'assets/data'
        assets.mkdir(parents=True)
        manifest = assets / 'files.json'
        manifest.write_text(json.dumps({'files': self.rows}))
        (assets / 'recipe.json').write_text(json.dumps({'source': source}))
        (assets / 'Dockerfile').write_text('FROM scratch\nCOPY rootfs/ /payload/rootfs/\nCOPY manifest/ /manifest/\nCOPY licenses/ /licenses/\n')
        self.resource = {'id': 'fixture', 'type': 'data', 'files_manifest': 'assets/data/files.json',
            'manifest_sha256': digest(manifest), 'content_version': 'fixed',
            'distribution': 'redistributable', 'public_upload_allowed': True,
            'recipe': 'assets/data/recipe.json', 'recipe_format': 'fixed_tar', 'target_root': '/app'}
        (self.root / 'assets/images.json').write_text(json.dumps({'images': [self.resource]}))
        self.cache = self.root / 'empty-cache'
        self.inputs = {'fixture-source': self.archive}

    def prepare(self):
        return prepare_resource(self.root, 'fixture', self.cache, self.inputs)

    def test_empty_cache_permissions_reuse_and_corruption(self):
        first = self.prepare()
        self.assertEqual((first / 'app/build.sh').stat().st_mode & 0o777, 0o755)
        self.assertFalse((first / '.complete.json').exists())
        with patch('tcsexam.resources.extract_tar', side_effect=AssertionError('must reuse')):
            self.assertEqual(self.prepare(), first)
        (first / 'app/build.sh').write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'Content differs'):
            self.prepare()

    def test_tool_recipe_uses_the_same_checked_preparation(self):
        self.resource['type'] = 'toolchain'
        (self.root / 'assets/images.json').write_text(json.dumps({'images': [self.resource]}))
        prepared = self.prepare()
        self.assertEqual((prepared / 'app/build.sh').read_bytes(), (self.payload / 'build.sh').read_bytes())
        self.assertEqual((prepared / 'app/build.sh').stat().st_mode & 0o777, 0o755)

    def test_wrong_hash_and_interruption_never_complete(self):
        bad = self.root / 'bad.tar.gz'
        bad.write_bytes(self.archive.read_bytes()[:-10])
        with self.assertRaisesRegex(ValueError, 'hash or size'):
            prepare_resource(self.root, 'fixture', self.cache, {'fixture-source': bad})
        self.assertFalse((self.cache / 'fixture/fixed').exists())
        with patch('tcsexam.resources.extract_tar', side_effect=RuntimeError('interrupted')):
            with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                self.prepare()
        self.assertFalse((self.cache / 'fixture/fixed').exists())
        self.assertFalse(list((self.cache / 'fixture').glob('.preparing-*')))
        self.prepare()

    def test_parallel_preparation_has_one_complete_result(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: self.prepare(), range(2)))
        self.assertEqual(results[0], results[1])
        self.assertEqual((results[0] / 'app/build.sh').read_bytes(), b'#!/bin/sh\nexit 0\n')

    def test_manifest_hash_cannot_be_bypassed(self):
        (self.root / 'assets/data/files.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Manifest hash'):
            self.prepare()

    def test_archive_paths_links_duplicates_permissions_and_corruption(self):
        for kind in ('traversal', 'absolute', 'symlink', 'hardlink', 'duplicate', 'permissions', 'corrupt'):
            with self.subTest(kind=kind):
                archive = self.root / (kind + '.tar.gz')
                with tarfile.open(archive, 'w:gz') as tar:
                    info = tarfile.TarInfo({'traversal': '../escape', 'absolute': '/escape'}.get(kind, 'build.sh'))
                    info.mode = 0o644 if kind == 'permissions' else 0o755
                    data = b'X' * self.rows[0]['bytes'] if kind == 'corrupt' else (self.payload / 'build.sh').read_bytes()
                    info.size = len(data)
                    if kind in ('symlink', 'hardlink'):
                        info.type = tarfile.SYMTYPE if kind == 'symlink' else tarfile.LNKTYPE
                        info.linkname = '/etc/passwd'
                        info.size = 0
                    tar.addfile(info, io.BytesIO(data))
                    if kind == 'duplicate':
                        tar.addfile(info, io.BytesIO(data))
                destination = self.root / kind
                destination.mkdir()
                with self.assertRaises(ValueError):
                    extract_tar(archive, destination, self.rows)
        self.assertFalse((self.root / 'escape').exists())

    def test_cache_links_are_rejected(self):
        target = self.cache / 'fixture/fixed'
        target.parent.mkdir(parents=True)
        target.symlink_to(self.payload, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symbolic link'):
            self.prepare()

    def test_data_context_has_original_paths_and_no_cache_marker(self):
        rootfs = self.prepare()
        context = stage_data_context(self.root, 'fixture', rootfs, self.root / 'context')
        self.assertEqual((context / 'rootfs/app/build.sh').read_bytes(), b'#!/bin/sh\nexit 0\n')
        self.assertFalse(list(context.rglob('.complete.json')))
        self.assertTrue((context / 'manifest/content.json').is_file())
        self.assertTrue((context / 'licenses').is_dir())
        self.assertEqual(resource_by_id(self.root, 'fixture')['files_manifest'], 'assets/data/files.json')

    def test_content_digest_ignores_recipe_metadata_but_checks_target_and_mode(self):
        old = content_digest(self.rows, '/app')
        self.assertEqual(old, content_digest([{**self.rows[0], 'source_member': 'upstream/a'}], '/app'))
        self.assertNotEqual(old, content_digest(self.rows, '/opt'))
        self.assertNotEqual(old, content_digest([{**self.rows[0], 'mode': '0644'}], '/app'))


    def test_root_target_is_supported(self):
        self.resource['target_root'] = '/'
        (self.root / 'assets/images.json').write_text(json.dumps({'images': [self.resource]}))
        rootfs = self.prepare()
        self.assertTrue((rootfs / 'build.sh').is_file())
        context = stage_data_context(self.root, 'fixture', rootfs, self.root / 'root-context')
        self.assertTrue((context / 'rootfs/build.sh').is_file())


    def test_declared_links_preserved_and_escaping_targets_rejected(self):
        (self.payload / 'alias.sh').symlink_to('build.sh')
        rows = self.rows + [{'path': 'alias.sh', 'type': 'symlink', 'link_target': 'build.sh', 'mode': '0777'}]
        archive = self.root / 'linked.tar.gz'
        make_archive(self.payload, rows, archive)
        target = self.root / 'linked-output'
        target.mkdir()
        extract_tar(archive, target, rows)
        self.assertTrue((target / 'alias.sh').is_symlink())
        self.assertEqual((target / 'alias.sh').read_bytes(), b'#!/bin/sh\nexit 0\n')
        with self.assertRaisesRegex(ValueError, 'Unsafe archive path'):
            content_digest(self.rows + [{'path': 'alias.sh', 'type': 'symlink', 'link_target': '../../escape', 'mode': '0777'}])


    def test_qbf_official_source_recreates_exact_frozen_compression(self):
        plain = b'p cnf 1 1\ne 1 0\n1 0\n'
        compressed = lzma.compress(plain, preset=9, check=lzma.CHECK_CRC64)
        import hashlib
        rows = [{'path': 'qbf-public100/example.qdimacs.xz', 'bytes': len(compressed),
                 'mode': '0644', 'sha256': hashlib.sha256(compressed).hexdigest(),
                 'source_member': './gallery22/example.qdimacs',
                 'source_sha256_plain': hashlib.sha256(plain).hexdigest()}]
        source = self.root / 'official.tar.gz'
        with tarfile.open(source, 'w:gz') as tar:
            entry = tarfile.TarInfo('./gallery22/example.qdimacs')
            entry.size = len(plain)
            tar.addfile(entry, io.BytesIO(plain))
        path = self.root / 'assets/data/files.json'
        path.write_text(json.dumps({'files': rows}))
        self.resource.update(id='qbf-public', files_manifest='assets/data/files.json',
                             manifest_sha256=digest(path), target_root='/opt')
        recipe = {'source_archive': {'bytes': source.stat().st_size, 'sha256': digest(source)},
                  'compression': {'preset': 9}}
        (self.root / self.resource['recipe']).write_text(json.dumps(recipe))
        (self.root / 'assets/images.json').write_text(json.dumps({'images': [self.resource]}))
        rootfs = prepare_resource(self.root, 'qbf-public', self.cache, {'source_archive': source})
        self.assertEqual((rootfs / 'opt' / rows[0]['path']).read_bytes(), compressed)

    def test_download_verifies_bytes_before_atomic_cache_publish(self):
        from tcsexam.resources import download
        source = {'url': 'https://example.invalid/verifier.zip', 'bytes': 4,
                  'sha256': hashlib.sha256(b'data').hexdigest()}
        with patch('tcsexam.resources.urllib.request.urlopen', return_value=io.BytesIO(b'data')):
            target = download(source, self.cache / 'downloads')
        self.assertEqual(target.read_bytes(), b'data')
        bad_source = {**source, 'sha256': '0' * 64}
        with patch('tcsexam.resources.urllib.request.urlopen', return_value=io.BytesIO(b'data')):
            with self.assertRaisesRegex(ValueError, 'hash or size'):
                download(bad_source, self.cache / 'downloads')
        self.assertFalse((self.cache / 'downloads' / ('0' * 64)).exists())
        self.assertFalse(list((self.cache / 'downloads').glob('.download-*')))

    def test_official_build_checks_archive_and_exact_installed_files(self):
        import zipfile
        source_files = {
            'Makefile': b'all:\n\tcp verifier.cpp verifier\n',
            'verifier.cpp': b'int main() { return 0; }\n',
        }
        archive = self.root / 'official.zip'
        with zipfile.ZipFile(archive, 'w') as output:
            for name, data in source_files.items():
                output.writestr(name, data)
        rows = []
        for name, data in source_files.items():
            rows.append({'path': 'opt/verifier/' + name, 'source_member': name,
                         'bytes': len(data), 'mode': '0644', 'sha256': hashlib.sha256(data).hexdigest()})
        binary_hash = hashlib.sha256(source_files['verifier.cpp']).hexdigest()
        rows.extend([
            {'path': 'opt/verifier/verifier', 'bytes': len(source_files['verifier.cpp']),
             'mode': '0755', 'sha256': binary_hash},
            {'path': 'usr/local/bin/test_verify', 'bytes': len(source_files['verifier.cpp']),
             'mode': '0755', 'sha256': binary_hash},
        ])
        path = self.root / 'assets/data/files.json'
        path.write_text(json.dumps({'files': rows}))
        source = {'id': 'fixture-source', 'url': 'https://example.invalid/official.zip',
                  'bytes': archive.stat().st_size, 'sha256': digest(archive)}
        builder = 'ubuntu:22.04@sha256:' + 'a' * 64
        recipe = {'source': source, 'archive_format': 'zip',
                  'build': {'builder_image': builder, 'command': ['make', 'all'], 'cwd': 'opt/verifier',
                            'artifact': 'verifier', 'install': 'usr/local/bin/test_verify'}}
        recipe_path = self.root / self.resource['recipe']
        recipe_path.write_text(json.dumps(recipe))
        self.resource.update(recipe_format='official_build', target_root='/',
                             manifest_sha256=digest(path))
        (self.root / 'assets/images.json').write_text(json.dumps({'images': [self.resource]}))

        container = 'a' * 64
        commands = []

        def compile_in_container(binary):
            def execute(command, **kwargs):
                from subprocess import CompletedProcess
                commands.append(command)
                action = command[1]
                if action == 'create':
                    return CompletedProcess(command, 0, stdout=container + '\n', stderr='')
                if action == 'wait':
                    return CompletedProcess(command, 0, stdout='0\n', stderr='')
                if action == 'logs':
                    return CompletedProcess(command, 0, stdout='compiler log\n', stderr='')
                if action == 'cp' and command[2] == container + ':/tcsexam-output/.':
                    output = Path(command[3])
                    (output / 'opt/verifier/verifier').write_bytes(binary)
                return CompletedProcess(command, 0, stdout='', stderr='')
            return execute

        with patch('tcsexam.resources.acquire_official_builder',
                   return_value='tcsexam/official-builder') as acquire, \
                patch('tcsexam.resources.subprocess.run',
                      side_effect=compile_in_container(source_files['verifier.cpp'])) as execute, \
                patch.dict('os.environ', {'HTTPS_PROXY': 'https://proxy.example:3128'}):
            rootfs = prepare_resource(self.root, 'fixture', self.cache, {'fixture-source': archive})
        acquire.assert_called_once()
        create = next(command for command in commands if command[1] == 'create')
        self.assertEqual(create[:2], ['docker', 'create'])
        self.assertIn('--pull=never', create)
        self.assertEqual(create[create.index('--platform') + 1], 'linux/amd64')
        self.assertEqual(create[create.index('/bin/sh') - 1], 'tcsexam/official-builder')
        self.assertEqual(create[-2:], ['make', 'all'])
        self.assertIn('HTTPS_PROXY=https://proxy.example:3128', create)
        self.assertFalse(any('--mount' in command or 'type=bind' in command for command in commands))
        self.assertFalse(any(command[:2] == ['make', 'all'] for command in commands))
        copy_in = next(command for command in commands
                       if command[:2] == ['docker', 'cp'] and command[3] == container + ':/tcsexam-output')
        self.assertTrue(copy_in[2].endswith('/.'))
        self.assertEqual(commands[-2][1], 'logs')
        self.assertEqual(commands[-1], ['docker', 'rm', '-f', container])
        logs = list((self.cache / 'official-container-logs').glob('tcsexam-official-build-*.log'))
        self.assertEqual(len(logs), 1)
        self.assertIn('compiler log', logs[0].read_text())
        self.assertEqual({p.relative_to(rootfs).as_posix() for p in rootfs.rglob('*') if p.is_file()},
                         {row['path'] for row in rows})
        self.assertEqual((rootfs / 'usr/local/bin/test_verify').stat().st_mode & 0o777, 0o755)

        with patch('tcsexam.resources.acquire_official_builder', return_value='tcsexam/official-builder'), \
                patch('tcsexam.resources.subprocess.run', side_effect=compile_in_container(b'wrong binary')):
            with self.assertRaisesRegex(ValueError, 'Content differs'):
                prepare_resource(self.root, 'fixture', self.root / 'wrong-binary-cache',
                                 {'fixture-source': archive})
        self.assertFalse((self.root / 'wrong-binary-cache/fixture/fixed').exists())

        bad = self.root / 'bad-official.zip'
        bad.write_bytes(archive.read_bytes() + b'x')
        with self.assertRaisesRegex(ValueError, 'hash or size'):
            prepare_resource(self.root, 'fixture', self.root / 'wrong-hash', {'fixture-source': bad})

        unexpected = self.root / 'unexpected.zip'
        with zipfile.ZipFile(unexpected, 'w') as output:
            for name, data in source_files.items():
                output.writestr(name, data)
            output.writestr('unexpected.cpp', 'unexpected')
        source.update(bytes=unexpected.stat().st_size, sha256=digest(unexpected))
        recipe_path.write_text(json.dumps(recipe))
        with self.assertRaisesRegex(ValueError, 'undeclared'):
            prepare_resource(self.root, 'fixture', self.root / 'unexpected-cache',
                             {'fixture-source': unexpected})
        self.assertFalse((self.root / 'unexpected-cache/fixture/fixed').exists())

    def test_official_archive_download_uses_checked_docker_cache(self):
        from subprocess import CompletedProcess
        from tcsexam.resources import download_official
        source = {'url': 'https://example.invalid/verifier.zip', 'bytes': 4,
                  'sha256': hashlib.sha256(b'data').hexdigest()}
        build = {'builder_image': 'ubuntu:22.04@sha256:' + 'a' * 64}
        calls = []
        container = 'b' * 64

        def fetch(command, **kwargs):
            calls.append(command)
            action = command[1]
            if action == 'create':
                return CompletedProcess(command, 0, stdout=container + '\n', stderr='')
            if action == 'wait':
                return CompletedProcess(command, 0, stdout='0\n', stderr='')
            if action == 'cp' and command[2] == container + ':/out/source':
                Path(command[3]).write_bytes(b'data')
            return CompletedProcess(command, 0, stdout='', stderr='')

        with patch('tcsexam.resources.subprocess.run', side_effect=fetch):
            target = download_official(source, self.cache / 'official-downloads', build,
                                       'tcsexam/official-builder')
            self.assertEqual(target.read_bytes(), b'data')
            first = len(calls)
            self.assertEqual(download_official(source, self.cache / 'official-downloads', build,
                                               'tcsexam/official-builder'), target)
            self.assertEqual(len(calls), first)
            target.write_bytes(b'bad')
            download_official(source, self.cache / 'official-downloads', build,
                              'tcsexam/official-builder')
        self.assertGreater(len(calls), first)
        self.assertEqual(target.read_bytes(), b'data')
        command = calls[0]
        self.assertEqual(command[:2], ['docker', 'create'])
        self.assertEqual(command[-3:], [source['url'], source['sha256'], '4'])
        self.assertEqual(command[command.index('/bin/sh') - 1], 'tcsexam/official-builder')
        self.assertIn('--pull=never', command)
        self.assertFalse(any('--mount' in call or 'type=bind' in call for call in calls))
        self.assertEqual(calls[-1], ['docker', 'rm', '-f', container])
        self.assertFalse(list((self.cache / 'official-downloads').glob('.download-*')))

    def test_official_container_failures_are_logged_and_cleaned(self):
        from subprocess import CompletedProcess, TimeoutExpired
        from tcsexam.resources import run_official_container
        for kind in ('create', 'start', 'compile', 'timeout'):
            with self.subTest(kind=kind):
                calls = []
                container = 'c' * 64
                name = 'tcsexam-official-build-' + kind
                create = ['docker', 'create', '--name', name, 'builder']

                def execute(command, **kwargs):
                    calls.append(command)
                    action = command[1]
                    if action == 'create':
                        return CompletedProcess(command, 1 if kind == 'create' else 0,
                                                stdout=container + '\n', stderr=kind + ' failure')
                    if action == 'start' and kind == 'start':
                        return CompletedProcess(command, 1, stdout='', stderr='start failure')
                    if action == 'wait':
                        if kind == 'timeout':
                            raise TimeoutExpired(command, kwargs['timeout'])
                        return CompletedProcess(command, 0,
                                                stdout='17\n' if kind == 'compile' else '0\n', stderr='')
                    if action == 'logs':
                        return CompletedProcess(command, 0, stdout=kind + ' container log\n', stderr='')
                    return CompletedProcess(command, 0, stdout='', stderr='')

                with patch('tcsexam.resources.subprocess.run', side_effect=execute):
                    with self.assertRaises(ValueError):
                        run_official_container(create, 5, self.root / 'failure-logs',
                                               copy_out=[('/tcsexam-output/.', self.root / kind)])
                self.assertEqual(calls[-2][1], 'logs')
                self.assertEqual(calls[-1], ['docker', 'rm', '-f', container])
                self.assertFalse(any('--mount' in call or 'type=bind' in call for call in calls))
                self.assertFalse(any(call[1] == 'cp' for call in calls))
                if kind == 'start':
                    self.assertFalse(any(call[1] == 'wait' for call in calls))
                log = self.root / 'failure-logs' / (name + '.log')
                self.assertIn(kind + ' container log', log.read_text())
                self.assertIn('failure', log.read_text())

    def test_independent_resource_preparation_reuses_image_builder_acquisition(self):
        from argparse import Namespace
        from tcsexam.resources import acquire_official_builder
        reference = 'ubuntu:22.04@sha256:' + 'a' * 64
        args = Namespace(docker_context='selected-host', pull_policy='never')
        with patch('tcsexam.build.ImageBuilder') as builder_type:
            builder_type.return_value.acquire.return_value = {
                'reference': reference, 'local_image': 'tcsexam/upstream-jammy'}
            image = acquire_official_builder(self.root, {'builder_image': reference}, self.cache, args)
        self.assertEqual(image, 'tcsexam/upstream-jammy')
        builder_type.assert_called_once()
        self.assertEqual(builder_type.call_args.args[1], [])
        options = builder_type.call_args.args[2]
        self.assertEqual(options.cache, self.cache)
        self.assertEqual(options.docker_context, 'selected-host')
        self.assertEqual(options.pull_policy, 'never')
        builder_type.return_value.acquire.assert_called_once_with(reference)

    def test_build_requires_remote_private_target(self):
        with self.assertRaisesRegex(ValueError, 'remote builder'):
            build_data_image(self.root, 'fixture', self.cache, 'example.invalid/data:v1', builder='default')
        with self.assertRaisesRegex(ValueError, 'authorized registry prefix'):
            build_data_image(self.root, 'fixture', self.cache, 'registry.example/public/data:v1')

    def test_registry_upload_checks_distribution_before_building(self):
        for distribution, allowed, public, message in (
                ('unresolved', False, False, 'no accepted distribution decision'),
                ('local_prepare', False, True, 'not approved for public registry upload'),
                ('redistributable', False, True, 'not approved for public registry upload')):
            with self.subTest(distribution=distribution, allowed=allowed, public=public):
                self.resource['distribution'] = distribution
                self.resource['public_upload_allowed'] = allowed
                (self.root / 'assets/images.json').write_text(json.dumps({'images': [self.resource]}))
                with patch('tcsexam.resources.prepare_resource') as prepare:
                    with self.assertRaisesRegex(ValueError, message):
                        build_data_image(self.root, 'fixture', self.cache, 'registry.example/data:v1',
                                         context='context', metadata_file='metadata',
                                         registry_prefix='registry.example', public=public)
                    prepare.assert_not_called()

    def test_local_prepare_can_use_an_explicit_private_registry(self):
        self.resource['distribution'] = 'local_prepare'
        self.resource['public_upload_allowed'] = False
        (self.root / 'assets/images.json').write_text(json.dumps({'images': [self.resource]}))
        metadata = self.root / 'build-metadata.json'
        metadata.write_text(json.dumps({'containerimage.digest': 'sha256:' + 'a' * 64}))
        with patch('tcsexam.resources.prepare_resource', return_value=self.payload), \
                patch('tcsexam.resources.stage_data_context'), \
                patch('tcsexam.resources.subprocess.run') as execute:
            execute.return_value.returncode = 0
            result = build_data_image(self.root, 'fixture', self.cache, 'registry.example/data:v1',
                                      context='context', metadata_file=metadata,
                                      registry_prefix='registry.example')
        self.assertEqual(result['distribution'], 'local_prepare')
        self.assertIn('--push', execute.call_args.args[0])

    def test_private_input_requires_explicit_named_file(self):
        recipe = self.root / self.resource['recipe']
        data = json.loads(recipe.read_text())
        data['source']['url'] = None
        recipe.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'explicit --input fixture-source=PATH'):
            prepare_resource(self.root, 'fixture', self.cache)
        self.assertTrue(self.prepare().is_dir())
