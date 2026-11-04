"""Keep public clone commands in sync with the package's repository URL."""
import argparse
from pathlib import Path
import re
import tomllib


GUIDES = ('docs/getting-started.md', 'docs/getting-started.zh-CN.md')


def update(root, repository_url=None, check=False):
    root = Path(root)
    metadata = root / 'pyproject.toml'
    original = metadata.read_text()
    previous = tomllib.loads(original)['project']['urls']['Repository']
    url = (repository_url or previous).removesuffix('/').removesuffix('.git')
    if not re.fullmatch(r'https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', url):
        raise ValueError('Use a public GitHub HTTPS repository URL without a query or fragment')
    prepared = {}
    if previous != url:
        pattern = r'(?m)^(Repository\s*=\s*)"' + re.escape(previous) + r'"\s*$'
        revised, count = re.subn(pattern, lambda m: m[1] + '"' + url + '"', original)
        if count != 1:
            raise ValueError('Expected one Repository entry in pyproject.toml')
        prepared[metadata] = revised
    for relative in GUIDES:
        path = root / relative
        content = path.read_text()
        revised, count = re.subn(r'(?m)^git clone \S+ TCSExam$',
                                lambda _: f'git clone {url}.git TCSExam', content)
        if count != 1:
            raise ValueError(f'Expected one clone command in {relative}')
        if content != revised:
            prepared[path] = revised
    if check and prepared:
        names = ', '.join(str(path.relative_to(root)) for path in prepared)
        raise ValueError(f'Public repository links need updating: {names}')
    if not check:
        for path, content in prepared.items():
            path.write_text(content)
    return [str(path.relative_to(root)) for path in prepared]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--repository-url')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    try:
        changed = update(args.root, args.repository_url, args.check)
    except (ValueError, KeyError, OSError) as error:
        parser.exit(1, f'{error}\n')
    print('Updated: ' + ', '.join(changed) if changed else 'Public repository links are consistent.')


if __name__ == '__main__':
    main()
