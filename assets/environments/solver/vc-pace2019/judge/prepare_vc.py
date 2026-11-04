"""Expose fixed hidden VC inputs under the original checker's .gr names."""
import hashlib
import json
import lzma
import os
from pathlib import Path, PurePosixPath
import re

from compressed_prepare import prepare as decompress

BLOCK = 1024 * 1024


def _verified_source(source, record):
    if source.is_symlink() or not source.is_file():
        raise ValueError(f'Fixed compressed VC input missing: {source.name}')
    if source.stat().st_size != record['bytes']:
        raise ValueError(f'Fixed compressed VC input size differs: {source.name}')
    digest = hashlib.sha256()
    with source.open('rb') as stream:
        for block in iter(lambda: stream.read(BLOCK), b''):
            digest.update(block)
    if digest.hexdigest() != record['sha256']:
        raise ValueError(f'Fixed compressed VC input hash differs: {source.name}')


def _verified_plain(source, target):
    if target.is_symlink() or not target.is_file():
        raise ValueError(f'Original decompressed VC input missing: {target.name}')
    with lzma.open(source, 'rb') as compressed, target.open('rb') as plain:
        while True:
            block = compressed.read(BLOCK)
            if block != plain.read(BLOCK):
                raise ValueError(f'Existing decompressed VC input differs: {target.name}')
            if not block:
                return


def prepare(directory, manifest_path='/judge/vc-instance-manifest.json'):
    # Public VC images already create .gr files in their development Dockerfile.
    if os.environ.get('INSTANCE_SET', 'hidden') != 'hidden':
        return decompress(directory)
    root = Path(directory)
    records = json.loads(Path(manifest_path).read_text())['files']
    mappings = []
    seen = set()
    for record in records:
        path = PurePosixPath(record['path'])
        if path.parent != PurePosixPath('tests/instances') or not re.fullmatch(r'vc-exact_\d{3}(?:\.gr)?\.xz', path.name):
            raise ValueError('Unexpected path in fixed hidden VC manifest')
        if path.name in seen:
            raise ValueError('Duplicate compressed input in fixed hidden VC manifest')
        seen.add(path.name)
        source = root / path.name
        target = source.with_suffix('')
        alias = target if target.suffix == '.gr' else target.with_name(target.name + '.gr')
        _verified_source(source, record)
        if target.exists() or target.is_symlink():
            _verified_plain(source, target)
        if alias != target:
            if alias.is_symlink():
                if os.readlink(alias) != target.name:
                    raise ValueError(f'Existing VC input alias differs: {alias.name}')
            elif alias.exists():
                raise ValueError(f'Refuse overwriting existing VC checker input: {alias.name}')
        mappings.append((source, target, alias))
    if not mappings:
        raise ValueError('Fixed hidden VC manifest is empty')
    # Preserve the existing decompressor and compressed/decompressed bytes.
    decompress(directory)
    for source, target, alias in mappings:
        if not target.is_file() or target.is_symlink():
            raise ValueError(f'Original decompressed VC input missing: {target.name}')
        if alias != target and not alias.is_symlink():
            alias.symlink_to(target.name)
