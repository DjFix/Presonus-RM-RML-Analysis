"""Explicit v1->v2 physical migration, sealed staging and resumable activation.

Run inside the graph runner with repository read-only except output/state. No
compiler replay. Staging only reads the operational index and remote graph.
"""
import argparse
import collections
import fcntl
import itertools
import json
import os
import pathlib
import shutil
import sqlite3
import time
from neo4j import GraphDatabase
from context_runtime import ContextError, inventory, sha
from memgraph_endpoint import memgraph_uri
from refresh_facts import connect
from refresh_graph import PRODUCERS
from refresh_publish import build_facts, main as publish_main

ROOT=pathlib.Path(__file__).resolve().parents[1]
BASE=ROOT/'dependency-graph'
OLD=ROOT/'temp/recovery-work/dependency-graph/refresh/1793460399608072116'
V2=ROOT/'temp/recovery-work/dependency-graph/identity-v2-01/current/index.sqlite'


def ro(path):return sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)


def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')


def marker(s):
    return dict(s.run('MATCH(g:ContextGeneration {id:"active"}) RETURN g.state AS state,g.digest AS digest').single())


def counters(s):
    return {'source_edges':{r['kind']:r['n'] for r in s.run('MATCH(:Artifact)-[r]->(:Artifact) RETURN type(r) AS kind,count(r) AS n')},
            'native_edges':{r['kind']:r['n'] for r in s.run('MATCH(:NativeArtifact)-[r]->(:NativeArtifact) RETURN type(r) AS kind,count(r) AS n')},
            'native_marker':dict(s.run('MATCH(g:NativeGeneration {id:"active"}) RETURN g.state AS state,g.digest AS digest').single())}


def capture_edges(s,db,table,kinds):
    db.execute('CREATE TABLE '+table+'(src,dst,kind,evidence,n INTEGER,PRIMARY KEY(src,dst,kind,evidence))')
    query='MATCH(a:Artifact)-[r]->(b:Artifact) WHERE type(r) IN $kinds RETURN a.id AS src,b.id AS dst,type(r) AS kind,r.evidence AS evidence'
    pending=[];n=0
    for record in s.run(query,kinds=kinds):
        row=tuple(record[field] for field in ('src','dst','kind','evidence'))
        if row[3] is None:raise ContextError('Unexpected null edge evidence')
        pending.append(row);n+=1
        if len(pending)==5000:
            db.executemany('INSERT INTO '+table+' VALUES(?,?,?,?,1) ON CONFLICT(src,dst,kind,evidence) DO UPDATE SET n=n+1',pending);db.commit();pending=[]
            if n%100000==0:print('capture',table,n,flush=True)
    if pending:db.executemany('INSERT INTO '+table+' VALUES(?,?,?,?,1) ON CONFLICT(src,dst,kind,evidence) DO UPDATE SET n=n+1',pending)
    db.commit()
    return n


