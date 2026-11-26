"""Count canonical package methods from exact frozen membership; never admit work."""
import argparse
import collections
import datetime
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys


def read_json(path):
    return json.loads(Path(path).read_text())


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def reference(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': digest(path)}


def validate_membership(package, membership):
    """Frozen grouping is authoritative; never regroup from friendly names."""
    expected = package['user_denominator']['components']
    if set(membership['scopes']) != set(expected):
        raise ValueError('Scope set differs from frozen package')
    if membership.get('grouping_issues') or any(membership.get('overlaps', {}).values()):
        raise ValueError('Frozen package has unresolved grouping or overlap')
    seen_methods, seen_identities, methods = set(), set(), []
    excluded = set()
    for scope, groups in membership['scopes'].items():
        if len(groups) != expected[scope]:
            raise ValueError('Method count differs for ' + scope)
        for group in groups:
            name = group['method']
            if name in seen_methods:
                raise ValueError('Duplicate method across package groups: ' + name)
            seen_methods.add(name)
            ordinary = []
            for row in group['originals']:
                elf = row.get('elf', row.get('elf_sha256'))
                key = elf, row['mangled']
                if not isinstance(elf, str) or not re.fullmatch(r'[0-9a-f]{64}', elf):
                    raise ValueError('Invalid original ELF SHA256')
                if key in seen_identities:
                    raise ValueError('Duplicate ordinary identity in membership: ' + str(key))
                if row.get('demangled', '').startswith('non-virtual thunk to '):
                    raise ValueError('Thunk incorrectly included as ordinary identity')
                seen_identities.add(key)
                ordinary.append({'elf': elf, 'mangled': key[1], 'role': row.get('role'),
                                 'task': row.get('task'), 'address': row.get('address'),
                                 'size': row.get('size'), 'range_sha256': row.get('range_sha256')})
            if not ordinary:
                raise ValueError('No ordinary identities for method ' + name)
            for row in group.get('excluded_thunk_identities', []):
                excluded.add((row.get('elf', row.get('elf_sha256')), row['mangled']))
            methods.append({'scope': scope, 'method': name, 'ordinary_identities': ordinary})
    if excluded & seen_identities:
        raise ValueError('Excluded identity also counted as ordinary')
    if len(methods) != package['user_denominator']['unique_methods']:
        raise ValueError('Package denominator differs from exact frozen grouping')
    threshold = (len(methods) * 80 + 99) // 100
    if threshold != package['user_denominator']['minimum_canonical_accepted_methods']:
        raise ValueError('Frozen eighty-percent threshold differs')
    return methods, excluded


def load_package(path, expected_package=None, expected_inventory=None):
    path = Path(path).resolve()
    inventory_path = path.with_name('INVENTORY.json')
    inventory = read_json(inventory_path)
    if expected_inventory and digest(inventory_path) != expected_inventory:
        raise ValueError('Frozen inventory SHA256 mismatch')
    if expected_package and digest(path) != expected_package:
        raise ValueError('Frozen package SHA256 mismatch')
    if inventory['files'].get(path.name) != digest(path):
        raise ValueError('Package differs from its frozen inventory')
    membership_path = path.with_name('MEMBERSHIP.json')
    if inventory['files'].get(membership_path.name) != digest(membership_path):
        raise ValueError('Membership differs from its frozen inventory')
    package = read_json(path)
    methods, excluded = validate_membership(package, read_json(membership_path))
    return package, methods, excluded, {'package': reference(path),
                                       'membership': reference(membership_path),
                                       'inventory': reference(inventory_path),
                                       'explicit_expected_package_sha256': expected_package,
                                       'explicit_expected_inventory_sha256': expected_inventory}


def snapshot_records(database, keys):
    """Only indexed identity point queries; close before any proof file reads."""
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    connection = sqlite3.connect(Path(database).resolve().as_uri() + '?mode=ro',
                                 uri=True, timeout=2, isolation_level=None)
    connection.row_factory = sqlite3.Row
    records = {}
    try:
        connection.execute('PRAGMA query_only=ON')
        connection.execute('BEGIN')
        for elf, mangled in sorted(keys):
            row = connection.execute(
                'SELECT id,status,elf,mangled,proof,metadata FROM records '
                'WHERE elf=? AND mangled=?', (elf, mangled)).fetchone()
            records[(elf, mangled)] = dict(row) if row else None
    finally:
        connection.close()
    return records, {'started_utc': start,
                     'closed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     'connection_closed': True, 'exact_identity_queries': len(keys),
                     'database': str(Path(database).resolve()),
                     'mode': 'mode=ro; query_only; short snapshot; no generation_guard broad scan'}


def tally(methods, records):
    counts = collections.defaultdict(collections.Counter)
    result = []
    for method in methods:
        observed, statuses, errors = [], [], []
        for identity in method['ordinary_identities']:
            key = identity['elf'], identity['mangled']
            record = records.get(key)
            if record:
                metadata = json.loads(record['metadata'])
                if (record['elf'], record['mangled']) != key:
                    errors.append('Record key differs from required identity')
                if metadata.get('original_elf_sha256', key[0]) != key[0] or metadata.get('mangled', key[1]) != key[1]:
                    errors.append('Record metadata identity differs from required identity')
                statuses.append(record['status'])
                observed.append({'identity': identity, 'record': record})
            else:
                observed.append({'identity': identity, 'record': None})
        admitted = not errors and len(statuses) == len(observed) and all(s in ('ready', 'pending') for s in statuses)
        category = ('ready' if all(s == 'ready' for s in statuses) else
                    'pending' if all(s == 'pending' for s in statuses) else
                    'mixed_ready_pending') if admitted else 'not_fully_admitted'
        counter = counts[method['scope']]
        for field in ('canonical_admitted', 'ready', 'pending', 'mixed_ready_pending', 'not_fully_admitted'):
            counter.setdefault(field, 0)
        counter['methods'] += 1
        counter['canonical_admitted'] += int(admitted)
        counter[category] += 1
        counter['ordinary_identities'] += len(observed)
        counter['ready_identities'] += statuses.count('ready')
        counter['pending_identities'] += statuses.count('pending')
        counter['missing_identities'] += sum(v['record'] is None for v in observed)
        result.append({**method, 'canonical_admitted': admitted, 'classification': category,
                       'identity_errors': errors, 'observations': observed})
    return {scope: dict(c) for scope, c in counts.items()}, result


def proof_observation(record, library, cache):
    """Report linked bytes only; this is not a proof-freshness validator."""
    metadata = json.loads(record['metadata'])
    path = record.get('proof') or metadata.get('validation')
    expected = metadata.get('validation_sha256')
    if not path:
        return {'path': None, 'available': False, 'freshness_checked': False}
    p = Path(path)
    p = p if p.is_absolute() else (library.parent / p if p.parts[0] == library.name else library / p)
    p = p.resolve()
    if p not in cache:
        try:
            cache[p] = {'path': str(p), 'sha256': digest(p), 'available': True}
        except OSError as error:
            cache[p] = {'path': str(p), 'available': False, 'error': str(error)}
    return {**cache[p], 'record_expected_sha256': expected,
            'matches_record_expected': cache[p].get('sha256') == expected if expected else None,
            'freshness_checked': False}


def reserve_output(path):
    """Exclusive directory reservation fails before opening the registry."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=False)
    return path


def repository_root():
    for parent in Path(__file__).resolve().parents:
        if (parent / 'uc-library/tools/registry/adapter.py').is_file():
            return parent
    raise ValueError('Cannot locate repository shared registry adapter')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True, help='New exclusive output directory')
    parser.add_argument('--package-sha256')
    parser.add_argument('--inventory-sha256')
    args = parser.parse_args(argv)
    package, methods, excluded, bindings = load_package(args.package, args.package_sha256, args.inventory_sha256)
    output = reserve_output(args.out)
    root = repository_root()
    library = root / 'uc-library'
    # Shared resolver only: adapter.snapshot() hashes the entire registry and is
    # intentionally avoided for this finite exact-target accounting operation.
    sys.path.insert(0, str(library / 'tools/registry'))
    from adapter import resolve_db
    active = library / 'validation/registry-sqlite/ACTIVE.json'
    database = resolve_db(library)
    keys = {(v['elf'], v['mangled']) for m in methods for v in m['ordinary_identities']}
    records, reader = snapshot_records(database, keys)
    counts, grouped = tally(methods, records)
    cache = {}
    for method in grouped:
        for observation in method['observations']:
            if observation['record']:
                observation['record_linked_proof'] = proof_observation(observation['record'], library, cache)
    numerator = sum(v['canonical_admitted'] for v in counts.values())
    denominator = len(methods)
    report = {'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'kind': 'exact_frozen_package_registry_membership_accounting',
              'inputs': bindings, 'active_registry_pointer': reference(active),
              'producer': reference(Path(__file__)), 'reader': reader,
              'denominator': denominator, 'required_canonical_methods': (denominator * 80 + 99) // 100,
              'canonical_admitted_methods': numerator, 'canonical_fraction': numerator / denominator,
              'registry_membership_threshold_met': numerator >= (denominator * 80 + 99) // 100,
              'scope_counts': counts, 'methods': grouped,
              'excluded_thunk_identities': [{'elf': e, 'mangled': m} for e, m in sorted(excluded)],
              'excluded_extra_selector_helper_or_reused_sender_credit': 0,
              'classification_policy': 'All ordinary role/ABI identities must exist as ready/pending. Ready-only, pending-only and mixed are reported separately; partial methods receive0credit.',
              'freshness_checked': False, 'graph_launch_authorized': False,
              'limitations': ['Record-linked proof hashes are observations, not current integration/source/native/provider gate validation.',
                             'Actual canonical proof gates and required commit remain separate Root obligations.',
                             'Local acceptance fields in frozen membership are historical and never substitute for registry admission.',
                             'No assignments, registry mutation, graph queries, graph launch or next-cycle action.']}
    with (output / 'SNAPSHOT.json').open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'out': str(output / 'SNAPSHOT.json'), 'sha256': digest(output / 'SNAPSHOT.json'),
                      'canonical_methods': numerator, 'denominator': denominator,
                      'threshold': report['required_canonical_methods'], 'connection_closed': True}))


if __name__ == '__main__':
    main()
