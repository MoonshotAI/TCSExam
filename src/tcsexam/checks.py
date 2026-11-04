"""Static source checks and a separate, conservative publication report."""
from collections import Counter
import hashlib
from ipaddress import ip_address
import os
import re
from pathlib import Path
import subprocess
import tomllib

from .layout import load, selection, within


UPSTREAM_CI_CACHE_EXAMPLE = '/home/runner/.cache/ms-playwright'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_task_identity(config, task_path, checkpoint_task=None):
    """Check public task identities without changing historical seed values."""
    require(config["task"]["name"].startswith("tcsexam/"), f"Wrong task namespace: {task_path}")
    require(config["task"]["authors"] == [{"name": "TCSExam Contributors"}],
            f"Wrong task contributors: {task_path}")
    if checkpoint_task is not None:
        require(checkpoint_task == config["task"]["name"],
                f"Checkpoint task identity differs: {task_path}")


def validate_source_pins(root):
    """Allow only explicitly external, identity-matched input bytes to be absent."""
    from .oracle_answers import is_oracle_answer_path
    pins = load(root / "assets/sources.json")
    changed = {r['path']: r for r in pins['packaging_changes']}
    removed = {r["path"] for r in pins["packaging_changes"] if r.get("action") == "remove"}
    external = {r['path']: r for r in load(root / 'assets/files.json')['files']
                if r.get('status') == 'source_omitted'
                and r.get('distribution') in ('local_prepare', 'private_only', 'unresolved')}
    checked = 0
    for row in pins["files"]:
        path = within(root, row["path"])
        if row["path"] in removed:
            require(not path.exists(), f"Removed source restored: {row['path']}")
            continue
        if not path.exists() and is_oracle_answer_path(row['path']):
            # Source exports intentionally omit concrete private answers. If a
            # maintainer has them locally, their pinned bytes are still checked.
            continue
        if not path.exists() and row['path'] in external:
            require(external[row['path']].get('sha256') == row['sha256'],
                    f"External input identity differs: {row['path']}")
            continue
        require(path.is_file(), f"Unrecorded removal: {row['path']}")
        expected = changed.get(row['path'], {}).get('current_sha256') if row['path'] in changed else row['sha256']
        require(expected, f"Packaging change lacks current hash: {row['path']}")
        require(hashlib.sha256(path.read_bytes()).hexdigest() == expected,
                f"Unrecorded source change: {row['path']}")
        checked += 1
    return checked


