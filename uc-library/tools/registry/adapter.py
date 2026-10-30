"""Shared SQLite consumer adapter. Source maps are borrowed read-only per snapshot."""
import datetime
import hashlib
import json
import pathlib
import sqlite3
import uuid
from sqlalchemy import insert
import orm
import registry as reg
import schema
import workflow


def resolve_db(library, explicit_db=None):
    library=pathlib.Path(library).resolve()
    if explicit_db is not None:
        path=pathlib.Path(explicit_db)
        return (library/path).resolve() if not path.is_absolute() else path.resolve()
    pointer=library/'validation/registry-sqlite/ACTIVE.json'
    payload=json.loads(pointer.read_text())
    item=payload['database'];path=pathlib.Path(item.get('absolute_path') or item['path'])
    return path.resolve() if path.is_absolute() else (library.parent/path).resolve()


def generation_guard(c):
    # Exclude catalog task traffic; include readiness work revisions and history.
    names=('registries','records','record_sets','source_sets','source_versions','source_members','work_state','stages','requests','journal')
    h=hashlib.sha256()
    for name in names:
        h.update(name.encode())
        for row in c.execute('SELECT * FROM '+name+' ORDER BY rowid'):
            h.update(reg.encode(list(row)).encode());h.update(b'\n')
    return h.hexdigest()


class RegistrySnapshot:
    def __init__(self,db):
        self.db=pathlib.Path(db).resolve();self.c=None;self.source_sets={};self.documents={}
    def __enter__(self):
        self.c=reg.connect(self.db)
        try:
            self.c.execute('BEGIN');schema.require_current(self.c)
            self.guard=generation_guard(self.c)
            return self
        except Exception:
            self.c.close();self.c=None;raise
    def __exit__(self,*args):
        self.c.rollback();self.c.close();self.c=None
    def metadata(self,status):
        row=self.c.execute('SELECT metadata FROM registries WHERE status=?',(status,)).fetchone()
        if row is None:raise ValueError('Unknown registry status: '+status)
        return json.loads(row[0])
    def restore(self,row):
        result=json.loads(row['metadata'])
        for field,sid in self.c.execute('SELECT field,set_id FROM record_sets WHERE record_id=?',(row['id'],)):
            if sid not in self.source_sets:
                self.source_sets[sid]={p:json.loads(d) for p,d in self.c.execute('SELECT v.path,v.digest_json FROM source_members m JOIN source_versions v ON v.id=m.version_id WHERE m.set_id=? ORDER BY m.ordinal',(sid,))}
            result[field]=self.source_sets[sid]
        return result
    def iter_records(self,status):
        for row in self.c.execute('SELECT * FROM records WHERE status=? ORDER BY ordinal',(status,)):
            yield self.restore(row)
    def load_registry(self,status):
        if status not in self.documents:
            self.documents[status]=dict(self.metadata(status),functions=list(self.iter_records(status)))
        return self.documents[status]
    @property
    def ready(self):return self.load_registry('ready')
    @property
    def pending(self):return self.load_registry('pending')
    def provenance(self):
        return {'database':str(self.db),'guard':self.guard,'storage_provenance':[json.loads(r[0]) for r in self.c.execute('SELECT json FROM provenance')],'alembic_revision':schema.revision(self.c)}


def snapshot(library,db=None):return RegistrySnapshot(resolve_db(library,db))


class FreshEvidence(workflow.Evidence):
    """Fresh operation-local hashes/JSON, plus absolute-path legacy helpers."""
    def sha(self,path):
        path=pathlib.Path(path)
        if not path.is_absolute():path=self.library/path
        resolved=path.resolve()
        if resolved.is_relative_to(self.library):return self.file(str(path.relative_to(self.library)))
        if resolved.is_relative_to(self.repository/'third_party/ccl-framework/core'):
            return self.file(str(path.relative_to(self.repository)),repository=True)
        raise ValueError('Evidence outside library/pinned Core: '+str(path))
    def json(self,path):
        path=pathlib.Path(path)
        if path.is_absolute():path=path.relative_to(self.library)
        return self.read(str(path))


