"""Publication checks cover release text and keep runtime evidence separate."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tcsexam.checks import (internal_reference_categories, legacy_name_lines, publication,
                            publication_paths, publication_text, validate_task_identity)


def fixture_domain():
    return '.'.join(('fixture', 'm' + 'sh', 'invalid'))


def fixture_ip(octets=(10, 123, 45, 67)):
    return '.'.join(map(str, octets))


def fixture_path(*parts):
    return '/'.join(('', *parts))


class PublicationChecks(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.write('assets/images.json', json.dumps({'images': []}))
        self.write('assets/files.json', json.dumps({'files': []}))
        self.write('suites/tasks.json', json.dumps({'tasks': []}))
        self.write('docs/licenses/third-party/distribution-decisions.json', json.dumps({
            'integration_complete': True, 'enforced_by_exporter': True}))

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def report(self):
        with patch('tcsexam.checks.validate', return_value={'static_integrity': 'passed'}):
            return publication(self.root)

    def test_all_release_locations_and_suffixes_are_scanned(self):
        names = ['pyproject.toml', '.github/workflows/checks.yml', '.gitlab-ci.yml',
                 'custom/RELEASE', 'environment/Dockerfile', 'config/settings.json',
                 'config/run.toml', 'scripts/run.sh', 'src/tcsexam/checks.py',
                 'src/tcsexam/tests/test_checks.py', 'nested/build/SOURCE']
        for name in names:
            self.write(name, 'endpoint = "https://' + fixture_domain() + '"\n')
        found = {r['path'] for r in self.report()['issues'] if r['kind'] == 'internal_reference'}
        self.assertEqual(found, set(names))

    def test_git_includes_tracked_and_new_but_not_ignored_outputs(self):
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True, capture_output=True)
        self.write('.gitignore', 'scratch/\n')
        tracked = self.write('tracked-no-suffix', fixture_domain())
        subprocess.run(['git', '-C', str(self.root), 'add', tracked.name], check=True, capture_output=True)
        self.write('new-no-suffix', fixture_domain())
        self.write('scratch/local', fixture_domain())
        found = {str(p.relative_to(self.root)) for p in publication_paths(self.root)}
        self.assertIn('tracked-no-suffix', found)
        self.assertIn('new-no-suffix', found)
        self.assertNotIn('scratch/local', found)
        self.assertNotIn('.git', found)

    def test_unicode_text_and_binary_classification(self):
        for encoding in ('utf-8-sig', 'utf-16', 'utf-32'):
            path = self.root / ('text-' + encoding)
            path.write_bytes(fixture_domain().encode(encoding))
            self.assertEqual(publication_text(path), fixture_domain())
        binary = self.root / 'image.dat'
        binary.write_bytes(b'\x89PNG\x00\xff')
        self.assertIsNone(publication_text(binary))
        report = self.report()
        self.assertEqual(report['source_scan']['binary_files_skipped'], 1)
        self.assertEqual(sum(r['kind'] == 'internal_reference' for r in report['issues']), 3)

    def test_internal_domains_and_network_addresses(self):
        domains = [fixture_domain(), fixture_domain() + '.', '.'.join(('build', 'internal')),
                   '.'.join(('fixture-vpc', 'example', 'invalid')),
                   '.'.join(('buildkit-fixture', 'launch' + 'pad'))]
        for domain in domains:
            with self.subTest(domain=domain):
                self.assertIn('internal_domain', internal_reference_categories('https://' + domain))
        addresses = [(10, 123, 45, 67), (172, 18, 3, 4), (192, 168, 7, 8),
                     (100, 80, 3, 4), (169, 254, 3, 4), (198, 18, 3, 4)]
        for octets in addresses:
            with self.subTest(octets=octets):
                address = fixture_ip(octets)
                for context in ('https://' + address, 'HOST="' + address + '"',
                                'SERVICE_URL="' + address + '"', 'worker=' + address,
                                'node=' + address, address + ':8443'):
                    self.assertIn('nonpublic_ip', internal_reference_categories(context))
                self.assertEqual(internal_reference_categories('coordinates = [' + address + ']'), [])
        for address in (':'.join(('fdab', '1234', '', '7')), ':'.join(('fe80', '', '7'))):
            self.assertIn('nonpublic_ip', internal_reference_categories('https://[' + address + ']:443'))

    def test_private_platform_names_in_prose_identifiers_and_paths(self):
        names = ['mang' + 'rove', 'agent' + 'gym', 'agent' + 'env']
        for name in names:
            for content in (name, name.upper(), f'{name}_sdk', f'{name}-service'):
                with self.subTest(content=content):
                    self.assertIn('internal_platform', internal_reference_categories(content))
        self.write('docs/guide.md', 'No dependency on ' + names[0] + '.')
        self.write('assets/' + names[1] + '-source.json', '{}')
        issues = self.report()['issues']
        self.assertIn('docs/guide.md', {r['path'] for r in issues
                                      if r['kind'] == 'internal_reference'})
        self.assertIn('assets/' + names[1] + '-source.json',
                      {r['path'] for r in issues if r['kind'] == 'internal_reference_path'})

    def test_private_document_links(self):
        host = '.'.join(('moon' + 'shot', 'fei' + 'shu', 'cn'))
        self.assertIn('internal_document', internal_reference_categories('https://' + host + '/docx/example'))
        self.assertEqual(internal_reference_categories('https://example.com/docs'), [])

    def test_docker_host_gateway_is_not_an_internal_service(self):
        docker_host = '.'.join(('host', 'docker', 'internal'))
        self.assertEqual(internal_reference_categories('http://' + docker_host + ':8420'), [])
        prefixed_host = '.'.join(('prefix', 'host', 'docker', 'internal'))
        other_domain = '.'.join(('host', 'docker', 'corp'))
        self.assertIn('internal_domain', internal_reference_categories('https://' + prefixed_host))
        self.assertIn('internal_domain', internal_reference_categories('https://' + other_domain))

    def test_public_examples_local_binds_and_invalid_addresses_are_allowed(self):
        for octets in ((127, 0, 0, 1), (0, 0, 0, 0), (192, 0, 2, 4),
                       (203, 0, 113, 7), (10, 999, 2, 3)):
            self.assertEqual(internal_reference_categories('http://' + fixture_ip(octets) + ':8000'), [])
        for content in ('http://localhost:8000', 'https://example.invalid',
                        'https://[::1]:8000', 'https://[2001:db8::7]:443',
                        'self.local = True', 'self.settings.local', 'cls.config.internal',
                        'https://' + '.'.join(('launchpad', 'net')),
                        'doc/adduser.local.8', 'chacha-core-internal.asm',
                        '/app/submission', '/opt/toolchain',
                        fixture_path('mnt', 'data', 'instances')):
            self.assertEqual(internal_reference_categories(content), [], content)
        for receiver in ('self', 'cls'):
            domain = '.'.join((receiver, 'settings', 'local'))
            for scheme in ('https://', 'https://fixture@'):
                self.assertIn('internal_domain', internal_reference_categories(scheme + domain))

    def test_only_the_exact_upstream_ci_cache_example_is_exempt(self):
        example = fixture_path('home', 'runner', '.cache', 'ms-playwright')
        self.assertEqual(internal_reference_categories(example), [])
        other = fixture_path('home', 'runner', '.cache', 'other-tool')
        self.assertEqual(internal_reference_categories(other), ['machine_path'])

    def test_personal_and_specific_mount_paths(self):
        paths = [fixture_path('home', 'synthetic-reviewer', 'project'),
                 fixture_path('Users', 'synthetic-reviewer', 'project'),
                 fixture_path('mnt', 'synthetic-shared-store', 'project'),
                 '\\'.join(('C:', 'Users', 'synthetic-reviewer', 'project'))]
        for path in paths:
            with self.subTest(path=path):
                self.assertIn('machine_path', internal_reference_categories(path))
                self.assertIn('machine_path', internal_reference_categories(json.dumps({'path': path})))
        self.assertIn('internal_storage', internal_reference_categories('storage = ' + 'moon' + 'fs'))

    def test_checker_and_test_sources_do_not_exempt_whole_files(self):
        for source in (Path(__file__), Path(__file__).parents[1] / 'checks.py'):
            self.assertEqual(internal_reference_categories(source.read_text()), [], source.name)
        target = 'src/tcsexam/checks.py'
        self.write(target, (Path(__file__).parents[1] / 'checks.py').read_text()
                   + '\n# endpoint: ' + fixture_domain() + '\n')
        self.assertIn(target, {r['path'] for r in self.report()['issues']})

    def test_symlink_files_and_directories_are_reported_without_following(self):
        self.write('payload', 'safe')
        (self.root / 'linked-file').symlink_to('payload')
        (self.root / 'linked-directory').symlink_to('assets', target_is_directory=True)
        links = {r['path'] for r in self.report()['issues'] if r['kind'] == 'source_symlink'}
        self.assertEqual(links, {'linked-file', 'linked-directory'})

    def test_credential_report_never_echoes_value(self):
        value = 'sk-' + 'x' * 30
        self.write('custom/SECRET', value)
        report = self.report()
        self.assertIn({'kind': 'possible_credential', 'path': 'custom/SECRET', 'line_numbers': [1]}, report['issues'])
        self.assertNotIn(value, json.dumps(report))

    def test_key_files_block_publication_even_when_binary(self):
        value = 'synthetic-key-material'
        path = self.write('tasks/fixture/tests/instance.key', value)
        path.write_bytes(b'\x00' + value.encode())
        report = self.report()
        self.assertFalse(report['ready_for_publication'])
        self.assertIn({'kind': 'possible_credential_file',
                       'path': 'tasks/fixture/tests/instance.key'}, report['issues'])
        self.assertNotIn(value, json.dumps(report))
        self.write('tasks/fixture/tests/public.pub', 'not a key file')
        self.assertNotIn({'kind': 'possible_credential_file',
                          'path': 'tasks/fixture/tests/public.pub'}, self.report()['issues'])

    def test_retired_display_names_and_namespaces_are_reported_everywhere(self):
        values = ['TCS' + 'HardBench', 'TCS' + 'HardProblem', 'tcs' + 'hard/fixture',
                  'TCS' + 'BENCH']
        for number, value in enumerate(values):
            target = f'custom/BRANDING-{number}'
            self.write(target, 'current name: TCSExam\n' + value + '\n')
        issues = [row for row in self.report()['issues'] if row['kind'] == 'legacy_project_name']
        self.assertEqual({row['path'] for row in issues},
                         {f'custom/BRANDING-{number}' for number in range(len(values))})
        self.assertTrue(all(row['line_numbers'] == [2] for row in issues))
        # Matching applies to case variants and filenames as well.
        name = 'custom/' + values[0].upper() + '-PATCHES.md'
        self.write(name, 'TCSExam\n')
        self.assertIn(name, {row['path'] for row in self.report()['issues']
                             if row['kind'] == 'legacy_project_path'})

    def test_historical_seeds_and_source_images_remain_valid_but_do_not_exempt_files(self):
        prefix = 'tcs' + 'hard'
        provenance = '\n'.join([prefix + '-transform-20260831',
                                prefix + '-form2-split-260920:fixture',
                                'source_image=' + prefix + '-lean:historical'])
        self.assertEqual(legacy_name_lines(provenance), [])
        self.assertEqual(legacy_name_lines(provenance + '\n' + prefix + '/fixture'), [4])
        for source in (Path(__file__), Path(__file__).parents[1] / 'checks.py'):
            self.assertEqual(legacy_name_lines(source.read_text()), [], source.name)

    def test_retired_backup_file_blocks_publication_even_when_binary(self):
        path = self.write('tasks/fixture/tests/test_local.sh.bak', 'retired')
        path.write_bytes(b'\x00\xff')
        report = self.report()
        self.assertFalse(report['ready_for_publication'])
        self.assertIn({'kind': 'retired_backup', 'path': 'tasks/fixture/tests/test_local.sh.bak'},
                      report['issues'])

    def test_task_namespace_contributors_and_checkpoint_identity_are_checked(self):
        config = {'task': {'name': 'tcsexam/fixture',
                           'authors': [{'name': 'TCSExam Contributors'}]}}
        validate_task_identity(config, 'tasks/fixture', 'tcsexam/fixture')
        validate_task_identity(config, 'tasks/fixture')
        with self.assertRaisesRegex(ValueError, 'Checkpoint task identity differs'):
            validate_task_identity(config, 'tasks/fixture', 'tcsexam/other')
        config['task']['name'] = 'tcs' + 'hard/fixture'
        with self.assertRaisesRegex(ValueError, 'Wrong task namespace'):
            validate_task_identity(config, 'tasks/fixture')
        config['task']['name'] = 'tcsexam/fixture'
        config['task']['authors'] = [{'name': 'Former contributors'}]
        with self.assertRaisesRegex(ValueError, 'Wrong task contributors'):
            validate_task_identity(config, 'tasks/fixture')

    def test_internal_resource_identifiers_are_reported_without_values(self):
        cases = [('/'.join(('schema-v' + '123', 'workbench', 'fixture.md')), 'internal_workspace'),
                 ('i-' + '1234567890123456789', 'cloud_instance'),
                 ('agent' + 'env:' + 'fixture', 'internal_profile'),
                 ('frontier' + '_' + 'smith:' + 'fixture-tag', 'internal_image_namespace')]
        for value, category in cases:
            self.assertIn(category, internal_reference_categories(value))
        self.write('custom/RESOURCE', '\n'.join(['ordinary text', *[value for value, _ in cases]]))
        issue = next(row for row in self.report()['issues'] if row['kind'] == 'internal_reference')
        self.assertEqual(issue['line_numbers'], [2, 3, 4, 5])
        self.assertEqual(set(issue['categories']),
                         {category for _, category in cases} | {'internal_platform'})
        for value, _ in cases:
            self.assertNotIn(value, json.dumps(issue))

    def test_historical_run_identifiers_require_named_context(self):
        number = '654' + '321'
        for label in ('容器', 'container', 'run'):
            self.assertIn('internal_run', internal_reference_categories(label + ' ' + number))
        self.assertEqual(internal_reference_categories('mathematical parameter = ' + number), [])
        self.assertEqual(internal_reference_categories('run ' + '12345'), [])

    def test_runtime_pending_blocks_runtime_release_but_not_source_export(self):
        tasks = [{'id': 'proof-fixture', 'variants': {'default': {'readiness': 'runtime_pending'}}},
                 {'id': 'solver-fixture', 'variants': {'online': {'readiness': 'user_backend_required'}}}]
        self.write('suites/tasks.json', json.dumps({'tasks': tasks}))
        report = self.report()
        self.assertFalse(report['ready_for_publication'])
        self.assertEqual(report['issues'], [{'kind': 'runtime_acceptance_pending', 'count': 1}])
        with patch('tcsexam.checks.validate', return_value={'static_integrity': 'passed'}):
            source = publication(self.root, phase='source')
        self.assertTrue(source['ready_for_publication'])
        self.assertEqual(source['runtime_validation'], report['runtime_validation'])
        self.assertFalse(report['runtime_validation']['complete'])
        self.assertEqual(report['runtime_validation']['pending'],
                         [{'task': 'proof-fixture', 'variant': 'default', 'status': 'runtime_pending'}])
        self.assertEqual(report['user_backend_requirements'],
                         [{'task': 'solver-fixture', 'variant': 'online', 'status': 'user_backend_required'}])

    def test_source_phase_only_excludes_public_distribution_pending(self):
        self.write('assets/images.json', json.dumps({'images': [{
            'id': 'candidate', 'public_upload_allowed': True, 'public_pull_verified': False,
            'acquisition': {'preferred': 'public_image'}}]}))
        with patch('tcsexam.checks.validate', return_value={'static_integrity': 'passed'}):
            source = publication(self.root, phase='source')
            release = publication(self.root, phase='release')
        self.assertTrue(source['ready_for_publication'])
        self.assertEqual(source['check_phase'], 'source')
        self.assertFalse(release['ready_for_publication'])
        self.assertEqual({row['kind'] for row in release['issues']},
                         {'required_public_images_pending'})
        self.write('assets/files.json', json.dumps({'files': [{
            'path': 'undecided', 'distribution': 'unresolved'}]}))
        with patch('tcsexam.checks.validate', return_value={'static_integrity': 'passed'}):
            source = publication(self.root, phase='source')
        self.assertFalse(source['ready_for_publication'])
        self.assertEqual({row['kind'] for row in source['issues']},
                         {'distribution_terms_unresolved'})

    def test_distribution_and_integrity_still_block_publication(self):
        self.write('assets/images.json', json.dumps({'images': [{'id': 'required-data',
            'public_upload_allowed': True, 'acquisition': {'preferred': 'public_image'}}]}))
        self.write('assets/files.json', json.dumps({'files': [{'path': 'missing', 'distribution': 'unresolved'}]}))
        report = self.report()
        self.assertFalse(report['ready_for_publication'])
        self.assertEqual({r['kind'] for r in report['issues']},
                         {'required_public_images_pending', 'distribution_terms_unresolved'})
        with patch('tcsexam.checks.validate', side_effect=ValueError('fixture integrity failure')):
            report = publication(self.root)
        self.assertIn('source_integrity', {r['kind'] for r in report['issues']})

    def test_review_flags_cannot_substitute_for_actual_file_checks(self):
        path = 'docs/licenses/third-party/distribution-decisions.json'
        for decisions in (
                {'integration_complete': False, 'enforced_by_exporter': True},
                {'integration_complete': True, 'enforced_by_exporter': False}):
            with self.subTest(decisions=decisions):
                self.write(path, json.dumps(decisions))
                report = self.report()
                self.assertTrue(report['ready_for_publication'])
                self.assertEqual(report['issues'], [])
        self.write(path, '[]')
        report = self.report()
        self.assertEqual({row['kind'] for row in report['issues']},
                         {'distribution_decisions_invalid'})

    def test_external_inputs_and_optional_images_do_not_block_source_review(self):
        self.write('assets/images.json', json.dumps({'images': [{
            'id': 'optional', 'public_upload_allowed': True, 'public_pull_verified': False,
            'acquisition': {'preferred': 'local_build'}}]}))
        self.write('assets/files.json', json.dumps({'files': [{
            'path': 'external.dat', 'distribution': 'unresolved', 'status': 'source_omitted'}]}))
        with patch('tcsexam.checks.validate', return_value={'static_integrity': 'passed'}):
            source = publication(self.root, phase='source')
            release = publication(self.root, phase='release')
        self.assertTrue(source['ready_for_publication'])
        self.assertEqual(source['external_input_delivery']['pending'], 1)
        self.assertEqual({r['kind'] for r in release['issues']}, {'external_input_delivery_pending'})


if __name__ == '__main__':
    unittest.main()
