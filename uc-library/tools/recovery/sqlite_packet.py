#!/usr/bin/env python3
"""Prepare and issue recovery task packets from the canonical SQLite catalog."""
import argparse
from contextlib import closing, contextmanager
import fcntl
import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3
import sys

from elftools.elf.elffile import ELFFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'registry'))
import adapter
import catalog

ROOT = Path(__file__).resolve().parents[3]
NAME = re.compile(r'[a-z][a-z0-9_]{0,63}\Z')
HEX = re.compile(r'[a-f0-9]{64}\Z')
OWNED = ('uc-library/src/', 'uc-library/include/', 'uc-library/tests/', 'uc-library/candidates/')
SOURCE = OWNED[:2]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def load(path):
    return json.loads(path.read_text())


def write(path, data):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write('\n')


def inside(root, name):
    require(isinstance(name, str), 'A repository-relative path is required')
    relative = Path(name)
    result = (root / relative).resolve()
    require(name == relative.as_posix() and not relative.is_absolute() and '..' not in relative.parts
            and result.is_relative_to(root), 'Invalid repository path: ' + name)
    return result


def reference(root, item):
    path = inside(root, item['path'])
    require(HEX.fullmatch(item['sha256']) and path.is_file() and digest(path) == item['sha256'],
            'Missing or changed evidence: ' + item['path'])
    return item['path'], item['sha256']


def connection(path):
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    db.execute('BEGIN')
    return db


def custody(root, descriptor):
    data = load(inside(root, reference(root, descriptor)[0]))
    require(data['version'] == 1 and data['authority'].strip(), 'Attributed exact custody required')
    by_anchor, reads, writes = {}, set(), set()
    for row in data['records']:
        anchor = row['anchor']
        require(HEX.fullmatch(anchor) and anchor not in by_anchor
                and row['disposition'] in ('available', 'retained', 'unresolved'),
                'Duplicate or invalid custody anchor')
        require(row['evidence'], 'Custody requires exact receipt evidence')
        for item in row['evidence']:
            reference(root, item)
        if row['disposition'] == 'retained':
            for key, paths in [('owned_files', writes), ('read_files', reads)]:
                for path in row.get(key, []):
                    inside(root, path)
                    paths.add(path)
        by_anchor[anchor] = row
    return by_anchor, reads, writes


def catalog_target(db, expected, custody_rows, assigned=None):
    anchor = expected['anchor']
    row = db.execute('''SELECT s.*,t.revision,t.state,t.owner,t.batch,t.notes
                        FROM catalog_symbols s JOIN catalog_tasks t USING(anchor)
                        WHERE s.anchor=?''', (anchor,)).fetchone()
    require(row is not None, 'No canonical catalog anchor: ' + anchor)
    row = dict(row)
    for key in ('elf', 'mangled', 'role', 'firmware', 'address', 'size', 'section'):
        actual = json.loads(row['section_json']) if key == 'section' else row[key]
        require(actual == expected[key], f'Canonical {key} differs for {anchor}')
    require(row['kind'] == 'STT_FUNC' and row['policy'] == 'application-or-other'
            and row['size'] > 0 and isinstance(expected['section'], int),
            'Application-owned, defined nonempty function required: ' + anchor)
    prior = custody_rows.get(anchor)
    if prior:
        require(all(prior[k] == row[k] for k in ('elf', 'mangled')), 'Historical custody identity mismatch: ' + anchor)
        require(prior['disposition'] != 'retained', 'Historically retained original: ' + anchor)
    if assigned is None:
        require(row['state'] == 'todo' and row['owner'] is None, 'Target unavailable: ' + anchor)
    else:
        batch, owner, revision = assigned
        require((row['state'], row['batch'], row['owner'], row['revision'])
                == ('assigned', batch, owner, revision), 'Assignment drift: ' + anchor)
    require(not db.execute('SELECT 1 FROM records WHERE elf=? AND mangled=?',
                           (row['elf'], row['mangled'])).fetchone(), 'Existing result requires a separate audit: ' + anchor)
    history = [
        dict(item) for item in db.execute('''SELECT request_id,actor,timestamp,reason,
                previous_revision,new_revision,previous_state,new_state
                FROM catalog_journal WHERE anchor=? ORDER BY sequence''', (anchor,))
    ]
    return row, history


