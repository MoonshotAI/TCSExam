"""Copy an explicit, hash-checked input allowlist from fixed official archives."""
from pathlib import Path
import stat
import tarfile
import zipfile

from .layout import load, within
from .resources import copy_official_member, input_file, relative, verify


def prepare_data(root, resource, rows, output, downloads, inputs=None, **kwargs):
    recipe = load(within(root, resource['recipe']))
    if recipe.get('graph_transform'):
        from .graph_relabel_data import prepare_data
        return prepare_data(root, resource, rows, output, downloads, inputs=inputs,
                            args=kwargs.get('args'), builder_image=kwargs.get('builder_image'))
    expected = {relative(row['path']): row for row in rows}
    declarations = {relative(row['path']): row for row in recipe['outputs']}
    if len(expected) != len(rows) or len(declarations) != len(recipe['outputs']) or set(expected) != set(declarations):
        raise ValueError('Official archive output allowlist differs from the frozen manifest')
    seen = set()
    for path, declaration in declarations.items():
        if declaration.get('operation') != 'project_file':
            continue
        source = within(root, declaration['source_path'])
        if source.is_symlink() or not source.is_file():
            raise ValueError('Declared shared input parameter is not a regular file')
        with source.open('rb') as stream:
            copy_official_member(stream, Path(output) / path,
                                 dict(expected[path], source_member=declaration['source_path']))
        seen.add(path)
    for source in recipe['sources']:
        archive = input_file(source, downloads, inputs)
        wanted = {relative(decl['source_member']): expected[path]
                  for path, decl in declarations.items() if decl.get('source_id') == source['id']}
        if len(wanted) != sum(decl.get('source_id') == source['id'] for decl in declarations.values()):
            raise ValueError('Duplicate official source member mapping')
        def accept(name, stream):
            row = wanted[name]
            if row['path'] in seen:
                raise ValueError('Duplicate selected official archive member')
            seen.add(row['path'])
            copy_official_member(stream, Path(output) / row['path'], dict(row, source_member=name))
        if source['format'] == 'zip':
            with zipfile.ZipFile(archive) as upstream:
                for member in upstream.infolist():
                    name = relative(member.filename)
                    if name not in wanted:
                        continue
                    if (member.is_dir() or member.flag_bits & 1 or
                            stat.S_IFMT(member.external_attr >> 16) not in (0, stat.S_IFREG)):
                        raise ValueError('Selected official ZIP member is not a regular unencrypted file')
                    with upstream.open(member) as stream:
                        accept(name, stream)
        elif source['format'] in ('tar.gz', 'tar.bz2', 'tar.xz'):
            mode = {'tar.gz': 'r|gz', 'tar.bz2': 'r|bz2', 'tar.xz': 'r|xz'}[source['format']]
            with tarfile.open(archive, mode) as upstream:
                for member in upstream:
                    name = relative(member.name)
                    if name not in wanted:
                        continue
                    if not member.isfile() or member.issym() or member.islnk():
                        raise ValueError('Selected official TAR member is not a regular file')
                    with upstream.extractfile(member) as stream:
                        accept(name, stream)
        else:
            raise ValueError('Unsupported fixed official archive format')
    if seen != set(expected):
        raise ValueError(f'Official archives are missing selected input files: {sorted(set(expected)-seen)[:5]}')
    return verify(output, rows)