def stage(out, resume=False):
    out.mkdir(parents=True,exist_ok=resume)
    os.environ['SQLITE_TMPDIR']=str(out)
    legacy=BASE/'state/refresh-index.sqlite'
    with ro(legacy) as old:
        pending=old.execute('SELECT value FROM meta WHERE key="pending"').fetchone()
        if not pending or pending[0]!=str(OLD):raise ContextError('Unexpected legacy pending journal')
    previous_active=json.loads((BASE/'ACTIVE.json').read_text())
    if resume:
        if (out/'STAGED.json').exists():raise ContextError('Stage already sealed; use activation')
        with ro(out/'v2-index.sqlite') as cached:
            if cached.execute('SELECT count(*) FROM units').fetchone()[0]!=630 or not cached.execute('SELECT 1 FROM node_facts WHERE owner="@build" LIMIT 1').fetchone():
                raise ContextError('Incomplete cached index; cannot reuse')
        archive=out/('partial-delta-'+str(time.time_ns()));archive.mkdir()
        retained=[]
        for file in out.glob('delta.sqlite*'):
            retained.append({'path':str(file),'sha256':sha(file),'size':file.stat().st_size})
            file.rename(archive/file.name)
        write(archive/'retained.json',{'reason':'Resume completed v2/build cache after diagnosed Docker sort-temp IO bottleneck; no server writes occurred','files':retained})
        print('reuse completed v2 index and build observations',flush=True)
        c=connect(out/'v2-index.sqlite');inputs={}
        for payload, in c.execute('SELECT payload FROM units'):
            data=json.loads(payload)
            for path,h in data['inputs'].items():
                if path in inputs and inputs[path]!=h:raise ContextError('Mixed cached input generation')
                inputs[path]=h
            inputs[data['ast']]=data['ast_sha256'];inputs[data['gcc']]=data['gcc_sha256']
    else:
        print('copy v2 index',flush=True)
        c=connect(out/'v2-index.sqlite')
        with ro(V2) as source:source.backup(c)
        shutil.copyfile(OLD/'ctest-inventory.log',out/'ctest-inventory.log')
        print('build current facts',flush=True)
        nodes,edges,inputs=build_facts(c,out)
        c.executemany('INSERT INTO node_facts VALUES(?,?,?,?,?)',(('@build',key,v['kind'],v['label'],json.dumps(v['metadata'],sort_keys=True)) for key,v in nodes.items()))
        c.executemany('INSERT INTO edge_facts VALUES(?,?,?,?,?)',(('@build',*e) for e in edges));c.commit()
    original_report=json.loads((OLD/'refresh-report.json').read_text())
    # Preserve configuration/provenance capture hashes; do not replace an old
    # expected hash with the current bytes merely to pass admission.
    for path,h in original_report['input_sha256'].items():
        if path in inputs and inputs[path]!=h:raise ContextError('Mixed input generation '+path)
        inputs[path]=h
    for path,h in inputs.items():
        if not pathlib.Path(path).is_file() or sha(path)!=h:raise ContextError('Input changed '+path)
    print('construct physical delta',flush=True)
    d=sqlite3.connect(out/'delta.sqlite')
    d.execute('ATTACH DATABASE ? AS legacy',(legacy.as_uri()+'?mode=ro',))
    d.execute('ATTACH DATABASE ? AS sealed',((OLD/'delta.sqlite').as_uri()+'?mode=ro',))
    d.execute('ATTACH DATABASE ? AS wanted',((out/'v2-index.sqlite').as_uri()+'?mode=ro',))
    d.executescript('''CREATE TABLE settings(key PRIMARY KEY,value);INSERT INTO settings VALUES('replace_legacy_build',0);
      CREATE TABLE prior_edges(src,dst,kind,evidence,PRIMARY KEY(src,dst,kind,evidence));
      CREATE TABLE desired_edges(src,dst,kind,evidence,PRIMARY KEY(src,dst,kind,evidence));
      CREATE TABLE old_edges(src,dst,kind,evidence,PRIMARY KEY(src,dst,kind,evidence));
      CREATE TABLE new_edges(src,dst,kind,evidence,PRIMARY KEY(src,dst,kind,evidence));
      CREATE TABLE nodes(id PRIMARY KEY,kind,label,metadata);CREATE TABLE orphan_nodes(id PRIMARY KEY);
      INSERT INTO prior_edges SELECT * FROM sealed.prior_edges ORDER BY src,dst,kind,evidence;
      INSERT INTO desired_edges SELECT * FROM wanted.logical_edges ORDER BY src,dst,kind,evidence;
      INSERT OR IGNORE INTO desired_edges SELECT src,dst,kind,evidence FROM wanted.edge_facts WHERE owner='@build' ORDER BY src,dst,kind,evidence;
      INSERT INTO old_edges SELECT * FROM prior_edges EXCEPT SELECT * FROM desired_edges ORDER BY 1,2,3,4;
      INSERT INTO new_edges SELECT * FROM desired_edges EXCEPT SELECT * FROM prior_edges ORDER BY 1,2,3,4;
      INSERT INTO orphan_nodes SELECT id FROM legacy.node_facts UNION SELECT id FROM sealed.orphan_nodes
       EXCEPT SELECT id FROM wanted.node_facts ORDER BY 1;''')
    print('merge desired node metadata',flush=True)
    rows=c.execute('SELECT id,kind,label,metadata FROM node_facts ORDER BY id,owner')
    batch=[]
    for key,group in itertools.groupby(rows,key=lambda row:row[0]):
        metadata={};kind=label=None
        for _,kind,label,text in group:
            for field,value in json.loads(text).items():
                if field in ('source_definition','compiler_definition'):metadata[field]=metadata.get(field,False) or value
                elif value is not None:metadata[field]=value
        batch.append((key,kind,label,json.dumps(metadata,sort_keys=True)))
        if len(batch)>=1000:d.executemany('INSERT INTO nodes VALUES(?,?,?,?)',batch);d.commit();batch=[]
    if batch:d.executemany('INSERT INTO nodes VALUES(?,?,?,?)',batch)
    d.commit()
    kinds=sorted({r[0] for r in d.execute('SELECT DISTINCT kind FROM prior_edges UNION SELECT DISTINCT kind FROM desired_edges')})
    with GraphDatabase.driver(memgraph_uri(ROOT),auth=None) as driver:
        with driver.session(fetch_size=5000) as s:
            if marker(s)!={'state':'refreshing','digest':previous_active['state_sha256']}:raise ContextError('Unexpected server baseline marker')
            baseline=counters(s);write(out/'baseline-counters.json',baseline)
            capture_edges(s,d,'server_before',kinds)
            missing=d.execute('''SELECT count(*) FROM prior_edges p WHERE NOT EXISTS(SELECT 1 FROM server_before b
              WHERE p.src=b.src AND p.dst=b.dst AND p.kind=b.kind AND p.evidence=b.evidence)''').fetchone()[0]
            if missing:raise ContextError('Server does not contain retained baseline owned edges: '+str(missing))
            if marker(s)!={'state':'refreshing','digest':previous_active['state_sha256']}:raise ContextError('Baseline moved during capture')
    seal_stage(out,c,d,inputs,previous_active,kinds,resume)