def native_range(root, target, source, verified_elfs):
    path = inside(root, source)
    if source not in verified_elfs:
        verified_elfs[source] = digest(path)
    require(verified_elfs[source] == target['elf'], 'Original ELF SHA-256 mismatch')
    with path.open('rb') as stream:
        elf = ELFFile(stream)
        section = elf.get_section(target['section'])
        require(elf.little_endian and elf['e_machine'] == 'EM_ARM' and elf.elfclass == 32,
                'Expected original little-endian ARM32 ELF')
        require(section['sh_type'] == 'SHT_PROGBITS' and section['sh_flags'] & 4,
                'Original section must be executable and file-backed')
        symtab = elf.get_section_by_name('.symtab')
        require(symtab is not None, 'Original exact ELF symbol table absent')
        matches = [sym for sym in symtab.get_symbol_by_name(target['mangled']) or ()
                   if (sym['st_value'], sym['st_size'], sym['st_shndx'])
                   == (target['address'], target['size'], target['section'])
                   and sym['st_info']['type'] == 'STT_FUNC']
        require(len(matches) == 1, 'Exact original symbol/range does not identify one row')
        relative = (target['address'] & ~1) - section['sh_addr']
        require(0 <= relative <= relative + target['size'] <= section['sh_size'],
                'Original range exceeds section')
        offset = section['sh_offset'] + relative
        stream.seek(offset)
        body = stream.read(target['size'])
    require(len(body) == target['size']
            and hashlib.sha256(body).hexdigest() == target['range_sha256'],
            'Original native range hash mismatch')
    return {**target, 'elf_path': source, 'section_name': section.name, 'file_offset': offset,
            'architecture': 'thumb' if target['address'] & 1 else 'arm', 'range_hex': body.hex()}


def owner_scope(root, task, verified):
    require(NAME.fullmatch(task['id']) and task['namespace'].strip()
            and task['objective'].strip(), 'Explicit task identity, namespace and objective required')
    require(task['mode'] in ('reconstruct', 'research'), 'Expected reconstruction or bounded research')
    paths = task['owned_files']
    require(len(set(paths)) == len(paths) and all(path.startswith(OWNED) for path in paths),
            'Unsafe shared file or duplicate ownership')
    for path in paths:
        inside(root, path)
    if task['mode'] == 'reconstruct':
        require(any(path.startswith(SOURCE) for path in paths), 'Reconstruction needs a production owner')
    else:
        require(not any(path.startswith(SOURCE) for path in paths), 'Research cannot own production files')
    review = task['review']
    require(review['reviewer'].strip() and review['domain'].strip() and review['oracle_plan'].strip()
            and review['limitations'], 'Attributed bounded contract and independent replay plan required')
    require(task['sources'] and review['evidence'], 'Explicit current source and exact review evidence required')
    providers = review['providers']
    required_providers = set(review['required_provider_paths'])
    require(isinstance(providers, list) and isinstance(review['required_provider_paths'], list)
            and len(required_providers) == len(review['required_provider_paths']),
            'Reviewed provider requirements must be explicit')
    provider_refs = dict(reference(root, item) for item in providers)
    require(set(provider_refs) == required_providers and len(provider_refs) == len(providers),
            'Missing, duplicate or unreviewed provider binding')
    require(required_providers or review.get('provider_free_reason'), 'Need a specific provider-free boundary reason')
    refs = dict(reference(root, item) for item in review['evidence'])
    for path, value in provider_refs.items():
        require(path in task['sources'] and task['sources'][path] == value,
                'Required provider must be pinned in the exact source reads: ' + path)
        require(path not in refs or refs[path] == value, 'Reviewed provider hash disagrees')
        refs[path] = value
    for path, sha in task['sources'].items():
        name, value = reference(root, {'path': path, 'sha256': sha})
        require(name not in refs or refs[name] == value, 'Evidence source hash disagrees')
        refs[name] = value
    require(all(not inside(root, path).is_file() or path in refs for path in paths),
            'Existing owned files require a direct baseline hash')
    for path, value in refs.items():
        require(path not in verified or verified[path] == value, 'Batch read hashes disagree')
        verified[path] = value
    return set(paths), set(refs)


