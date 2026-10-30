#!/usr/bin/env python3
"""Explicit SQLite-only work tracking and evidence-gated classification operators."""
import argparse
import datetime
from collections import OrderedDict
import hashlib
import json
import pathlib
import sqlite3
import time
import registry as reg
import orm
import schema
from sqlalchemy import insert

STAGES = {
    'catalogued': ('catalogued',),
    'bytes_extracted': ('bytes_extracted',),
    'bytes_verified': ('bytes_verified',),
    'pseudocode': ('pseudocode_exported',),
    'compiled': ('cpp_compiled',),
    'namespace_mangling': ('mangling_namespace_checked', 'compiled_mangled_names_matched', 'compiled_original_mangled_names_matched'),
    'behavior': ('cpp_differential_passed', 'arm_differential_passed'),
    'hardware': ('hardware_validation_passed',),
}
SCHEMA = '''
CREATE TABLE work_state(record_id INTEGER PRIMARY KEY REFERENCES records(id), revision INTEGER NOT NULL DEFAULT 0, assignment TEXT, blocker TEXT);
INSERT INTO work_state(record_id) SELECT id FROM records;
CREATE TABLE stages(record_id INTEGER REFERENCES records(id), stage TEXT NOT NULL, proof TEXT NOT NULL, proof_sha256 TEXT NOT NULL, domain TEXT NOT NULL, PRIMARY KEY(record_id,stage));
CREATE TABLE requests(request_id TEXT PRIMARY KEY, digest TEXT NOT NULL, result TEXT NOT NULL);
CREATE TABLE evidence_checks(request_id TEXT REFERENCES requests(request_id), path TEXT NOT NULL, sha256 TEXT NOT NULL, fingerprint TEXT NOT NULL, PRIMARY KEY(request_id,path));
CREATE TABLE journal(sequence INTEGER PRIMARY KEY, request_id TEXT NOT NULL REFERENCES requests(request_id), record_id INTEGER NOT NULL REFERENCES records(id), actor TEXT NOT NULL, timestamp TEXT NOT NULL, reason TEXT NOT NULL, previous_revision INTEGER NOT NULL, new_revision INTEGER NOT NULL, previous_state TEXT NOT NULL, new_state TEXT NOT NULL, bindings TEXT NOT NULL);
CREATE TRIGGER journal_no_update BEFORE UPDATE ON journal BEGIN SELECT RAISE(ABORT,'append-only journal'); END;
CREATE TRIGGER journal_no_delete BEFORE DELETE ON journal BEGIN SELECT RAISE(ABORT,'append-only journal'); END;
CREATE TABLE workflow_info(version INTEGER NOT NULL, baseline_sha256 TEXT NOT NULL, baseline_path TEXT NOT NULL);
'''

def require(condition, message):
    if not condition:
        raise ValueError(message)

