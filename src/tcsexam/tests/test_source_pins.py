import hashlib
import json

import pytest

from tcsexam.checks import validate_source_pins


def fixture(tmp_path, declared=True):
    (tmp_path / 'assets').mkdir()
    data = b'external input'
    row = {'path': 'inputs/example.dat', 'sha256': hashlib.sha256(data).hexdigest()}
    (tmp_path / 'assets/sources.json').write_text(json.dumps({'files': [row], 'packaging_changes': []}))
    external = dict(row, status='source_omitted', distribution='local_prepare')
    (tmp_path / 'assets/files.json').write_text(json.dumps({'files': [external] if declared else []}))
    return row, data


def test_missing_declared_input_allowed_and_present_bytes_still_checked(tmp_path):
    row, data = fixture(tmp_path)
    assert validate_source_pins(tmp_path) == 0
    path = tmp_path / row['path']
    path.parent.mkdir()
    path.write_bytes(data)
    assert validate_source_pins(tmp_path) == 1
    path.write_bytes(b'wrong bytes')
    with pytest.raises(ValueError, match='Unrecorded source change'):
        validate_source_pins(tmp_path)


def test_undeclared_source_removal_still_fails(tmp_path):
    fixture(tmp_path, declared=False)
    with pytest.raises(ValueError, match='Unrecorded removal'):
        validate_source_pins(tmp_path)


def test_external_input_hash_must_match_source_pin(tmp_path):
    fixture(tmp_path)
    path = tmp_path / 'assets/files.json'
    doc = json.loads(path.read_text())
    doc['files'][0]['sha256'] = '0' * 64
    path.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match='External input identity differs'):
        validate_source_pins(tmp_path)


def test_concrete_private_answer_may_be_absent_but_solution_entrypoint_may_not(tmp_path):
    row, _ = fixture(tmp_path, declared=False)
    path = tmp_path / 'assets/sources.json'
    doc = json.loads(path.read_text())
    doc['files'][0]['path'] = 'tasks/fixture/solution/solutions/example.sol'
    path.write_text(json.dumps(doc))
    assert validate_source_pins(tmp_path) == 0
    doc['files'][0]['path'] = 'tasks/fixture/solution/solve.sh'
    path.write_text(json.dumps(doc))
    with pytest.raises(ValueError, match='Unrecorded removal'):
        validate_source_pins(tmp_path)