def seal_stage(out,c,d,inputs,previous_active,kinds,resume,reconciliation=None):
    d.executescript('''CREATE TABLE expected_edges AS SELECT * FROM server_before;
      CREATE UNIQUE INDEX expected_keys ON expected_edges(src,dst,kind,evidence);
      DELETE FROM expected_edges WHERE EXISTS(SELECT 1 FROM old_edges o WHERE o.src=expected_edges.src AND o.dst=expected_edges.dst AND o.kind=expected_edges.kind AND o.evidence=expected_edges.evidence);
      INSERT OR IGNORE INTO expected_edges SELECT src,dst,kind,evidence,1 FROM new_edges;
      DELETE FROM expected_edges WHERE kind='ENCODED_NAME_MATCH' AND src IN(SELECT id FROM orphan_nodes);''')
    counts={table:d.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in ('prior_edges','desired_edges','old_edges','new_edges','nodes','orphan_nodes')}
    if reconciliation is None and counts['prior_edges']!=2702118:raise ContextError('Retained baseline count differs from audited baseline')
    d.commit();d.close()
    c.execute('DROP TABLE logical_edges')
    c.execute('INSERT OR REPLACE INTO meta VALUES(?,?)',('pending',str(out)));c.commit()
    c.execute('PRAGMA wal_checkpoint(TRUNCATE)');c.close()
    producers={str((BASE/name).relative_to(ROOT)):sha(BASE/name) for name in PRODUCERS}
    producers['dependency-graph/migrate_source_identity.py']=sha(BASE/'migrate_source_identity.py')
    plan={'identity_version':2,'previous_active':previous_active,'producer_sha256':producers,
          'migration':True,'baseline_reconciliation':reconciliation,'resumed_completed_staging_cache':resume,'legacy_delta':str(OLD),'legacy_delta_sha256':sha(OLD/'delta.sqlite'),
          'baseline_kinds':kinds,'counts':counts,'source_identity_index':str(V2),'no_compiler_replay':True}
    write(out/'plan.json',plan)
    write(out/'refresh-report.json',{'source_graph_refresh':True,'input_sha256':inputs,'source_inventory':inventory(ROOT),
          'producer_sha256':producers,'observation_provenance':{'scope':'v2 transforms of retained observations, not new compiler execution','lineage':str(ROOT/'temp/recovery-work/dependency-graph/identity-v2-01/current/lineage.json')},'runtime_or_original_firmware_callgraph_complete':False})
    shutil.copyfile(out/'refresh-report.json',out/'captured-report.json')
    write(out/'STAGED.json',{'passed':True,'delta_sha256':sha(out/'delta.sqlite'),'plan_sha256':sha(out/'plan.json'),
          'index_sha256':sha(out/'v2-index.sqlite'),'report_sha256':sha(out/'refresh-report.json'),'counts':counts,'activated':False})
    print(json.dumps(counts),flush=True)


