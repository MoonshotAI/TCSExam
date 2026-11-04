import hashlib
import json
from pathlib import Path

import pytest

from tcsexam.official_file_data import prepare_data


def test_binary_decoder_and_saved_vertex_mapping_match_original_serializer(tmp_path):
    root = Path(__file__).resolve().parents[3]
    transform = 'assets/data/solver/maxclique-dimacs/transform.py'
    preamble = b'c original author notice\np edge 3 2\n'
    source = tmp_path / 'source.b'
    source.write_bytes(str(len(preamble)).encode() + b'\n' + preamble + b'\0\x80\x40')
    expected = b'c max clique instance (DIMACS ASCII)\np edge 3 2\ne 1 2\ne 1 3\n'
    declaration = {'path': 'tests/instances/tx001.clq', 'source_id': 'original',
                   'operation': 'dimacs_binary_relabel', 'n': 3, 'm': 2, 'perm': [3, 1, 2]}
    recipe = {'transform': transform,
              'transform_sha256': hashlib.sha256((root / transform).read_bytes()).hexdigest(),
              'sources': [{'id': 'original', 'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                           'bytes': source.stat().st_size}], 'outputs': [declaration]}
    recipe_path = tmp_path / 'recipe.json'
    recipe_path.write_text(json.dumps(recipe))
    # The fixture repository contains only the exact source helper and declaration.
    fixture = tmp_path / 'repo'
    (fixture / transform).parent.mkdir(parents=True)
    (fixture / transform).write_bytes((root / transform).read_bytes())
    (fixture / 'recipe.json').write_bytes(recipe_path.read_bytes())
    row = {'path': declaration['path'], 'bytes': len(expected), 'mode': '0644',
           'sha256': hashlib.sha256(expected).hexdigest()}
    prepare_data(fixture, {'recipe': 'recipe.json'}, [row], tmp_path / 'out',
                 tmp_path / 'downloads', inputs={'original': source})
    assert (tmp_path / 'out' / row['path']).read_bytes() == expected
    declaration['perm'] = [1, 1, 3]
    (fixture / 'recipe.json').write_text(json.dumps(recipe))
    with pytest.raises(ValueError, match='dimensions or permutation'):
        prepare_data(fixture, {'recipe': 'recipe.json'}, [row], tmp_path / 'bad',
                     tmp_path / 'downloads', inputs={'original': source})
