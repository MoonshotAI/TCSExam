"""Generate and relabel only the explicitly frozen graph input files."""
import bz2
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import importlib.util


def main():
    recipe = json.loads(Path(sys.argv[1]).read_text())
    folder = Path(__file__).parent
    source_directory, output_directory = Path(sys.argv[2]), Path(sys.argv[3])
    import numpy
    import scipy
    if (numpy.__version__, scipy.__version__) != ('1.26.4', '1.11.4'):
        raise ValueError('Frozen graph generation requires NumPy1.26.4 and SciPy1.11.4')
    subprocess.run(['g++', '-O3', '-std=c++17', str(folder / 'gen.cpp'), '-o', str(folder / 'gen')], check=True)
    spec = importlib.util.spec_from_file_location('graph_transform', folder / 'transform.py')
    transform = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transform)
    parameters = {}
    if recipe.get('parameters_file'):
        with gzip.open(folder / recipe['parameters_file'], 'rt') as stream:
            parameters = json.load(stream)['instances']
    generated = {}
    records = []
    for row in recipe['outputs']:
        if 'source_id' in row:
            source = source_directory / row['source_id']
            if not row.get('parameter_key'):
                destination = output_directory / row['path']
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(source.read_bytes())
                destination.chmod(0o644)
                continue
            with bz2.open(source, 'rt') as stream:
                text = stream.read()
        else:
            declaration = recipe['generated'][row['generator_key']]
            key = row['generator_key']
            if key not in generated:
                destination = folder / (key + '.raw.graph')
                args = declaration['arguments']
                command = ([sys.executable, str(folder / 'gen_delaunay.py')] + list(map(str, args))
                           if declaration['kind'] == 'delaunay' else
                           [str(folder / 'gen'), declaration['kind']] + list(map(str, args)))
                with destination.open('wb') as output:
                    subprocess.run(command, stdout=output, check=True)
                generated[key] = destination
                records.append({'key': key, **declaration,
                                'sha256': hashlib.sha256(destination.read_bytes()).hexdigest()})
            text = generated[key].read_text()
        if row.get('parameter_key'):
            saved = parameters[row['parameter_key']]
            n, m, adjacency = transform.load_metis(text)
            if (n, m) != (saved['n'], saved['m']) or transform.token_sha256_text(text) != saved['sha256_orig_tokens']:
                raise ValueError('Official/generated graph differs before saved relabeling')
            permutation = saved['perm']
            if sorted(permutation) != list(range(1, n + 1)):
                raise ValueError('Saved graph vertex permutation is not a bijection')
            changed = [None] * n
            for old, neighbors in enumerate(adjacency):
                changed[permutation[old] - 1] = sorted(permutation[v - 1] for v in neighbors)
            text = transform.canonical_text(n, m, changed)
            if transform.token_sha256_text(text) != saved['sha256_new_tokens']:
                raise ValueError('Frozen transformed graph token identity differs')
        destination = output_directory / row['path']
        destination.parent.mkdir(parents=True, exist_ok=True)
        with bz2.open(destination, 'wb', compresslevel=9) as output:
            output.write(text.encode())
        destination.chmod(0o644)
    Path('generation-report.json').write_text(json.dumps({
        'python': sys.version.split()[0], 'numpy': numpy.__version__, 'scipy': scipy.__version__,
        'compiler': subprocess.check_output(['g++', '--version'], text=True).splitlines()[0],
        'generated': records,
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
