"""Reproduce the frozen OR-Library railway row-major serialization."""
import gzip


def normalize_rail(source, destination, compressed=False):
    opener = gzip.open if compressed else open
    with opener(source, 'rt') as stream:
        tokens = stream.read().split()
    m, n = map(int, tokens[:2])
    costs, rows, position = [], [[] for _ in range(m)], 2
    for column in range(1, n + 1):
        cost, count = map(int, tokens[position:position + 2])
        position += 2
        covered = sorted(map(int, tokens[position:position + count]))
        if len(covered) != count or any(row < 1 or row > m for row in covered):
            raise ValueError('Railway row index is outside the declared matrix')
        position += count
        costs.append(cost)
        for row in covered:
            rows[row - 1].append(column)
    if position != len(tokens):
        raise ValueError('Railway source has trailing tokens')
    # Match the original normalize.py byte layout exactly.
    with destination.open('w') as stream:
        stream.write(f'{m} {n}\n')
        for start in range(0, n, 10):
            stream.write(' '.join(map(str, costs[start:start + 10])) + '\n')
        for row in rows:
            stream.write(str(len(row)) + ' ' + ' '.join(map(str, row)) + '\n')