class Evidence:
    """Fresh, operation-local hash cache. Never persists or reuses old proof results."""
    def __init__(self, library):
        self.library = pathlib.Path(library).resolve()
        self.repository = self.library.parent
        self.cache = {}
        self.paths = {}
        self.bytes_hashed = 0
        self.hash_seconds = 0.0
        self.started = time.monotonic()
        self.originals = None
        self.parsed = OrderedDict()
        self.json_parses = 0
        self.json_cache_hits = 0
        self.source_domains = set()
        self.source_domain_cache_hits = 0
        self.integration_checked = False

    def file(self, relative, repository=False):
        root = self.repository if repository else self.library
        key=(str(relative),repository)
        path=self.paths.get(key)
        if path is None:
            path = (root / relative).resolve()
            require(path.is_relative_to(root) and path.is_file(), 'Evidence path outside root or missing: '+str(relative))
            if repository:
                core = (root/'third_party/ccl-framework/core').resolve()
                require(not pathlib.Path(relative).is_absolute() and pathlib.Path(relative).parts[:3] == ('third_party','ccl-framework','core') and path.is_relative_to(core), 'Core dependency must use explicit repository-relative Core path')
            self.paths[key]=path
        if path not in self.cache:
            before = path.stat()
            started = time.monotonic()
            value = reg.digest(path)
            self.hash_seconds += time.monotonic()-started
            after = path.stat()
            fingerprint = lambda s: (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
            require(fingerprint(before)==fingerprint(after), 'Evidence changed while hashing: '+str(path))
            self.cache[path] = (value,fingerprint(after))
            self.bytes_hashed += after.st_size
        return self.cache[path][0]

    def read(self, relative):
        self.file(relative)
        path=(self.library/relative).resolve()
        if path in self.parsed:
            self.json_cache_hits += 1
            self.parsed.move_to_end(path)
            return self.parsed[path]
        value=json.loads(path.read_bytes())
        self.json_parses += 1
        self.parsed[path]=value
        if len(self.parsed)>8:
            self.parsed.popitem(last=False)
        return value

    def unchanged(self):
        for (relative,repository),path in self.paths.items():
            root=self.repository if repository else self.library
            require((root/relative).resolve()==path,'Evidence path resolution changed after validation: '+relative)
        for p, (_, expected) in self.cache.items():
            s=p.stat()
            require((s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)==expected, 'Evidence changed after validation: '+str(p))

    def summary(self):
        return {'source_domains_checked':len(self.source_domains),'source_domain_cache_hits':self.source_domain_cache_hits,'json_parses':self.json_parses,'json_cache_hits':self.json_cache_hits,'files_hashed':len(self.cache),'bytes_hashed':self.bytes_hashed,'hash_seconds':self.hash_seconds,'total_evidence_seconds':time.monotonic()-self.started,'cache':'fresh per operation; duplicate paths hashed once; stat fingerprint rechecked before commit'}

    def original(self, entry):
        if self.originals is None:
            self.originals = {}
            for role in ('client','server'):
                root='recovered-all/'+role+'/'
                manifest=self.read(root+'manifest.json')
                for symbol in self.read(root+'symbols.json'):
                    if symbol['kind']=='STT_FUNC' and isinstance(symbol['section'],int) and symbol['size']:
                        key=(manifest['sha256'],symbol['mangled'])
                        self.originals.setdefault(key,[]).append((role,symbol['address']))
        key=(entry['original_elf_sha256'],entry['mangled'])
        require(key in self.originals,'Original ELF/symbol not in native catalog')
        if 'original_address' in entry:
            require(any(a==entry['original_address'] for _,a in self.originals[key]),'Original address mismatch')
        if entry.get('role') is not None:
            require(any(role==entry['role'] for role,_ in self.originals[key]),'Original role mismatch')

    def source_checks(self, entry, compiled=True, source_token=None):
        require(isinstance(entry.get('sources'),dict) and bool(entry['sources']), 'Nonempty source bindings required')
        token=(source_token if source_token is not None else hashlib.sha256(reg.encode({field:entry.get(field,{}) for field in reg.FIELDS}).encode()).hexdigest(),compiled)
        if token in self.source_domains:
            self.source_domain_cache_hits+=1
            return
        formatting=self.read('validation/formatting.json') if compiled else None
        if compiled:
            require(formatting.get('format_check_passed') is True,'Formatting failed')
            if not self.integration_checked:
                integration=self.read('validation/integration.json')
                require(integration.get('ctest_passed') is True,'Integration failed')
                for p,h in integration['files'].items():
                    require(self.file(p)==h,'Stale integration source: '+p)
                self.integration_checked=True
        for p,h in entry['sources'].items():
            require(self.file(p)==h,'Stale source: '+p)
            if compiled and pathlib.Path(p).suffix in ('.cpp','.hpp','.h'):
                require(formatting['files'].get(p)==h,'Source not format-checked: '+p)
        sources=entry.get('repository_sources',{})
        require(isinstance(sources,dict),'Invalid Core source bindings')
        for p,h in sources.items():
            require(self.file(p,repository=True)==h,'Stale Core dependency: '+p)
        self.source_domains.add(token)
        # Historical formatting_sha256 is provenance; the legacy gate checks the
        # current formatting map against every current source and refreshes ready
        # bindings on admission. Pending metadata retains its historical reference.

    def proof(self, entry):
        require(isinstance(entry.get('validation'),str) and isinstance(entry.get('validation_sha256'),str),'Proof path and SHA-256 required')
        require(self.file(entry['validation'])==entry['validation_sha256'],'Proof hash mismatch')
        return self.read(entry['validation'])

    def classify(self, entry, target, source_token=None):
        self.original(entry)
        require(entry.get('hardware_verified',False) is False,'Hardware verification requires the separate authorized observation stage')
        self.source_checks(entry,source_token=source_token)
        proof=self.proof(entry)
        if target=='ready':
            require(isinstance(entry.get('domain'),str) and entry['domain'].strip(),'Bounded nonempty domain required')
            require(entry.get('portable_ready') is True,'Ready requires explicit portable_ready')
            passed=proof.get('cpp_differential_passed',proof.get('arm_differential_passed',False))
            checked=proof.get('compiled_mangled_names_matched',proof.get('compiled_original_mangled_names_matched',proof.get('mangling_namespace_checked',False)))
            detailed=proof.get('functions',[])
            names=proof.get('mangled_names',[v.get('mangled') for v in detailed if isinstance(v,dict)] or [proof.get('mangled')])
            require(passed is True and checked is True and proof.get('portable_ready',True) is True and entry['mangled'] in names,'Ready proof lacks passing behavior/signature coverage')
            if any(isinstance(v,dict) and 'original_elf_sha256' in v for v in detailed):
                require(any(isinstance(v,dict) and v.get('mangled')==entry['mangled'] and v.get('original_elf_sha256')==entry['original_elf_sha256'] for v in detailed),'Proof ELF identity mismatch')
        else:
            require(target=='pending' and entry.get('portable_ready') is False,'Pending must explicitly remain portable_ready false')
            require(entry.get('cpp_compiled') is True and entry.get('mangling_namespace_checked') is True,'Pending requires compile/signature checks')
            # Legacy pending proof is the fragment itself: require exact entry membership.
            members=proof.get('functions',[]) if isinstance(proof,dict) else proof
            require(isinstance(members,list) and any(isinstance(v,dict) and v.get('mangled')==entry['mangled'] and v.get('original_elf_sha256')==entry['original_elf_sha256'] and v.get('portable_ready') is False and v.get('cpp_compiled') is True and v.get('mangling_namespace_checked') is True and v.get('sources')==entry['sources'] and v.get('repository_sources',{})==entry.get('repository_sources',{}) for v in members),'Pending proof must freshly cover the original key and compile/signature checks')
            for field in ('behavior_validation','compile_validation'):
                if entry.get(field):
                    require(self.file(entry[field])==entry[field+'_sha256'],'Pending underlying proof mismatch')
        return proof

    def stage(self, entry, op):
        stage=op['stage']
        require(stage in STAGES,'Unsupported evidence stage')
        require(isinstance(op.get('domain'),str) and op['domain'].strip(),'Stage requires bounded domain')
        self.original(entry)
        candidate=dict(entry,validation=op['proof'],validation_sha256=op['proof_sha256'])
        proof=self.proof(candidate)
        detailed=proof.get('functions',[])
        names=proof.get('mangled_names',[])
        require((proof.get('original_elf_sha256')==entry['original_elf_sha256'] and (proof.get('mangled')==entry['mangled'] or entry['mangled'] in names)) or any(isinstance(v,dict) and v.get('mangled')==entry['mangled'] and v.get('original_elf_sha256')==entry['original_elf_sha256'] for v in detailed),'Stage proof must identify exact original key')
        require(any(proof.get(flag) is True for flag in STAGES[stage]),'Stage proof lacks explicit successful stage flag')
        if stage=='hardware':
            require(proof.get('hardware_verified') is True and isinstance(proof.get('device_identifier'),str) and proof['device_identifier'].strip(),'Hardware proof requires actual device identity and explicit verified observation')
            authorization=proof.get('hardware_authorization')
            require(isinstance(authorization,dict) and isinstance(authorization.get('path'),str) and isinstance(authorization.get('sha256'),str),'Hardware proof requires explicit recorded user authorization binding')
            require(self.file(authorization['path'])==authorization['sha256'],'Hardware authorization hash mismatch')
            observations=proof.get('hardware_observations')
            require(isinstance(observations,list) and bool(observations),'Hardware proof requires nonempty actual observation artifact bindings')
            for observation in observations:
                require(isinstance(observation,dict) and self.file(observation['path'])==observation['sha256'],'Hardware observation hash mismatch')
            self.source_checks(entry)
        if stage in ('compiled','namespace_mangling','behavior'):
            self.source_checks(entry)
        return proof


def working_copy(baseline, output):
    require(not output.exists(),'Refusing to replace working database')
    with reg.connect(baseline) as source:
        require(source.execute("SELECT count(*) FROM sqlite_master WHERE name='workflow_info'").fetchone()[0]==0,'Working copy must derive from immutable import baseline')
        dest=sqlite3.connect(output)
        try:
            source.backup(dest)
            dest.executescript(SCHEMA)
            dest.execute('INSERT INTO workflow_info VALUES (1,?,?)',(reg.digest(baseline),str(baseline.resolve())))
            dest.commit()
        finally:
            dest.close()


def state(c,rid):
    row=c.execute('SELECT * FROM work_state WHERE record_id=?',(rid,)).fetchone()
    require(row is not None,'Missing work state')
    return dict(row)


def replace_record(c,session,rid,entry,target):
    row=dict(entry)
    c.execute('DELETE FROM record_sets WHERE record_id=?',(rid,))
    for field in reg.FIELDS:
        if field not in row or not isinstance(row[field],dict):
            continue
        sources=row.pop(field)
        sid=hashlib.sha256(reg.encode(list(sources.items())).encode()).hexdigest()
        exists=c.execute('SELECT 1 FROM source_sets WHERE id=?',(sid,)).fetchone()
        if not exists:
            c.execute('INSERT INTO source_sets VALUES (?)',(sid,))
            for n,(p,d) in enumerate(sources.items()):
                d=reg.encode(d)
                c.execute('INSERT OR IGNORE INTO source_versions(path,digest_json) VALUES (?,?)',(p,d))
                vid=c.execute('SELECT id FROM source_versions WHERE path=? AND digest_json=?',(p,d)).fetchone()[0]
                c.execute('INSERT INTO source_members VALUES (?,?,?)',(sid,n,vid))
        c.execute('INSERT INTO record_sets VALUES (?,?,?)',(rid,field,sid))
    old=c.execute('SELECT status,ordinal FROM records WHERE id=?',(rid,)).fetchone()
    ordinal=old['ordinal'] if old['status']==target else c.execute('SELECT coalesce(max(ordinal),-1)+1 FROM records WHERE status=?',(target,)).fetchone()[0]
    record=session.get(orm.Record,rid)
    record.status=target;record.ordinal=ordinal;record.proof=row.get('validation');record.metadata_json=reg.encode(row)


def operate(db,library,payload,dry_run=True):
    started=time.monotonic()
    require(isinstance(payload.get('request_id'),str) and payload['request_id'].strip(),'Request id required')
    require(isinstance(payload.get('actor'),str) and payload['actor'].strip(),'Actor required')
    require(isinstance(payload.get('operations'),list) and bool(payload['operations']),'Nonempty operations required')
    checksum=hashlib.sha256(reg.encode(payload).encode()).hexdigest()
    with reg.connect(db) as check:
        schema.require_current(check)
    unit=orm.Unit(db,write=not dry_run)
    c=unit.raw;session=unit.session
    try:
        schema.require_current(c)
        require(c.execute('SELECT version FROM workflow_info').fetchone()[0]==1,'Unsupported workflow schema')
        old=c.execute('SELECT digest,result FROM requests WHERE request_id=?',(payload['request_id'],)).fetchone()
        if old:
            require(old['digest']==checksum,'Request id reused with different payload')
            return dict(json.loads(old['result']),idempotent_replay=True)
        evidence=Evidence(library)
        prepared=[]; seen=set()
        for op in payload['operations']:
            key=(op['original_elf_sha256'],op['mangled'])
            require(key not in seen,'Duplicate original key in one batch');seen.add(key)
            row=c.execute('SELECT * FROM records WHERE elf=? AND mangled=?',key).fetchone()
            if row is None:
                require(op['kind']=='admit','Unknown original key; use explicit evidence-gated admit')
                row={'id':None,'status':None,'elf':key[0],'mangled':key[1]}
                prior={'revision':-1,'assignment':None,'blocker':None}
            else:
                require(op['kind']!='admit','Original key already admitted')
                prior=state(c,row['id'])
            require(op.get('expected_revision')==prior['revision'],'Optimistic revision mismatch')
            require(isinstance(op.get('reason'),str) and op['reason'].strip(),'Explicit reason required')
            entry=reg.restored(c,row) if row['id'] is not None else {'original_elf_sha256':key[0],'mangled':key[1]}
            before={'classification':row['status'],'work':prior,'validation_sha256':entry.get('validation_sha256'),
                    'record_metadata':json.loads(row['metadata']) if row['id'] is not None else None,
                    'source_sets':[dict(v) for v in c.execute('SELECT field,set_id FROM record_sets WHERE record_id=?',(row['id'],))] if row['id'] is not None else [],
                    'stages':[dict(v) for v in c.execute('SELECT stage,proof,proof_sha256,domain FROM stages WHERE record_id=?',(row['id'],))] if row['id'] is not None else []}
            kind=op['kind'];newentry=None
            if kind in ('classify','admit'):
                require(op.get('target') in ('ready','pending'),'Classification must be ready or pending')
                if kind=='classify':
                    require(op.get('previous_validation_sha256')==entry.get('validation_sha256') and bool(entry.get('validation_sha256')),'Previous proof hash guard mismatch')
                else:
                    require(op.get('previous_validation_sha256') is None,'New admission cannot carry a prior proof hash')
                newentry=dict(op['entry'])
                require((newentry['original_elf_sha256'],newentry['mangled'])==key,'Replacement changes original identity')
                classification_proof=evidence.classify(newentry,op['target'])
                if op['target']=='ready':
                    newentry.update(original_function_verified=False,hardware_verified=False,formatting_reference='validation/formatting.json',formatting_sha256=evidence.file('validation/formatting.json'),declaration_uncertainties=newentry.get('declaration_uncertainties',newentry.get('method_declaration_uncertainties',classification_proof.get('declaration_uncertainties',classification_proof.get('return_declaration_choices',classification_proof.get('limitations',[]))))))
                if row['status']=='ready' and op['target']=='pending':
                    require(newentry['validation_sha256']!=entry['validation_sha256'],'Demotion requires fresh pending proof')
            elif kind=='stage': evidence.stage(entry,op)
            elif kind in ('assign','block'):
                require(isinstance(op.get('value'),str),'Assignment/blocker value must be a string (empty clears)')
            else: raise ValueError('Unsupported operation kind')
            prepared.append((op,row,prior,before,newentry))
        evidence.unchanged()
        result={'request_id':payload['request_id'],'dry_run':dry_run,'operations':len(prepared),'evidence':evidence.summary(),'database_seconds_before_mutation':time.monotonic()-started,'revisions':[{'original_elf_sha256':op['original_elf_sha256'],'mangled':op['mangled'],'previous':prior['revision'],'next':prior['revision']+1} for op,_,prior,_,_ in prepared]}
        if dry_run: return result
        session.add(orm.Request(request_id=payload['request_id'],digest=checksum,result=reg.encode(result)))
        session.flush()
        if evidence.cache:
            session.execute(insert(orm.EvidenceCheck),[{'request_id':payload['request_id'],'path':str(path),'sha256':sha,'fingerprint':reg.encode(fingerprint)} for path,(sha,fingerprint) in evidence.cache.items()])
        for op,row,prior,before,newentry in prepared:
            kind=op['kind'];rid=row['id']
            if kind=='admit':
                ordinal=c.execute('SELECT coalesce(max(ordinal),-1)+1 FROM records WHERE status=?',(op['target'],)).fetchone()[0]
                record=orm.Record(status=op['target'],ordinal=ordinal,elf=op['original_elf_sha256'],mangled=op['mangled'],metadata_json='{}')
                session.add(record);session.flush();rid=record.id
                session.add(orm.WorkState(record_id=rid,revision=-1));session.flush()
            if kind in ('classify','admit'): replace_record(c,session,rid,newentry,op['target'])
            elif kind=='stage':
                stage=session.get(orm.Stage,(rid,op['stage']))
                if stage is None:
                    stage=orm.Stage(record_id=rid,stage=op['stage']);session.add(stage)
                stage.proof=op['proof'];stage.proof_sha256=op['proof_sha256'];stage.domain=op['domain']
            work=session.get(orm.WorkState,rid)
            if kind=='assign':work.assignment=op['value']
            elif kind=='block':work.blocker=op['value']
            work.revision+=1
            session.flush()
            current=c.execute('SELECT * FROM records WHERE id=?',(rid,)).fetchone()
            after={'classification':current['status'],'work':state(c,rid),'validation_sha256':reg.restored(c,current).get('validation_sha256'),
                   'record_metadata':json.loads(current['metadata']),
                   'source_sets':[dict(v) for v in c.execute('SELECT field,set_id FROM record_sets WHERE record_id=?',(rid,))],
                   'stages':[dict(v) for v in c.execute('SELECT stage,proof,proof_sha256,domain FROM stages WHERE record_id=?',(rid,))]}
            compact_op={k:v for k,v in op.items() if k!='entry'}
            bindings={'operation':compact_op,'source_sets':[dict(v) for v in c.execute('SELECT field,set_id FROM record_sets WHERE record_id=?',(rid,))],'fresh_evidence_request':payload['request_id']}
            session.add(orm.Journal(request_id=payload['request_id'],record_id=rid,actor=payload['actor'],timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),reason=op['reason'],previous_revision=prior['revision'],new_revision=prior['revision']+1,previous_state=reg.encode(before),new_state=reg.encode(after),bindings=reg.encode(bindings)))
        session.flush()
        evidence.unchanged()
        require(not c.execute('PRAGMA foreign_key_check').fetchall(),'Foreign key violation')
        unit.commit()
        result['elapsed_seconds']=time.monotonic()-started
        return result
    except Exception:
        unit.rollback()
        raise
    finally: unit.close()


