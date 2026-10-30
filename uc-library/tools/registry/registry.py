#!/usr/bin/env python3
"""Additive, read-only-by-default SQLite mirror of the legacy readiness registries."""
import argparse
import hashlib
import json
import pathlib
import shutil
import sqlite3
import subprocess
import time

VERSION = 1
FIELDS = ('sources', 'repository_sources')

def encode(value):
    return json.dumps(value, ensure_ascii=True, separators=(',', ':'), allow_nan=False)

def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()

def connect(path):
    c = sqlite3.connect(pathlib.Path(path).resolve().as_uri() + '?mode=ro', uri=True)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    try:
        markers = c.execute('SELECT version, complete FROM schema_info').fetchall()
        if len(markers) != 1 or tuple(markers[0]) != (VERSION, 1):
            raise ValueError('Unsupported or incomplete registry')
    except sqlite3.Error as exc:
        c.close()
        raise ValueError('Missing completion marker; failed/legacy import is not readable') from exc
    if c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='alembic_version'").fetchone():
        revisions=c.execute('SELECT version_num FROM alembic_version').fetchall()
        if len(revisions)!=1 or revisions[0][0] not in ('0001_adopt','0002_workflow_indexes'):
            c.close()
            raise ValueError('Unsupported/newer or ambiguous Alembic revision')
    return c

def capture(paths, destination, expected_manifest=None):
    """Reject a changed capture; copies are independent, never hardlinks."""
    destination.mkdir(parents=True, exist_ok=False)
    before = {k: digest(p) for k, p in paths.items()}
    producer = None
    if expected_manifest is not None:
        producer_bytes = expected_manifest.read_bytes()
        expected = json.loads(producer_bytes)
        for status, path in paths.items():
            if expected.get(path.name) != before[status]:
                raise ValueError('Input pair differs from expected producer manifest: '+path.name)
        producer = {'path':str(expected_manifest.resolve()),'sha256':hashlib.sha256(producer_bytes).hexdigest(),'expected':expected}
    for k, p in paths.items():
        shutil.copyfile(p, destination / (k + '.json'))
    copied = {k: digest(destination / (k + '.json')) for k in paths}
    after = {k: digest(p) for k, p in paths.items()}
    if before != copied or before != after:
        raise RuntimeError('Input changed during capture; rejected snapshots retained for inspection')
    manifest = {'schema_version': VERSION, 'captured_unix': time.time(), 'tool_sha256': digest(pathlib.Path(__file__)),
                'capture_consistency': 'before/copy/after hashes; atomic multi-file generation requires trusted expected producer pair', 'expected_producer_manifest': producer,
                'checkout_commit': subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=pathlib.Path(__file__).resolve().parents[3], check=True, capture_output=True, text=True).stdout.strip(), 'inputs': {
        k: {'canonical': str(p.resolve()), 'parent': str(p.resolve().parent),
            'sha256': before[k], 'snapshot': k + '.json'} for k, p in paths.items()}}
    (destination / 'capture.json').write_text(json.dumps(manifest, indent=2) + '\n')
    for p in destination.glob('*.json'):
        p.chmod(0o444)
    return manifest

