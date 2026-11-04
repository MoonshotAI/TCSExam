"""Check BPPLIB official packing recovery and judging-instance reconstruction."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tcsexam import bpplib


ROOT = Path(__file__).resolve().parents[3]
TRANSFORM = 'tasks/solver/online/bpp-bpplib/tests/transform.py'


def sha(data):
    return hashlib.sha256(data).hexdigest()


class PackingTests(unittest.TestCase):
    def setUp(self):
        self.original = b'3 10 6 4 4'
        self.csp = b'2 10 6 1 4 2'

    def test_official_log_parse_and_canonical_packing(self):
        log = b'ignored header\nSolution:\n1 x [i=1 i=2]\n1 x [i=2]\n'
        self.assertEqual(bpplib.packing(self.original, self.csp, log), b'2\n1 1 2\n')

    def test_missing_coverage_and_excess_capacity_are_rejected(self):
        cases = {
            'Packing does not cover all items': b'Solution:\n1 x [i=1 i=2]\n',
            'Packing exceeds capacity': b'Solution:\n1 x [i=1 i=2 i=2]\n',
        }
        for message, log in cases.items():
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                bpplib.packing(self.original, self.csp, log)

    def test_transform_inverse_and_packing_mapping(self):
        transform = bpplib.load_transform(ROOT, TRANSFORM)
        weights = [6, 4, 4]
        transformed, perm = transform.transform_instance('fixture.txt', 3, weights)
        restored, inverse_perm = transform.invert_instance('fixture.txt', 3, transformed)
        self.assertEqual(restored, weights)
        self.assertEqual(inverse_perm, perm)
        mapped = transform.rewrite_packing([1, 1, 2], perm)
        instance = transform.serialize(3, 10, transformed)
        packing = ('2\n' + ' '.join(map(str, mapped)) + '\n').encode()
        self.assertEqual(bpplib.validate_packing(instance, packing, 2), (2, mapped))


class PrepareJudgingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / 'output'
        self.transform = bpplib.load_transform(ROOT, TRANSFORM)
        original = {
            'hidden.txt': b'3 10 6 4 4',
            'public.txt': b'2 5 2 3',
        }
        csp = {
            'hidden.txt': b'2 10 6 1 4 2',
            'public.txt': b'2 5 2 1 3 1',
        }
        log = {
            'hidden.txt': b'Solution:\n1 x [i=1 i=2]\n1 x [i=2]\n',
            'public.txt': b'Solution:\n1 x [i=1 i=2]\n',
        }
        official_packing = {'hidden.txt': b'2\n1 1 2\n', 'public.txt': b'1\n1 1\n'}
        self.members = {'1_Falkenauer': [], '1_Falkenauer_CSP': [], 'Results_VPS': []}
        original_specs = []
        for name in original:
            original_member = 'Falkenauer/Falkenauer_T/' + name
            csp_member = 'Falkenauer_CSP/Falkenauer_T/' + name
            log_member = 'Results_VPS/' + name.replace('.txt', '_Results_VPS.txt')
            self.members['1_Falkenauer'].append((original_member, original[name]))
            self.members['1_Falkenauer_CSP'].append((csp_member, csp[name]))
            self.members['Results_VPS'].append((log_member, log[name]))
            original_specs.append({
                'path': 'tests/official-packs/' + name.replace('.txt', '.pack'),
                'sha256': sha(official_packing[name]),
                'bins': 2 if name == 'hidden.txt' else 1,
                'csp': '1_Falkenauer_CSP/' + csp_member,
                'log': 'Results_VPS/' + log_member,
            })
        self.members['1_Falkenauer'].append(('Falkenauer/unrelated.txt', b'1 1 1'))
        transformed, perm = self.transform.transform_instance('hidden.txt', 3, [6, 4, 4])
        instance = self.transform.serialize(3, 10, transformed)
        mapped = self.transform.rewrite_packing([1, 1, 2], perm)
        transformed_packing = ('2\n' + ' '.join(map(str, mapped)) + '\n').encode()
        self.reconstruction = {
            'byte_identical_original_packings': 2,
            'byte_identical_transformed_instances_and_packings': 1,
            'original_packings': original_specs,
            'transformed': [{
                'code': 'ex001.txt', 'official': 'hidden.txt',
                'instance_sha256': sha(instance), 'packing_sha256': sha(transformed_packing),
            }],
        }
        self.rows = [{'path': 'tests/instances/ex001.txt', 'bytes': len(instance),
                      'mode': '0644', 'sha256': sha(instance)}]
        self.inputs = {}
        sources = []
        for source_id in self.members:
            archive = self.root / (source_id + '.rar')
            archive.write_bytes(('checked ' + source_id).encode())
            self.inputs[source_id] = archive
            sources.append({'id': source_id, 'url': None, 'bytes': archive.stat().st_size,
                            'sha256': sha(archive.read_bytes())})
        sources.append({'id': 'Solutions.xlsx', 'url': None, 'bytes': 0, 'sha256': sha(b'')})
        self.write_json('assets/data/bpplib/development.json', {'sources': sources})
        self.write_json('docs/licenses/third-party/bpplib-reconstruction.json', self.reconstruction)
        self.write_json('assets/data/bpplib/judging.json', {
            'source_recipe': 'assets/data/bpplib/development.json',
            'reconstruction': 'docs/licenses/third-party/bpplib-reconstruction.json',
            'transform': TRANSFORM,
        })
        self.bundle = {'recipe': 'assets/data/bpplib/judging.json'}

    def write_json(self, relative, data):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))

    def prepare(self):
        def fake_rar_members(archive):
            return iter(self.members[Path(archive).stem])
        with patch('tcsexam.bpplib.rar_members', side_effect=fake_rar_members), \
                patch('tcsexam.bpplib.load_transform', return_value=self.transform):
            bpplib.prepare_judging(self.root, self.bundle, self.rows, self.output,
                                   self.root / 'downloads', self.inputs)

    def test_only_declared_instances_are_written(self):
        self.prepare()
        files = {path.relative_to(self.output).as_posix(): path
                 for path in self.output.rglob('*') if path.is_file()}
        self.assertEqual(set(files), {self.rows[0]['path']})
        output = files[self.rows[0]['path']]
        self.assertEqual(sha(output.read_bytes()), self.rows[0]['sha256'])
        self.assertEqual(output.stat().st_mode & 0o777, 0o644)

    def test_every_original_packing_hash_is_checked(self):
        self.reconstruction['original_packings'][1]['sha256'] = '0' * 64
        self.write_json('docs/licenses/third-party/bpplib-reconstruction.json', self.reconstruction)
        with self.assertRaisesRegex(ValueError, 'Original packing bytes differ'):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_transformed_packing_hash_mismatch_is_rejected(self):
        self.reconstruction['transformed'][0]['packing_sha256'] = '0' * 64
        self.write_json('docs/licenses/third-party/bpplib-reconstruction.json', self.reconstruction)
        with self.assertRaisesRegex(ValueError, 'Transformed packing bytes differ'):
            self.prepare()
        self.assertFalse(self.output.exists())


class RecipeTests(unittest.TestCase):
    def test_public_recipe_references_fixed_sources_and_reconstruction(self):
        recipe = json.loads((ROOT / 'assets/data/bpplib/judging.json').read_text())
        sources = json.loads((ROOT / recipe['source_recipe']).read_text())['sources']
        reconstruction = json.loads((ROOT / recipe['reconstruction']).read_text())
        rows = json.loads((ROOT / 'assets/data/bpplib/judging-files.json').read_text())['files']
        self.assertEqual(len(sources), 19)
        self.assertEqual(len(reconstruction['original_packings']), 63)
        self.assertEqual(len(reconstruction['transformed']), 39)
        self.assertEqual(len(rows), 39)
        self.assertNotIn('source', recipe)
        self.assertFalse(recipe['public_upload_allowed'])
        self.assertEqual(recipe['distribution'], 'local_prepare')
        self.assertTrue((ROOT / TRANSFORM).is_file())


if __name__ == '__main__':
    unittest.main()
