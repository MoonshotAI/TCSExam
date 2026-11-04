"""Report source, image, host, backend and runtime acceptance independently."""
import os

from .layout import load, within
from .runtime import BACKEND_KEYS, http_host
from .setup import (PIN, host_support_targets, inspect_image, inspect_tag_id, local_reference,
                    offline_host_capacity, required_image_roles, resolved_images)


def prerequisites(root, rows, args):
    from .backend_cli import client_plan
    planned_backend = client_plan(root, rows, args)
    mapping, evidence = resolved_images(root, rows, args)
    omitted = load(root / 'assets/files.json')['files']
    tasks, blockers, inspected = [], [], {}
    for row in rows:
        report = {'task': row['id'], 'path': row['path'], 'variant': row['variant'], 'checks': [],
                  'runtime_acceptance': {'status': row.get('readiness'), 'evidence': 'suites/tasks.json'}}

        def add(kind, ok, reason, detail):
            check = {'kind': kind, 'ok': bool(ok), 'reason': reason, 'evidence': detail}
            report['checks'].append(check)
            if not ok:
                blockers.append({'task': row['id'], **check})

        if not row['path']:
            add('adapter', False, 'Selected protocol has no adapter', 'suites/tasks.json')
            tasks.append(report)
            continue
        roles = mapping.get(row['path'], {})
        for role in required_image_roles(root, row):
            add('complete_' + role + '_image', bool(roles.get(role)),
                'Supply a complete image for every required container', roles.get(role))
        for role, ref in roles.items():
            product = evidence.get(ref, {})
            pinned = bool(PIN.fullmatch(ref) or local_reference(product, ref))
            add(role + '_image_reference', pinned, 'Actual execution requires a fixed image identity', ref)
            report.setdefault('image_products', {})[role] = {
                'reference': ref, 'content_evidence': product.get('verification', {}),
                'content_verified': product.get('content_verified', False),
                'startup_verified': product.get('startup_verified', False),
                'historical_layer_isolation_verified': product.get('historical_layer_isolation_verified', False),
                'public_distribution': product.get('distribution', 'user_supplied')}
            if role == 'backend' or not pinned:
                continue
            if ref not in inspected:
                inspected[ref] = inspect_image(ref, args, product)
            add(role + '_host_image', bool(inspected[ref]),
                'Image must exist on the selected execution host; use tcsexam build or setup', ref)
        report['source_rebuild'] = {
            'required_for_complete_image_run': False,
            'missing_development_inputs': [r['path'] for r in omitted
                if r['path'].startswith(row['path']+'/environment/') and not within(root,r['path']).is_file()]}
        report['reference_validation'] = {
            'required_for_normal_run': False,
            'missing_paths': [r['path'] for r in omitted
                if r['path'].startswith(row['path']+'/solution/') and not within(root,r['path']).is_file()]}
        if row['variant'] == 'online':
            backend = getattr(args, 'judge_url', None) or os.environ.get('TCSEXAM_BASE_URL')
            try:
                host = http_host(backend) if backend else None
            except ValueError:
                host = None
            missing = [k for k in BACKEND_KEYS if k != 'TCSEXAM_BASE_URL' and not os.environ.get(k)]
            if not os.environ.get('TCSEXAM_ARCHIVE_TOKEN'):
                missing.append('TCSEXAM_ARCHIVE_TOKEN (verifier only)')
            add('backend', bool(host) and not missing,
                'User supplies the backend and credentials; archive access belongs to the verifier',
                {'host': host, 'missing_variable_names': missing})
            add('backend_image', bool(roles.get('backend')),
                'Map the backend judge image to the prepared product', roles.get('backend'))
            report['backend_acceptance'] = 'user_configuration_required'
            if planned_backend:
                report['backend_resource_plan'] = planned_backend['tasks'][row['id']]
        tasks.append(report)
    host_checks = []
    try:
        support = host_support_targets(evidence, args)
    except (ValueError, ImportError) as exc:
        support = []
        check = {'kind': 'harbor_host_support', 'ok': False, 'reason': str(exc)}
        host_checks.append(check)
        blockers.append({'task': '(execution_host)', **check})
    for product in support:
        ref = product['image']
        if ref not in inspected:
            inspected[ref] = inspect_image(ref, args, product)
        local = inspected[ref]
        tag = product.get('local_tag') if product.get('support_kind') == 'harbor_egress_control' else None
        ok = bool(local) and (not tag or inspect_tag_id(tag, args) == local['id'])
        check = {'kind': 'harbor_host_support', 'ok': bool(ok), 'artifact_id': product['id'],
                 'image': ref, 'local_tag': tag,
                 'reason': 'Harbor support images and matching local helper tag must be prepared; use setup'}
        host_checks.append(check)
        if not ok:
            blockers.append({'task': '(execution_host)', **check})
    offline = [row for row in rows if row.get('path') and row['variant'] == 'offline']
    if offline and all(inspected.get(mapping.get(row['path'], {}).get('verifier')) for row in offline):
        try:
            capacity_checks = offline_host_capacity(root, rows, mapping, args)
        except ValueError as exc:
            capacity_checks = [{'task': '(execution_host)', 'kind': 'offline_host_capacity',
                                'ok': False, 'reason': str(exc)}]
        host_checks.extend(capacity_checks)
        blockers.extend(check for check in capacity_checks if not check['ok'])
    image_blockers = [r for r in blockers if r['kind'] not in ('backend', 'backend_image')]
    agent_report = None
    if hasattr(args, 'agent'):
        from .agent_config import configure_agent
        try:
            settings = configure_agent(args)
            settings.require_credentials()
            agent_report = {'ok': True, **settings.provenance}
        except ValueError as exc:
            agent_report = {'ok': False, 'reason': str(exc)}
            blockers.append({'task': '(agent)', 'kind': 'agent_configuration', **agent_report})
    return {'tasks': tasks, 'blockers': blockers, 'host_prepared': not image_blockers,
            'agent_configuration': agent_report,
            'host_support': host_checks,
            'runtime_acceptance_complete': all(r.get('runtime_acceptance', {}).get('status') == 'ready' for r in tasks),
            'ready': not blockers,
            'note': 'Host preparation, public publication and real Harbor acceptance are separate states.'}