def import_snapshots(snapshots, db):
    started = time.monotonic()
    manifest = json.loads((snapshots / 'capture.json').read_text())
    if db.exists():
        raise ValueError('Refusing to replace existing database')
    c = sqlite3.connect(db)
    c.executescript('''
      PRAGMA foreign_keys=ON;
      CREATE TABLE schema_info(version INTEGER NOT NULL, complete INTEGER NOT NULL);
      INSERT INTO schema_info VALUES (1,0);
      CREATE TABLE provenance(json TEXT NOT NULL);
      CREATE TABLE registries(status TEXT PRIMARY KEY, metadata TEXT NOT NULL);
      CREATE TABLE source_sets(id TEXT PRIMARY KEY);
      CREATE TABLE source_versions(id INTEGER PRIMARY KEY, path TEXT NOT NULL, digest_json TEXT NOT NULL, UNIQUE(path,digest_json));
      CREATE TABLE source_members(set_id TEXT REFERENCES source_sets(id), ordinal INTEGER, version_id INTEGER REFERENCES source_versions(id), PRIMARY KEY(set_id,ordinal));
      CREATE INDEX reverse_source ON source_members(version_id,set_id);
      CREATE TABLE records(id INTEGER PRIMARY KEY, status TEXT REFERENCES registries(status), ordinal INTEGER NOT NULL, elf TEXT NOT NULL, mangled TEXT NOT NULL, proof TEXT, metadata TEXT NOT NULL, UNIQUE(elf,mangled), UNIQUE(status,ordinal));
      CREATE INDEX status_lookup ON records(status);
      CREATE INDEX proof_lookup ON records(proof);
      CREATE TABLE record_sets(record_id INTEGER REFERENCES records(id), field TEXT, set_id TEXT REFERENCES source_sets(id), PRIMARY KEY(record_id,field));
      CREATE INDEX set_records ON record_sets(set_id,record_id);
    ''')
    c.execute('INSERT INTO provenance VALUES (?)', (encode(manifest),))
    known = set()
    counts = {}
    for status, item in manifest['inputs'].items():
        path = snapshots / item['snapshot']
        if digest(path) != item['sha256']:
            raise ValueError('Snapshot hash mismatch')
        data = json.loads(path.read_bytes())
        rows = data.pop('functions')
        c.execute('INSERT INTO registries VALUES (?,?)', (status, encode(data)))
        counts[status] = len(rows)
        for ordinal, original in enumerate(rows):
            row = dict(original)
            sets = []
            for field in FIELDS:
                if field not in row or not isinstance(row[field], dict):
                    continue
                sources = row.pop(field)
                # Ordered pairs preserve even the manifest insertion order.
                sid = hashlib.sha256(encode(list(sources.items())).encode()).hexdigest()
                if sid not in known:
                    c.execute('INSERT INTO source_sets VALUES (?)', (sid,))
                    for n, (p, d) in enumerate(sources.items()):
                        d = encode(d)
                        c.execute('INSERT OR IGNORE INTO source_versions(path,digest_json) VALUES (?,?)', (p, d))
                        vid = c.execute('SELECT id FROM source_versions WHERE path=? AND digest_json=?', (p,d)).fetchone()[0]
                        c.execute('INSERT INTO source_members VALUES (?,?,?)', (sid,n,vid))
                    known.add(sid)
                sets.append((field,sid))
            rid = c.execute('INSERT INTO records(status,ordinal,elf,mangled,proof,metadata) VALUES (?,?,?,?,?,?)', (status,ordinal,row['original_elf_sha256'],row['mangled'],row.get('validation'),encode(row))).lastrowid
            c.executemany('INSERT INTO record_sets VALUES (?,?,?)', [(rid,f,s) for f,s in sets])
        del data, rows
    checks = {'foreign_key_check': c.execute('PRAGMA foreign_key_check').fetchall(), 'integrity_check': c.execute('PRAGMA integrity_check').fetchall()}
    if checks['foreign_key_check'] or checks['integrity_check'] != [('ok',)]:
        c.rollback()
        c.close()
        raise ValueError('Import integrity failed; database remains incomplete')
    c.execute('UPDATE schema_info SET complete=1')
    c.commit()
    report = {'schema_version': VERSION, 'counts': counts, 'checks': checks, 'import_seconds': time.monotonic()-started, 'database_bytes': db.stat().st_size,
              'source_sets': c.execute('SELECT count(*) FROM source_sets').fetchone()[0], 'source_versions': c.execute('SELECT count(*) FROM source_versions').fetchone()[0]}
    c.close()
    return report

def restored(c, row):
    result = json.loads(row['metadata'])
    for field, sid in c.execute('SELECT field,set_id FROM record_sets WHERE record_id=?', (row['id'],)):
        result[field] = {p: json.loads(d) for p,d in c.execute('SELECT v.path,v.digest_json FROM source_members m JOIN source_versions v ON v.id=m.version_id WHERE m.set_id=? ORDER BY m.ordinal', (sid,))}
    return result

