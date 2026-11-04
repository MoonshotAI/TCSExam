"""Solver data-pair declarations and explicit data-only candidate preparation.

This module returns patches; it never rewrites the shared asset registries.
A frozen-directory candidate is not a public acquisition path.
"""
import copy
from pathlib import Path, PurePosixPath
import re
import shutil

from .layout import load, within
from .resources import content_digest, digest, relative, verify

EXCEPTIONS = {'bpp-bpplib': ('bpplib-development', 'bpplib-judging'),
              'qbf-qbfeval': ('qbf-public', 'qbf-judging')}


def product_ids(task_id):
    return EXCEPTIONS.get(task_id, (f'solver-{task_id}-development-data',
                                    f'solver-{task_id}-judging-data'))


def data_pairs(root):
    """Return all registered Solver tasks with their existing stable IDs."""
    tasks = load(within(root, 'suites/tasks.json'))['tasks']
    return [{'task_id': row['id'], 'public': product_ids(row['id'])[0],
             'hidden': product_ids(row['id'])[1]}
            for row in tasks if row['track'] == 'solver']


def validate_payload(rows, split):
    """Restrict new candidates to explicit instance paths, with full byte identity."""
    if split not in ('public', 'hidden') or not rows:
        raise ValueError('A data candidate requires a nonempty public or hidden manifest')
    paths = set()
    roots = ('app/instances/', 'app/test-instances/') if split == 'public' else ('tests/instances/',)
    for row in rows:
        path = relative(row['path'])
        if path in paths or not path.startswith(roots):
            raise ValueError(f'Duplicate or undeclared data candidate path: {path}')
        paths.add(path)
        if row.get('type', 'file') != 'file' or not re.fullmatch(r'[0-9a-f]{64}', row.get('sha256', '')):
            raise ValueError(f'Data candidate requires a regular file with SHA-256: {path}')
        if type(row.get('bytes')) is not int or row['bytes'] < 0:
            raise ValueError(f'Data candidate requires a byte size: {path}')
        if int(row['mode'], 8) & ~0o777:
            raise ValueError(f'Data candidate permission is invalid: {path}')
        parts = PurePosixPath(path).parts
        if (PurePosixPath(path).suffix.lower() in {'.key', '.pem', '.secret', '.log', '.token'}
                or any(part.lower() in {'solution', 'solutions', 'precomputed', 'logs', 'neither', 'credentials'} for part in parts)):
            raise ValueError(f'Excluded material in a data candidate: {path}')
    return paths


def prepare_frozen_directory(root, resource, rows, output, downloads=None, inputs=None, **kwargs):
    """Build a review candidate from explicit checked files, copying no extra inputs.

    No repository path, internal image, or private cache is used as an implicit
    fallback. Until a public source or approved public image is fixed, the
    declaration remains pending for external release.
    """
    recipe = load(within(root, resource['recipe']))
    validate_payload(rows, resource['data_split'])
    key = recipe['input_id']
    supplied = (inputs or {}).get(key)
    if supplied is None:
        raise ValueError(f'Public data acquisition remains pending for {resource["id"]}; '
                         f'review-only candidate requires explicit --input {key}=ROOTFS_DIRECTORY')
    source = Path(supplied).expanduser().resolve()
    if not source.is_dir():
        raise ValueError('Frozen candidate input must be an explicit rootfs directory')
    output = Path(output)
    for row in rows:
        name = relative(row['path'])
        original = source / name
        # Resolve every ancestor, rejecting links even when they stay in source.
        current = source
        for part in PurePosixPath(name).parts:
            current = current / part
            if current.is_symlink():
                raise ValueError(f'Frozen candidate source contains a link: {name}')
        if not original.is_file() or original.stat().st_size != row['bytes'] or digest(original) != row['sha256']:
            raise ValueError(f'Frozen candidate source content differs: {name}')
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, destination)
        destination.chmod(int(row['mode'], 8))
    return verify(output, rows)


