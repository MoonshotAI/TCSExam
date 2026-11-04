"""Acquire published images and build missing products on the local Docker host."""
import copy
from contextlib import ExitStack, suppress
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tarfile
import tempfile
import uuid
from urllib.parse import urlsplit

from .layout import load, require_paths, within
from .resources import (content_digest, data_image_metadata, data_image_source_paths,
                        manifest, prepare_resource, stage_data_context, verify)
from .setup import (IMAGE_ID, LOCAL_ID, PIN, artifacts, image_map, cache_path, docker_command, host_support_targets,
                    inspect_image, inspect_tag_id, local_reference, required_image_roles,
                    resolved_images, save_record, setup_selection)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def docker_from_instructions(dockerfile, build_args):
    """Resolve FROM images using global ARG defaults and explicit overrides.

    Stage-local ARG declarations cannot change the global scope used by FROM.
    Keep the original text spans so local mirror substitutions preserve flags,
    stage names, and all unrelated Dockerfile bytes.
    """
    arguments = {name: str(value) for name, value in build_args.items()}
    global_scope = True
    variable = re.compile(r'\$\{([A-Za-z_][A-Za-z_0-9]*)\}|\$([A-Za-z_][A-Za-z_0-9]*)')

    def expand(value):
        return variable.sub(lambda match: arguments.get(match.group(1) or match.group(2),
                                                        match.group(0)), value)

    for index, line in enumerate(dockerfile.read_text().splitlines(keepends=True)):
        declaration = re.match(r'\s*ARG\s+([A-Za-z_][A-Za-z_0-9]*)(?:=(.*?))?\s*$', line, re.I)
        if global_scope and declaration:
            name, default = declaration.groups()
            if name not in build_args and default is not None:
                # Docker permits a quoted default; do not pass the quote bytes
                # to image acquisition or treat an inline # as a comment.
                values = shlex.split(default, comments=False)
                arguments[name] = expand(' '.join(values))
        match = re.match(r'(\s*FROM\s+(?:--[^\s]+\s+)*)([^\s]+)(.*)', line, re.I)
        if not match:
            continue
        global_scope = False
        reference = expand(match.group(2))
        if '$' in reference:
            raise ValueError(f'Unresolved Docker base argument in {dockerfile}: {line.rstrip()}')
        stage = re.match(r'\s+AS\s+([^\s]+)', match.group(3), re.I)
        yield index, match, reference, stage.group(1).lower() if stage else None


def proxy_arguments():
    result = {}
    for name in ('HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY'):
        value = os.environ.get(name) or os.environ.get(name.lower())
        if not value:
            continue
        if name != 'NO_PROXY':
            parsed = urlsplit(value)
            if parsed.username or parsed.password:
                raise ValueError('Proxy credentials must be configured in the Docker daemon, not passed as build arguments')
            if parsed.scheme not in ('http', 'https') or not parsed.hostname:
                raise ValueError(f'Invalid proxy URL for {name}')
        result[name] = value
    return result


