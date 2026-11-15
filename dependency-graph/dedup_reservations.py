"""Fail-closed reservations for ownership carried from a preserved generation."""
import hashlib
import json
import pathlib
import sqlite3
from context_runtime import ContextError


def rows_digest(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def check(c, members):
    row = c.execute("SELECT value FROM index_meta WHERE key='carryover_manifest'").fetchone()
    if row is None:
        if c.execute("SELECT 1 FROM sqlite_master WHERE name='carryover_reservations'").fetchone():
            raise ContextError('Carry-over tables lack their manifest')
        return
    manifest = json.loads(row[0])
    database = pathlib.Path(next(r[2] for r in c.execute('PRAGMA database_list') if r[1] == 'main'))
    backup = database.parent / manifest['snapshot_relative']
    if not backup.is_file() or backup.is_symlink():
        raise ContextError('Preserved claim history snapshot unavailable')
    for suffix in ('-wal', '-journal'):
        sidecar = pathlib.Path(str(backup) + suffix)
        if sidecar.exists() and sidecar.stat().st_size:
            raise ContextError('Preserved claim history is not a quiescent backup')
    with backup.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != manifest['snapshot_sha256']:
            raise ContextError('Preserved claim history snapshot changed')
    rows = [list(r) for r in c.execute('SELECT occurrence_id,old_claim_id,status FROM carryover_reservations ORDER BY occurrence_id,old_claim_id')]
    if rows_digest(rows) != manifest['reservations_sha256']:
        raise ContextError('Carry-over reservation coverage changed')
    if c.execute('SELECT count(*) FROM carryover_claims').fetchone()[0] != manifest['claims'] or c.execute('SELECT count(*) FROM carryover_events').fetchone()[0] != manifest['events']:
        raise ContextError('Preserved claim/event lineage incomplete')
    # Independently derive coverage from the immutable old owner records. A
    # migration receipt cannot declare an omitted owner or alias absent.
    with sqlite3.connect(backup.resolve().as_uri() + '?mode=ro&immutable=1', uri=True) as old:
        fields = ('elf_sha256','original_mangled','original_address','original_size','section_index','catalog_anchor')
        if c.execute('SELECT 1 FROM symbol_occurrences GROUP BY ' + ','.join(fields) + ' HAVING count(*)>1 LIMIT 1').fetchone():
            raise ContextError('Duplicate full original identity in candidate')
        old.row_factory = sqlite3.Row
        old_claims = [dict(r) for r in old.execute('SELECT * FROM work_claims ORDER BY id')]
        expected_claims = [(r['id'],r['state'],r['owner'],r['packet_path'],r['generation'],json.dumps(r,sort_keys=True)) for r in old_claims]
        actual_claims = [tuple(r) for r in c.execute('SELECT old_claim_id,state,owner,packet_path,old_generation,payload FROM carryover_claims ORDER BY old_claim_id')]
        expected_events = [(r['id'],r['claim_id'],json.dumps(dict(r),sort_keys=True)) for r in old.execute('SELECT * FROM claim_history ORDER BY id')]
        actual_events = [tuple(r) for r in c.execute('SELECT old_event_id,old_claim_id,payload FROM carryover_events ORDER BY old_event_id')]
        if expected_claims != actual_claims or expected_events != actual_events:
            raise ContextError('Preserved exact claim/event lineage differs')
        columns = ','.join('o.' + field for field in fields)
        expected = {(r[0], tuple(r[1:])) for r in old.execute('SELECT c.id,' + columns + ' FROM work_claims c JOIN work_item_members m ON m.work_item_id=c.work_item_id JOIN symbol_occurrences o ON o.id=m.occurrence_id WHERE c.state="active"')}
        if old.execute('SELECT count(*) FROM work_claims').fetchone()[0] != manifest['claims'] or old.execute('SELECT count(*) FROM claim_history').fetchone()[0] != manifest['events']:
            raise ContextError('Preserved lineage source counts differ')
    actual = set()
    for occurrence, claim, status in rows:
        current = c.execute('SELECT ' + ','.join(fields) + ' FROM symbol_occurrences WHERE id=?', (occurrence,)).fetchone()
        if current is None:
            raise ContextError('Reserved original missing from new generation')
        actual.add((claim, tuple(current)))
    if expected != actual:
        raise ContextError('Prior owner full identity reservation coverage incomplete')
    targets = {m['id'] for m in members}
    conflicts = [r for r in rows if r[0] in targets]
    if conflicts:
        raise ContextError('Prior owner reservation blocks new work; explicit owner review/repreparation required: ' + json.dumps(conflicts))