def product_patch(root):
    """Return 60 idempotent product patches without discarding accepted evidence."""
    root = Path(root)
    existing = {r['id']: r for r in load(root / 'assets/images.json')['images'] if r.get('id')}
    patches = []
    for pair in data_pairs(root):
        for split in ('public', 'hidden'):
            name = pair[split]
            row = copy.deepcopy(existing.get(name, {'id': name, 'type': 'data'}))
            generated = (name not in existing or row.get('source_recipe_generator') == 'solver_data_recipes'
                         or row.get('content_version') == 'frozen-inputs-261029-v1'
                         or row.get('missing_frozen_manifest') is True)
            row.update(task_id=pair['task_id'], data_split=split,
                       consumers=[f'tasks/solver/{protocol}/{pair["task_id"]}'
                                  for protocol in ('online', 'offline')])
            if generated:
                prefix = f'assets/data/solver/{name}'
                row.update(source_recipe_generator='solver_data_recipes',
                           content_version='frozen-inputs-261029-v1', target_root='/',
                           product_record_id=name, recipe=prefix + '-recipe.json',
                           files_manifest=prefix + '-files.json',
                           build_argument=('TCSEXAM_PUBLIC_DATA_IMAGE' if split == 'public'
                                           else 'TCSEXAM_JUDGE_DATA_IMAGE'))
                for key, value in {'image_digest': None, 'public_image': None,
                                   'public_pull_verified': False, 'product_prepared': False,
                                   'public_upload_allowed': False, 'distribution': 'unresolved',
                                   'distribution_evidence': 'docs/licenses/third-party/solver-frozen-data-candidates.json',
                                   'status': 'public_acquisition_pending'}.items():
                    row.setdefault(key, value)
            manifest_path = row.get('files_manifest')
            recipe_path = row.get('recipe')
            recipe = load(root / recipe_path) if recipe_path and (root / recipe_path).is_file() else {}
            version = recipe.get('content_version')
            if version is not None:
                if not isinstance(version, str) or not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,95}', version):
                    raise ValueError('A data content version must be a safe cache component')
                row['content_version'] = version
                if recipe.get('history'):
                    row['data_history'] = copy.deepcopy(recipe['history'])
                if recipe.get('distribution_evidence'):
                    within(root, recipe['distribution_evidence'])
                    row['distribution_evidence'] = recipe['distribution_evidence']
                if recipe.get('format') == 'frozen_directory':
                    # A versioned explicit input cannot inherit another version's
                    # upstream sources or builder dependencies.
                    row.update(dependencies=[], acquisition={'preferred': 'local_build'},
                               status='local_preparation_required')
                    for key in ('source_input', 'source_inputs', 'source_input_file'):
                        row.pop(key, None)
            special_format = ('official_atcoder_generator' if recipe.get('calibration_files')
                              and recipe.get('generator_files') else recipe.get('format'))
            managed_recipe = special_format in ('official_atcoder_generator', 'official_files', 'official_mqlib',
                                                'official_archive', 'official_dfvs_xz', 'official_ce_xz',
                                                'official_vc_xz', 'official_gp_generator',
                                                'official_maxsat_generator', 'official_qbf_generator')
            if generated or managed_recipe:
                if manifest_path and (root / manifest_path).is_file():
                    files = load(root / manifest_path)['files']
                    if generated and not managed_recipe:
                        validate_payload(files, split)
                    old_identity = row.get('content_digest')
                    identity = content_digest(files, '/')
                    row.update(manifest_sha256=digest(root / manifest_path),
                               content_digest=identity, files=len(files),
                               bytes=sum(f['bytes'] for f in files))
                    row.pop('missing_frozen_manifest', None)
                    if old_identity and old_identity != identity:
                        row['previous_content_digest'] = old_identity
                        row['content_verification_refresh_required'] = True
                    row['recipe_format'] = special_format if managed_recipe else 'frozen_directory'
                    if managed_recipe:
                        row['acquisition'] = {'preferred': 'local_build'}
                        if special_format != 'official_qbf_generator' or name not in existing:
                            row.update(distribution='local_prepare', public_upload_allowed=False)
                        if recipe.get('sources'):
                            source_list = recipe['sources']
                            row['source_inputs'] = (list(source_list.values())
                                                    if isinstance(source_list, dict) else source_list)
                            row.pop('source_input', None)
                            row.pop('source_input_file', None)
                        elif recipe.get('source'):
                            row['source_input'] = recipe['source']
                            row.pop('source_input_file', None)
                        evidence = {
                            'qap-qaplib': 'qap-frozen-data-source.json',
                            'oscm-pace2024': 'oscm-pace2024-hidden-source.json' if split == 'hidden' else None,
                        }.get(pair['task_id'])
                        candidate_evidence = (within(root, recipe['distribution_evidence'])
                                              if recipe.get('distribution_evidence') else
                                              root / 'docs/licenses/third-party' / (evidence or f'{pair["task_id"]}-public-rebuild-source.json'))
                        if candidate_evidence.is_file():
                            row['distribution_evidence'] = candidate_evidence.resolve().relative_to(root.resolve()).as_posix()
                        if row.get('status') in ('public_acquisition_pending', 'unavailable',
                                                'local_preparation_required'):
                            row['status'] = 'local_preparation_required'
                        if special_format == 'official_atcoder_generator':
                            tag = 'ahc041' if pair['task_id'] == 'christmas-tree-ahc041' else 'ahc058'
                            row['distribution_evidence'] = f'docs/licenses/third-party/{tag}-frozen-data-source.json'
                else:
                    row.update(missing_frozen_manifest=True, recipe_format='unavailable')
            patches.append(row)
    return patches
