"""Prepare fixed public source archives for the Lean Docker build context."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import urlsplit
from urllib.request import urlopen


GRAPHVIZ = Path('assets/environments/lean-base/graphviz-epl')
BLOCK_SIZE = 1024 * 1024


def explicit_sources(values):
    result = {}
    for value in values or []:
        name, separator, path = value.partition('=')
        if not separator or name not in {'graphviz', 'wrapper'} or not path or name in result:
            raise ValueError('Source inputs must be unique graphviz=PATH or wrapper=PATH values')
        result[name] = Path(path).expanduser()
    return result


def _check(path, record):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'Source archive must be a regular file: {path}')
    if path.stat().st_size != record['bytes']:
        raise ValueError(f'Source archive size mismatch: {path}')
    digests = {'sha256': hashlib.sha256(), 'sha512': hashlib.sha512()}
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(BLOCK_SIZE), b''):
            for digest in digests.values():
                digest.update(block)
    for name, digest in digests.items():
        if name in record and digest.hexdigest() != record[name]:
            raise ValueError(f'Source archive {name} mismatch: {path}')


def _install(stream, destination, record):
    """Write bounded blocks and publish only after the complete fixed hash matches."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.source-', delete=False) as output:
            temporary = Path(output.name)
            size = 0
            while block := stream.read(BLOCK_SIZE):
                size += len(block)
                if size > record['bytes']:
                    raise ValueError('Source archive exceeds its declared size')
                output.write(block)
        _check(temporary, record)
        temporary.chmod(0o644)
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


@contextmanager
def _lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        yield


def prepare_source_inputs(root, cache=None, inputs=None, offline=False):
    """Acquire only the two archives declared in the existing Graphviz manifest."""
    root = Path(root).resolve()
    directory = root / GRAPHVIZ
    manifest = json.loads((directory / 'source-manifest.json').read_text())
    cache = Path(cache or os.environ.get('TCSEXAM_CACHE', '~/.cache/tcsexam')).expanduser().resolve()
    inputs = inputs or {}
    if set(inputs) - {'graphviz', 'wrapper'}:
        raise ValueError('Unknown Lean source input; expected graphviz or wrapper')
    records = {name: manifest[name]['archive'] for name in ('graphviz', 'wrapper')}
    # Check every explicit input before any network access or context mutation.
    for name, path in inputs.items():
        _check(path, records[name])
    results = []
    for name, record in records.items():
        destination = directory / record['file']
        if (not destination.parent.resolve().is_relative_to(directory.resolve())
                or destination.parent.resolve() != (directory / 'source').resolve()
                or destination.name != Path(record['file']).name):
            raise ValueError('Source archive must be directly inside graphviz-epl/source')
        url = urlsplit(record['official_url'])
        if url.scheme != 'https' or not url.hostname or url.username or url.password:
            raise ValueError('Source archive needs a public HTTPS URL without credentials')
        cached = cache / 'lean-source-inputs' / (record['sha256'] + '.tar.gz')
        with _lock(cache / 'lean-source-inputs' / (record['sha256'] + '.lock')):
            # A corrupted context or hot cache fails explicitly; never silently repair it.
            if destination.exists() or destination.is_symlink():
                _check(destination, record)
            if cached.exists() or cached.is_symlink():
                _check(cached, record)
            if destination.is_file():
                acquisition = 'verified_context'
            else:
                if not cached.is_file():
                    if name in inputs:
                        with Path(inputs[name]).open('rb') as stream:
                            _install(stream, cached, record)
                        acquisition = 'explicit_input'
                    elif offline:
                        raise ValueError(f'Missing {name} source archive; run tcsexam source-inputs '
                                         f'or pass --input {name}=PATH with the exact declared archive')
                    else:
                        try:
                            with urlopen(record['official_url'], timeout=60) as stream:
                                _install(stream, cached, record)
                        except (OSError, ValueError) as error:
                            raise ValueError(f'Cannot obtain verified {name} archive from its public URL '
                                             f'({type(error).__name__}); use --input {name}=PATH '
                                             'with the exact declared archive') from error
                        acquisition = 'public_download'
                else:
                    acquisition = 'verified_cache'
                with cached.open('rb') as stream:
                    _install(stream, destination, record)
            # Recheck the complete context bytes, including repeated invocations.
            _check(destination, record)
        results.append({'component': name, 'file': str(destination.relative_to(root)),
                        'bytes': record['bytes'], 'sha256': record['sha256'],
                        'acquisition': acquisition})
    return {'prepared': results, 'scope': 'Fixed source archive preparation only; no image build or runtime acceptance.'}
