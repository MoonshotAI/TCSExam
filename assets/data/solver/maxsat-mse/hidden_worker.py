"""Process only the explicitly selected original MaxSAT inputs and public PDFs."""
import gc
import hashlib
import json
import lzma
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile
import convert
import transform

recipe_path, input_root, output_root = map(Path, sys.argv[1:])
recipe = json.loads(recipe_path.read_text())
reports = []
sha = lambda data: hashlib.sha256(data).hexdigest()
with zipfile.ZipFile(input_root / 'instances.zip') as archive:
    for row in recipe['outputs']:
        destination = output_root / row['path']
        destination.parent.mkdir(parents=True, exist_ok=True)
        if row['operation'] == 'copy_pdf':
            shutil.copyfile(input_root / row['input_filename'], destination)
        else:
            matches = [m for m in archive.infolist() if m.filename == row['source_member']]
            if len(matches) != 1 or matches[0].is_dir() or matches[0].flag_bits & 1:
                raise ValueError('Selected MaxSAT ZIP member is duplicate, missing or encrypted')
            member = matches[0]
            if member.file_size > 150 * 1024 * 1024:
                raise ValueError('Selected MaxSAT source exceeds the original bound')
            with tempfile.TemporaryDirectory(prefix='maxsat-input-') as temporary:
                temporary = Path(temporary)
                raw = temporary / 'raw.wcnf'
                with archive.open(member) as source:
                    stream = lzma.LZMAFile(source) if member.filename.endswith('.xz') else source
                    with raw.open('wb') as target:
                        remaining = 150 * 1024 * 1024
                        while block := stream.read(min(1024 * 1024, remaining + 1)):
                            remaining -= len(block)
                            if remaining < 0:
                                raise ValueError('Expanded MaxSAT input exceeds the original bound')
                            target.write(block)
                canonical = temporary / 'canonical.wcnf'
                convert.convert(str(raw), str(canonical))
                plain = canonical.read_bytes()
                if sha(plain) != row['source_sha256_plain']:
                    raise ValueError('Original MaxSAT input conversion differs')
                if row['operation'] == 'maxsat_relabel':
                    plain, n, top, clauses = transform.read_wcnf(str(canonical))
                    seed = transform.derive_seed(row['original_seed_name'])
                    if f'{seed:016x}' != row['seed_hex']:
                        raise ValueError('Historical MaxSAT seed name differs')
                    changed, perm = transform.transform_clauses(n, clauses, seed)
                    if sha(json.dumps(perm[1:], separators=(',', ':')).encode()) != row['permutation_sha256']:
                        raise ValueError('Full saved MaxSAT variable permutation differs')
                    plain = transform.serialize(n, top, changed)
                    if sha(plain) != row['output_sha256_plain']:
                        raise ValueError('Transformed MaxSAT plaintext differs')
                    preset = row.get('compression_preset', 6)
                    threads = row.get('compression_threads', 1)
                    if preset not in (6, 9) or threads not in (1, 2):
                        raise ValueError('Unsupported frozen MaxSAT compression parameters')
                    command = ['/tmp/xz-5.2.5/src/xz/xz', '-z', f'-{preset}', '-c']
                    if threads == 2:
                        command.append('--threads=2')
                    with destination.open('wb') as target:
                        subprocess.run(command, input=plain, stdout=target, check=True)
                    del clauses, changed, perm
                elif row['operation'] == 'maxsat_pack':
                    version = row.get('compression_tool_version', '5.2.5')
                    if version not in ('5.2.5', '5.8.4'):
                        raise ValueError('Unsupported frozen MaxSAT compression tool')
                    with destination.open('wb') as target:
                        subprocess.run([f'/tmp/xz-{version}/src/xz/xz', '-z', '-6', '-c'],
                                       input=plain, stdout=target, check=True)
                else:
                    destination.write_bytes(plain)
                del plain
                gc.collect()
        destination.chmod(0o644)
        reports.append({'path': row['path'], 'bytes': destination.stat().st_size})
Path('generation-report.json').write_text(json.dumps({'files': reports}, indent=2) + '\n')