def query(db,kind,filters):
    with reg.connect(db) as c:
        schema.check_supported(c)
        if kind=='counts':
            return {'classifications':[dict(x) for x in c.execute('SELECT status,count(*) AS count FROM records GROUP BY status')], 'stages':[dict(x) for x in c.execute('SELECT stage,count(*) AS count FROM stages GROUP BY stage')], 'assigned':c.execute("SELECT count(*) FROM work_state WHERE coalesce(assignment,'')!=''").fetchone()[0], 'blocked':c.execute("SELECT count(*) FROM work_state WHERE coalesce(blocker,'')!=''").fetchone()[0]}
        clauses=[];args=[]
        for name,col in [('elf','r.elf'),('mangled','r.mangled'),('status','r.status'),('proof','r.proof'),('assignment','w.assignment')]:
            if filters.get(name) is not None: clauses.append(col+'=?');args.append(filters[name])
        if filters.get('role') is not None: clauses.append("json_extract(r.metadata,'$.role')=?");args.append(filters['role'])
        if filters.get('scope') is not None:
            # Exact namespace/class prefix on preserved demangled name; no mangling inference.
            clauses.append("substr(json_extract(r.metadata,'$.demangled'),1,?)=?");args.extend([len(filters['scope'])+2,filters['scope']+'::'])
        if filters.get('blocked'): clauses.append("coalesce(w.blocker,'')!=''")
        if filters.get('stage') is not None: clauses.append('EXISTS(SELECT 1 FROM stages s WHERE s.record_id=r.id AND s.stage=?)');args.append(filters['stage'])
        if filters.get('source') is not None: clauses.append('EXISTS(SELECT 1 FROM record_sets x JOIN source_members m ON m.set_id=x.set_id JOIN source_versions v ON v.id=m.version_id WHERE x.record_id=r.id AND v.path=?)');args.append(filters['source'])
        sql='SELECT r.*,w.revision,w.assignment,w.blocker FROM records r JOIN work_state w ON w.record_id=r.id'+(' WHERE '+' AND '.join(clauses) if clauses else '')+' ORDER BY r.status,r.ordinal'
        if kind=='audit':
            ids=[x['id'] for x in c.execute(sql,args)]
            return [dict(x) for x in c.execute('SELECT * FROM journal ORDER BY sequence') if x['record_id'] in ids]
        return [{k:row[k] for k in ('id','elf','mangled','status','proof','revision','assignment','blocker')} for row in c.execute(sql,args)]