def file_digest(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def source_digest(root, paths):
    files = {}
    for value in dict.fromkeys(paths):
        path = within(root, value)
        candidates = sorted(path.rglob('*')) if path.is_dir() else [path]
        for candidate in candidates:
            relative = candidate.relative_to(root).as_posix()
            if '.git' in candidate.parts or '__pycache__' in candidate.parts or candidate.suffix == '.pyc':
                continue
            if candidate.is_symlink():
                files[relative] = {'type': 'symlink', 'target': os.readlink(candidate)}
            elif candidate.is_file():
                files[relative] = {'type': 'file', 'sha256': file_digest(candidate),
                                   # Git preserves the executable bit, not a
                                   # maintainer's local group-write umask.
                                   'mode': '0755' if candidate.stat().st_mode & 0o111 else '0644'}
            elif not candidate.is_dir():
                raise ValueError(f'Build source is not a regular file: {relative}')
    return 'sha256:' + hashlib.sha256(canonical(files)).hexdigest()


def build_definition(root, row):
    if row.get('type') in ('data', 'toolchain') and row.get('recipe') and row.get('files_manifest'):
        recipe = load(within(root, row['recipe']))
        paths = [row['recipe'], row['files_manifest'], 'src/tcsexam/resources.py', 'src/tcsexam/build.py',
                 *data_image_source_paths(root, row, recipe),
                 *recipe.get('generator_paths', [])]
        paths += [recipe[key] for key in ('source_recipe', 'reconstruction', 'transform')
                  if recipe.get(key)]
        definition = {'kind': 'resource', 'source_digest': source_digest(root, paths),
                      'image_metadata': data_image_metadata(row),
                      'dependencies': sorted(row.get('dependencies', [])),
                      'target_root': row['target_root'], 'manifest_sha256': row['manifest_sha256'],
                      'platform': row.get('platform', 'linux/amd64')}
        if row.get('selected_data_recipe'):
            definition['selected_data_recipe'] = row['selected_data_recipe']
            definition['data_recipe_signature'] = row['data_recipe_signature']
            definition['source_inputs'] = row['source_inputs']
        if row.get('recipe_format') in ('official_build', 'official_xz', 'official_zip', 'official_wheel',
                                       'official_atcoder_generator', 'official_dfvs_xz', 'official_ce_xz',
                                       'official_vc_xz', 'official_gp_generator',
                                       'official_maxsat_generator', 'official_qbf_generator'):
            from .resources import official_builder_reference
            reference = official_builder_reference(recipe['build'])
            definition['official_builder'] = reference
            definition['pull_args'] = {'TCSEXAM_OFFICIAL_BUILDER': reference}
        return definition
    config = row.get('build')
    if not config:
        return None
    kind = config.get('kind', 'docker')
    if kind == 'public_image':
        source = config['source_product']
        dependencies = sorted(set(row.get('dependencies', [])) | {source})
        paths = [config['manifest'], 'src/tcsexam/public_image.py', 'src/tcsexam/build.py']
        return {'kind': kind, 'source_digest': source_digest(root, paths),
                'dependencies': dependencies, 'source_product': source,
                'manifest': config['manifest'],
                'platform': config.get('platform', row.get('platform', 'linux/amd64'))}
    if kind != 'docker':
        raise ValueError(f'Unsupported local build kind for {row["id"]}: {kind}')
    dockerfile = config['dockerfile']
    context = config.get('context', str(Path(dockerfile).parent))
    sources = config.get('source_paths')
    if sources is None:
        if within(root, context) == root.resolve():
            raise ValueError(f'Repository-wide build context needs explicit source_paths: {row["id"]}')
        sources = [context]
    image_args = config.get('image_args', {})
    pull_args = config.get('pull_args', {})
    if (not isinstance(image_args, dict) or not isinstance(pull_args, dict)
            or any(not isinstance(value, str) or not value for value in (*image_args.values(), *pull_args.values()))):
        raise ValueError(f'Invalid image build arguments: {row["id"]}')
    network = config.get('network')
    if network not in (None, 'host'):
        raise ValueError(f'Unsupported Docker build network for {row["id"]}: {network}')
    for reference in pull_args.values():
        if not PIN.fullmatch(reference):
            raise ValueError(f'Base image must have a fixed digest: {row["id"]}')
    dependencies = sorted(set(row.get('dependencies', [])) | set(image_args.values()))
    paths = [dockerfile, *sources, 'src/tcsexam/build.py']
    if row.get('support_kind') == 'harbor_egress_control':
        paths.append('src/tcsexam/harbor_support.py')
    definition = {'kind': 'docker', 'source_digest': source_digest(root, paths),
                  'dockerfile': dockerfile, 'context': context, 'dependencies': dependencies,
                  'image_args': image_args, 'pull_args': pull_args,
                  'build_args': config.get('build_args', {}),
                  'platform': config.get('platform', row.get('platform', 'linux/amd64'))}
    if network:
        definition['network'] = network
    if row.get('support_kind') == 'harbor_egress_control':
        definition['harbor_context_hash'] = row.get('harbor_context_hash')
    return definition


def input_identity(row):
    if row.get('local'):
        return row['build_signature']
    reference = row.get('reference') or row.get('image')
    if not reference or not PIN.fullmatch(reference):
        raise ValueError(f'Build input has no fixed identity: {row.get("id", "unnamed")}')
    return reference


def acquisition_route(row):
    """Select acquisition before inspecting or expanding local build inputs."""
    public = row.get('public_image') or row.get('replacement')
    policy = row.get('acquisition', {})
    if not isinstance(policy, dict):
        raise ValueError(f'Invalid acquisition policy: {row["id"]}')
    route = policy.get('preferred', 'public_image' if public else 'local_build')
    if route not in ('public_image', 'local_build'):
        raise ValueError(f'Unknown acquisition route for {row["id"]}: {route}')
    if route == 'public_image' and not PIN.fullmatch(public or ''):
        raise ValueError(f'Published acquisition requires a fixed image digest: {row["id"]}')
    return route


def definition_signature(definition, inputs):
    return 'sha256:' + hashlib.sha256(canonical({'definition': definition, 'inputs': inputs})).hexdigest()


def validate_manifest(root, data):
    records = data.get('images', [])
    by_id = {}
    for row in records:
        if row.get('id'):
            if row['id'] in by_id:
                raise ValueError(f'Duplicate artifact identity: {row["id"]}')
            by_id[row['id']] = row
    declared = {row['id']: row for row in load(root / 'assets/images.json')['images'] if row.get('id')}
    for row in records:
        if not row.get('local'):
            continue
        identity = row.get('id')
        if identity not in declared:
            raise ValueError(f'Local image is no longer declared: {identity}')
        current = declared[identity]
        if row.get('selected_data_recipe'):
            from .fixed_data_archive import effective_resource
            current = effective_resource(root, current, {identity: row['selected_data_recipe']})
            if row.get('data_recipe_signature') != current['data_recipe_signature']:
                raise ValueError(f'Selected data recipe is stale: {identity}; run tcsexam build')
        definition = build_definition(root, current)
        if definition is None:
            raise ValueError(f'Local image no longer has a build recipe: {identity}')
        inputs = {}
        for dependency in definition['dependencies']:
            if dependency not in by_id:
                raise ValueError(f'Local image record lacks input {dependency}: {identity}')
            inputs[dependency] = input_identity(by_id[dependency])
        expected = definition_signature(definition, inputs)
        if row.get('build_signature') != expected or row.get('build_inputs', {}) != inputs:
            raise ValueError(f'Local image is stale or its inputs differ: {identity}; run tcsexam build')


def selection_artifact_path(root, rows, args, *, recipe_specific=True):
    """Keep exact build routes and a stable continuation for the Docker target.

    An explicit recipe/input request keeps its own key. A successful build also
    publishes its complete validated records under the selection-only key, so
    later prepare/doctor/run commands need not retain archive paths. Only build
    publishes this continuation; it never changes the recipe used by a new build.
    """
    selection = {'root': str(root.resolve()), 'suite': args.suite,
                 'solver_protocol': args.solver_protocol,
                 'tasks': [{'id': row['id'], 'variant': row['variant'], 'path': row['path']} for row in rows],
                 'docker_context': getattr(args, 'docker_context', None) or os.environ.get('DOCKER_CONTEXT'),
                 'docker_host': os.environ.get('DOCKER_HOST', '') if not getattr(args, 'docker_context', None) else ''}
    if recipe_specific and (getattr(args, 'data_recipe', None) or getattr(args, 'input', None)):
        selection['data_recipe'] = sorted(getattr(args, 'data_recipe', None) or [])
        selection['explicit_inputs'] = sorted(getattr(args, 'input', None) or [])
    key = hashlib.sha256(canonical(selection)).hexdigest()
    return cache_path(args) / 'selections' / (key + '.json')


class ImageBuilder:
    def __init__(self, root, rows, args, inputs=None):
        self.root = Path(root).resolve()
        self.args = args
        from .fixed_data_archive import recipe_choices, explicit_inputs, effective_resource
        self.inputs = explicit_inputs(getattr(args, 'input', None))
        self.inputs.update(inputs or {})
        self.data_recipes = recipe_choices(getattr(args, 'data_recipe', None))
        self.cache = cache_path(args).resolve()
        self.records = {row['id']: row for row in load(self.root / 'assets/images.json')['images']
                        if row.get('id') and row.get('type') != 'historical_reference'}
        for identity in self.data_recipes:
            if identity not in self.records:
                raise ValueError(f'Unknown data product: {identity}')
            self.records[identity] = effective_resource(
                self.root, self.records[identity], self.data_recipes)
        self.mapping, self.evidence = resolved_images(self.root, rows, args)
        self.explicit_mapping, explicit_evidence = artifacts(getattr(args, 'artifacts', None))
        for task, roles in image_map(getattr(args, 'image_map', None)).items():
            self.explicit_mapping.setdefault(task, {}).update(roles)
        self.evidence_by_id = {row['id']: ref for ref, row in explicit_evidence.items() if row.get('id')}
        self.products = {}
        self.references = {}
        self.local_aliases = set()
        self.actions = []
        self.stack = []
        self.support = []

    def action(self, identity, action, reference):
        self.actions.append({'id': identity, 'action': action, 'image': reference})
        print(f'{action}: {identity} -> {reference}', flush=True)

    def acquire(self, reference, evidence=None):
        if reference in self.references:
            return self.references[reference]
        evidence = evidence or {}
        if evidence.get('local'):
            if not local_reference(evidence, reference):
                raise ValueError(f'Invalid local image record: {evidence.get("id")}')
            local = inspect_image(reference, self.args, evidence)
            if not local:
                raise ValueError(f'Local image is missing or differs: {evidence["id"]}')
            record = dict(evidence)
        else:
            if not PIN.fullmatch(reference):
                raise ValueError(f'Published image must have a fixed digest: {reference}')
            cached = self.side_cached(reference)
            if cached:
                evidence = {**cached, **evidence}
            policy = getattr(self.args, 'pull_policy', 'missing')
            local = inspect_image(reference, self.args, evidence) if policy != 'always' else None
            present = local is not None
            if not local:
                if policy == 'never':
                    raise ValueError(f'Published image is absent locally: {reference}')
                result = subprocess.run(docker_command(self.args) + ['pull', '--platform', 'linux/amd64', reference],
                                        capture_output=True, text=True)
                if result.returncode:
                    evidence = {**self.side_load(reference), **evidence}
                else:
                    evidence.pop('side_loaded', None)
                    evidence.pop('local_image', None)
                local = inspect_image(reference, self.args, evidence)
            if not local:
                raise ValueError(f'Pulled image identity cannot be verified: {reference}')
            if evidence.get('platform') and local['platform'] != evidence['platform']:
                raise ValueError(f'Image platform differs from the product record: {reference}')
            record = {**evidence, 'image': reference, 'reference': reference,
                      'image_digest': reference.split('@', 1)[1], 'local': False}
            self.action(evidence.get('id', reference), 'reused' if present else 'pulled', reference)
        record['image_id'] = local['id']
        record['platform'] = local['platform']
        if record.get('local_image'):
            self.local_aliases.add(record['local_image'])
        self.references[reference] = record
        return record

    def upstream_path(self, reference):
        return self.cache / 'upstream' / reference.split('@', 1)[1]

    def side_cached(self, reference):
        path = self.upstream_path(reference).with_suffix('.json')
        return load(path) if path.is_file() else None

    def side_load(self, reference):
        if not shutil.which('crane'):
            raise ValueError('Docker pull failed and crane is unavailable for direct registry acquisition')
        lock_path = self.upstream_path(reference).with_suffix('.lock')
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            cached = self.side_cached(reference)
            if cached and inspect_image(reference, self.args, cached):
                return cached

            def call(*arguments):
                result = subprocess.run(['crane', *arguments], capture_output=True, text=True)
                if result.returncode:
                    raise ValueError(f'crane {arguments[0]} failed: {result.stderr[-2000:]}')
                return result

            selected = reference
            document = json.loads(call('manifest', reference).stdout)
            if 'manifests' in document:
                candidates = [row for row in document['manifests']
                              if row.get('platform', {}).get('os') == 'linux'
                              and row.get('platform', {}).get('architecture') == 'amd64']
                if len(candidates) != 1:
                    raise ValueError('Cannot select one linux/amd64 image from the upstream index')
                selected = reference.split('@', 1)[0] + '@' + candidates[0]['digest']
                document = json.loads(call('manifest', selected).stdout)
            config = json.loads(call('config', selected).stdout)
            selected_digest = selected.split('@', 1)[1]
            local_image = 'tcsexam/upstream-' + selected_digest[7:23]
            temporary = tempfile.TemporaryDirectory(prefix='acquire-', dir=lock_path.parent)
            try:
                archive = Path(temporary.name) / 'image.tar'
                call('pull', '--platform', 'linux/amd64', reference, str(archive))
                self.retag_archive(archive, local_image)
                result = subprocess.run(docker_command(self.args) + ['image', 'load', '-i', str(archive)],
                                        capture_output=True, text=True)
                if result.returncode:
                    raise ValueError(f'Cannot load the upstream image archive: {result.stderr[-2000:]}')
            finally:
                temporary.cleanup()
            image_id = inspect_tag_id(local_image, self.args)
            if not IMAGE_ID.fullmatch(image_id or ''):
                raise ValueError('Cannot inspect the side-loaded upstream image')
            record = {'image': reference, 'reference': reference,
                      'image_digest': reference.split('@', 1)[1],
                      'upstream_manifest_digest': reference.split('@', 1)[1],
                      'upstream_image_digest': selected_digest,
                      'upstream_config_digest': document.get('config', {}).get('digest'),
                      'upstream_config': config, 'side_loaded': True, 'local': False,
                      'local_image': local_image, 'image_id': image_id,
                      'platform': config['os'] + '/' + config['architecture'],
                      'verification': {'upstream_rootfs_and_config': True}}
            if not inspect_image(reference, self.args, record):
                raise ValueError(f'Side-loaded image does not match the upstream image: {reference}')
            save_record(self.upstream_path(reference).with_suffix('.json'), record)
            return record

    @staticmethod
    def retag_archive(archive, local_image):
        import io
        archive = Path(archive)
        if ':' not in local_image.rsplit('/', 1)[-1]:
            local_image += ':latest'
        replacement = archive.with_suffix('.tagged.tar')
        with tarfile.open(archive, 'r') as source, tarfile.open(replacement, 'w') as output:
            for member in source:
                stream = source.extractfile(member) if member.isfile() else None
                if member.name == 'manifest.json':
                    entries = json.load(stream)
                    if len(entries) != 1:
                        raise ValueError('Upstream archive must contain exactly one image')
                    entries[0]['RepoTags'] = [local_image]
                    payload = json.dumps(entries, separators=(',', ':')).encode()
                    member.size = len(payload)
                    stream = io.BytesIO(payload)
                output.addfile(member, stream)
                if stream:
                    stream.close()
        os.replace(replacement, archive)

    def product_for(self, row, role):
        candidates = [record['id'] for record in self.records.values()
                      if record.get('runtime_role') == role and row['path'] in record.get('consumers', [])]
        if len(candidates) > 1:
            raise ValueError(f'Multiple image products for {row["path"]}/{role}: {candidates}')
        if candidates:
            return candidates[0]
        adapter = within(self.root, row['path']) / 'offline-adapter.json'
        if adapter.is_file() and role in ('development', 'verifier'):
            key = 'development_dependency' if role == 'development' else 'verifier_dependency'
            identity = load(adapter)[key]
            if identity not in self.records:
                raise ValueError(f'Unknown offline image dependency: {identity}')
            return identity
        raise ValueError(f'No image product is declared for {row["path"]}/{role}')

    def cached(self, identity, signature, reference):
        path = self.cache / 'images' / (identity + '.json')
        if not path.is_file():
            return None
        record = load(path)
        if record.get('build_signature') != signature or not local_reference(record, reference):
            return None
        local = inspect_image(reference, self.args, record)
        if not local or local['platform'] != record.get('platform'):
            return None
        return record

    def prepare_product(self, identity):
        if identity in self.products:
            return self.products[identity]
        if identity in self.stack:
            raise ValueError('Image dependency cycle: ' + ' -> '.join([*self.stack, identity]))
        if identity not in self.records:
            raise ValueError(f'Unknown image product: {identity}')
        row = self.records[identity]
        if row.get('selected_data_recipe'):
            from .fixed_data_archive import check_explicit_input
            check_explicit_input(self.root, row, self.cache / 'downloads', self.inputs)
        external = None if row.get('selected_data_recipe') else self.evidence_by_id.get(identity)
        if external:
            record = self.acquire(external, self.evidence[external])
            if row.get('type') in ('data', 'toolchain') and row.get('files_manifest') and not record.get('local'):
                record = self.verify_published_resource(row, record)
            self.products[identity] = record
            return record
        public = row.get('public_image') or row.get('replacement')
        if acquisition_route(row) == 'public_image':
            record = self.acquire(public, row)
            if row.get('files_manifest'):
                record = self.verify_published_resource(row, record)
            self.products[identity] = record
            return record
        definition = build_definition(self.root, row)
        if definition is None:
            raise ValueError(f'No local build recipe for {identity}')
        self.stack.append(identity)
        try:
            inputs = {dependency: self.prepare_product(dependency) for dependency in definition['dependencies']}
            for reference in definition.get('pull_args', {}).values():
                self.acquire(reference)
            identities = {name: input_identity(record) for name, record in inputs.items()}
            signature = definition_signature(definition, identities)
            reference = f'tcsexam/{identity}:{signature[7:23]}'
            lock_path = self.cache / 'images' / (identity + '.lock')
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            with lock_path.open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                record = self.cached(identity, signature, reference)
                if record:
                    self.action(identity, 'reused', reference)
                else:
                    record = self.build(row, definition, inputs, signature, reference, identities)
                    save_record(self.cache / 'images' / (identity + '.json'), record)
                    self.action(identity, 'built', reference)
            self.products[identity] = record
            self.references[record['reference']] = record
            return record
        finally:
            self.stack.pop()

    def verify_published_resource(self, row, record):
        """Check the payload without executing any code from a data image."""
        rows = manifest(self.root, row)
        expected = content_digest(rows, row['target_root'])
        if row.get('content_digest') != expected:
            raise ValueError(f'Resource content digest differs: {row["id"]}')
        prefix = row['target_root'].strip('/')
        if prefix and ('..' in Path(prefix).parts or '\\' in prefix):
            raise ValueError(f'Unsafe resource target: {row["id"]}')
        image = record.get('local_image', record['reference'])
        container = 'tcsexam-inspect-' + uuid.uuid4().hex
        command = docker_command(self.args)
        made = False
        work_parent = self.cache / 'tmp'
        work_parent.mkdir(parents=True, exist_ok=True)
        try:
            create = subprocess.run(command + ['create', '--name', container, '--network', 'none',
                                    '--entrypoint', '/tcsexam-inspection-not-executed', image],
                                    capture_output=True, text=True)
            if create.returncode:
                raise ValueError(f'Cannot inspect data image: {row["id"]}')
            made = True
            with tempfile.TemporaryDirectory(prefix='tcsexam-inspect-', dir=work_parent) as folder:
                # Verify the entire payload, including undeclared sibling paths.
                source = '/payload/rootfs/.'
                result = subprocess.run(command + ['cp', container + ':' + source, folder],
                                        capture_output=True, text=True)
                if result.returncode:
                    raise ValueError(f'Cannot read data image payload: {row["id"]}')
                expected_rows = []
                for entry in rows:
                    entry = dict(entry)
                    if prefix:
                        entry['path'] = prefix + '/' + entry['path']
                        if entry.get('type') == 'hardlink':
                            entry['link_target'] = prefix + '/' + entry['link_target']
                    expected_rows.append(entry)
                verify(folder, expected_rows)
        finally:
            if made:
                cleanup = subprocess.run(command + ['rm', '-f', container], capture_output=True, text=True)
                if cleanup.returncode:
                    raise ValueError(f'Data inspection container cleanup failed: {container}')
        checked = {**record, 'content_digest': expected, 'content_verified': True,
                   'manifest_sha256': row['manifest_sha256']}
        self.references[record['reference']] = checked
        return checked

    def build(self, row, definition, inputs, signature, reference, identities):
        platform = definition['platform']
        if platform != 'linux/amd64':
            raise ValueError(f'Only linux/amd64 local products are supported: {row["id"]}')
        if definition['kind'] == 'public_image':
            return self.build_public(row, definition, inputs, signature, reference, identities)
        build_args = {}
        if definition['kind'] == 'docker':
            build_args.update({name: inputs[dependency].get('local_image', inputs[dependency]['reference'])
                               for name, dependency in definition['image_args'].items()})
            build_args.update({name: self.references[reference].get('local_image', reference)
                               for name, reference in definition['pull_args'].items()})
            build_args.update(definition['build_args'])
        build_args.update(proxy_arguments())
        for name in build_args:
            if re.search(r'KEY|TOKEN|SECRET|PASSWORD', name, re.I):
                raise ValueError(f'Credentials must not be Docker build arguments: {name}')
        work_parent = self.cache / 'tmp'
        work_parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='tcsexam-build-', dir=work_parent) as folder:
            if definition['kind'] == 'resource':
                builder_image = None
                if definition.get('official_builder'):
                    record = self.references[definition['official_builder']]
                    builder_image = record.get('local_image', record['reference'])
                rootfs = prepare_resource(self.root, row['id'], self.cache, self.inputs,
                                          args=self.args, builder_image=builder_image, resource=row)
                context = Path(folder) / 'context'
                stage_data_context(self.root, row['id'], rootfs, context, resource=row)
                dockerfile = context / 'Dockerfile'
            else:
                if row.get('support_kind') == 'harbor_egress_control':
                    from .harbor_support import normalized_context
                    context, context_hash = normalized_context(self.cache)
                    if definition.get('harbor_context_hash') != context_hash:
                        raise ValueError(f'Harbor helper context hash differs: {row["id"]}')
                    dockerfile = context / 'Dockerfile'
                else:
                    context = within(self.root, definition['context'])
                    dockerfile = within(self.root, definition['dockerfile'])
                replacements = self.prepare_bases(dockerfile, build_args)
                if replacements:
                    rewritten = Path(folder) / 'Dockerfile.generated'
                    self.rewrite_bases(dockerfile, replacements, rewritten, build_args)
                    dockerfile = rewritten
            command = docker_command(self.args) + [
                'build', '--pull=false', '--platform', platform,
                '--provenance=false', '--sbom=false', '--file', str(dockerfile),
                '--tag', reference]
            if definition.get('network'):
                command += ['--network', definition['network']]
            for name, value in sorted(build_args.items()):
                command += ['--build-arg', f'{name}={value}']
            command.append(str(context))
            result = subprocess.run(command, env={**os.environ, 'DOCKER_BUILDKIT': '1'})
            if result.returncode:
                raise ValueError(f'Docker build failed for {row["id"]} with exit code {result.returncode}')
        image_id = inspect_tag_id(reference, self.args)
        if not IMAGE_ID.fullmatch(image_id or ''):
            raise ValueError(f'Built image has no verifiable local ID: {row["id"]}')
        record = {key: row[key] for key in ('id', 'type', 'runtime_role', 'consumers', 'distribution',
                  'support_kind', 'harbor_context_hash', 'content_digest', 'content_description',
                  'selected_data_recipe', 'data_recipe_signature') if key in row}
        record.update({'image': reference, 'reference': reference, 'local': True,
                       'image_id': image_id, 'build_signature': signature,
                       'build_inputs': identities, 'platform': platform,
                       'status': 'local_build_verified',
                       'verification': {'local_build': True, 'inputs_verified': True}})
        if definition['kind'] == 'resource':
            resource = self.records[row['id']]
            expected = content_digest(manifest(self.root, resource), resource['target_root'])
            if record.get('content_digest', expected) != expected:
                raise ValueError(f'Resource content digest differs: {row["id"]}')
            record['content_digest'] = expected
            record['content_verified'] = True
        local = inspect_image(reference, self.args, record)
        if not local or local['platform'] != platform:
            raise ValueError(f'Built image failed local inspection: {row["id"]}')
        return record

    def build_public(self, row, definition, inputs, signature, reference, identities):
        from .public_image import DockerClient, build_public_image, load_manifest

        source = inputs[definition['source_product']]['reference']
        docker = DockerClient(context=getattr(self.args, 'docker_context', None))
        report = build_public_image(source, reference, load_manifest(within(self.root, definition['manifest'])),
                                    pull=False, push=False, docker=docker)
        image_id = inspect_tag_id(reference, self.args)
        if not IMAGE_ID.fullmatch(image_id or ''):
            raise ValueError(f'Public image has no verifiable local ID: {row["id"]}')
        record = {key: row[key] for key in ('id', 'type', 'runtime_role', 'consumers', 'distribution',
                  'support_kind', 'harbor_context_hash', 'content_description') if key in row}
        record.update({'image': reference, 'reference': reference, 'local': True,
                       'image_id': image_id, 'build_signature': signature,
                       'build_inputs': identities, 'platform': definition['platform'],
                       'status': 'local_build_verified', 'content_verified': True,
                       'final_filesystem_isolation_verified': True,
                       'historical_layer_isolation_verified': True,
                       'verification': {'local_build': True, 'inputs_verified': True,
                                        'public_image': report}})
        local = inspect_image(reference, self.args, record)
        if not local or local['platform'] != definition['platform']:
            raise ValueError(f'Public image failed local inspection: {row["id"]}')
        return record

    def prepare_bases(self, dockerfile, build_args):
        replacements = {}
        stages = set()
        for _, _, reference, stage in docker_from_instructions(dockerfile, build_args):
            if reference.lower() == 'scratch' or reference.lower() in stages:
                if stage:
                    stages.add(stage)
                continue
            if stage:
                stages.add(stage)
            if reference.startswith(('tcsexam/', 'tcsexam' + '.local/')):
                if reference not in self.references and reference not in self.local_aliases:
                    raise ValueError(f'Local base image was not built: {reference}')
                continue
            record = self.acquire(reference)
            if record.get('local_image'):
                replacements[reference] = record['local_image']
        return replacements

    @staticmethod
    def rewrite_bases(dockerfile, replacements, output, build_args=None):
        lines = dockerfile.read_text().splitlines(keepends=True)
        for index, match, reference, _ in docker_from_instructions(dockerfile, build_args or {}):
            if reference in replacements:
                line = lines[index]
                lines[index] = line[:match.start(2)] + replacements[reference] + line[match.end(2):]
        output.write_text(''.join(lines))

    def prepare_support(self):
        evidence = dict(self.evidence)
        required = {'harbor_egress_control', 'harbor_kernel_probe'}
        for identity, row in self.records.items():
            if (row.get('type') != 'host_support' or row.get('support_kind') not in required
                    or identity in self.evidence_by_id):
                continue
            if row.get('build'):
                record = self.prepare_product(identity)
            elif row.get('support_kind') == 'harbor_kernel_probe':
                from harbor.environments.docker.docker import DockerEnvironment
                reference = DockerEnvironment._EGRESS_CONTROL_KERNEL_PROBE_IMAGE
                record = self.acquire(reference, row)
            else:
                public = row.get('public_image') or row.get('replacement')
                if not public:
                    raise ValueError(f'No published image or local build recipe for {identity}')
                record = self.acquire(public, row)
            evidence[record['reference']] = record
        self.support = host_support_targets(evidence, self.args)
        for row in self.support:
            reference = row.get('image') or row.get('reference')
            if reference not in self.references:
                self.references[reference] = evidence[reference]

    def prepare(self, rows):
        for identity in self.data_recipes:
            self.prepare_product(identity)
        tasks, supporting = {}, []
        for row in rows:
            roles = list(required_image_roles(self.root, row))
            if row['variant'] == 'online':
                roles.append('backend')
            for role in roles:
                reference = self.mapping.get(row['path'], {}).get(role)
                explicit = self.explicit_mapping.get(row['path'], {}).get(role)
                candidates = [r for r in self.records.values() if r.get('runtime_role') == role
                              and row['path'] in r.get('consumers', [])]
                declared = candidates[0] if len(candidates) == 1 else None
                declared_public = (declared.get('public_image') or declared.get('replacement')) if declared else None
                if explicit or (reference and reference != declared_public
                                and (PIN.fullmatch(reference) or local_reference(self.evidence.get(reference), reference))):
                    record = self.acquire(reference, self.evidence.get(reference))
                else:
                    record = self.prepare_product(self.product_for(row, role))
                tasks.setdefault(row['path'], {})[role] = record.get('id', record['reference'])
            if row['variant'] == 'online':
                identity = self.product_for(row, 'public_backend')
                record = self.prepare_product(identity)
                supporting.append({'task': row['path'], 'role': 'public_backend', 'product': record.get('id')})
        self.prepare_support()
        images = list(self.references.values())
        for record in self.products.values():
            if record['reference'] not in self.references:
                images.append(record)
        return tasks, supporting, images


