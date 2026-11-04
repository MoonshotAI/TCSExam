"""Generate the shared product manifest from task-specific build declarations."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import tempfile

from .layout import load, repository
from .lean_recipes import with_build_recipes
from .product_graph import validate_graph
from .solver_data_recipes import product_patch
from .solver_recipes import solver_runtime_manifest


def generated(root, document):
    result = with_build_recipes(root, document)
    positions = {row.get('id'): index for index, row in enumerate(result['images'])
                 if row.get('id')}
    for patch in product_patch(root):
        if patch['id'] in positions:
            result['images'][positions[patch['id']]] = patch
        else:
            result['images'].append(patch)
    result = solver_runtime_manifest(Path(root), result)
    validate_graph(result)
    return result


def refresh(root, check=False):
    root = Path(root)
    path = root / 'assets/images.json'
    before = load(path)
    after = generated(root, before)
    changed = before != after
    if changed and check:
        raise ValueError('Product recipes are stale; run python -m tcsexam.recipes')
    if changed:
        temporary = None
        try:
            with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent,
                                             prefix=path.name + '.', delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(after, stream, ensure_ascii=False, indent=2)
                stream.write('\n')
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    counts = Counter(row.get('runtime_role') or row.get('type')
                     for row in after['images'] if row.get('type') != 'historical_reference')
    return {'changed': changed, 'check': check, 'counts': dict(counts),
            'graph': validate_graph(after),
            'scope': 'Source declarations only; build and runtime acceptance are recorded separately.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    result = refresh(repository(args.root), args.check)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