def validate_all(db, library):
    started=time.monotonic();evidence=Evidence(library);failures=[];counts={};checked=0
    with reg.connect(db) as c:
        for row in c.execute('SELECT * FROM records ORDER BY status,ordinal'):
            counts[row['status']]=counts.get(row['status'],0)+1
            try:
                token=tuple(tuple(v) for v in c.execute('SELECT field,set_id FROM record_sets WHERE record_id=? ORDER BY field',(row['id'],)))
                evidence.classify(reg.restored(c,row),row['status'],source_token=token)
                checked+=1
            except (ValueError,KeyError,FileNotFoundError,TypeError) as exc:
                failures.append({'original_elf_sha256':row['elf'],'mangled':row['mangled'],'status':row['status'],'error':str(exc)})
        evidence.unchanged()
        integrity=c.execute('PRAGMA integrity_check').fetchall()
        foreign=c.execute('PRAGMA foreign_key_check').fetchall()
        require(not foreign and len(integrity)==1 and integrity[0][0]=='ok','SQLite integrity failed')
    return {'all_evidence_passed':not failures,'checked':checked,'counts':counts,'failures':failures,'evidence':evidence.summary(),'elapsed_seconds':time.monotonic()-started,'read_only':True}


def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    q=s.add_parser('init');q.add_argument('--baseline',type=pathlib.Path,required=True);q.add_argument('--db',type=pathlib.Path,required=True)
    q=s.add_parser('apply');q.add_argument('--db',type=pathlib.Path,required=True);q.add_argument('--library',type=pathlib.Path,required=True);q.add_argument('--manifest',type=pathlib.Path,required=True);q.add_argument('--commit',action='store_true',help='Commit explicit transaction; default is read-only preflight')
    q=s.add_parser('validate-all');q.add_argument('--db',type=pathlib.Path,required=True);q.add_argument('--library',type=pathlib.Path,required=True)
    for kind in ('query','counts','audit'):
        q=s.add_parser(kind);q.add_argument('--db',type=pathlib.Path,required=True)
        for flag in ('elf','mangled','status','role','scope','proof','source','assignment','stage'):q.add_argument('--'+flag)
        q.add_argument('--blocked',action='store_true')
    a=p.parse_args()
    if a.command=='init':working_copy(a.baseline,a.db);print('{"initialized":true}')
    elif a.command=='validate-all': print(reg.encode(validate_all(a.db,a.library)))
    elif a.command=='apply':print(reg.encode(operate(a.db,a.library,json.loads(a.manifest.read_text()),not a.commit)))
    else: print(reg.encode(query(a.db,a.command,vars(a))))

if __name__=='__main__':main()