def publish_selection_manifests(paths, data):
    """Publish every output, restoring prior files if any replacement fails.

    Locks serialize overlapping writers, including custom output paths. Stage
    both new records and rollback copies on each destination filesystem before
    touching any published record. This handles publication errors; it does not
    make several files a single crash-atomic filesystem operation.
    """
    paths = list(dict.fromkeys(Path(path).resolve() for path in paths))
    for path in paths:
        if path.name.endswith('.lock'):
            raise ValueError(f'Manifest output cannot use the reserved .lock suffix: {path}')
    staged, backups, attempted, restored = {}, {}, [], set()
    publication_complete = False
    with ExitStack() as locks:
        for path in sorted(paths):
            path.parent.mkdir(parents=True, exist_ok=True)
            lock = locks.enter_context(path.with_name(path.name + '.lock').open('a'))
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            for path in paths:
                staged[path] = path.with_name(path.name + '.tmp-' + uuid.uuid4().hex)
                save_record(staged[path], data)
                if path.exists():
                    backups[path] = path.with_name(path.name + '.rollback-' + uuid.uuid4().hex)
                    shutil.copy2(path, backups[path])
            try:
                for path in paths:
                    # Register before replacement: an interruption may arrive
                    # after the filesystem changed but before os.replace returns.
                    attempted.append(path)
                    os.replace(staged[path], path)
                publication_complete = True
            except BaseException as error:
                failures = []
                for path in reversed(attempted):
                    try:
                        if path in backups:
                            os.replace(backups[path], path)
                        else:
                            path.unlink(missing_ok=True)
                    except BaseException as restore_error:
                        backup = backups.get(path)
                        failures.append(f'{path}: {type(restore_error).__name__}: {restore_error}; '
                                        f'previous record: {backup or "absent"}')
                    else:
                        restored.add(path)
                if failures:
                    raise RuntimeError('Manifest publication failed and rollback was incomplete: '
                                       + '; '.join(failures)) from error
                raise
        finally:
            # Preserve every pending recovery copy even if interruption occurs
            # between individual restore operations or while reporting failure.
            retained = {backups[path] for path in attempted if path in backups and path not in restored}
            if publication_complete:
                retained.clear()
            for temporary in [*staged.values(), *backups.values()]:
                if temporary not in retained:
                    # Cleanup failure must not turn a completed publication into
                    # a failed command. Leftover temporary files are not selected.
                    with suppress(OSError):
                        temporary.unlink(missing_ok=True)


