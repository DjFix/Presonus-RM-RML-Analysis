#!/usr/bin/env python3
"""Reproducible full-data SQLite sidecar benchmark; never writes canonical JSON."""
import argparse
import copy
import json
import pathlib
import sqlite3
import shutil
import sys
import platform
import time
import registry as r
import workflow as w
import schema
from importlib.metadata import version

def timed(call):
    start=time.perf_counter();value=call();return value,time.perf_counter()-start

def run(baseline,snapshots,library,out):
    out.mkdir(parents=True,exist_ok=False)
    sources=pathlib.Path(__file__).resolve().parent
    frozen={str(p.relative_to(sources)):r.digest(p) for p in sources.rglob('*') if p.is_file() and p.suffix in ('.py','.md','.txt')}
    (out/'executed-source').mkdir()
    for name in frozen:
        target=out/'executed-source'/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(sources/name,target)
    report={'source_sha256_before':frozen,'command':sys.argv,'python':sys.version,'platform':platform.platform(),'cache_conditions':'No OS page-cache flush or privileged cache controls. First observed process use versus repeated warm operations; not disk-cold guarantees. Every evidence validation freshly hashes files with an operation-local cache.', 'baseline':str(baseline.resolve()),'baseline_sha256':r.digest(baseline),'sqlite_version':sqlite3.sqlite_version,'dependencies':{name:version(name) for name in ('SQLAlchemy','alembic','greenlet','Mako','MarkupSafe','typing_extensions')}}
    for n in (1,2):
        value,seconds=timed(lambda:r.import_snapshots(snapshots,out/('import-'+str(n)+'.sqlite')))
        report['import_'+str(n)]={'elapsed_seconds':seconds,**value}
    db=out/'workflow-working.sqlite'
    _,report['working_copy_seconds']=timed(lambda:w.working_copy(baseline,db))
    report['migration'],report['migration_seconds']=timed(lambda:schema.upgrade(db,out/'pre-migration.sqlite',True))
    with r.connect(db) as c:
        first=c.execute('SELECT * FROM records WHERE status="ready" ORDER BY ordinal LIMIT 1').fetchone()
        selected=dict(first);entry=r.restored(c,first)
        source=next(iter(entry['sources']))
    cases={'original_key':('SELECT id FROM records WHERE elf=? AND mangled=?',(selected['elf'],selected['mangled'])), 'status':('SELECT count(*) FROM records WHERE status=?',('pending',)), 'proof':('SELECT count(*) FROM records WHERE proof=?',(selected['proof'],)), 'source':('SELECT count(DISTINCT x.record_id) FROM record_sets x JOIN source_members m ON m.set_id=x.set_id JOIN source_versions v ON v.id=m.version_id WHERE v.path=?',(source,)), 'counts':('SELECT status,count(*) FROM records GROUP BY status',())}
    report['queries']={}
    for name,(sql,args) in cases.items():
        timings=[]
        for i in range(6):
            def call():
                with r.connect(db) as c:return [list(v) for v in c.execute(sql,args)]
            value,elapsed=timed(call);timings.append(elapsed)
        report['queries'][name]={'first_open_and_query_seconds':timings[0],'warm_reopen_seconds':timings[1:],'result':value}
    with r.connect(db) as c:
        keys=[dict(row) for row in c.execute('SELECT elf,mangled FROM records ORDER BY id LIMIT 16')]
    def payload(request,keys,revision=0):
        return {'request_id':request,'actor':'sqlite-benchmark','operations':[{'kind':'assign','original_elf_sha256':v['elf'],'mangled':v['mangled'],'expected_revision':revision,'value':'sqlite-benchmark','reason':'Explicit isolated sidecar workflow timing; no readiness claim'} for v in keys]}
    single=payload('single',keys[:1]);batch=payload('batch',keys[1:])
    for name,body,preflight in [('single_dryrun',single,True),('single_commit',single,False),('single_idempotent',single,False),('batch_dryrun',batch,True),('batch_commit',batch,False)]:
        before=r.digest(db);value,elapsed=timed(lambda:w.operate(db,library,body,preflight))
        report[name]={'elapsed_seconds':elapsed,'result':value,'database_unchanged':before==r.digest(db)}
    bad=payload('rollback',keys[:2],1);bad['operations'][1]['expected_revision']=999
    before=r.digest(db);start=time.perf_counter()
    try:w.operate(db,library,bad,False);raise AssertionError('Expected stale revision rejection')
    except ValueError as exc:report['rollback']={'elapsed_seconds':time.perf_counter()-start,'error':str(exc),'database_unchanged':before==r.digest(db)}
    report['audit'],report['audit_seconds']=timed(lambda:w.query(db,'audit',{}))
    # Revalidate and reseal one already-ready record in the isolated working DB.
    # This refreshes formatting binding exactly as the legacy merger does.
    entry['formatting_reference']='validation/formatting.json';entry['formatting_sha256']=r.digest(library/'validation/formatting.json')
    with r.connect(db) as c:revision=c.execute('SELECT revision FROM work_state WHERE record_id=?',(selected['id'],)).fetchone()[0]
    body={'request_id':'evidence-revalidate','actor':'sqlite-benchmark','operations':[{'kind':'classify','original_elf_sha256':selected['elf'],'mangled':selected['mangled'],'expected_revision':revision,'target':'ready','entry':entry,'previous_validation_sha256':entry['validation_sha256'],'reason':'Fresh isolated replay of existing ready classification with current formatting binding'}]}
    (out/'classification-manifest.json').write_text(json.dumps(body,indent=2)+'\n')
    for name,preflight in [('classification_dryrun',True),('classification_commit',False)]:
        start=time.perf_counter()
        try:report[name]={'result':w.operate(db,library,body,preflight),'elapsed_seconds':time.perf_counter()-start}
        except (ValueError,KeyError,FileNotFoundError) as exc:report[name]={'rejected':str(exc),'elapsed_seconds':time.perf_counter()-start}
    with r.connect(baseline) as c:
        report['lossless_baseline'],report['baseline_validation_seconds']=timed(lambda:r.validate(c,snapshots))
        for status in ('ready','pending'):
            target=out/(status+'-export.json');_,elapsed=timed(lambda:r.export(c,status,target))
            expected=json.loads((snapshots/(status+'.json')).read_bytes());actual=json.loads(target.read_bytes());assert expected==actual
            del expected,actual
            report[status+'_export']={'stream_seconds':elapsed,'bytes':target.stat().st_size,'parsed_equal':True}
    for n in (1,2):
        value,elapsed=timed(lambda:w.validate_all(db,library))
        (out/('full-evidence-'+str(n)+'.json')).write_text(json.dumps(value,indent=2)+'\n')
        report['full_evidence_'+str(n)]={k:v for k,v in value.items() if k!='failures'}
        report['full_evidence_'+str(n)]['failures']=len(value['failures'])
    with r.connect(db) as c:
        report['foreign_key_check']=[list(x) for x in c.execute('PRAGMA foreign_key_check')]
        report['integrity_check']=[list(x) for x in c.execute('PRAGMA integrity_check')]
        report['journal_rows']=c.execute('SELECT count(*) FROM journal').fetchone()[0]
    report['sizes']={p.name:p.stat().st_size for p in out.glob('*.sqlite')}
    report['baseline_unchanged']=r.digest(baseline)==report['baseline_sha256']
    report['source_sha256_after']={name:r.digest(sources/name) for name in frozen}
    assert report['source_sha256_after']==frozen, 'Executed sources changed during benchmark; result not sealed'
    report['source_unchanged']=True
    (out/'benchmark.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('audit',)},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('baseline','snapshots','library','out'):p.add_argument('--'+name,type=pathlib.Path,required=True)
    a=p.parse_args();run(a.baseline,a.snapshots,a.library,a.out)