def verify_collisions(scopes, retained_reads, retained_writes):
    names = list(scopes)
    for index, owner in enumerate(names):
        writes, reads = scopes[owner]
        conflict = (writes & (retained_reads | retained_writes)) | (reads & retained_writes)
        require(not conflict, f'{owner} overlaps retained scope: {sorted(conflict)}')
        for other in names[index + 1:]:
            other_writes, other_reads = scopes[other]
            conflict = (writes & (other_reads | other_writes)) | (reads & other_writes)
            require(not conflict, f'{owner} and {other} overlap: {sorted(conflict)}')


def catalog_scopes(root, db, excluded_packet_sha256=None):
    reads, writes = set(), set()
    for row in db.execute("SELECT batch,notes FROM catalog_tasks WHERE state IN ('assigned','in_progress')"):
        try:
            note = json.loads(row['notes'])
        except (ValueError, TypeError):
            continue
        if not isinstance(note, dict) or note.get('format') != 'sqlite_recovery_assignment_v1':
            continue
        if excluded_packet_sha256 and note.get('packet_sha256') == excluded_packet_sha256:
            continue
        for key, paths in [('owned_files', writes), ('read_files', reads)]:
            for path in note.get(key, ()):
                inside(root, path)
                paths.add(path)
    return reads, writes


@contextmanager
def assignment_lease(root):
    path = root / 'temp/recovery-work/sqlite-catalog-assignment.lock'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def reserve_history(root, custody_path, db_path, apply=False):
    with assignment_lease(root):
        return reserve_history_locked(root, custody_path, db_path, apply)


def reserve_history_locked(root, custody_path, db_path, apply):
    desc = {'path': str(custody_path.relative_to(root)), 'sha256': digest(custody_path)}
    dispositions, _, _ = custody(root, desc)
    request_id = 'sqlite-legacy-hold:' + desc['sha256']
    payload = {'request_id': request_id, 'actor': 'sqlite-only-historical-custody', 'operations': []}
    with closing(connection(db_path)) as db:
        previous = db.execute('SELECT result FROM catalog_requests WHERE request_id=?', (request_id,)).fetchone()
        if previous:
            return {**json.loads(previous['result']), 'idempotent_replay': True}
        for anchor, item in sorted(dispositions.items()):
            if item['disposition'] != 'retained':
                continue
            row = db.execute('''SELECT s.elf,s.mangled,t.*
                FROM catalog_tasks t JOIN catalog_symbols s USING(anchor) WHERE anchor=?''', (anchor,)).fetchone()
            require(row and all(row[key] == item[key] for key in ('elf', 'mangled')),
                    'Historical reservation canonical identity differs: ' + anchor)
            if row['state'] != 'todo':
                continue
            note = {'format': 'sqlite_recovery_assignment_v1', 'kind': 'verified_legacy_hold',
                    'receipt': desc, 'historical_assignments': item.get('historical_assignments', []),
                    'historical_claim': item.get('claim'), 'historical_work': item.get('work_item'),
                    'prior_owner': row['owner'], 'prior_batch': row['batch'],
                    'read_files': item.get('read_files', []), 'owned_files': item.get('owned_files', []),
                    'prior_notes': row['notes']}
            payload['operations'].append({'anchor': anchor, 'expected_revision': row['revision'],
                'state': 'assigned', 'owner': row['owner'] or 'retained_legacy_scope', 'batch': 'sqlite_legacy_holds',
                'reason': 'Verified historical reservation from ' + desc['sha256'],
                'notes': encoded(note).decode()})
    if not payload['operations']:
        return {'request_id': request_id, 'operations': 0, 'dry_run': not apply, 'readiness_changed': False}
    return catalog.operate(db_path, payload, dry_run=not apply)