def build_selection(root, rows, args, inputs=None):
    require_paths(rows)
    builder = ImageBuilder(root, rows, args, inputs=inputs)
    tasks, supporting, images = builder.prepare(rows)
    data = {'schema_version': 1,
            'selection': {'suite': args.suite, 'solver_protocol': args.solver_protocol,
                          'tasks': [{'id': row['id'], 'variant': row['variant'], 'path': row['path']} for row in rows]},
            'images': images, 'tasks': tasks, 'supporting_images': supporting,
            'host_support': [row['id'] for row in builder.support]}
    canonical = selection_artifact_path(root, rows, args).resolve()
    destination = Path(getattr(args, 'output', None) or canonical).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + '.tmp-' + uuid.uuid4().hex)
    save_record(temporary, data)
    try:
        prepared_args = copy.copy(args)
        prepared_args.artifacts = temporary
        readiness = setup_selection(root, rows, prepared_args)
        if readiness.get('host_prepared') is not True:
            raise ValueError('Build host preparation did not complete; previous selection is unchanged')
        data['host_prepared'] = True
        data['actions'] = builder.actions
        continuation = selection_artifact_path(root, rows, args, recipe_specific=False).resolve()
        outputs = [path for path in (canonical, destination) if path != continuation]
        publish_selection_manifests([*outputs, continuation], data)
    finally:
        with suppress(OSError):
            temporary.unlink(missing_ok=True)
    return {'manifest': str(destination), 'host_prepared': True,
            'tasks': len(rows), 'images': builder.actions, 'model_started': False}
