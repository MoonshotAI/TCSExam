"""Describe resource use and Docker build inputs without executing builds."""
from collections import Counter
import fnmatch
import json
from pathlib import Path
import re
import shlex
import tomllib

from .layout import load, within
from .oracle_answers import is_oracle_answer_path


def classification(path):
    parts = Path(path).parts
    phase = next((p for p in ('environment', 'tests', 'solution') if p in parts), None)
    purpose = {'environment': 'public_development', 'tests': 'hidden_judging',
               'solution': 'reference_validation'}.get(phase, 'build_support')
    task = parts[3] if parts[:2] == ('tasks', 'solver') else None
    evidence = 'docs/licenses/distribution.md'
    if task != 'qbf-qbfeval' and is_oracle_answer_path(path):
        return purpose, 'private_only', 'docs/licenses/third-party/distribution-decisions.json'
    if task == 'bpp-bpplib':
        return purpose, 'local_prepare', evidence
    if task in ('ce-pace2021', 'dfvs-pace2022') and '/environment/app/verifier/' in path:
        return purpose, 'local_prepare', evidence
    if task == 'ce-pace2021' and '/environment/app/instances/' in path:
        match = re.fullmatch(r'heur(\d{3})\.gr\.xz', Path(path).name)
        if match and 1 <= int(match.group(1)) <= 199 and int(match.group(1)) % 2 == 1:
            return purpose, 'redistributable', 'docs/licenses/third-party/ce-pace2021-source.json'
    if task == 'dfvs-pace2022' and '/environment/app/instances/' in path:
        match = re.fullmatch(r'e_(\d{3})\.xz', Path(path).name)
        if match and 1 <= int(match.group(1)) <= 199 and int(match.group(1)) % 2 == 1:
            return purpose, 'local_prepare', 'docs/licenses/third-party/dfvs-pace2022-source.json'
    if task == 'vc-pace2019' and '/environment/app/instances/' in path:
        match = re.fullmatch(r'vc-exact_(\d{3})\.xz', Path(path).name)
        if match and 1 <= int(match.group(1)) <= 199 and int(match.group(1)) % 2 == 1:
            return purpose, 'redistributable', 'docs/licenses/third-party/vc-pace2019-source.json'
    if (task == 'ahc058-atcoder' and purpose == 'public_development'
            and '/environment/app/instances/' in path):
        name = Path(path).name
        official = re.fullmatch(r'(\d{4})\.txt', name)
        if ((official and 0 <= int(official.group(1)) <= 99)
                or name in {'h00.txt', 'h04.txt', 'h19.txt', 'h24.txt', 'h27.txt'}):
            return purpose, 'local_prepare', 'docs/licenses/third-party/ahc058-atcoder-source.json'
    oscm_evidence = 'docs/licenses/third-party/oscm-pace2024-source.json'
    if task == 'oscm-pace2024' and purpose == 'public_development':
        if path.endswith('/environment/app/verifier/numpy-2.2.6-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl'):
            return purpose, 'local_prepare', 'docs/licenses/third-party/oscm-pace2024-development-tools-source.json'
        if path.endswith('/environment/app/testsets/LICENSE'):
            return purpose, 'local_prepare', oscm_evidence
        match = re.fullmatch(r'(\d+)\.gr', Path(path).name)
        if '/environment/app/instances/' in path and match and 1 <= int(match.group(1)) <= 100:
            return purpose, 'local_prepare', oscm_evidence
        if ('/environment/app/testsets/medium_test_set/instances/' in path and match
                and 1 <= int(match.group(1)) <= 60):
            return purpose, 'local_prepare', oscm_evidence
        tiny = {
            'complete_4_5.gr', 'cycle_8_shuffled.gr', 'cycle_8_sorted.gr',
            'grid_9_shuffled.gr', 'ladder_4_4_shuffled.gr', 'ladder_4_4_sorted.gr',
            'matching_4_4.gr', 'path_9_shuffled.gr', 'path_9_sorted.gr',
            'plane_5_6.gr', 'star_6.gr', 'tree_6_10.gr', 'website_20.gr',
        }
        if ('/environment/app/testsets/tiny_test_set/instances/' in path
                and Path(path).name in tiny):
            return purpose, 'local_prepare', oscm_evidence
    if task == 'qbf-qbfeval':
        reference_or_mapping = Path(path).name in {
            'reference.json', 'reference-hidden.json', 'reference-transformed.json',
            'anchors.json', 'manifest.json', 'mapping.json', 'transform.json'
        }
        if '/solution/' in path or reference_or_mapping:
            return purpose, 'redistributable', 'docs/licenses/third-party/distribution-decisions.json'
        if Path(path).suffix in ('.xz', '.qdimacs', '.qcnf'):
            return purpose, 'redistributable', 'docs/licenses/third-party/qbf-data-distribution-source.json'
        return purpose, 'unresolved', evidence
    if (task == 'logic-syn-iwls2023' and '/environment/app/' in path
            and (path.endswith('.truth') or path.endswith('/abc-src.tar.xz'))):
        return purpose, 'redistributable', 'docs/licenses/third-party/logic-syn-iwls2023-source.json'
    if task == 'mr-roadef2012':
        if path.endswith('.pdf'):
            return purpose, 'local_prepare', evidence
        return purpose, 'redistributable', 'docs/licenses/third-party/roadef-data-source.json'
    if task == 'maxcut-mqlib':
        if Path(path).name in ('g001642.txt', 'g002564.txt', 'g002776.txt'):
            return purpose, 'redistributable', 'docs/licenses/third-party/mqlib-family-license-review.json'
        return purpose, 'local_prepare', evidence
    if task == 'curriculum-itc2007':
        if 'comp11' in path or path.endswith('validator.cc') or '/solution/' in path:
            return purpose, 'local_prepare', evidence
        # The source record covers data, not every binary in this task.
        if Path(path).suffix in ('.ctt', '.sol'):
            return purpose, 'redistributable', 'docs/licenses/third-party/ctt-source-comparison.json'
    return purpose, 'unresolved', 'docs/licenses/third-party/distribution-decisions.json'


