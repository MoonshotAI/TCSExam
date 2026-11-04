"""Render the common Harbor reward writer without changing any scoring code."""
import argparse
from pathlib import Path
from .layout import repository

TEMPLATE = 'assets/environments/solver/online-runtime/reward_writer.py'


def rendered(source, template):
    marker = '\n\nif __name__ == "__main__":'
    end = source.index(marker)
    if '\ndef _write_json_atomic(' in source:
        start = source.index('\ndef _write_json_atomic(') + 1
    else:
        start = source.index('\ndef write_violation(') + 1
    # The task-specific score calculation and submission history stay byte-identical.
    return source[:start] + template[template.index('def _write_json_atomic('):].rstrip() + source[end:]


def sync(root, check=False):
    root = Path(root)
    template = (root / TEMPLATE).read_text()
    paths = sorted((root / 'tasks/solver/online').glob('*/tests/fetch_final.py'))
    if not paths:
        raise ValueError('No online final verifiers found')
    changed = []
    for path in paths:
        before = path.read_text()
        after = rendered(before, template)
        if before != after:
            changed.append(str(path.relative_to(root)))
            if not check:
                path.write_text(after)
    if changed and check:
        raise ValueError('Online reward writers are stale: ' + ', '.join(changed))
    return {'online_tasks': len(paths), 'changed': changed, 'check': check}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    print(sync(repository(args.root), args.check))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