def prepare(root, plan_path, out, db_path):
    plan = load(plan_path)
    require(plan['version'] == 1 and NAME.fullmatch(plan['batch']), 'Versioned batch name required')
    by_anchor, retained_reads, retained_writes = custody(root, plan['custody']) if plan.get('custody') else ({}, set(), set())
    tasks = plan['tasks']
    groups = plan['groups']
    require(0 < len(groups) <= 10 and 0 < len(tasks) <= 100, 'Expected one to ten owner groups')
    task_groups, scopes, workspace_paths = {}, {}, set()
    for group in groups:
        name = group['owner']
        require(NAME.fullmatch(name) and name not in scopes, 'Distinct owner names required')
        workspace = inside(root, group['workspace'])
        require(workspace.is_dir() and (workspace / '.git').exists() and workspace != root and workspace not in workspace_paths,
                'Existing distinct physical checkout required')
        workspace_paths.add(workspace)
        owners = group['tasks']
        require(0 < len(owners) <= 10 and not (set(owners) & set(task_groups)),
                'One ordered owner, one to ten tasks')
        for ident in owners:
            task_groups[ident] = group
        scopes[name] = set(), set()
    require({t['id'] for t in tasks} == set(task_groups) and len(tasks) == len(task_groups),
            'Task and owner coverage differ')
    copies, raw_elfs, targets, prepared = {}, {}, set(), {}
    original_producers = {}
    with closing(connection(db_path)) as db:
        active_reads, active_writes = catalog_scopes(root, db)
        retained_reads.update(active_reads)
        retained_writes.update(active_writes)
        for task in tasks:
            name = task['id']
            owner = task_groups[name]['owner']
            write_paths, read_paths = owner_scope(root, task, copies)
            scopes[owner][0].update(write_paths)
            scopes[owner][1].update(read_paths)
            originals = task['originals']
            require(originals and len({t['mangled'] for t in originals}) == 1,
                    'Each task must model exactly one source interface and its reviewed exact originals')
            if len(originals) > 1:
                require(task['review'].get('equivalence'), 'Multi-role work requires explicit reviewed equivalence')
                path, sha = reference(root, task['review']['equivalence'])
                copies[path] = sha
                read_paths.add(path)
                scopes[owner][1].add(path)
            boundaries = []
            for target in originals:
                key = target['elf'], target['mangled']
                require(key not in targets,
                        'Duplicate exact original')
                previous = original_producers.setdefault(target['mangled'], name)
                require(previous == name, 'One source producer per mangled interface')
                targets.add(key)
                row, history = catalog_target(db, target, by_anchor)
                require(row['demangled'].startswith(task['namespace'] + '::'),
                        'Original namespace differs from owned scope')
                if row['notes'] or history:
                    require(task['review'].get('historical_notes_reviewed'), 'Prior notes require explicit review')
                native = native_range(root, target, plan['elfs'][target['elf']], raw_elfs)
                boundaries.append({'original': native, 'catalog_revision': row['revision'],
                                   'history': history, 'notes': row['notes']})
            prepared[name] = {'task': task, 'owner': owner, 'originals': boundaries,
                              'read_files': sorted(read_paths), 'write_files': sorted(write_paths)}
    verify_collisions(scopes, retained_reads, retained_writes)
    bytes_to_copy = 0
    for path in copies:
        source = inside(root, path)
        with source.open('rb') as stream:
            magic = stream.read(16)
        require(not magic.startswith((b'\x7fELF', b'SQLite format 3\x00')),
                'Reference full binaries/databases outside the scoped source snapshot')
        bytes_to_copy += source.stat().st_size
    require(bytes_to_copy <= 64 * 1024**2, 'Scoped source snapshot exceeds 64 MiB')
    out.mkdir(parents=True, exist_ok=False)
    for path, expected in sorted(copies.items()):
        snapshot = out / 'inputs' / path
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(inside(root, path), snapshot)
        require(digest(snapshot) == expected and digest(inside(root, path)) == expected,
                'File changed during scoped capture: ' + path)
    for name, packet in prepared.items():
        folder = out / 'tasks' / name
        folder.mkdir(parents=True)
        write(folder / 'CONTEXT.json', packet)
        (folder / 'TASK.md').write_text(
            f"# {name}\n\n{packet['task']['objective']}\n\n"
            f"{packet['task']['review']['domain']}\n\n"
            f"{packet['task']['review']['oracle_plan']}\n", encoding='utf-8')
    index = {'version': 1, 'mode': 'canonical_sqlite_only', 'batch': plan['batch'],
             'plan': {'path': str(plan_path.relative_to(root)), 'sha256': digest(plan_path)},
             'database': str(db_path), 'custody': plan.get('custody'), 'groups': groups, 'sources': copies,
             'elfs': raw_elfs, 'tasks': {n: digest(out / 'tasks' / n / 'CONTEXT.json') for n in prepared},
             'task_docs': {n: digest(out / 'tasks' / n / 'TASK.md') for n in prepared}}
    write(out / 'PACKET.json', index)
    return index


