"""Build an isolated, ownership-preserving candidate; never activate a pointer."""
import argparse
import hashlib
import json
import pathlib
import shutil
import sqlite3
from dedup_reservations import rows_digest


def sha(path):
    with pathlib.Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def require_backup(path):
    for suffix in ('-wal', '-journal'):
        sidecar = pathlib.Path(str(path) + suffix)
        if sidecar.exists() and sidecar.stat().st_size:
            raise ValueError('Supported quiescent SQLite backup required: ' + str(sidecar))
    with sqlite3.connect(path.as_uri() + '?mode=ro&immutable=1', uri=True) as c:
        if c.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Input integrity check failed')
        with sqlite3.connect(':memory:') as reference:
            reference.executescript(pathlib.Path(__file__).with_name('dedup_schema.sql').read_text())
            query = "SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
            if c.execute(query).fetchall() != reference.execute(query).fetchall():
                raise ValueError('Exact dedup input schema required')
        values = {k: json.loads(v) for k, v in c.execute('SELECT key,value FROM index_meta')}
        generation = values.get('generation')
        if values.get('complete') is not True or not isinstance(generation, str) or len(generation) != 64 or any(v not in '0123456789abcdef' for v in generation):
            raise ValueError('Complete valid input generation required')


def identity(row):
    return tuple(row[k] for k in ('elf_sha256', 'original_mangled', 'original_address', 'original_size', 'section_index', 'catalog_anchor'))