def docker_inputs(root):
    """Keep FROM/COPY/ADD evidence, including dynamic and multi-stage inputs."""
    omitted = {r['path'] for r in load(root / 'assets/files.json')['files']}
    result = []
    contexts = {}
    for record in load(root / 'assets/images.json')['images']:
        config = record.get('build', {})
        if config.get('dockerfile'):
            dockerfile = within(root, config['dockerfile'])
            context = within(root, config.get('context', str(Path(config['dockerfile']).parent)))
            if dockerfile in contexts and contexts[dockerfile] != context:
                raise ValueError('Conflicting build contexts for ' + config['dockerfile'])
            contexts[dockerfile] = context
    paths = set((root / 'tasks').rglob('*Dockerfile*')) | set(contexts)
    for path in sorted(paths):
        if not path.is_file():
            continue
        context = contexts.get(path, path.parent)
        text = re.sub(r'\\\n\s*', ' ', path.read_text())
        if path not in contexts and re.search(r'^# Build context: repository root\.', text, re.M):
            context = root
        for line in text.splitlines():
            match = re.match(r'^\s*(FROM|COPY|ADD)\s+(.+)', line, re.I)
            if not match:
                continue
            op, args = match[1].upper(), match[2]
            row = {'dockerfile': str(path.relative_to(root)), 'operation': op, 'expression': args}
            if op == 'FROM':
                row['dynamic'] = '$' in args
            elif '--from=' in args:
                row['stage_input'] = True
            else:
                stripped = re.sub(r'^--\S+\s+', '', args)
                values = json.loads(stripped) if stripped.startswith('[') else shlex.split(stripped)
                sources = values[:-1]
                items = []
                for source in sources:
                    rel = str(context.relative_to(root) / source).rstrip('/')
                    present = sorted(str(p.relative_to(root)) for p in ([context] if source in (".", "./") else context.glob(source))
                                     if p.exists()) if '$' not in source and not source.startswith('http') else []
                    absent = sorted(p for p in omitted if p == rel or p.startswith(rel + '/')
                                    or fnmatch.fnmatch(p, rel))
                    items.append({'source': source, 'present_paths': present,
                                  'omitted_paths': absent, 'dynamic': '$' in source,
                                  'remote': source.startswith(('http://','https://'))})
                row['inputs'] = items
            result.append(row)
    return result


def refresh(root):
    files = load(root / 'assets/files.json')
    groups = {}
    for row in files['files']:
        purpose, distribution, evidence = classification(row['path'])
        parts = Path(row['path']).parts
        task = '/'.join(parts[:4])
        group = task.replace('/', '-') + '-' + purpose + '-' + distribution
        row.update(purpose=purpose, distribution=distribution, distribution_evidence=evidence,
                   group_id=group, status='source_omitted',
                   reason='Consult build inputs and execution mode; source omission alone is not a runtime dependency')
        if row.get('data_image_id'):
            group = row['data_image_id']
            row['group_id'] = group
        item = groups.setdefault(group, {'id': group, 'purpose': purpose, 'distribution': distribution,
                                        'evidence': evidence, 'files': 0, 'bytes': 0})
        item['files'] += 1
        item['bytes'] += row['bytes']
    files['schema_version'] = 2
    files['description'] = 'Omitted source files, with independent use and distribution classifications. Run dependencies depend on the selected build or prebuilt-image path.'
    (root / 'assets/files.json').write_text(json.dumps(files,ensure_ascii=False,indent=2)+'\n')
    (root / 'assets/resource-groups.json').write_text(json.dumps({'groups':list(groups.values())},indent=2)+'\n')
    (root / 'assets/build-inputs.json').write_text(json.dumps({'docker_inputs':docker_inputs(root)},indent=2)+'\n')
    return {'resource_groups':len(groups),'build_instructions':len(docker_inputs(root)),
            'distribution':dict(Counter(r['distribution'] for r in files['files']))}
