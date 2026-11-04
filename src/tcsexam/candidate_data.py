"""Prepare an exact input-only image review context without publishing it."""
from pathlib import Path
import json
import shutil
import tarfile

from .layout import load, within
from .resources import copy_official_member, digest, relative, verify
from .solver_data_recipes import validate_payload


def prepare_review_context(root, resource, archive, context, *, archive_sha256, archive_bytes, notices):
    archive, context = Path(archive), Path(context)
    if archive.stat().st_size != archive_bytes or digest(archive) != archive_sha256:
        raise ValueError('Explicit review input archive differs from its CPU-verified identity')
    rows = load(within(root, resource['files_manifest']))['files']
    validate_payload(rows, resource['data_split'])
    expected = {relative(row['path']): row for row in rows}
    if len(expected) != len(rows):
        raise ValueError('Duplicate review payload declaration')
    output = context / 'rootfs'
    output.mkdir(parents=True, exist_ok=False)
    seen = set()
    with tarfile.open(archive, 'r|gz') as source:
        for member in source:
            name = relative(member.name)
            if (name not in expected or name in seen or not member.isfile()
                    or member.issym() or member.islnk()):
                raise ValueError('Review archive has an undeclared, duplicate or special member')
            row = expected[name]
            if member.size != row['bytes'] or member.mode & 0o7777 != int(row['mode'], 8):
                raise ValueError('Review archive member size or mode differs')
            with source.extractfile(member) as stream:
                copy_official_member(stream, output / name, dict(row, source_member=name))
            seen.add(name)
    if seen != set(expected):
        raise ValueError('Review archive is missing frozen input members')
    result = verify(output, rows)
    notice_directory = context / 'notices'
    notice_directory.mkdir()
    for name, source_path in notices.items():
        if Path(name).name != name:
            raise ValueError('Review notice filename must be a basename')
        source_path = Path(source_path)
        if source_path.is_symlink() or not source_path.is_file():
            raise ValueError('Review notice must be a regular file')
        shutil.copyfile(source_path, notice_directory / name)
    (context / 'Dockerfile').write_text(
        'FROM scratch\nCOPY rootfs/ /payload/rootfs/\nCOPY notices/ /licenses/tcsexam-data/\n')
    record = dict(id=resource['id'], result=result, source_archive_sha256=archive_sha256,
                  source_manifest_sha256=digest(within(root, resource['files_manifest'])),
                  image_status='context_prepared_not_built_not_published', public_pin=None,
                  public_upload_allowed=False, new_distribution_authorization=False)
    (context / 'review-source-manifest.json').write_text(json.dumps(record, indent=2) + '\n')
    return record
