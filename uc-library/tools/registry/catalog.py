#!/usr/bin/env python3
"""Original symbol catalog and independent audited task metadata. No readiness writes."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
import time
import registry as reg
import orm
import schema
import catalog_models as models
from sqlalchemy import update

SCHEMA = '''
CREATE TABLE catalog_info(version INTEGER NOT NULL, imported_at TEXT NOT NULL);
CREATE TABLE catalog_inputs(path TEXT PRIMARY KEY, sha256 TEXT NOT NULL, metadata TEXT NOT NULL);
CREATE TABLE catalog_symbols(anchor TEXT PRIMARY KEY, elf TEXT NOT NULL, role TEXT NOT NULL, firmware TEXT NOT NULL, mangled TEXT NOT NULL, demangled TEXT NOT NULL, address INTEGER NOT NULL, size INTEGER NOT NULL, section_json TEXT NOT NULL, kind TEXT NOT NULL, binding TEXT NOT NULL, policy TEXT NOT NULL);
CREATE INDEX catalog_name ON catalog_symbols(elf,mangled);
CREATE INDEX catalog_range ON catalog_symbols(elf,section_json,address,size);
CREATE TABLE catalog_rows(input_path TEXT REFERENCES catalog_inputs(path), ordinal INTEGER NOT NULL, anchor TEXT REFERENCES catalog_symbols(anchor), raw TEXT NOT NULL, PRIMARY KEY(input_path,ordinal));
CREATE INDEX catalog_row_anchor ON catalog_rows(anchor);
CREATE TABLE catalog_tasks(anchor TEXT PRIMARY KEY REFERENCES catalog_symbols(anchor), revision INTEGER NOT NULL, state TEXT NOT NULL CHECK(state IN ('todo','assigned','in_progress','blocked','done')), owner TEXT, batch TEXT, notes TEXT NOT NULL);
CREATE TABLE catalog_requests(request_id TEXT PRIMARY KEY, digest TEXT NOT NULL, result TEXT NOT NULL);
CREATE TABLE catalog_journal(sequence INTEGER PRIMARY KEY, request_id TEXT NOT NULL REFERENCES catalog_requests(request_id), anchor TEXT NOT NULL REFERENCES catalog_symbols(anchor), actor TEXT NOT NULL, timestamp TEXT NOT NULL, reason TEXT NOT NULL, previous_revision INTEGER NOT NULL, new_revision INTEGER NOT NULL, previous_state TEXT NOT NULL, new_state TEXT NOT NULL);
CREATE TRIGGER catalog_journal_no_update BEFORE UPDATE ON catalog_journal BEGIN SELECT RAISE(ABORT,'append-only catalog journal'); END;
CREATE TRIGGER catalog_journal_no_delete BEFORE DELETE ON catalog_journal BEGIN SELECT RAISE(ABORT,'append-only catalog journal'); END;
CREATE TRIGGER catalog_requests_no_update BEFORE UPDATE ON catalog_requests BEGIN SELECT RAISE(ABORT,'immutable catalog request'); END;
CREATE TRIGGER catalog_requests_no_delete BEFORE DELETE ON catalog_requests BEGIN SELECT RAISE(ABORT,'immutable catalog request'); END;
'''
STATES = {'todo', 'assigned', 'in_progress', 'blocked', 'done'}

def require(value, message):
    if not value:
        raise ValueError(message)

def timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def writable(db):
    require(Path(db).is_file(), 'Existing independent workflow database required')
    unit = orm.Unit(db, write=True)
    try:
        schema.require_current(unit.raw)
        return unit
    except Exception:
        unit.close()
        raise


def identity(elf, row):
    # Source table indices are provenance only, never file offsets/identity.
    fields = [elf, row.get('mangled', ''), row.get('address', 0), row.get('size', 0),
              row.get('section'), row.get('kind', ''), row.get('binding', '')]
    return hashlib.sha256(reg.encode(fields).encode()).hexdigest()

def import_catalog(db, library, dry_run=True):
    """Full raw catalog union. Atomic new extension only, refuses reimport."""
    start = time.monotonic()
    library = Path(library).resolve()
    coverage_path = library/'tracking/coverage.json'
    paths = [coverage_path]
    for role in ('client', 'server'):
        paths += [library/'recovered-all'/role/name for name in ('manifest.json', 'all-symbols.json', 'symbols.json')]
    before = {str(p.relative_to(library)): reg.digest(p) for p in paths}
    data = {str(p.relative_to(library)): json.loads(p.read_bytes()) for p in paths}
    require(before == {str(p.relative_to(library)): reg.digest(p) for p in paths}, 'Inputs changed during read')
    unit = writable(db)
    c = unit.raw
    try:
        require(not c.execute("SELECT 1 FROM sqlite_master WHERE name='catalog_info'").fetchone(), 'Catalog already initialized')
        orm.Base.metadata.create_all(unit.session.get_bind(), tables=models.TABLES)
        # SQLite triggers remain database-enforced, independent of ORM callers.
        for statement in SCHEMA.splitlines():
            if statement.startswith('CREATE TRIGGER'):
                c.execute(statement)
        c.execute('INSERT INTO catalog_info VALUES(1,?)', (timestamp(),))
        coverage = data['tracking/coverage.json']
        for name in before:
            document = data[name]
            metadata = document if isinstance(document, dict) and name != 'tracking/coverage.json' else {'rows': len(document)} if isinstance(document, list) else {**{k:v for k,v in document.items() if k != 'roles'}, 'roles': {k:{a:b for a,b in v.items() if a != 'symbols'} for k,v in document['roles'].items()}}
            c.execute('INSERT INTO catalog_inputs VALUES(?,?,?)', (name, before[name], reg.encode(metadata)))
        counts = {}
        for role in ('client', 'server'):
            manifest = data[f'recovered-all/{role}/manifest.json']
            summary = coverage['roles'][role]['summary']
            require(manifest['sha256'] == summary['sha256'], 'Coverage/manifest ELF identity mismatch')
            elf = manifest['sha256']
            firmware = summary.get('label', role)
            for origin, rows in [(f'recovered-all/{role}/all-symbols.json', data[f'recovered-all/{role}/all-symbols.json']),
                                 (f'recovered-all/{role}/symbols.json', data[f'recovered-all/{role}/symbols.json']),
                                 ('tracking/coverage.json', coverage['roles'][role]['symbols'])]:
                # coverage has two roles in one document: provenance ordinal is role-qualified.
                ordinal_offset = 0 if role == 'client' or origin != 'tracking/coverage.json' else len(coverage['roles']['client']['symbols'])
                for ordinal, row in enumerate(rows, ordinal_offset):
                    anchor = identity(elf, row)
                    demangled = row.get('demangled', '')
                    core = any(demangled.startswith(prefix) for prefix in ('Core::', 'typeinfo for Core::', 'typeinfo name for Core::', 'vtable for Core::', 'guard variable for Core::', 'non-virtual thunk to Core::', 'virtual thunk to Core::', 'construction vtable for Core::', 'VTT for Core::')) or row.get('mangled', '').startswith(('_ZN4Core', '_ZNK4Core', '_ZTVN4Core', '_ZTIN4Core', '_ZTSN4Core'))
                    policy = 'core-source-provided' if row.get('upstream_body_available') else 'core-deferred' if core else 'application-or-other'
                    c.execute('INSERT OR IGNORE INTO catalog_symbols VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                              (anchor, elf, role, firmware, row.get('mangled', ''), row.get('demangled', ''), row.get('address', 0), row.get('size', 0), reg.encode(row.get('section')), row.get('kind', ''), row.get('binding', ''), policy))
                    if policy != 'application-or-other':
                        c.execute("UPDATE catalog_symbols SET policy=? WHERE anchor=? AND policy!='core-source-provided'", (policy, anchor))
                    c.execute('INSERT INTO catalog_rows VALUES(?,?,?,?)', (origin, ordinal, anchor, reg.encode(row)))
                counts[f'{role}:{origin}'] = len(rows)
        c.execute("INSERT INTO catalog_tasks SELECT anchor,0,'todo',NULL,NULL,'' FROM catalog_symbols")
        result = {'dry_run': dry_run, 'input_counts': counts, 'symbols': c.execute('SELECT count(*) FROM catalog_symbols').fetchone()[0],
                  'raw_rows': c.execute('SELECT count(*) FROM catalog_rows').fetchone()[0], 'seconds': time.monotonic()-start,
                  'input_hashes': before, 'readiness_changed': False}
        require(before == {str(p.relative_to(library)): reg.digest(p) for p in paths}, 'Input changed before commit')
        unit.rollback() if dry_run else unit.commit()
        return result
    except Exception:
        unit.rollback()
        raise
    finally:
        unit.close()

def query(db, role=None, name=None, kind=None, policy=None, source=None, limit=100, raw=False, state=None, owner=None, batch=None):
    """Read-only catalog lookup; source filters exact input provenance path."""
    c = reg.connect(db)
    try:
        schema.check_supported(c)
        terms, args = [], []
        for column, value in [('role', role), ('kind', kind), ('policy', policy)]:
            if value is not None:
                terms.append('s.'+column+'=?'); args.append(value)
        for column, value in [('state', state), ('owner', owner), ('batch', batch)]:
            if value is not None:
                terms.append('t.'+column+'=?'); args.append(value)
        if name is not None:
            terms.append('(s.mangled LIKE ? OR s.demangled LIKE ?)'); args += ['%'+name+'%']*2
        if source is not None:
            terms.append('EXISTS(SELECT 1 FROM catalog_rows r WHERE r.anchor=s.anchor AND r.input_path=?)'); args.append(source)
        require(isinstance(limit, int) and 0 < limit <= 1000000, 'Invalid limit')
        sql = 'SELECT s.*,t.revision,t.state,t.owner,t.batch,t.notes FROM catalog_symbols s JOIN catalog_tasks t USING(anchor)'
        if terms: sql += ' WHERE '+' AND '.join(terms)
        sql += ' ORDER BY s.role,s.address,s.mangled,s.anchor LIMIT ?'; args.append(limit)
        result = []
        for row in c.execute(sql, args):
            v = dict(row); v['section'] = json.loads(v.pop('section_json'))
            v['aliases'] = [] if not isinstance(v['section'], int) or v['size'] == 0 else [dict(x) for x in c.execute('SELECT anchor,mangled,kind,binding FROM catalog_symbols WHERE elf=? AND section_json=? AND address=? AND size=? AND anchor!=? ORDER BY mangled', (v['elf'], reg.encode(v['section']), v['address'], v['size'], v['anchor']))]
            v['alias_scope'] = 'Same defined nonempty section/address/size candidates only; not semantic or ABI verification.'
            v['zero_size'] = v['size'] == 0
            v['function'] = v['kind'] == 'STT_FUNC'
            raw_values = [json.loads(x['raw']) for x in c.execute('SELECT raw FROM catalog_rows WHERE anchor=?', (v['anchor'],))]
            v['NOBITS'] = any('NOBITS' in x.get('storage', '') or x.get('section_type') == 'SHT_NOBITS' for x in raw_values)
            v['ranges'] = [{key: x[key] for key in ('file_offset', 'sha256', 'export_path', 'storage', 'machine_code') if key in x} for x in raw_values if any(key in x for key in ('file_offset', 'sha256', 'export_path', 'storage', 'machine_code'))]
            if raw: v['raw_rows'] = [{'input_path': x['input_path'], 'ordinal': x['ordinal'], 'row': json.loads(x['raw'])} for x in c.execute('SELECT * FROM catalog_rows WHERE anchor=? ORDER BY input_path,ordinal', (v['anchor'],))]
            result.append(v)
        return result
    finally:
        c.close()

def operate(db, payload, dry_run=True):
    """Atomic metadata-only batch. done has NO effect on proofs/readiness."""
    require(isinstance(payload, dict), 'Object request required')
    for key in ('request_id', 'actor'):
        require(isinstance(payload.get(key), str) and payload[key].strip(), key+' required')
    ops = payload.get('operations'); require(isinstance(ops, list) and bool(ops), 'Operations required')
    checksum = hashlib.sha256(reg.encode(payload).encode()).hexdigest()
    unit = writable(db)
    c = unit.raw
    try:
        old = c.execute('SELECT digest,result FROM catalog_requests WHERE request_id=?', (payload['request_id'],)).fetchone()
        if old:
            require(old['digest'] == checksum, 'Request id reused with different payload')
            unit.rollback(); return {**json.loads(old['result']), 'idempotent_replay': True}
        prepared = []; seen = set()
        for op in ops:
            require(set(op) <= {'anchor', 'expected_revision', 'state', 'owner', 'batch', 'notes', 'reason'}, 'Unknown task field')
            anchor = op.get('anchor'); require(anchor not in seen, 'Duplicate task in atomic batch'); seen.add(anchor)
            before = c.execute('SELECT * FROM catalog_tasks WHERE anchor=?', (anchor,)).fetchone(); require(before is not None, 'Unknown original anchor')
            before = dict(before)
            require(type(op.get('expected_revision')) is int and op['expected_revision'] == before['revision'], 'Stale task revision')
            require(isinstance(op.get('reason'), str) and op['reason'].strip(), 'Reason required')
            after = dict(before)
            for key in ('state', 'owner', 'batch', 'notes'):
                if key in op: after[key] = op[key]
            require(after['state'] in STATES, 'Invalid task state')
            require(after['owner'] is None or isinstance(after['owner'], str), 'Invalid owner')
            require(after['batch'] is None or isinstance(after['batch'], str), 'Invalid batch')
            require(isinstance(after['notes'], str), 'Invalid notes')
            require(after['state'] not in ('assigned', 'in_progress') or bool(after['owner'] and after['owner'].strip()), 'Assigned/in-progress requires owner')
            require(after['state'] != 'blocked' or bool(after['notes'].strip()), 'Blocked requires notes')
            after['revision'] += 1; prepared.append((op, before, after))
        result = {'request_id': payload['request_id'], 'dry_run': dry_run, 'operations': len(prepared), 'readiness_changed': False,
                  'revisions': [{'anchor': op['anchor'], 'previous': before['revision'], 'next': after['revision']} for op,before,after in prepared]}
        if dry_run:
            unit.rollback(); return result
        unit.session.add(models.CatalogRequest(request_id=payload['request_id'], digest=checksum, result=reg.encode(result)))
        unit.session.flush()
        for op,before,after in prepared:
            changed = unit.session.execute(update(models.CatalogTask).where(models.CatalogTask.anchor == op['anchor'], models.CatalogTask.revision == before['revision']).values(**{key: after[key] for key in ('revision', 'state', 'owner', 'batch', 'notes')}))
            require(changed.rowcount == 1, 'Concurrent task revision changed')
            unit.session.add(models.CatalogJournal(request_id=payload['request_id'], anchor=op['anchor'], actor=payload['actor'], timestamp=timestamp(), reason=op['reason'], previous_revision=before['revision'], new_revision=after['revision'], previous_state=reg.encode(before), new_state=reg.encode(after)))
        unit.commit(); return result
    except Exception:
        unit.rollback(); raise
    finally:
        unit.close()

def rollback_request(db, target_request, request_id, actor, reason, dry_run=True):
    """Audited compensating operation; never deletes history or readiness."""
    c = reg.connect(db)
    try:
        rows = c.execute('SELECT * FROM catalog_journal WHERE request_id=? ORDER BY sequence', (target_request,)).fetchall()
        require(bool(rows), 'Unknown task request or no journal')
        operations = []
        for row in rows:
            previous = json.loads(row['previous_state'])
            operations.append({'anchor': row['anchor'], 'expected_revision': row['new_revision'],
                               **{key: previous[key] for key in ('state', 'owner', 'batch', 'notes')},
                               'reason': reason + ' (compensates ' + target_request + ')'})
    finally:
        c.close()
    return operate(db, {'request_id': request_id, 'actor': actor, 'operations': operations}, dry_run)

def main():
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='command', required=True)
    i = sub.add_parser('import'); i.add_argument('--db', type=Path, required=True); i.add_argument('--library', type=Path, required=True); i.add_argument('--apply', action='store_true')
    q = sub.add_parser('query'); q.add_argument('--db', type=Path, required=True)
    for key in ('role', 'name', 'kind', 'policy', 'source', 'state', 'owner', 'batch'): q.add_argument('--'+key)
    q.add_argument('--limit', type=int, default=100); q.add_argument('--raw', action='store_true')
    t = sub.add_parser('operate'); t.add_argument('--db', type=Path, required=True); t.add_argument('--request', type=Path, required=True); t.add_argument('--apply', action='store_true')
    u = sub.add_parser('rollback'); u.add_argument('--db', type=Path, required=True)
    for key in ('target-request', 'request-id', 'actor', 'reason'): u.add_argument('--'+key, required=True)
    u.add_argument('--apply', action='store_true')
    a = p.parse_args()
    if a.command == 'import': result = import_catalog(a.db, a.library, not a.apply)
    elif a.command == 'query': result = query(a.db, a.role, a.name, a.kind, a.policy, a.source, a.limit, a.raw, a.state, a.owner, a.batch)
    elif a.command == 'rollback': result = rollback_request(a.db, a.target_request, a.request_id, a.actor, a.reason, not a.apply)
    else: result = operate(a.db, json.loads(a.request.read_bytes()), not a.apply)
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