def reconcile_stage(out):
    analysis=json.loads((out/'baseline-reconciliation-analysis.json').read_text())
    if analysis['extra_not_in_historical_graph'] or analysis['missing_present_in_historical_graph']:
        raise ContextError('Ownership reconciliation contains unexplained tuples')
    if sum(analysis['missing_by_kind'].values())!=25488 or sum(analysis['extra_by_kind'].values())!=32464:
        raise ContextError('Unexpected reconciliation cardinalities')
    if set(analysis['extra_by_kind'])-{'GCC_CALLS','GCC_REFERENCES','ALIAS_OF','GCC_UNRESOLVED'}:
        raise ContextError('Unexpected unowned source relationship kind')
    previous_active=json.loads((BASE/'ACTIVE.json').read_text())
    with GraphDatabase.driver(memgraph_uri(ROOT),auth=None) as driver:
        with driver.session() as session:
            if marker(session)!={'state':'refreshing','digest':previous_active['state_sha256']}:raise ContextError('Generation moved')
            if counters(session)!=json.loads((out/'baseline-counters.json').read_text()):raise ContextError('Baseline counters moved')
    print('reconcile exact historical GCC baseline; reuse complete server capture',flush=True)
    d=sqlite3.connect(out/'delta.sqlite')
    d.executescript('''ALTER TABLE prior_edges RENAME TO indexed_prior_edges;
      ALTER TABLE old_edges RENAME TO unreconciled_old_edges;
      ALTER TABLE new_edges RENAME TO unreconciled_new_edges;
      CREATE TABLE prior_edges(src,dst,kind,evidence,PRIMARY KEY(src,dst,kind,evidence));
      INSERT INTO prior_edges SELECT src,dst,kind,evidence FROM server_before ORDER BY src,dst,kind,evidence;
      CREATE TABLE old_edges(src,dst,kind,evidence,PRIMARY KEY(src,dst,kind,evidence));
      CREATE TABLE new_edges(src,dst,kind,evidence,PRIMARY KEY(src,dst,kind,evidence));
      INSERT INTO old_edges SELECT * FROM prior_edges EXCEPT SELECT * FROM desired_edges ORDER BY 1,2,3,4;
      INSERT INTO new_edges SELECT * FROM desired_edges EXCEPT SELECT * FROM prior_edges ORDER BY 1,2,3,4;
      INSERT OR IGNORE INTO orphan_nodes SELECT src FROM server_before WHERE src NOT LIKE 'catalog:%'
       AND NOT EXISTS(SELECT 1 FROM nodes n WHERE n.id=server_before.src);
      INSERT OR IGNORE INTO orphan_nodes SELECT dst FROM server_before WHERE dst NOT LIKE 'catalog:%'
       AND NOT EXISTS(SELECT 1 FROM nodes n WHERE n.id=server_before.dst);''')
    kinds=[row[0] for row in d.execute('SELECT DISTINCT kind FROM prior_edges UNION SELECT DISTINCT kind FROM desired_edges')]
    c=connect(out/'v2-index.sqlite');inputs={}
    for payload, in c.execute('SELECT payload FROM units'):
        data=json.loads(payload)
        for path,h in data['inputs'].items():
            if path in inputs and inputs[path]!=h:raise ContextError('Mixed cached inputs')
            inputs[path]=h
        inputs[data['ast']]=data['ast_sha256'];inputs[data['gcc']]=data['gcc_sha256']
    for path,h in json.loads((OLD/'refresh-report.json').read_text())['input_sha256'].items():
        if path in inputs and inputs[path]!=h:raise ContextError('Mixed legacy inputs')
        inputs[path]=h
    for path,h in inputs.items():
        if sha(path)!=h:raise ContextError('Changed input '+path)
    reconciliation={**analysis,'reason':'Historical full loader reparsed raw GCC dumps; later ownership seeding used incomplete stored GCC JSON. Exact missing/extras checked against original full graph, not name-normalized.',
                    'historical_graph_sha256':sha(ROOT/analysis['historical_source']),
                    'indexed_prior_retained':'indexed_prior_edges','actual_physical_prior':'server_before'}
    write(out/'baseline-reconciliation.json',reconciliation)
    seal_stage(out,c,d,inputs,previous_active,kinds,True,reconciliation)


