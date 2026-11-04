"""Judge composition must satisfy the original engine integrity declarations."""
import hashlib
import json
from pathlib import Path
import re
import shlex

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('split,directory', [('public', '/tests-public'), ('hidden', '/tests')])
def test_sygus_original_integrity_inputs_are_composed(split, directory):
    dockerfile = ROOT / f'assets/environments/solver/sygus-comp/judge/Dockerfile.{split}'
    copies = {}
    for line in dockerfile.read_text().splitlines():
        if line.startswith('COPY ') and '--from=' not in line:
            parts = shlex.split(line)
            if len(parts) == 3:
                copies[parts[2]] = ROOT / parts[1]
    # checker.py reads integrity.json next to itself before solving any input.
    assert copies[directory + '/checker.py'].is_file()
    integrity = json.loads(copies[directory + '/integrity.json'].read_text())
    for target in ['/opt/sygus/scoring.py', '/opt/sygus/sygus_check.py']:
        assert hashlib.sha256(copies[target].read_bytes()).hexdigest() == integrity[target]
    development = (ROOT / 'tasks/solver/online/sygus-comp/environment/Dockerfile').read_text()
    binary = re.search(r'^ARG CVC5_BIN_SHA256=([0-9a-f]{64})$', development, re.M)
    assert binary and binary.group(1) == integrity['/opt/sygus/cvc5']
