#!/usr/bin/env python3
"""Explicit, backed-up Alembic upgrades of independent working databases."""
import argparse
import datetime
import hashlib
import json
import pathlib
import sqlite3
from sqlalchemy import Column,Integer,Text
from alembic.migration import MigrationContext
from alembic.operations import Operations
import orm
import registry as reg

REVISIONS=('0001_adopt','0002_workflow_indexes')
CURRENT=REVISIONS[-1]
REQUIRED={'schema_info','provenance','registries','source_sets','source_versions','source_members','records','record_sets','workflow_info','work_state','stages','requests','journal','evidence_checks'}

def require(value,message):
    if not value:raise ValueError(message)

def tables(c):
    return {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}

def revision(c):
    if 'alembic_version' not in tables(c):return None
    rows=c.execute('SELECT version_num FROM alembic_version').fetchall()
    require(len(rows)==1,'Ambiguous Alembic version')
    value=rows[0][0]
    require(value in REVISIONS,'Unsupported/newer Alembic revision: '+value)
    return value

def check_supported(c):
    value=revision(c)
    markers=c.execute('SELECT version,complete FROM schema_info').fetchall()
    require(len(markers)==1 and tuple(markers[0])==(1,1),'Unsupported/incomplete storage schema')
    return value

def require_current(c):
    require(check_supported(c)==CURRENT,'Explicit working-copy schema upgrade required before mutation')


def identify_working(c,db):
    require(REQUIRED <= tables(c),'Missing known working schema tables')
    check_supported(c)
    info=c.execute('SELECT version,baseline_sha256,baseline_path FROM workflow_info').fetchall()
    require(len(info)==1 and info[0][0]==1,'Unsupported/ambiguous workflow identity')
    baseline=pathlib.Path(info[0][2]).resolve();db=pathlib.Path(db).resolve()
    require(baseline!=db and baseline.is_file(),'Upgrade must target an independent working copy, never its baseline')
    require((baseline.stat().st_dev,baseline.stat().st_ino)!=(db.stat().st_dev,db.stat().st_ino),'Working database must not be a baseline hardlink')
    require(reg.digest(baseline)==info[0][1],'Referenced immutable baseline hash changed')
    with reg.connect(baseline) as source:
        require('workflow_info' not in tables(source),'Referenced baseline must be an immutable import, not another working DB')


def fingerprint(c,selected=None):
    names=sorted(selected or tables(c))
    output={}
    for name in names:
        require(name.replace('_','').isalnum(),'Unexpected table identifier')
        h=hashlib.sha256();count=0
        # All adopted tables are ordinary SQLite rowid tables. Do not fabricate
        # keys for provenance/schema_info/catalog_info or collapse duplicate rows.
        for row in c.execute('SELECT * FROM "'+name+'" ORDER BY rowid'):
            h.update(reg.encode(list(row)).encode());h.update(b'\n');count+=1
        output[name]={'rows':count,'sha256':h.hexdigest()}
    output['_objects']=[tuple(r) for r in c.execute("SELECT type,name,sql FROM sqlite_master WHERE type IN ('trigger','index') AND sql IS NOT NULL ORDER BY type,name")]
    return output


def plan(db):
    with reg.connect(db) as c:
        identify_working(c,db)
        old=revision(c)
        return {'database':str(pathlib.Path(db).resolve()),'current_revision':old,'target_revision':CURRENT,'steps':list(REVISIONS[REVISIONS.index(old)+1:] if old else REVISIONS),'read_only':True,'backup_required':old!=CURRENT}