def migrate(old_path, new_path, out, old_sha, new_sha):
    old_path, new_path, out = map(lambda p: pathlib.Path(p).resolve(), (old_path, new_path, out))
    require_backup(old_path); require_backup(new_path)
    if sha(old_path) != old_sha or sha(new_path) != new_sha:
        raise ValueError('Reviewed input hash mismatch')
    if out.exists() or out == old_path.parent or out == new_path.parent:
        raise ValueError('Fresh isolated output directory required')
    out.mkdir(parents=True)
    history = out / 'history'; history.mkdir()
    preserved = history / 'old-dedup.sqlite'
    shutil.copyfile(old_path, preserved)
    preserved.chmod(0o444)
    if sha(preserved) != old_sha:
        raise ValueError('Preserved history byte hash mismatch')
    old = sqlite3.connect(preserved.as_uri() + '?mode=ro&immutable=1', uri=True)
    old.row_factory = sqlite3.Row
    source = sqlite3.connect(new_path.as_uri() + '?mode=ro&immutable=1', uri=True)
    c = sqlite3.connect(out / 'dedup.sqlite'); c.row_factory = sqlite3.Row
    source.backup(c); source.close()
    try:
        if c.execute('SELECT count(*) FROM work_claims').fetchone()[0]:
            raise ValueError('Fresh candidate already has claims; preserve it')
        producers = json.loads(c.execute("SELECT value FROM index_meta WHERE key='producer_inputs'").fetchone()[0])
        if any(producers.get(name) != sha(pathlib.Path(__file__).with_name(name)) for name in ('dedup_reservations.py','dedup_migrate.py')):
            raise ValueError('New generation must bind reservation gate producer')
        c.executescript('''CREATE TABLE carryover_claims(old_claim_id TEXT PRIMARY KEY,state TEXT NOT NULL,owner TEXT NOT NULL,packet_path TEXT NOT NULL,old_generation TEXT NOT NULL,payload TEXT NOT NULL);
        CREATE TABLE carryover_events(old_event_id INTEGER PRIMARY KEY,old_claim_id TEXT NOT NULL,payload TEXT NOT NULL);
        CREATE TABLE carryover_reservations(occurrence_id TEXT NOT NULL REFERENCES symbol_occurrences(id),old_claim_id TEXT NOT NULL REFERENCES carryover_claims(old_claim_id),status TEXT NOT NULL,PRIMARY KEY(occurrence_id,old_claim_id));''')
        occurrences = {}
        for occurrence in c.execute('SELECT * FROM symbol_occurrences'):
            ident = identity(occurrence)
            if ident in occurrences:
                raise ValueError('Duplicate full original identity in candidate')
            occurrences[ident] = occurrence['id']
        old_occurrences = {r['id']: r for r in old.execute('SELECT * FROM symbol_occurrences')}
        current_jobs = {}
        for job in c.execute('SELECT * FROM reconstruction_work_items'):
            members = frozenset(r[0] for r in c.execute('SELECT occurrence_id FROM work_item_members WHERE work_item_id=?', (job['id'],)))
            current_jobs.setdefault((job['work_kind'], members), []).append(job['id'])
        claims = [dict(r) for r in old.execute('SELECT * FROM work_claims ORDER BY id')]
        active = 0; changed = 0
        for claim in claims:
            c.execute('INSERT INTO carryover_claims VALUES(?,?,?,?,?,?)', (claim['id'], claim['state'], claim['owner'], claim['packet_path'], claim['generation'], json.dumps(claim, sort_keys=True)))
            if claim['state'] != 'active':
                continue
            old_members = [r[0] for r in old.execute('SELECT occurrence_id FROM work_item_members WHERE work_item_id=?', (claim['work_item_id'],))]
            if not old_members:
                raise ValueError('Active claim has no original identities')
            mapped = []
            for member in old_members:
                target = occurrences.get(identity(old_occurrences[member]))
                if target is None:
                    raise ValueError('Active original absent/changed in candidate; retain previous generation')
                mapped.append(target)
            kind = old.execute('SELECT work_kind FROM reconstruction_work_items WHERE id=?', (claim['work_item_id'],)).fetchone()[0]
            exact = len(current_jobs.get((kind, frozenset(mapped)), [])) == 1
            status = 'reserved_exact_members' if exact else 'blocked_owner_review'
            changed += not exact; active += 1
            c.executemany('INSERT INTO carryover_reservations VALUES(?,?,?)', [(member, claim['id'], status) for member in mapped])
        for row in old.execute('SELECT * FROM claim_history ORDER BY id'):
            c.execute('INSERT INTO carryover_events VALUES(?,?,?)', (row['id'], row['claim_id'], json.dumps(dict(row), sort_keys=True)))
        rows = [list(r) for r in c.execute('SELECT occurrence_id,old_claim_id,status FROM carryover_reservations ORDER BY occurrence_id,old_claim_id')]
        manifest = {'version': 1, 'snapshot_relative': 'history/old-dedup.sqlite', 'snapshot_sha256': old_sha, 'claims': len(claims), 'events': old.execute('SELECT count(*) FROM claim_history').fetchone()[0], 'reservations_sha256': rows_digest(rows), 'active_claims': active, 'changed_owner_review': changed, 'migration_producer_sha256': sha(pathlib.Path(__file__))}
        c.execute('INSERT INTO index_meta VALUES(?,?)', ('carryover_manifest', json.dumps(manifest, sort_keys=True)))
        for table in ('carryover_claims', 'carryover_events', 'carryover_reservations'):
            for action in ('INSERT', 'UPDATE', 'DELETE'):
                c.execute(f"CREATE TRIGGER {table}_{action.lower()} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'carry-over lineage immutable'); END")
        for action in ('UPDATE', 'DELETE'):
            c.execute(f"CREATE TRIGGER carryover_meta_{action.lower()} BEFORE {action} ON index_meta WHEN OLD.key='carryover_manifest' BEGIN SELECT RAISE(ABORT,'carry-over manifest immutable'); END")
        c.commit()
        if c.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or c.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Candidate integrity failed')
        require_backup(old_path); require_backup(new_path)
        if sha(old_path) != old_sha or sha(new_path) != new_sha:
            raise ValueError('Input changed during migration')
        receipt = {'ok': True, 'manifest': manifest, 'old': {'path': str(old_path), 'sha256': old_sha}, 'fresh': {'path': str(new_path), 'sha256': new_sha}, 'candidate': {'path': str(out / 'dedup.sqlite'), 'sha256': sha(out / 'dedup.sqlite')}, 'prior_claim_states_relabelled': False, 'new_work_statuses_modified': False, 'old_packets': 'retain exact old DB/claim lineage; fresh generation requires owner review and fresh preparation', 'canonical_pointer_written': False}
        (out / 'MIGRATION.json').write_text(json.dumps(receipt, indent=2) + '\n')
        return receipt
    finally:
        c.close(); old.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('old', 'new', 'out', 'old-sha256', 'new-sha256'):
        parser.add_argument('--' + flag, required=True)
    args = parser.parse_args()
    print(json.dumps(migrate(args.old, args.new, args.out, args.old_sha256, args.new_sha256)))


if __name__ == '__main__':
    main()
