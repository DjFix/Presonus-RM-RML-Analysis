#!/usr/bin/env python3
"""Explicit stable-key workflow history transfer; never copies classifications."""
import argparse
import json
import pathlib
from sqlalchemy import insert
import orm
import registry as reg
import schema
import workflow


def transfer(source,destination,apply=False):
    """Transfer ALL workflow history to a fresh generation, or report conflicts.

    Intended only for meaningful operational history. Benchmark/test history must
    remain archived in its old DB and must not be imported into operational work.
    The destination must be a new working DB with no requests/journal/stages and
    zero task revisions; classification always remains the new baseline's data.
    """
    source_before=reg.digest(source)
    with reg.connect(source) as old,reg.connect(destination) as new:
        if old.execute('PRAGMA journal_mode').fetchone()[0]!='delete':raise ValueError('History source must be quiescent in DELETE journal mode; snapshot WAL explicitly before transfer')
        schema.require_current(old);schema.require_current(new)
        oldrows={r['id']:(r['elf'],r['mangled']) for r in old.execute('SELECT id,elf,mangled FROM records')}
        newrows={(r['elf'],r['mangled']):r['id'] for r in new.execute('SELECT id,elf,mangled FROM records')}
        missing=[v for v in oldrows.values() if v not in newrows]
        if missing:raise ValueError('Generation conflict: original keys absent in new baseline: '+str(missing[:10]))
        for table in ('requests','journal','stages','evidence_checks'):
            if new.execute('SELECT count(*) FROM '+table).fetchone()[0]:raise ValueError('Destination workflow history is not empty: '+table)
        if new.execute("SELECT count(*) FROM work_state WHERE revision!=0 OR assignment IS NOT NULL OR blocker IS NOT NULL").fetchone()[0]:raise ValueError('Destination work annotations are not fresh')
        mapping={rid:newrows[key] for rid,key in oldrows.items()}
        prior={name:[dict(row) for row in old.execute('SELECT * FROM '+name)] for name in ('work_state','stages','requests','evidence_checks','journal')}
        # Retain historical source sets referenced by journal snapshots even when
        # the new generation no longer uses them. No old source row is overwritten.
        sets=[tuple(row) for row in old.execute('SELECT id FROM source_sets')]
        versions={row['id']:(row['path'],row['digest_json']) for row in old.execute('SELECT * FROM source_versions')}
        members=[tuple(row) for row in old.execute('SELECT set_id,ordinal,version_id FROM source_members')]
    if reg.digest(source)!=source_before:raise ValueError('Source history changed during preflight')
    report={'source':str(pathlib.Path(source).resolve()),'source_sha256':reg.digest(source),'destination':str(pathlib.Path(destination).resolve()),'dry_run':not apply,'record_key_mapping':len(mapping),'counts':{k:len(v) for k,v in prior.items()},'classifications_transferred':False,'historical_embedded_record_ids':'Preserved verbatim in audit JSON; generation_identity maps original numeric IDs to new IDs'}
    if not apply:return report
    unit=orm.Unit(destination,write=True);c=unit.raw;s=unit.session
    try:
        schema.require_current(c)
        for table in ('requests','journal','stages','evidence_checks'):
            if c.execute('SELECT count(*) FROM '+table).fetchone()[0]:raise ValueError('Destination changed after preflight')
        if reg.digest(source)!=report['source_sha256']:raise ValueError('Source history changed after preflight')
        for (sid,) in sets:c.execute('INSERT OR IGNORE INTO source_sets VALUES (?)',(sid,))
        vmapping={}
        for vid,(p,d) in versions.items():
            c.execute('INSERT OR IGNORE INTO source_versions(path,digest_json) VALUES (?,?)',(p,d))
            vmapping[vid]=c.execute('SELECT id FROM source_versions WHERE path=? AND digest_json=?',(p,d)).fetchone()[0]
        for sid,n,vid in members:
            previous=c.execute('SELECT version_id FROM source_members WHERE set_id=? AND ordinal=?',(sid,n)).fetchone()
            if previous and previous[0]!=vmapping[vid]:raise ValueError('Content-addressed historical source-set conflict')
            c.execute('INSERT OR IGNORE INTO source_members VALUES (?,?,?)',(sid,n,vmapping[vid]))
        for row in prior['requests']:s.add(orm.Request(**row))
        s.flush()
        if prior['evidence_checks']:s.execute(insert(orm.EvidenceCheck),prior['evidence_checks'])
        for row in prior['work_state']:
            work=s.get(orm.WorkState,mapping[row['record_id']])
            work.revision=row['revision'];work.assignment=row['assignment'];work.blocker=row['blocker']
        for row in prior['stages']:
            row=dict(row,record_id=mapping[row['record_id']]);s.add(orm.Stage(**row))
        for row in prior['journal']:
            row=dict(row,record_id=mapping[row['record_id']]);s.add(orm.Journal(**row))
        c.execute('CREATE TABLE generation_identity(source_sha256 TEXT,old_record_id INTEGER,new_record_id INTEGER REFERENCES records(id),PRIMARY KEY(source_sha256,old_record_id))')
        c.executemany('INSERT INTO generation_identity VALUES (?,?,?)',[(report['source_sha256'],a,b) for a,b in mapping.items()])
        c.execute('CREATE TABLE generation_transfer(json TEXT NOT NULL)')
        c.execute('INSERT INTO generation_transfer VALUES (?)',(reg.encode(report),))
        s.flush()
        if c.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Generation transfer foreign-key failure')
        if reg.digest(source)!=report['source_sha256']:raise ValueError('Source changed during history transfer')
        unit.commit();return dict(report,dry_run=False)
    except Exception:unit.rollback();raise
    finally:unit.close()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=pathlib.Path,required=True);p.add_argument('--destination',type=pathlib.Path,required=True);p.add_argument('--apply',action='store_true');a=p.parse_args()
    print(json.dumps(transfer(a.source,a.destination,a.apply),indent=2))
