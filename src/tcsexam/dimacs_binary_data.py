"""Decode original DIMACS binary inputs while retaining their preamble bytes.

The row order and bit order follow the original bin2asc translator by Tamas
Badics and Marcus Peinado. No graph relabeling or comment rewriting is applied.
"""
import re


def convert(source, destination):
    with source.open('rb') as inp, destination.open('wb') as out:
        length_line = inp.readline(32)
        if not re.fullmatch(rb'[0-9]+\n', length_line):
            raise ValueError('Invalid DIMACS binary preamble length')
        length = int(length_line)
        if not 0 < length < 10000:
            raise ValueError('DIMACS binary preamble exceeds the original limit')
        preamble = inp.read(length)
        if len(preamble) != length:
            raise ValueError('Truncated DIMACS binary preamble')
        header = re.search(rb'^p\s+\S+\s+(\d+)\s+(\d+)', preamble, re.MULTILINE)
        if header is None or not 0 < int(header[1]) <= 5000:
            raise ValueError('Invalid original DIMACS binary graph dimensions')
        out.write(preamble)
        for i in range(int(header[1])):
            row = inp.read((i + 8) // 8)
            if len(row) != (i + 8) // 8:
                raise ValueError('Truncated DIMACS binary adjacency row')
            for j in range(i + 1):
                if row[j >> 3] & (1 << (7 - (j & 7))):
                    out.write(f'e {i + 1} {j + 1}\n'.encode())
        if inp.read(1):
            raise ValueError('Unexpected trailing DIMACS binary graph content')