def verify_workspace(root, workspace, packet):
    require(workspace.is_dir() and (workspace / '.git').exists(), 'Physical checkout unavailable')
    for path, expected in packet['task']['sources'].items():
        if not path.startswith(('uc-library/', 'third_party/')):
            continue
        candidate = inside(workspace, path)
        require(candidate.is_file() and digest(candidate) == expected,
                'Physical checkout input differs: ' + str(candidate))
    for path in packet['write_files']:
        if path not in packet['task']['sources']:
            candidate = inside(workspace, path)
            baseline = inside(root, path)
            require(not candidate.exists() and not baseline.exists(),
                    'New output path already exists: ' + path)


def bind_worker_packet(root, out, group, task, expected):
    workspace = inside(root, group['workspace'])
    target = workspace / 'temp/recovery-work/sqlite-issued' / out.name / task
    require(target.resolve().is_relative_to(workspace), 'Physical packet path escapes checkout')
    target.mkdir(parents=True, exist_ok=True)
    for name in ('CONTEXT.json', 'TASK.md'):
        source = out / 'tasks' / task / name
        dest = target / name
        if not dest.exists():
            with dest.open('xb') as stream:
                stream.write(source.read_bytes())
        require(digest(dest) == digest(source), 'Physical packet changed: ' + str(dest))
    context = target / 'CONTEXT.json'
    require(digest(context) == expected, 'Physical packet identity differs')
    return str(context.relative_to(workspace))


def dispatch(root, out, db_path):
    with assignment_lease(root):
        return dispatch_locked(root, out, db_path)


