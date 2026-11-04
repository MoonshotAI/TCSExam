"""Exact historical weighted-clause conversion and seeded order with bounded RAM."""
from array import array
import hashlib
import mmap
from pathlib import Path
import random
import shutil
import tempfile

SEED_TAG = 'tcshard-transform-20260831'
BLOCK = 1024 * 1024
MAX_LINE_BYTES = 64 * BLOCK


def file_sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(BLOCK), b''):
            h.update(block)
    return h.hexdigest()


def lines(source):
    while raw := source.readline(MAX_LINE_BYTES + 1):
        if len(raw) > MAX_LINE_BYTES:
            raise ValueError('MaxSAT input line exceeds the declared preparation bound')
        yield raw


def canonicalize(source_path, output_path, workdir, style="original-v1"):
    """Match the original new-to-classic converter, including comments and order."""
    if style not in ('original-v1', 'streaming-two-pass-v1'):
        raise ValueError('Unknown historical MaxSAT canonical format')
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    nvars = hard_count = soft_count = soft_sum = 0
    with tempfile.TemporaryDirectory(dir=workdir, prefix='canonical-') as temporary:
        temporary = Path(temporary)
        with (temporary / 'hard').open('wb') as hard, (temporary / 'soft').open('wb') as soft, \
                (temporary / 'comments').open('wb') as comments, \
                (temporary / 'ordered').open('wb') as ordered, Path(source_path).open('rb') as source:
            for raw in lines(source):
                line = raw.strip()
                if not line:
                    continue
                if line[:1] == b'c':
                    comments.write((line.decode('ascii', 'replace') + '\n').encode())
                    continue
                if line[:1] == b'p':
                    continue
                tokens = line.split()
                literals = [int(token) for token in tokens[1:] if int(token) != 0]
                if literals:
                    nvars = max(nvars, max(abs(lit) for lit in literals))
                body = (' '.join(map(str, literals)) + ' 0\n').encode()
                if style == 'streaming-two-pass-v1':
                    ordered.write(tokens[0] + b' ' + body)
                if tokens[0] == b'h':
                    hard.write(body)
                    hard_count += 1
                else:
                    weight = int(tokens[0])
                    soft.write(str(weight).encode() + b' ' + body)
                    soft_count += 1
                    soft_sum += weight
        top = soft_sum + 1
        if top >= 1 << 63:
            raise ValueError('MaxSAT hard-clause weight exceeds the original int64 bound')
        nclauses = hard_count + soft_count
        with Path(output_path).open('wb', buffering=BLOCK) as target:
            if style == 'streaming-two-pass-v1':
                target.write(b'c converted from MSE new format (h-lines, no p-line), streaming two-pass\n')
            else:
                target.write(b'c converted from MSE new format (h-lines, no p-line)\n')
                with (temporary / 'comments').open('rb') as source:
                    shutil.copyfileobj(source, target, BLOCK)
            target.write(f'p wcnf {nvars} {nclauses} {top}\n'.encode())
            if style == 'streaming-two-pass-v1':
                with (temporary / 'ordered').open('rb') as source:
                    for body in lines(source):
                        target.write(f'{top} '.encode() + body[2:] if body.startswith(b'h ') else body)
            else:
                with (temporary / 'hard').open('rb') as source:
                    prefix = f'{top} '.encode()
                    for body in lines(source):
                        target.write(prefix)
                        target.write(body)
                with (temporary / 'soft').open('rb') as source:
                    shutil.copyfileobj(source, target, BLOCK)
    return {'nvars': nvars, 'nclauses': nclauses, 'top': top,
            'source_sha256_plain': file_sha256(output_path)}


def permutation_hash(permutation):
    """Hash the original compact JSON permutation without building a large string."""
    h = hashlib.sha256(b'[')
    first = True
    for start in range(0, len(permutation), 65536):
        text = ','.join(str(value) for value in permutation[start:start + 65536])
        if not first:
            h.update(b',')
        h.update(text.encode())
        first = False
    h.update(b']')
    return h.hexdigest()


