"""Validate image dependency identities and development-data separation."""
from collections import Counter


def dependencies(row):
    config = row.get('build', {})
    result = set(row.get('dependencies', []))
    result.update(config.get('image_args', {}).values())
    if config.get('kind') == 'public_image':
        result.add(config['source_product'])
    return result


def validate_graph(document):
    rows = [r for r in document['images'] if r.get('type') != 'historical_reference']
    by_id = {r['id']: r for r in rows}
    if len(by_id) != len(rows):
        raise ValueError('Duplicate product identity')
    visiting, ancestry = [], {}

    def walk(identity):
        if identity in visiting:
            raise ValueError('Product dependency cycle: ' + ' -> '.join([*visiting, identity]))
        if identity not in by_id:
            raise ValueError('Unknown product dependency: ' + identity)
        if identity in ancestry:
            return ancestry[identity]
        visiting.append(identity)
        parents = set()
        for parent in sorted(dependencies(by_id[identity])):
            parents.add(parent)
            parents.update(walk(parent))
        visiting.pop()
        ancestry[identity] = parents
        return parents

    for identity in by_id:
        walk(identity)
    public_roles = ('development', 'public_backend')
    isolated = 0
    for row in rows:
        if row.get('runtime_role') not in public_roles:
            continue
        hidden = sorted(identity for identity in ancestry[row['id']]
                        if by_id[identity].get('data_split') == 'hidden'
                        or by_id[identity].get('purpose') in ('hidden_judging', 'private_judging'))
        if hidden:
            raise ValueError(f'Public runtime {row["id"]} depends on hidden data: {", ".join(hidden)}')
        isolated += 1
    return {'products': len(rows), 'dependencies_acyclic': True,
            'public_runtime_dependencies_checked': isolated,
            'data_splits': dict(Counter(r.get('data_split', 'undeclared')
                                       for r in rows if r.get('type') == 'data')),
            'scope': 'Declared dependency graph only; image content and runtime isolation require separate acceptance.'}