def activate(out):
    receipt=json.loads((out/'STAGED.json').read_text());plan=json.loads((out/'plan.json').read_text())
    for file,key in [('delta.sqlite','delta_sha256'),('plan.json','plan_sha256'),('captured-report.json','report_sha256')]:
        if sha(out/file)!=receipt[key]:raise ContextError('Staged migration changed '+file)
    for path,h in plan['producer_sha256'].items():
        if sha(ROOT/path)!=h:raise ContextError('Producer changed since staging '+path)
    for path,h in json.loads((out/'refresh-report.json').read_text())['input_sha256'].items():
        if not pathlib.Path(path).is_file() or sha(path)!=h:raise ContextError('Staged inputs changed '+path)
    path=BASE/'state/refresh-index.sqlite'
    with ro(path) as db:pending=db.execute('SELECT value FROM meta WHERE key="pending"').fetchone()
    if pending and pending[0]==str(OLD):
        if sha(out/'v2-index.sqlite')!=receipt['index_sha256']:raise ContextError('Staged index changed')
        if json.loads((BASE/'ACTIVE.json').read_text())!=plan['previous_active']:raise ContextError('Local generation moved')
        with GraphDatabase.driver(memgraph_uri(ROOT),auth=None) as driver:
            with driver.session() as s:
                if marker(s)!={'state':'refreshing','digest':plan['previous_active']['state_sha256']}:raise ContextError('Remote generation moved')
                if counters(s)!=json.loads((out/'baseline-counters.json').read_text()):raise ContextError('Remote baseline counts moved')
        # Consistent backup plus original DB/WAL/SHM bytes retained. Installation
        # is journaled before replacement so a crash is explicitly resumable.
        archive=BASE/'state'/('legacy-v1-'+out.name);archive.mkdir(exist_ok=True)
        with ro(path) as source:
            dest=sqlite3.connect(archive/'consistent-backup.sqlite');source.backup(dest);dest.close()
        incoming=BASE/'state'/('incoming-'+out.name+'.sqlite')
        with ro(out/'v2-index.sqlite') as source:
            dest=sqlite3.connect(incoming);source.backup(dest);dest.execute('PRAGMA journal_mode=DELETE');dest.close()
        write(out/'INSTALLING.json',{'legacy':str(path),'archive':str(archive),'incoming':str(incoming),'pending':str(out)})
        for suffix in ('-wal','-shm'):
            side=pathlib.Path(str(path)+suffix)
            if side.exists():side.rename(archive/side.name)
        # Hard link preserves original base bytes while replacement is atomic.
        os.link(path,archive/'original-base.sqlite')
        os.replace(incoming,path)
        write(out/'SUPERSESSION.json',{'legacy_delta':str(OLD),'legacy_delta_sha256':plan['legacy_delta_sha256'],
             'legacy_index_archive':str(archive),'new_delta_sha256':receipt['delta_sha256'],'installed':True,'timestamp_ns':time.time_ns()})
    elif not pending or pending[0]!=str(out):raise ContextError('Unexpected migration activation state')
    publish_main(out)


def verify(session,out):
    """Exact edge multiset and immutable native/provider boundaries before ready."""
    plan=json.loads((out/'plan.json').read_text())
    if not plan.get('migration'):return
    with ro(out/'delta.sqlite') as expected:
        target=out/('verify-'+str(time.time_ns())+'.sqlite');c=sqlite3.connect(target)
        capture_edges(session,c,'actual',plan['baseline_kinds'])
        c.execute('ATTACH DATABASE ? AS expected',((out/'delta.sqlite').as_uri()+'?mode=ro',))
        different=c.execute('''SELECT count(*) FROM (SELECT * FROM actual EXCEPT SELECT * FROM expected.expected_edges)''').fetchone()[0]
        missing=c.execute('''SELECT count(*) FROM (SELECT * FROM expected.expected_edges EXCEPT SELECT * FROM actual)''').fetchone()[0]
        if missing or different:raise ContextError(f'Physical graph mismatch missing={missing} unexpected={different}')
        # Every desired code node must exist; no hash/range original is discarded.
        ids=expected.execute('SELECT id FROM nodes');checked=0
        while True:
            batch=[r[0] for r in ids.fetchmany(2000)]
            if not batch:break
            n=session.run('UNWIND $ids AS id MATCH(n:Artifact {id:id}) RETURN count(n) AS n',ids=batch).single()['n']
            if n!=len(batch):raise ContextError('Desired node coverage mismatch')
            checked+=n
        baseline=json.loads((out/'baseline-counters.json').read_text());after=counters(session)
        if after['native_edges']!=baseline['native_edges'] or after['native_marker']!=baseline['native_marker']:raise ContextError('Native boundary changed')
        for kind,n in baseline['source_edges'].items():
            if kind not in plan['baseline_kinds'] and after['source_edges'].get(kind)!=n:raise ContextError('Unowned edge kind changed '+kind)
        write(out/'verification.json',{'passed':True,'missing':missing,'unexpected':different,'desired_nodes_checked':checked,'native_unchanged':True,'unowned_kinds_unchanged':True,'actual_edges':str(target)})
        c.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['stage','resume-stage','reconcile-stage','activate']);parser.add_argument('--out',type=pathlib.Path,required=True);args=parser.parse_args()
    out=args.out.resolve()
    if not out.is_relative_to(ROOT/'temp/recovery-work'):raise ContextError('Output must be project recovery work')
    with (BASE/'state/context.lock').open('r') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if args.action in ('stage','resume-stage'):stage(out,resume=args.action=='resume-stage')
        elif args.action=='reconcile-stage':reconcile_stage(out)
        else:activate(out)