def _entries(document):
    return document['functions'] if isinstance(document,dict) and 'functions' in document else document

def _key(entry):return entry['original_elf_sha256'],entry['mangled']


def commit_snapshot(ready,pending,expected_guard,*,library,db=None,actor,reason,request_id=None,demotions=(),promotions=(),metadata=None,backup_dir=None,precommit_guard=None,operation_metadata=None,demotion_manifests=None):
    """Persist already-gate-validated merger output; caller retains all proof gates.

    No implicit deletion, no unguarded demotion, no legacy JSON write. Only
    changed rows are journaled. Sources remain normalized. Caller must close its
    read snapshot first; optimistic guard binds the validated generation.
    """
    workflow.require(isinstance(actor,str) and actor.strip() and isinstance(reason,str) and reason.strip(),'Actor/reason required')
    db=resolve_db(library,db);new={};status_for={}
    for status,document in (('ready',ready),('pending',pending)):
        for entry in _entries(document):
            key=_key(entry);workflow.require(key not in new,'Ready/pending original keys must be unique and disjoint')
            workflow.require(entry.get('portable_ready') is (status=='ready'),'Classification flag mismatch')
            if status=='ready':workflow.require(isinstance(entry.get('domain'),str) and entry['domain'].strip(),'Bounded ready domain required')
            else:workflow.require(entry.get('cpp_compiled') is True and entry.get('mangling_namespace_checked') is True,'Pending compile/signature gates required')
            new[key]=entry;status_for[key]=status
    metadata=metadata or {}
    workflow.require(isinstance(metadata,dict) and set(metadata)<= {'ready','pending'},'Metadata status keys must be ready/pending')
    for status,values in metadata.items():
        workflow.require(isinstance(values,dict) and 'functions' not in values,'Top-level metadata must exclude functions')
    if isinstance(demotions,dict):demotions=demotions.values()
    demotions={_key(v):v for v in demotions};promotions={_key(v) if isinstance(v,dict) else tuple(v) for v in promotions}
    with RegistrySnapshot(db) as old:
        workflow.require(old.guard==expected_guard,'Registry generation changed; repeat preflight')
        previous={};rows={};changed=[]
        for row in old.c.execute('SELECT * FROM records ORDER BY id'):
            key=(row['elf'],row['mangled']);previous[key]=old.restore(row);rows[key]=dict(row)
        missing=set(previous)-set(new)
        workflow.require(not missing,'Implicit removal forbidden; explicitly review stale records: '+str(sorted(missing)[:10]))
        for key,entry in new.items():
            prior=previous.get(key);row=rows.get(key)
            if row and row['status']=='ready' and status_for[key]=='pending':
                guard=demotions.get(key)
                workflow.require(guard is not None and guard.get('previous_validation_sha256')==prior.get('validation_sha256') and isinstance(guard.get('reason'),str) and guard['reason'].strip(),'Guarded demotion manifest required')
                workflow.require(entry.get('validation_sha256')!=prior.get('validation_sha256'),'Demotion needs fresh pending proof')
            if row and row['status']=='pending' and status_for[key]=='ready' and promotions:
                workflow.require(key in promotions,'Promotion key missing from explicit promotion list')
            if prior!=entry or row is None or row['status']!=status_for[key]:changed.append(key)
        metadata_changes={status:{'before':old.metadata(status),'after':values} for status,values in metadata.items() if old.metadata(status)!=values}
        if not changed and not metadata_changes:
            if precommit_guard:precommit_guard()
            return {'changed':0,'metadata_changed':[],'guard':old.guard,'database':str(db),'no_op':True}
        backup_dir=pathlib.Path(backup_dir) if backup_dir else db.parent/'admission-history'
        backup_dir.mkdir(parents=True,exist_ok=True)
        backup=backup_dir/(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')+'-'+uuid.uuid4().hex+'.sqlite')
        dest=sqlite3.connect(backup);old.c.backup(dest);dest.close()
    with reg.connect(backup) as check:
        workflow.require(check.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not check.execute('PRAGMA foreign_key_check').fetchall(),'Previous DB backup integrity failed')
    backup.chmod(0o444)
    unit=orm.Unit(db,write=True);c=unit.raw;s=unit.session
    try:
        schema.require_current(c);workflow.require(generation_guard(c)==expected_guard,'Registry changed after backup; repeat preflight')
        if precommit_guard:precommit_guard()
        request_id=request_id or 'merger-'+uuid.uuid4().hex
        payload={'changed_keys':sorted(changed),'metadata_changes':metadata_changes,'operation_metadata':operation_metadata or {},'demotion_manifests':demotion_manifests or {},'expected_guard':expected_guard,'backup_sha256':reg.digest(backup)}
        checksum=hashlib.sha256(reg.encode(payload).encode()).hexdigest()
        workflow.require(c.execute('SELECT 1 FROM requests WHERE request_id=?',(request_id,)).fetchone() is None,'Merger request id already used')
        s.add(orm.Request(request_id=request_id,digest=checksum,result=reg.encode({'changed':len(changed),'backup':str(backup),'metadata_changes':metadata_changes,'operation_metadata':operation_metadata or {},'demotion_manifests':demotion_manifests or {}})));s.flush()
        for key in changed:
            entry=new[key];status=status_for[key];oldrow=rows.get(key)
            if oldrow:
                rid=oldrow['id'];work=s.get(orm.WorkState,rid);oldwork=workflow.state(c,rid)
                before={'classification':oldrow['status'],'record_metadata':json.loads(oldrow['metadata']),'work':oldwork,'source_sets':[dict(r) for r in c.execute('SELECT field,set_id FROM record_sets WHERE record_id=?',(rid,))]}
            else:
                ordinal=c.execute('SELECT coalesce(max(ordinal),-1)+1 FROM records WHERE status=?',(status,)).fetchone()[0]
                record=orm.Record(status=status,ordinal=ordinal,elf=key[0],mangled=key[1],metadata_json='{}');s.add(record);s.flush();rid=record.id
                work=orm.WorkState(record_id=rid,revision=-1);s.add(work);s.flush();oldwork={'revision':-1};before={'classification':None,'record_metadata':None,'work':oldwork,'source_sets':[]}
            workflow.replace_record(c,s,rid,entry,status);work.revision+=1;s.flush()
            current=c.execute('SELECT * FROM records WHERE id=?',(rid,)).fetchone()
            after={'classification':status,'record_metadata':json.loads(current['metadata']),'work':workflow.state(c,rid),'source_sets':[dict(r) for r in c.execute('SELECT field,set_id FROM record_sets WHERE record_id=?',(rid,))]}
            bindings={'demotion':demotions.get(key),'demotion_manifests':demotion_manifests or (operation_metadata or {}).get('demotion_manifests',{}),'operation_request':request_id,'backup':str(backup),'backup_sha256':payload['backup_sha256'],'source_sets':after['source_sets'],'validation':entry.get('validation'),'validation_sha256':entry.get('validation_sha256')}
            s.add(orm.Journal(request_id=request_id,record_id=rid,actor=actor,timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),reason=demotions.get(key,{}).get('reason',reason),previous_revision=oldwork['revision'],new_revision=work.revision,previous_state=reg.encode(before),new_state=reg.encode(after),bindings=reg.encode(bindings)))
        if metadata:
            for status,values in metadata.items():
                c.execute('UPDATE registries SET metadata=? WHERE status=?',(reg.encode(values),status))
        s.flush()
        if precommit_guard:precommit_guard()
        workflow.require(not c.execute('PRAGMA foreign_key_check').fetchall(),'Admission foreign-key failure')
        unit.commit()
        return {'changed':len(changed),'metadata_changed':list(metadata_changes),'guard':generation_guard(c),'database':str(db),'backup':str(backup),'backup_sha256':payload['backup_sha256'],'request_id':request_id}
    except Exception:unit.rollback();raise
    finally:unit.close()