def validate(root):
    """Check structure and pinned bytes without starting any task."""
    registry = load(root / "suites/tasks.json")["tasks"]
    keys = {(r["track"], r["id"]) for r in registry}
    require(len(keys) == len(registry), "Duplicate task")
    variants = []
    for r in registry:
        allowed = {"online", "offline"} if r["track"] == "solver" else {"default"}
        require(set(r["variants"]) <= allowed, f"Unknown variant: {r['id']}")
        require(bool(r["variants"]), f"No variants: {r['id']}")
        for name, v in r["variants"].items():
            prefix = f"tasks/solver/{name}/" if r["track"] == "solver" else f"tasks/{r['track']}/"
            require(v["path"] == prefix + r["id"], f"Unexpected task path: {v['path']}")
            variants.append((name, v))
    require(len({v["path"] for _, v in variants}) == len(variants), "Duplicate variant path")
    suite_keys = {}
    for name in ("lite", "full"):
        suite, _ = selection(root, name)
        members = {(r["track"], r["id"]) for r in suite["tasks"]}
        require(len(members) == len(suite["tasks"]) == suite["task_count"], f"Invalid {name} selection")
        require(members <= keys, f"Unknown {name} task")
        expected_protocol = "online" if name == "full" else "offline"
        require(suite["default_solver_protocol"] == expected_protocol, f"Wrong {name} default protocol")
        suite_keys[name] = members
    require(suite_keys["lite"] <= suite_keys["full"], "Lite must be a subset of Full")
    require(suite_keys['full'] == keys, 'Full selection and task registry differ')
    task_paths = {v["path"] for _, v in variants}
    found = {str(p.parent.relative_to(root)) for p in (root / "tasks").rglob("task.toml")}
    require(task_paths == found, "Task folders and registry differ")
    for _, row in variants:
        task = within(root, row["path"])
        for required in ["task.toml", "instruction.md", "environment/Dockerfile", "tests/test.sh"]:
            require((task / required).is_file(), f"Missing {row['path']}/{required}")
        config = tomllib.loads((task / "task.toml").read_text())
        checkpoints = task / "tests/checkpoints.json"
        checkpoint_task = load(checkpoints).get("task") if checkpoints.is_file() else None
        validate_task_identity(config, row["path"], checkpoint_task)
        require(config["agent"]["timeout_sec"] == 43200., f"Wrong budget: {row['path']}")
        require("/app" in config["artifacts"], f"Missing workspace artifact: {row['path']}")
        for path in task.rglob("*"):
            require(not path.is_symlink(), f"Task symlink: {path.relative_to(root)}")
            require(path.suffix != ".bak", f"Retired backup file: {path.relative_to(root)}")
            require(path.suffix.lower() != ".key", f"Credential key file in task package: {path.relative_to(root)}")
            if path.suffix == ".sh":
                require(bool(path.stat().st_mode & 0o111), f"Nonexecutable shell script: {path.relative_to(root)}")
            require(not path.name.startswith("harvest-"), f"Historical experiment file: {path}")
    checked = validate_source_pins(root)
    for name in ["ex-c3c4-maxedges", "kissing-d13", "ramsey-r46"]:
        config = tomllib.loads((root / f"tasks/construction/{name}/task.toml").read_text())
        require(config["verifier"]["env"]["REWARD_JSON"] == "/logs/verifier/score-details.json",
                f"Missing Harbor details output: {name}")
    for old in ["catalog", "scripts", "scoring", "environments", "tests", "results", "trajectories"]:
        require(not (root / old).exists(), f"Unexpected first-release folder: {old}")
    for inventory, field in [("files", "path"), ("images", "locations")]:
        for row in load(root / f"assets/{inventory}.json")[inventory]:
            locations = row.get(field, [])
            locations = locations if isinstance(locations, list) else [locations]
            for location in locations:
                require("/harvest-" not in location, f"Historical experiment asset: {location}")
                require(any(location.startswith(p + "/") for p in task_paths),
                        f"Asset outside registered task: {location}")
                within(root, location)
    images = load(root / 'assets/images.json')['images']
    identities = [r['id'] for r in images if r.get('id')]
    require(len(identities) == len(set(identities)), 'Duplicate image identity')
    from .product_graph import validate_graph
    graph = validate_graph({'images': images})
    for task in registry:
        if task['track'] == 'solver':
            products = [r for r in images if r.get('type') == 'data' and r.get('task_id') == task['id']]
            require(Counter(r.get('data_split') for r in products) == {'public': 1, 'hidden': 1},
                    f'Solver needs one public and one hidden data product: {task["id"]}')
        else:
            path = task['variants']['default']['path']
            products = [r for r in images if r.get('type') == 'runtime' and path in r.get('consumers', [])]
            require(Counter(r.get('runtime_role') for r in products) == {'development': 1, 'verifier': 1},
                    f'Lean task needs a development and independent verifier product: {task["id"]}')
    data_checked = 0
    for row in images:
        for consumer in row.get('consumers', []):
            require(consumer in task_paths, f'Unknown image consumer: {consumer}')
        if row.get('type') in ('data', 'toolchain') and row.get('files_manifest'):
            from .resources import content_digest, manifest
            entries = manifest(root, row)
            require(not row.get('content_digest') or row['content_digest'] == content_digest(entries, row['target_root']),
                    f'Data content digest differs: {row["id"]}')
            if 'files' in row:
                require(row['files'] == len(entries), f'Data file count differs: {row["id"]}')
            if row.get('recipe'):
                require(within(root, row['recipe']).is_file(), f'Missing data recipe: {row["id"]}')
            data_checked += 1
    omitted = load(root / 'assets/files.json')['files']
    require(len({r['path'] for r in omitted}) == len(omitted), 'Duplicate omitted source path')
    for row in omitted:
        if row.get('data_image_id'):
            require(row['data_image_id'] in identities, f'Unknown data image: {row["path"]}')
    counts = Counter(n for n, _ in variants)
    return {"static_integrity": "passed", "task_count": len(registry), "task_variants": len(variants),
            "full_tasks": len(suite_keys['full']), "lite_tasks": len(suite_keys['lite']),
            "shared_lite_tasks": sum(track != 'solver' for track, _ in suite_keys['lite']),
            "solver_online": counts['online'], "solver_offline": counts['offline'],
            "source_files_checked": checked, 'data_manifests_checked': data_checked,
            'product_graph': graph}


