from pathlib import Path

import pytest

from tcsexam.dimacs_binary_data import convert


def test_original_binary_row_bit_order_and_exact_preamble(tmp_path):
    preamble = b'c original comment: 100% retained\r\np edge 9 3\n'
    # Edges cross both the first-byte boundary and successive row boundaries.
    rows = [b'\0' * ((i + 8) // 8) for i in range(9)]
    rows[1] = b'\x80'
    rows[8] = b'\x81\x00'
    source, output = tmp_path / 'original.b', tmp_path / 'original.col'
    source.write_bytes(str(len(preamble)).encode() + b'\n' + preamble + b''.join(rows))
    convert(source, output)
    assert output.read_bytes() == preamble + b'e 2 1\ne 9 1\ne 9 8\n'


@pytest.mark.parametrize('content', [
    b'10001\n',
    b'14\np edge 5001 1\n',
    b'13\np edge 9 1\n',
    b'11\np edge 1 1\n\x00extra',
])
def test_binary_decoder_rejects_oversized_truncated_and_trailing_inputs(tmp_path, content):
    source, output = tmp_path / 'bad.b', tmp_path / 'bad.col'
    source.write_bytes(content)
    with pytest.raises(ValueError):
        convert(source, output)