def export(c, status, output):
    metadata = json.loads(c.execute('SELECT metadata FROM registries WHERE status=?', (status,)).fetchone()[0])
    with open(output, 'x') as f:
        f.write('{"functions":[')
        first = True
        for row in c.execute('SELECT * FROM records WHERE status=? ORDER BY ordinal', (status,)):
            if not first:
                f.write(',')
            first = False
            f.write(encode(restored(c,row)))
        f.write(']')
        for k,v in metadata.items():
            f.write(',' + encode(k) + ':' + encode(v))
        f.write('}\n')

def validate(c, snapshots):
    provenance = json.loads(c.execute('SELECT json FROM provenance').fetchone()[0])
    supplied = json.loads((snapshots / 'capture.json').read_text())
    if supplied != provenance:
        raise ValueError('Snapshot manifest differs from database provenance')
    for item in provenance['inputs'].values():
        if digest(snapshots / item['snapshot']) != item['sha256']:
            raise ValueError('Snapshot SHA-256 differs from captured provenance')
    counts = {}
    for status, in c.execute('SELECT status FROM registries'):
        original = json.loads((snapshots / (status + '.json')).read_bytes())
        rows = original.pop('functions')
        assert original == json.loads(c.execute('SELECT metadata FROM registries WHERE status=?', (status,)).fetchone()[0])
        actual = c.execute('SELECT * FROM records WHERE status=? ORDER BY ordinal', (status,))
        n = 0
        for n,row in enumerate(actual,1):
            assert rows[n-1] == restored(c,row), (status,n)
        assert n == len(rows)
        counts[status] = n
    assert not c.execute('PRAGMA foreign_key_check').fetchall()
    assert c.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    return {'lossless_records_and_top_metadata': counts, 'integrity': 'ok'}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    s = sub.add_parser('capture-import'); s.add_argument('--ready',type=pathlib.Path,required=True); s.add_argument('--pending',type=pathlib.Path,required=True); s.add_argument('--run',type=pathlib.Path,required=True); s.add_argument('--expected-manifest',type=pathlib.Path)
    for name in ('query','export','validate'):
        s = sub.add_parser(name); s.add_argument('--db',type=pathlib.Path,required=True)
        if name == 'query':
            for flag in ('status','elf','mangled','proof','source','digest'): s.add_argument('--'+flag)
        elif name == 'export': s.add_argument('--status',required=True); s.add_argument('--output',type=pathlib.Path,required=True)
        else: s.add_argument('--snapshots',type=pathlib.Path,required=True)
    a = p.parse_args()
    if a.command == 'capture-import':
        a.run.mkdir(parents=True,exist_ok=False)
        capture({'ready':a.ready,'pending':a.pending},a.run/'snapshots',a.expected_manifest)
        report = import_snapshots(a.run/'snapshots',a.run/'registry.sqlite')
        (a.run/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report)); return
    with connect(a.db) as c:
        if a.command == 'export': export(c,a.status,a.output)
        elif a.command == 'validate': print(json.dumps(validate(c,a.snapshots)))
        else:
            where=[]; args=[]
            for key in ('status','elf','mangled','proof'):
                if getattr(a,key) is not None: where.append('r.'+key+'=?'); args.append(getattr(a,key))
            if a.source is not None or a.digest is not None:
                cond=[]
                if a.source is not None: cond.append('v.path=?'); args.append(a.source)
                if a.digest is not None: cond.append('v.digest_json=?'); args.append(encode(a.digest))
                where.append('EXISTS (SELECT 1 FROM record_sets x JOIN source_members m ON m.set_id=x.set_id JOIN source_versions v ON v.id=m.version_id WHERE x.record_id=r.id AND '+' AND '.join(cond)+')')
            for row in c.execute('SELECT r.* FROM records r'+(' WHERE '+' AND '.join(where) if where else '')+' ORDER BY status,ordinal',args):
                print(encode({k:row[k] for k in ('status','ordinal','elf','mangled','proof')}))

if __name__ == '__main__': main()