def publication_paths(root):
    """Include tracked and new release files, without Git metadata or local outputs."""
    if (root / '.git').exists():
        try:
            result = subprocess.run(['git', '-C', str(root), 'ls-files', '-z',
                                     '--cached', '--others', '--exclude-standard'],
                                    capture_output=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            result = None
        if result is not None and result.returncode == 0:
            for name in sorted(set(result.stdout.split(b'\0')) - {b''}):
                yield root / os.fsdecode(name)
            return
    ignored = {'.git', '.venv', '__pycache__'}
    for directory, folders, files in os.walk(root, followlinks=False):
        retained = []
        for name in sorted(folders):
            path = Path(directory) / name
            if name in ignored or name.endswith('.egg-info'):
                continue
            if Path(directory) == root and name in {'build', 'dist', 'jobs'}:
                continue
            if path.is_symlink():
                yield path
            else:
                retained.append(name)
        folders[:] = retained
        for name in sorted(files):
            if name != '.git' and not name.endswith(('.pyc', '.pyo')):
                yield Path(directory) / name


def publication_text(path):
    """Detect text by bytes rather than suffix, including Unicode BOMs."""
    data = path.read_bytes()
    encoding = 'utf-8-sig'
    if data.startswith((b'\xff\xfe\0\0', b'\0\0\xfe\xff')):
        encoding = 'utf-32'
    elif data.startswith((b'\xff\xfe', b'\xfe\xff')):
        encoding = 'utf-16'
    elif b'\0' in data:
        return None
    try:
        return data.decode(encoding)
    except UnicodeError:
        return None


def legacy_name_lines(content):
    """Find retired project display names and task namespaces.

    Deterministic data seeds and immutable source image names use other
    suffixes; those provenance values must remain byte-for-byte unchanged.
    Build the pattern in parts so the check scans its own source as well.
    """
    pattern = re.compile("tcs" + r"(?:" + "hard" + r"(?:bench|problem|/)|bench)", re.I)
    return [number for number, line in enumerate(content.splitlines(), 1)
            if pattern.search(line)]


def internal_reference_categories(content):
    """Find nonpublic endpoints and personal or machine-specific storage paths."""
    content = content.replace(UPSTREAM_CI_CACHE_EXAMPLE, '<upstream-ci-cache>')
    categories = set()
    # Apply to prose, SDK identifiers and filenames alike. Split literals keep
    # the checker itself subject to the same publication rules as other files.
    platform_names = '|'.join(('mang' + 'rove', 'agent' + 'gym', 'agent' + 'env'))
    if re.search(platform_names, content, flags=re.I):
        categories.add('internal_platform')
    if re.search(r'\b' + 'ms' + r'ai(?:-|\.example\.)', content, flags=re.I):
        categories.add('internal_image_namespace')
    if re.search('moon' + 'fs', content, flags=re.I):
        categories.add('internal_storage')
    if re.search(r'\bschema-v\d+/workbench/', content):
        categories.add('internal_workspace')
    if re.search(r'\bi-\d{15,}\b', content):
        categories.add('cloud_instance')
    if re.search(r'(?:容器\s+|(?<!\w)(?:container|run)\s+)\d{6,}\b', content, flags=re.I):
        categories.add('internal_run')
    if re.search(r'\b' + 'agent' + r'env:[a-z0-9_-]+\b', content, flags=re.I):
        categories.add('internal_profile')
    if re.search(r'\b' + 'frontier' + '_' + r'smith:[a-z0-9_.-]+\b', content, flags=re.I):
        categories.add('internal_image_namespace')
    if re.search(r'\b' + 'moon' + 'shot' + r'\.fei' + r'shu\.cn\b', content, flags=re.I):
        categories.add('internal_document')
    domains = re.finditer(r'(?<![\w.-])(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,63}\b(?![\w-]|\.[\w-])',
                          content, flags=re.I)
    for match in domains:
        labels = match.group().lower().split('.')
        if labels == ['host', 'docker', 'internal']:
            continue
        # Python receivers and their attributes are not endpoint literals.
        prefix = content[max(0, match.start() - 200):match.start()].split('\n')[-1]
        url_host = re.search(r'\b[a-z][a-z0-9+.-]*://[^\s/]*$', prefix, flags=re.I)
        if labels[0] in {'self', 'cls'} and not url_host:
            continue
        if ('m' + 'sh' in labels or labels[-1] in {'internal', 'intranet', 'corp', 'lan', 'local', 'launchpad'}
                or len(labels) >= 3 and any(label.endswith(('-vpc', '-internal')) for label in labels)
                or ('cr' in labels and labels[0].startswith(('ms' + 'ai-', 'moon' + 'shot-')))):
            categories.add('internal_domain')
    ipv4 = list(re.finditer(r'(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])', content))
    ipv6 = list(re.finditer(r'(?<![\w:])(?:[0-9a-f]{0,4}:){2,}[0-9a-f:.]*(?:%[\w.-]+)?', content, flags=re.I))
    for match in ipv4 + ipv6:
        candidate = match.group().rstrip('.')
        try:
            address = ip_address(candidate)
        except ValueError:
            continue
        if address.version == 4:
            first, second, *_ = address.packed
            private = (first == 10 or first == 172 and 16 <= second <= 31
                       or first == 192 and second == 168 or first == 100 and 64 <= second <= 127
                       or first == 169 and second == 254 or first == 198 and second in (18, 19))
        else:
            private = address.packed[0] & 0xfe == 0xfc or address.is_link_local
        # Addresses in numeric datasets can resemble IPv4. Require an endpoint,
        # network assignment or CIDR context; loopback and wildcard binds remain allowed.
        before = content[max(0, match.start() - 100):match.start()].split('\n')[-1]
        after = content[match.end():match.end() + 12]
        network = (re.search(r'(?:[a-z][a-z0-9+.-]*://|@)\[?$', before, flags=re.I)
                   or re.search(r'(?<![a-z0-9])(?:host|hostname|server|endpoint|address|ip|proxy|registry|dns|gateway|url|domain|bind|listen|nameserver|worker|node)(?![a-z0-9])[^\n]{0,60}$', before, flags=re.I)
                   or re.match(r'\]?:\d{1,5}\b|/\d{1,3}\b', after))
        if private and network:
            categories.add('nonpublic_ip')
    if re.search(r'(?<![\w.])/(?:home|Users)/[A-Za-z0-9_.-]+(?:/|\b)', content):
        categories.add('machine_path')
    generic_mounts = {'data', 'work', 'workspace', 'cache', 'tmp', 'output', 'outputs',
                      'input', 'inputs', 'resources', 'instances', 'task', 'tasks', 'app', 'models', 'test'}
    for match in re.finditer(r'(?<![\w.])/mnt/([A-Za-z0-9_.-]+)(?:/|\b)', content):
        if match.group(1).lower() not in generic_mounts:
            categories.add('machine_path')
    if re.search(r'\b[A-Za-z]:[\\/]+Users[\\/]+[A-Za-z0-9_.-]+(?:[\\/]|\b)', content, flags=re.I):
        categories.add('machine_path')
    return sorted(categories)


def publication(root, phase='release'):
    """Report outstanding distribution work separately from source integrity."""
    if phase not in ('source', 'release'):
        raise ValueError(f'Unknown publication check phase: {phase}')
    secret = re.compile(r"(?:sk-[A-Za-z0-9_-]{25,}|glpat-[A-Za-z0-9_-]{15,}|"
                        r"AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY)")
    issues = []
    text_files, binary_files = 0, 0
    for path in publication_paths(root):
        if path.is_symlink():
            issues.append({'kind': 'source_symlink', 'path': str(path.relative_to(root))})
            continue
        if not path.is_file():
            continue
        if path.suffix == '.bak':
            issues.append({'kind': 'retired_backup', 'path': str(path.relative_to(root))})
        if path.suffix.lower() == '.key':
            issues.append({'kind': 'possible_credential_file', 'path': str(path.relative_to(root))})
        if legacy_name_lines(str(path.relative_to(root))):
            issues.append({'kind': 'legacy_project_path', 'path': str(path.relative_to(root))})
        path_categories = internal_reference_categories(str(path.relative_to(root)))
        if path_categories:
            issues.append({'kind': 'internal_reference_path', 'path': str(path.relative_to(root)),
                           'categories': path_categories})
        content = publication_text(path)
        if content is None:
            binary_files += 1
            continue
        text_files += 1
        old_names = legacy_name_lines(content)
        if old_names:
            issues.append({'kind': 'legacy_project_name', 'path': str(path.relative_to(root)),
                           'line_numbers': old_names})
        if secret.search(content):
            issues.append({'kind': 'possible_credential', 'path': str(path.relative_to(root)),
                           'line_numbers': [i for i, line in enumerate(content.splitlines(), 1)
                                            if secret.search(line)]})
        categories = internal_reference_categories(content)
        if categories:
            issues.append({'kind': 'internal_reference', 'path': str(path.relative_to(root)),
                           'categories': categories,
                           'line_numbers': [i for i, line in enumerate(content.splitlines(), 1)
                                            if internal_reference_categories(line)]})
    images = [r for r in load(root / 'assets/images.json')['images']
              if r.get('type') != 'historical_reference']
    public_candidates = [r for r in images if r.get('public_upload_allowed', False)]
    pending_images = sum(not r.get('public_pull_verified', False) for r in public_candidates)
    missing = [r["path"] for r in load(root / "assets/files.json")["files"]
               if not within(root, r["path"]).is_file()]
    # Public runtime images are optional for source-based installations. Only
    # products selecting a published image need anonymous distribution evidence.
    required_published = [r for r in images
                          if r.get('acquisition', {}).get('preferred') == 'public_image'
                          or ((r.get('public_image') or r.get('replacement'))
                              and not r.get('acquisition', {}).get('preferred') == 'local_build')]
    pending_required = [r['id'] for r in required_published
                        if not r.get('public_pull_verified', False)]
    if phase == 'release' and pending_required:
        issues.append({'kind': 'required_public_images_pending', 'count': len(pending_required),
                       'products': pending_required})
    undecided_rows = [r for r in load(root/'assets/files.json')['files']
                      if r.get('distribution', 'unresolved') == 'unresolved']
    bundled_undecided = [r['path'] for r in undecided_rows if r.get('status') != 'source_omitted']
    external_undecided = [r['path'] for r in undecided_rows if r.get('status') == 'source_omitted']
    if bundled_undecided:
        issues.append({'kind': 'distribution_terms_unresolved', 'count': len(bundled_undecided)})
    if phase == 'release' and external_undecided:
        issues.append({'kind': 'external_input_delivery_pending', 'count': len(external_undecided)})
    try:
        decisions = load(root / 'docs/licenses/third-party/distribution-decisions.json')
    except (OSError, ValueError):
        decisions = None
    if not isinstance(decisions, dict):
        issues.append({'kind': 'distribution_decisions_invalid'})
    # Per-file exclusions are enforced by the exporter; global review flags
    # remain historical metadata and cannot authorize any bytes by themselves.
    pending = [{"task": r["id"], "variant": name, "status": v["readiness"]}
               for r in load(root / "suites/tasks.json")["tasks"]
               for name, v in r["variants"].items() if v["readiness"] != "ready"]
    # User-provided online backends are an integration dependency, not a
    # requirement for this project to deploy a hosted public judging service.
    runtime_pending = [r for r in pending if r['status'] != 'user_backend_required']
    if phase == 'release' and runtime_pending:
        issues.append({'kind': 'runtime_acceptance_pending', 'count': len(runtime_pending)})
    try:
        integrity = validate(root)
    except (ValueError, KeyError, OSError) as exc:
        integrity = {'static_integrity': 'failed', 'reason': str(exc)}
        issues.append({'kind': 'source_integrity', 'reason': str(exc)})
    prepared = sum(bool(r.get('product_prepared') and r.get('image_digest')) for r in images)
    return {"ready_for_publication": not issues, "issues": issues,
            'check_phase': phase, 'source_integrity': integrity,
            'image_products': {'prepared': prepared, 'recorded': len(images)},
            'public_images': {'verified': len(public_candidates)-pending_images, 'pending': pending_images,
                              'local_or_unresolved_distribution': len(images)-len(public_candidates)},
            'omitted_source_files': {'count': len(missing), 'independent_downloads_required': False},
            'external_input_delivery': {'pending': len(external_undecided),
                                        'blocks_source_only_export': False},
            'distribution_review': ({key: decisions.get(key) for key in
                                    ('integration_complete', 'enforced_by_exporter')}
                                   if isinstance(decisions, dict) else None),
            'user_backend_requirements': [r for r in pending if r['variant'] == 'online'],
            'runtime_validation': {'complete': not runtime_pending, 'pending': runtime_pending,
                                   'note': 'Unverified task variants retain their recorded status; representative validation does not establish all-task acceptance.'},
            'source_scan': {'text_files': text_files, 'binary_files_skipped': binary_files,
                            'scope': 'Tracked and unignored release files, or recursive source files in an exported checkout; no filename suffix filter.'},
            "note": "Results and trajectories are outside the first-release scope."}
