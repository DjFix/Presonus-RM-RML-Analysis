#!/usr/bin/env python3
"""Finalize exact admitted SQLite packet assignments and append proof history."""
import argparse
from contextlib import closing
import json
from pathlib import Path

from sqlite_packet import ROOT, adapter, catalog, connection, digest, inside, load, require


def receipt_ref(root, path):
    return {'path': path.relative_to(root).as_posix(), 'sha256': digest(path)}


def finalize(root, packet_dir, admission_path, db_path, affected, apply=False):
    packet_path = packet_dir / 'PACKET.json'
    index = load(packet_path)
    dispatch_path = packet_dir / 'DISPATCH.json'
    dispatch = load(dispatch_path)
    require(index['mode'] == dispatch['mode'] == 'canonical_sqlite_only'
            and dispatch['publication_state'] == 'complete'
            and dispatch['packet_sha256'] == digest(packet_path)
            and Path(index['database']) == db_path,
            'Different or incomplete canonical SQLite dispatch')
    assignment_path = packet_dir / 'ASSIGNMENT_REQUEST.json'
    assignment_ref = receipt_ref(root, assignment_path)
    assignment = load(assignment_path)
    require(assignment['request_id'] == 'sqlite-packet:' + dispatch['packet_sha256'],
            'Published assignment request differs')
    operations = {row['anchor']: row for row in assignment['operations']}
    require(len(operations) == len(assignment['operations']) == dispatch['assigned_originals'],
            'Assignment counts differ')
    admission_ref = receipt_ref(root, admission_path)
    dispatch_ref = receipt_ref(root, dispatch_path)
    receipt = load(admission_path)
    require(not receipt.get('validated_only', False), 'Guarded live readiness receipt required')
    commit = receipt['sqlite_commit']
    require(Path(commit['database']) == db_path and commit['changed'] > 0
            and not commit.get('no_op'), 'Exact guarded SQLite admission required')

    originals = {}
    verified_paths = [(packet_path, dispatch['packet_sha256']),
                      (assignment_path, assignment_ref['sha256'])]
    for name in affected:
        require(name in index['tasks'], 'Unknown dispatched task: ' + name)
        context = packet_dir / 'tasks' / name / 'CONTEXT.json'
        require(digest(context) == index['tasks'][name], 'Task context changed: ' + name)
        verified_paths.append((context, index['tasks'][name]))
        data = load(context)
        for row in data['originals']:
            target = row['original']
            anchor = target['anchor']
            require(anchor not in originals, 'Duplicate original: ' + anchor)
            assignment_op = operations[anchor]
            require((assignment_op['state'], assignment_op['owner'], assignment_op['batch'],
                     assignment_op['expected_revision'])
                    == ('assigned', data['owner'], index['batch'], row['catalog_revision']),
                    'Assignment differs from sealed task: ' + anchor)
            originals[anchor] = (target, data, assignment_op)
    require(originals, 'At least one complete dispatched task is required')
    request_id = 'sqlite-admission:' + admission_ref['sha256'] + ':' + dispatch['packet_sha256']
    request_id += ':' + '#'.join(sorted(affected))
    readback = []
    proof_paths = list(verified_paths)

    def admission_guard(db):
        require(adapter.generation_guard(db) == commit['guard'],
                'Canonical registry changed since guarded readiness receipt')
        require(db.execute('SELECT 1 FROM requests WHERE request_id=?',
                           (commit['request_id'],)).fetchone(), 'Readiness request absent')
        require(digest(admission_path) == admission_ref['sha256']
                and digest(dispatch_path) == dispatch_ref['sha256'], 'Admission or dispatch receipt changed')
        require(all(digest(path) == expected for path, expected in proof_paths),
                'Bound packet evidence or admission proof changed')

    request = {'request_id': request_id, 'actor': 'sqlite-only-recovery-integrator', 'operations': []}
    with closing(connection(db_path)) as db:
        admission_guard(db)
        for anchor, (target, data, operation) in sorted(originals.items()):
            identity = (target['elf'], target['mangled'])
            bound = db.execute('SELECT elf,mangled,role,firmware,address,size,section_json '
                               'FROM catalog_symbols WHERE anchor=?', (anchor,)).fetchone()
            require(bound and tuple(bound) == (*identity, target['role'], target['firmware'],
                    target['address'], target['size'], json.dumps(target['section'])),
                    'Catalog original drift: ' + anchor)
            assigned = db.execute('SELECT previous_revision,new_revision,new_state FROM catalog_journal '
                                  'WHERE request_id=? AND anchor=?',
                                  (assignment['request_id'], anchor)).fetchone()
            require(assigned is not None and assigned['previous_revision'] == operation['expected_revision']
                    and assigned['new_revision'] == operation['expected_revision'] + 1,
                    'Original assignment journal missing: ' + anchor)
            assignment_state = json.loads(assigned['new_state'])
            require(tuple(assignment_state[key] for key in ('state', 'owner', 'batch'))
                    == ('assigned', data['owner'], index['batch']), 'Journal assignment drift: ' + anchor)
            found = db.execute('SELECT id,status,metadata FROM records WHERE elf=? AND mangled=?',
                               identity).fetchone()
            require(found and found['status'] in ('ready', 'pending'), 'Admitted original missing: ' + anchor)
            journal = db.execute('SELECT previous_state,new_state FROM journal '
                                 'WHERE request_id=? AND record_id=?',
                                 (commit['request_id'], found['id'])).fetchone()
            require(journal and json.loads(journal['previous_state'])['classification'] is None,
                    'Original is not newly admitted by this request: ' + anchor)
            meta = json.loads(found['metadata'])
            after = json.loads(journal['new_state'])
            require(after['classification'] == found['status'] and after['record_metadata'] == meta,
                    'Journal/readback mismatch: ' + anchor)
            field = 'validation' if found['status'] == 'ready' else 'behavior_validation'
            proof = inside(root, 'uc-library/' + meta[field])
            proof_paths.append((proof, meta[field + '_sha256']))
            require(digest(proof) == proof_paths[-1][1], 'Admitted proof changed: ' + anchor)
            note = {'original_elf_sha256': identity[0], 'mangled': identity[1], 'admission': admission_ref,
                    'role': target['role'], 'original_address': target['address'], 'original_size': target['size'],
                    'section': target['section'], 'range_sha256': target['range_sha256'],
                    'classification': found['status'], 'proof': receipt_ref(root, proof),
                    'dispatch': dispatch_ref, 'domain': meta['domain'],
                    'limitations': data['task']['review']['limitations'],
                    'declaration_uncertainties': meta.get('declaration_uncertainties', [])}
            request['operations'].append({'anchor': anchor, 'expected_revision': assigned['new_revision'],
                    'state': 'done', 'owner': data['owner'], 'batch': index['batch'],
                    'reason': 'Guarded exact reconstruction admission completed',
                    'notes': assignment_state['notes'] + '\n' + json.dumps(note, sort_keys=True)})
            readback.append(note)
    result = catalog.operate(db_path, request, dry_run=not apply, preflight=admission_guard)
    require(result['operations'] == len(originals) and not result['readiness_changed'],
            'Unexpected catalog completion count')
    if apply:
        with closing(connection(db_path)) as db:
            admission_guard(db)
            for operation in request['operations']:
                row = db.execute('SELECT state,owner,batch,revision,notes FROM catalog_tasks WHERE anchor=?',
                                 (operation['anchor'],)).fetchone()
                require(tuple(row) == (operation['state'], operation['owner'], operation['batch'],
                        operation['expected_revision'] + 1, operation['notes']), 'Catalog readback mismatch')
    return {'catalog': result, 'guard': commit['guard'], 'readback': readback}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--registry-db', type=Path)
    parser.add_argument('--packet', required=True)
    parser.add_argument('--admission', required=True)
    parser.add_argument('--task', action='append', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    database = adapter.resolve_db(root / 'uc-library', args.registry_db)
    result = finalize(root, inside(root, args.packet), inside(root, args.admission), database,
                      args.task, apply=args.apply)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
