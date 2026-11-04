"""Reproduce the adopted PACE graph permutations from pinned official inputs.

The seed tag is a fixed algorithm parameter. It must retain its original bytes.
Only judging graphs are transformed; scoring references are never inputs here.
"""
import hashlib
import ctypes
import json
import lzma
from pathlib import Path
import random
import stat
import sys
import tarfile
import zipfile

SEED_TAG = 'tcshard-transform-20260831'
TRANSFORMS = {'dfvs-pace2022': 'vertex-relabeling-v1',
              'oscm-pace2024': 'free-layer-relabeling-v1'}
MAX_PLAINTEXT_BYTES = 128 * 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def token_sha(text):
    return sha(' '.join(text.split()).encode())


def seed(name):
    return int.from_bytes(hashlib.sha256((SEED_TAG + ':' + name).encode()).digest()[:8], 'big')


def transform(plain, name, task):
    """Return exact transformed UTF-8 bytes and independently checkable metadata."""
    if len(plain) > MAX_PLAINTEXT_BYTES:
        raise ValueError('Graph input exceeds the declared plaintext limit')
    text = plain.decode('utf-8', errors='replace')
    rng = random.Random(seed(name))
    if task == 'dfvs-pace2022':
        content = [line for line in text.split('\n') if not line.startswith('%')]
        i = 0
        while i < len(content) and not content[i].strip():
            i += 1
        if i == len(content):
            raise ValueError('Missing DFVS graph header')
        header = content[i].split()
        n = int(header[0])
        adj = [[int(token) for token in line.split()] for line in content[i+1:i+1+n]]
        if n < 1 or len(adj) != n or any(v < 1 or v > n for out in adj for v in out):
            raise ValueError('Invalid DFVS adjacency rows or vertex label')
        perm = list(range(1, n+1))
        rng.shuffle(perm)
        new_adj = [None] * n
        for v, out in enumerate(adj):
            renamed = [perm[w-1] for w in out]
            rng.shuffle(renamed)
            new_adj[perm[v]-1] = renamed
        m = sum(map(len, adj))
        transformed = '\n'.join([f'{n} {m} 0', *(' '.join(map(str, out)) for out in new_adj)]) + '\n'
        dimensions = {'n': n, 'm': m}
    elif task == 'oscm-pace2024':
        n1 = n2 = None
        edges = []
        for line in text.splitlines():
            if not line.strip() or line[0] == 'c':
                continue
            tokens = line.split()
            if tokens[0] == 'p':
                if n1 is not None:
                    raise ValueError('Duplicate OSCM graph header')
                n1, n2 = int(tokens[2]), int(tokens[3])
                continue
            u, v = int(tokens[0]), int(tokens[1])
            if u > v:
                u, v = v, u
            edges.append((u, v))
        if n1 is None or n2 is None or n1 < 1 or n2 < 1:
            raise ValueError('Missing or invalid OSCM graph header')
        if any(not (1 <= u <= n1 and n1 < v <= n1+n2) for u, v in edges):
            raise ValueError('Invalid OSCM bipartite edge')
        perm = list(range(1, n2+1))
        rng.shuffle(perm)
        new_edges = [(u, n1+perm[v-(n1+1)]) for u, v in edges]
        rng.shuffle(new_edges)
        transformed = f'p ocr {n1} {n2} {len(new_edges)}\n' + ''.join(f'{u} {v}\n' for u, v in new_edges)
        dimensions = {'n1': n1, 'n2': n2, 'm': len(edges)}
    else:
        raise ValueError('Unsupported graph transformation')
    result = transformed.encode()
    return result, dict(dimensions, seed_hex=f'{seed(name):016x}',
                        sha256_orig_tokens=token_sha(text), sha256_new_tokens=token_sha(transformed),
                        source_sha256_plain=sha(plain), output_sha256_plain=sha(result))


def rebuild(recipe, archive, output):
    policy = recipe['graph_transform']
    task = policy['task_id']
    if policy['id'] != TRANSFORMS.get(task) or policy['seed_tag'] != SEED_TAG:
        raise ValueError('Graph transform identity or seed tag differs')
    if task == 'dfvs-pace2022':
        library = ctypes.CDLL('liblzma.so.5')
        library.lzma_version_string.restype = ctypes.c_char_p
        version = library.lzma_version_string().decode('ascii')
        if version != recipe['compression']['liblzma_version']:
            raise ValueError('DFVS requires the declared liblzma compression version')
    declarations = {row['source_member']: row for row in recipe['outputs']}
    if len(declarations) != len(recipe['outputs']):
        raise ValueError('Duplicate graph source member declaration')
    report = []
    seen = set()
    def accept(name, stream):
        if name not in declarations:
            return
        if name in seen:
            raise ValueError('Duplicate selected graph member')
        row = declarations[name]
        data = stream.read(MAX_PLAINTEXT_BYTES + 1)
        payload, actual = transform(data, Path(row['path']).name, task)
        for key, expected in row['transform_contract'].items():
            if actual.get(key) != expected:
                raise ValueError(f'Graph transformation contract differs for {name}: {key}')
        if task == 'dfvs-pace2022':
            payload = lzma.compress(payload, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64, preset=6)
        if len(payload) != row['bytes'] or sha(payload) != row['sha256']:
            raise ValueError(f'Transformed graph payload differs for {name}')
        destination = output / row['path']
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
        destination.chmod(0o644)
        seen.add(name)
        report.append(dict(actual, path=row['path'], bytes=len(payload), sha256=sha(payload)))
    if recipe['archive_format'] == 'tar.gz':
        with tarfile.open(archive, 'r|gz') as source:
            for member in source:
                name = member.name.removeprefix('./')
                if name not in declarations:
                    continue
                if not member.isfile() or member.issym() or member.islnk():
                    raise ValueError('Selected graph archive member is not a regular file')
                with source.extractfile(member) as stream:
                    accept(name, stream)
    elif recipe['archive_format'] == 'zip':
        with zipfile.ZipFile(archive) as source:
            for member in source.infolist():
                if member.filename not in declarations:
                    continue
                if member.is_dir() or member.flag_bits & 1 or stat.S_IFMT(member.external_attr >> 16) not in (0, stat.S_IFREG):
                    raise ValueError('Selected graph ZIP member is not a regular unencrypted file')
                with source.open(member) as stream:
                    accept(member.filename, stream)
    else:
        raise ValueError('Unsupported graph source archive format')
    if seen != set(declarations):
        raise ValueError('Official graph archive is missing selected members')
    return {'task_id': task, 'transform_id': policy['id'], 'seed_tag': SEED_TAG,
            'files': sorted(report, key=lambda row: row['path'])}


def main():
    recipe_path, archive, output, report_path = map(Path, sys.argv[1:])
    report = rebuild(json.loads(recipe_path.read_text()), archive, output)
    report_path.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