def dispatch_locked(root, out, db_path):
    packet_path = out / 'PACKET.json'
    index = load(packet_path)
    require(index['mode'] == 'canonical_sqlite_only' and index['database'] == str(db_path),
            'Canonical catalog path changed')
    reference(root, index['plan'])
    by_anchor, legacy_reads, legacy_writes = custody(root, index['custody']) if index['custody'] else ({}, set(), set())
    packet_hash = digest(packet_path)
    request = {'request_id': 'sqlite-packet:' + packet_hash, 'actor': 'sqlite-only-recovery-operator',
               'operations': []}
    contexts = {}
    for task, expected in index['tasks'].items():
        path = out / 'tasks' / task / 'CONTEXT.json'
        require(digest(path) == expected and digest(path.with_name('TASK.md')) == index['task_docs'][task],
                'Scoped task packet changed')
        contexts[task] = load(path)

    def check_files():
        for path, value in index['sources'].items():
            require(digest(out / 'inputs' / path) == value and digest(inside(root, path)) == value,
                    'Current source or immutable copy changed: ' + path)
        for path, value in index['elfs'].items():
            reference(root, {'path': path, 'sha256': value})

    check_files()
    for group in index['groups']:
        for task in group['tasks']:
            verify_workspace(root, inside(root, group['workspace']), contexts[task])
    with closing(connection(db_path)) as db:
        previous = db.execute('SELECT 1 FROM catalog_requests WHERE request_id=?',
                              (request['request_id'],)).fetchone()
        active_reads, active_writes = catalog_scopes(root, db, packet_hash if previous else None)
        scopes = {g['owner']: (set(), set()) for g in index['groups']}
        for value in contexts.values():
            owner = value['owner']
            scopes[owner][0].update(value['write_files'])
            scopes[owner][1].update(value['read_files'])
            for row in value['originals']:
                target, revision = row['original'], row['catalog_revision']
                assigned = (index['batch'], owner, revision + 1) if previous else None
                live, _ = catalog_target(db, target, by_anchor, assigned)
                require(live['revision'] == revision + bool(previous), 'Task revision changed')
                note = {'format': 'sqlite_recovery_assignment_v1', 'kind': 'recovery_packet',
                        'packet_sha256': packet_hash, 'read_files': value['read_files'],
                        'owned_files': value['write_files'], 'prior_notes': row['notes']}
                request['operations'].append({'anchor': target['anchor'], 'expected_revision': revision,
                    'state': 'assigned', 'owner': owner, 'batch': index['batch'],
                    'reason': 'Exact canonical SQLite recovery assignment from ' + packet_hash,
                    'notes': encoded(note).decode()})
        verify_collisions(scopes, legacy_reads | active_reads, legacy_writes | active_writes)

    existing = out / 'ASSIGNMENT_REQUEST.json'
    if existing.is_file():
        require(load(existing) == request, 'Prior assignment request differs')
    else:
        write(existing, request)
    result = catalog.operate(db_path, request, dry_run=False)
    require(result['operations'] == len(request['operations']) and not result['readiness_changed'],
            'Unexpected assignment receipt')
    check_files()
    with closing(connection(db_path)) as db:
        for value in contexts.values():
            for row in value['originals']:
                catalog_target(db, row['original'], by_anchor,
                               (index['batch'], value['owner'], row['catalog_revision'] + 1))

    workers = []
    for group in index['groups']:
        owner = group['owner']
        paths = [bind_worker_packet(root, out, group, name, index['tasks'][name]) for name in group['tasks']]
        message = (
            'Work only in the assigned physical checkout ' + str(inside(root, group['workspace'])) + '. '
            'Read local AGENTS.md and each exact packet before editing. Resolve remaining dependencies from current code. '
            'Use the verified original ELF ranges for the independent native oracle and the pinned provider implementations. '
            'Respect exact owned files. Root owns CMake, canonical integration and SQLite readiness. '
            'Do not start another agent or use graph tooling. Run Linux format, compile, symbol and native/portable replay checks '
            'and deliver one hash-bound HANDOFF v1 per exact reconstruction packet. Research tasks report evidence without an implementation handoff. '
            f'Canonical immutable input evidence remains in {out}. Exact ordered checkout-relative context files and SHA-256 values:\n'
            + '\n'.join(f"{path} {index['tasks'][name]}" for name, path in zip(group['tasks'], paths, strict=True))
        )
        workers.append({'owner': owner, 'packets': paths, 'arguments': {'task_name': owner,
                        'model': 'gpt-6.2-sol', 'fork_turns': 'none', 'message': message}})
    receipt = {'version': 1, 'mode': index['mode'], 'publication_state': 'complete',
               'packet_sha256': packet_hash, 'assigned_originals': len(request['operations']), 'workers': workers}
    dispatch_path = out / 'DISPATCH.json'
    if dispatch_path.is_file():
        require(load(dispatch_path) == receipt, 'Existing dispatch differs')
    else:
        write(dispatch_path, receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--registry-db', type=Path)
    commands = parser.add_subparsers(dest='action', required=True)
    prep = commands.add_parser('prepare')
    prep.add_argument('--plan', required=True)
    prep.add_argument('--out', required=True)
    issue = commands.add_parser('dispatch')
    issue.add_argument('--packet', required=True)
    migrate = commands.add_parser('reserve-history')
    migrate.add_argument('--custody', required=True)
    migrate.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    db = adapter.resolve_db(root / 'uc-library', args.registry_db)
    if args.action == 'prepare':
        out = inside(root, args.out)
        require(out.is_relative_to(root / 'temp/recovery-work'), 'Use scoped recovery work output')
        result = prepare(root, inside(root, args.plan), out, db)
        print(json.dumps({'prepared_tasks': len(result['tasks']), 'output': str(out)}))
    elif args.action == 'reserve-history':
        print(json.dumps(reserve_history(root, inside(root, args.custody), db, args.apply)))
    else:
        result = dispatch(root, inside(root, args.packet), db)
        print(json.dumps({'publication_state': result['publication_state'],
                          'assigned_originals': result['assigned_originals'], 'workers': len(result['workers'])}))


if __name__ == '__main__':
    main()