def upgrade(db,backup=None,apply=False,fail_after=None):
    db=pathlib.Path(db);result=plan(db)
    if not apply or not result['steps']:return result
    require(backup is not None,'Explicit new backup path required')
    backup=pathlib.Path(backup)
    require(not backup.exists() and backup.resolve()!=db.resolve(),'Backup must be a new independent file')
    # Hold the same observation connection across backup and lock acquisition;
    # data_version detects concurrent commits in the gap. Backup is a consistent
    # SQLite snapshot, not a file copy that could omit WAL content.
    source=sqlite3.connect(db,isolation_level=None);source.row_factory=sqlite3.Row
    version=source.execute('PRAGMA data_version').fetchone()[0]
    dest=sqlite3.connect(backup)
    source.backup(dest);dest.close()
    with reg.connect(backup) as check:
        require(check.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not check.execute('PRAGMA foreign_key_check').fetchall(),'Backup integrity failed')
        baseline_fingerprint=fingerprint(check)
    unit=orm.Unit(db,write=True)
    connection=unit.connection
    observation=source
    source=unit.raw
    try:
        require(observation.execute('PRAGMA data_version').fetchone()[0]==version,'Working DB changed while backing up; retained backup, retry explicitly with new path')
        identify_working(source,db)
        require(fingerprint(source)==baseline_fingerprint,'Backup differs from locked working state')
        context=MigrationContext.configure(connection,opts={'transactional_ddl':True})
        op=Operations(context)
        before_names=tables(source)
        previous_migrations=[tuple(r) for r in source.execute('SELECT * FROM migration_journal ORDER BY sequence')] if 'migration_journal' in before_names else []
        for step in result['steps']:
            if step=='0001_adopt':
                op.create_table('alembic_version',Column('version_num',Text,primary_key=True,nullable=False))
                op.create_table('migration_journal',Column('sequence',Integer,primary_key=True),Column('revision',Text,nullable=False),Column('applied_at',Text,nullable=False),Column('backup_sha256',Text,nullable=False),Column('previous_fingerprint',Text,nullable=False))
                op.execute("CREATE TRIGGER migration_no_update BEFORE UPDATE ON migration_journal BEGIN SELECT RAISE(ABORT,'append-only migration journal'); END")
                op.execute("CREATE TRIGGER migration_no_delete BEFORE DELETE ON migration_journal BEGIN SELECT RAISE(ABORT,'append-only migration journal'); END")
                connection.exec_driver_sql('INSERT INTO alembic_version VALUES (?)',(step,))
            elif step=='0002_workflow_indexes':
                op.create_index('workflow_assignment_lookup','work_state',['assignment'])
                op.create_index('workflow_blocker_lookup','work_state',['blocker'])
                op.create_index('workflow_stage_lookup','stages',['stage','record_id'])
                connection.exec_driver_sql('UPDATE alembic_version SET version_num=?',(step,))
            connection.exec_driver_sql('INSERT INTO migration_journal(revision,applied_at,backup_sha256,previous_fingerprint) VALUES (?,?,?,?)',(step,datetime.datetime.now(datetime.timezone.utc).isoformat(),reg.digest(backup),reg.encode(baseline_fingerprint)))
            if fail_after==step:raise RuntimeError('Injected migration failure for rollback test')
        after=fingerprint(source,before_names)
        require(all(after[k]==v for k,v in baseline_fingerprint.items() if k not in ('_objects','alembic_version','migration_journal')),'Migration changed adopted table contents')
        migration_rows=[tuple(r) for r in source.execute('SELECT * FROM migration_journal ORDER BY sequence')]
        require(migration_rows[:len(previous_migrations)]==previous_migrations and len(migration_rows)==len(previous_migrations)+len(result['steps']),'Migration history was changed or not appended exactly once per revision')
        require(revision(source)==CURRENT,'Migration failed to reach requested revision')
        require(set(baseline_fingerprint['_objects'])<=set(after['_objects']),'Migration changed existing triggers/indexes')
        require(not source.execute('PRAGMA foreign_key_check').fetchall() and source.execute('PRAGMA integrity_check').fetchone()[0]=='ok','Post-migration integrity failed')
        connection.commit()
        result.update(applied=True,backup=str(backup.resolve()),backup_sha256=reg.digest(backup),preserved_table_fingerprint=baseline_fingerprint)
        return result
    except Exception:
        connection.rollback();raise
    finally:
        unit.close();observation.close()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',type=pathlib.Path,required=True);p.add_argument('--backup',type=pathlib.Path);p.add_argument('--apply',action='store_true');a=p.parse_args()
    print(json.dumps(upgrade(a.db,a.backup,a.apply),indent=2))
