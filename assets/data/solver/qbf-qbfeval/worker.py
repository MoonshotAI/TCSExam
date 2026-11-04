"""Rebuild only the fixed selected QDIMACS matrix inputs."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys


def main():
    recipe = json.loads(Path(sys.argv[1]).read_text())
    inputs, output = Path(sys.argv[2]), Path(sys.argv[3])
    spec = importlib.util.spec_from_file_location('qdimacs_transform', Path(__file__).with_name('transform.py'))
    transform = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transform)
    records = []
    for declaration in recipe['outputs']:
        plain, variables, prefix, clauses = transform.read_qdimacs(str(inputs / declaration['input_filename']))
        if hashlib.sha256(plain).hexdigest() != declaration['source_sha256_plain']:
            raise ValueError('QDIMACS original plaintext differs')
        seed = transform.derive_seed(declaration['original_seed_name'])
        if f'{seed:016x}' != declaration['seed_hex']:
            raise ValueError('Original QDIMACS transformation seed differs')
        changed, variable_map, blocks = transform.transform_instance(variables, prefix, clauses, seed)
        block_digest = hashlib.sha256(json.dumps(blocks, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        if block_digest != declaration['blocks_sha256']:
            raise ValueError('Original saved quantifier-block permutations differ')
        transformed = transform.serialize(variables, prefix, changed)
        if hashlib.sha256(transformed).hexdigest() != declaration['output_sha256_plain']:
            raise ValueError('Frozen QDIMACS output plaintext differs')
        destination = output / declaration['path']
        destination.parent.mkdir(parents=True, exist_ok=True)
        preset = declaration.get('compression_preset', 6)
        threads = declaration.get('compression_threads', 1)
        version = declaration.get('compression_tool_version', '5.2.5')
        if preset not in (6, 9) or threads not in (1, 2) or version not in ('5.2.5', '5.8.4'):
            raise ValueError('Unsupported frozen QBF compression parameters')
        command = [f'/tmp/xz-{version}/src/xz/xz', '-z', f'-{preset}', '-c']
        if threads == 2:
            command.append('--threads=2')
        with destination.open('wb') as stream:
            subprocess.run(command, input=transformed,
                           stdout=stream, check=True)
        destination.chmod(0o644)
        records.append({'path': declaration['path'], 'variables': variables,
                        'clauses': len(changed), 'blocks_sha256': block_digest})
        del plain, clauses, changed, variable_map, blocks, transformed
    Path('generation-report.json').write_text(json.dumps({'inputs': records}, indent=2) + '\n')


if __name__ == '__main__':
    main()