def relabel(source_path, output_path, seed_name, workdir, expected=None):
    """Preserve Random calls: variable shuffle, each literal shuffle, clause shuffle."""
    expected = expected or {}
    seed = int.from_bytes(hashlib.sha256(f'{SEED_TAG}:{seed_name}'.encode()).digest()[:8], 'big')
    seed_hex = f'{seed:016x}'
    if expected.get('seed_hex', seed_hex) != seed_hex:
        raise ValueError('Historical MaxSAT seed differs')
    source_sha256 = file_sha256(source_path)
    if expected.get('source_sha256_plain', source_sha256) != source_sha256:
        raise ValueError('MaxSAT input contract differs: source_sha256_plain')
    nvars = top = None
    nclauses = 0
    rng = random.Random(seed)
    offsets = array('Q')
    if offsets.itemsize != 8:
        raise ValueError('MaxSAT offsets require an unsigned 64-bit array')
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=workdir, prefix='relabel-') as temporary:
        spool = Path(temporary) / 'clauses'
        with Path(source_path).open('rb') as source, spool.open('wb', buffering=BLOCK) as target:
            for raw in lines(source):
                line = raw.strip()
                if not line or line.startswith(b'c'):
                    continue
                if line.startswith(b'p'):
                    if nvars is not None:
                        raise ValueError('MaxSAT canonical input has duplicate headers')
                    parts = line.split()
                    if len(parts) >= 5 and parts[1] == b'wcnf':
                        nvars, declared_count, top = int(parts[2]), int(parts[3]), int(parts[4])
                        for key, value in (('nvars', nvars), ('nclauses', declared_count), ('top', top)):
                            if key in expected and expected[key] != value:
                                raise ValueError(f'MaxSAT input contract differs: {key}')
                        if not 0 <= nvars < 2 ** 32 or declared_count < 0:
                            raise ValueError('MaxSAT canonical dimensions exceed the array bounds')
                        permutation = array('I', range(1, nvars + 1))
                        if permutation.itemsize != 4:
                            raise ValueError('MaxSAT variables require an unsigned 32-bit array')
                        rng.shuffle(permutation)
                    continue
                if nvars is None or top is None:
                    raise ValueError('MaxSAT canonical input is missing its header')
                parts = line.split()
                weight = int(parts[0])
                renamed = []
                for token in parts[1:]:
                    literal = int(token)
                    if literal == 0:
                        break
                    if abs(literal) > nvars:
                        raise ValueError('MaxSAT literal exceeds its declared variable count')
                    renamed.append((1 if literal > 0 else -1) * permutation[abs(literal) - 1])
                rng.shuffle(renamed)
                offsets.append(target.tell())
                target.write((f'{weight} ' + ' '.join(map(str, renamed)) + ' 0\n').encode())
                nclauses += 1
        if nvars is None or top is None:
            raise ValueError('MaxSAT canonical input is missing its header')
        actual = {'nvars': nvars, 'nclauses': nclauses, 'top': top, 'seed_hex': seed_hex,
                  'source_sha256_plain': source_sha256,
                  'permutation_sha256': permutation_hash(permutation)}
        for key in ('nvars', 'nclauses', 'top', 'seed_hex', 'source_sha256_plain', 'permutation_sha256'):
            if key in expected and expected[key] != actual[key]:
                raise ValueError(f'MaxSAT input contract differs: {key}')
        rng.shuffle(offsets)
        h = hashlib.sha256()
        total = 0
        with Path(output_path).open('wb', buffering=BLOCK) as target:
            header = f'p wcnf {nvars} {nclauses} {top}\n'.encode()
            target.write(header)
            h.update(header)
            total += len(header)
            if offsets:
                with spool.open('rb') as source, mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_READ) as mapped:
                    for offset in offsets:
                        end = mapped.find(b'\n', offset)
                        if end < offset:
                            raise ValueError('MaxSAT clause spool line is incomplete')
                        line = mapped[offset:end + 1]
                        target.write(line)
                        h.update(line)
                        total += len(line)
        actual.update(output_sha256_plain=h.hexdigest(), output_plaintext_bytes=total)
        for key in ('output_sha256_plain', 'output_plaintext_bytes'):
            if key in expected and actual[key] != expected[key]:
                raise ValueError(f'MaxSAT transformed plaintext contract differs: {key}')
    return actual
