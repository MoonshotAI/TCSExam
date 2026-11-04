"""Rebuild historical judging formulas from pinned official inputs with bounded RAM."""
import json
import lzma
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time
import zipfile

from bounded_transform import BLOCK, canonicalize, file_sha256, relabel


def rebuild_one(archive, row, destination, workdir, compressor):
    """Convert, relabel and compress one declared instance, enforcing both plaintext hashes."""
    started = time.monotonic()
    members = [member for member in archive.infolist() if member.filename == row['source_member']]
    if len(members) != 1 or members[0].is_dir() or members[0].flag_bits & 1:
        raise ValueError('Selected MaxSAT ZIP member is duplicate, missing or encrypted')
    member = members[0]
    if member.file_size != row['source_member_bytes']:
        raise ValueError('Selected MaxSAT ZIP member size differs')
    bound = row['source_expanded_limit_bytes']
    if type(bound) is not int or not 0 < bound <= 8 * 1024 ** 3:
        raise ValueError('MaxSAT expanded input needs an explicit bounded size')
    with tempfile.TemporaryDirectory(prefix='maxsat-instance-', dir=workdir) as temporary:
        temporary = Path(temporary)
        raw, canonical, changed = (temporary / name for name in ('raw', 'canonical', 'changed'))
        expanded = 0
        with archive.open(member) as packed:
            stream = lzma.LZMAFile(packed)
            with stream, raw.open('wb') as target:
                while block := stream.read(BLOCK):
                    expanded += len(block)
                    if expanded > bound:
                        raise ValueError('Expanded MaxSAT input exceeds its declared size bound')
                    target.write(block)
        metadata = canonicalize(raw, canonical, temporary, style=row.get('canonical_format', 'original-v1'))
        for key in ('source_sha256_plain', 'nvars', 'nclauses', 'top'):
            if metadata[key] != row[key]:
                raise ValueError(f'MaxSAT canonical input contract differs: {key}')
        raw.unlink()
        metadata = relabel(canonical, changed, row['original_seed_name'], temporary, expected=row)
        canonical.unlink()
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary_output = destination.with_name(destination.name + '.partial')
        preset, threads = row.get('compression_preset', 6), row.get('compression_threads', 1)
        if preset != 6 or threads != 1:
            raise ValueError('Judging211 rebuilding requires fixed XZ preset6 with one thread')
        with changed.open('rb') as source, temporary_output.open('wb') as target:
            subprocess.run([str(compressor), '-z', '-6', '-c', '-T1'], stdin=source,
                           stdout=target, check=True)
        os.chmod(temporary_output, 0o644)
        temporary_output.replace(destination)
        metadata.update(path=row['path'], canonical_format=row.get('canonical_format', 'original-v1'),
                        source_id=row['source_id'], source_member=row['source_member'],
                        source_member_bytes=member.file_size, source_expanded_bytes=expanded,
                        bytes=destination.stat().st_size, sha256=file_sha256(destination),
                        elapsed_seconds=time.monotonic() - started,
                        max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                        compression_tool_version='5.2.5', compression_preset=6, compression_threads=1)
        return metadata


def main(argv=None):
    recipe_path, input_root, output_root = map(Path, (argv or sys.argv[1:]))
    recipe = json.loads(recipe_path.read_text())
    input_root, output_root = Path(input_root), Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    compressor = Path('/tmp/xz-5.2.5/src/xz/xz')
    version = subprocess.check_output([str(compressor), '--version'], text=True).splitlines()[0]
    if version != 'xz (XZ Utils) 5.2.5' or recipe['compression_tool_version'] != '5.2.5':
        raise ValueError('Fixed MaxSAT compression tool differs')
    reports = []
    with zipfile.ZipFile(input_root / 'instances.zip') as archive:
        for row in recipe['outputs']:
            if row['operation'] != 'maxsat_relabel':
                raise ValueError('Judging211 rebuilding only accepts the declared relabel operation')
            report = rebuild_one(archive, row, output_root / row['path'], output_root.parent, compressor)
            reports.append(report)
            (output_root.parent / 'generation-report.json').write_text(json.dumps({'files': reports}, indent=2) + '\n')
            print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
