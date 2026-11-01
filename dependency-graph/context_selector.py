"""Memgraph-backed context packets for reconstruction subagents, not user chats."""
import argparse
import json
import pathlib
import shutil
import time

from neo4j import GraphDatabase
from memgraph_endpoint import memgraph_uri
from context_runtime import ContextError, fingerprint, guard, inside, inventory, sha
from full_queries import QUERIES, graph_closure
from native_context import make_context, require_nonempty, open_index, select as native_select

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = ROOT/'dependency-graph'
ACTIVE = BASE/'ACTIVE.json'


def tools():
    paths=('dependency-graph/context_selector.py','dependency-graph/context_runtime.py',
           'dependency-graph/context_slices.py','dependency-graph/full_queries.py',
           'uc-library/tools/recovery/select_context.py','dependency-graph/refresh_graph.py',
           'dependency-graph/refresh_facts.py','dependency-graph/refresh_extract.py',
           'dependency-graph/refresh_publish.py','dependency-graph/native_graph.py',
           'dependency-graph/native_context.py','dependency-graph/dedup_index.py',
           'dependency-graph/dedup_work.py','dependency-graph/dedup_schema.sql',
           'dependency-graph/memgraph_endpoint.py','dependency-graph/code_identity.py',
           'dependency-graph/full_source_graph.py','dependency-graph/gcc_source_graph.py',
           'dependency-graph/batch_publication.py')
    return {p:sha(ROOT/p) for p in paths}


def graph_marker(session, active):
    row = session.run('MATCH (g:ContextGeneration {id:"active"}) RETURN g.state AS state,g.digest AS digest').single()
    if not row or row['state'] != 'ready' or row['digest'] != active['state_sha256']:
        raise ContextError('Memgraph generation is absent, loading or differs from ACTIVE')


def register(session, out, reports=None):
    if reports is None and ACTIVE.exists():
        previous = json.loads(ACTIVE.read_text())
        previous_state = inside(ROOT, previous['state'])
        if sha(previous_state) != previous['state_sha256']: raise ContextError('Generation state hash mismatch')
        previous_state = json.loads(previous_state.read_text())
        if previous_state.get('automatic_refresh_version'):
            reports = [inside(ROOT, path) for path in previous_state['reports']]
    reports = reports or [BASE/'runs/full-01/full-graph.json', BASE/'runs/core-source-01/full-graph-qualified.json']
    prefix = '/home/rs/projects/opencs/ai-line-analysis/'
    expected = {}
    for report in reports:
        for path,digest in json.loads(report.read_text())['input_sha256'].items():
            if not path.startswith(prefix):
                raise ContextError('Unknown input root: '+path)
            relative = path[len(prefix):]
            if relative in expected and expected[relative] != digest:
                raise ContextError('Mixed input generations: '+relative)
            expected[relative] = digest
    files = {}
    snapshots={}
    for relative,digest in expected.items():
        path = inside(ROOT,relative)
        before = fingerprint(path)
        if sha(path) != digest or fingerprint(path) != before:
            raise ContextError('Refresh graph before registration: '+relative)
        files[relative] = {'sha256':digest,'fingerprint':before}
        if path.suffix in ('.cpp','.hpp','.h','.cc','.cxx','.c','.inc'):
            snapshot=BASE/'state/sources'/digest
            snapshot.parent.mkdir(parents=True,exist_ok=True)
            if not snapshot.exists():shutil.copyfile(path,snapshot)
            if sha(snapshot)!=digest:raise ContextError('Frozen source snapshot mismatch')
            snapshots[relative]=str(snapshot.relative_to(ROOT))
    for relative in ('uc-library/CMakeLists.txt', 'uc-library/cmake/ProductionSourceGroups.cmake',
                     'temp/core-upstream/root-integration-01/compile_commands.json',
                     'temp/core-upstream/root-integration-01/upstream-core/build/compile_commands.json'):
        path = inside(ROOT,relative)
        files[relative] = {'sha256':sha(path),'fingerprint':fingerprint(path)}
    registry = json.loads((ROOT/'uc-library/validation/registry-sqlite/ACTIVE.json').read_text())
    final = json.loads(reports[-1].read_text())
    nodes = {r['kind']:r['n'] for r in session.run('MATCH (n:Artifact) RETURN n.kind AS kind,count(n) AS n')}
    edges = {r['kind']:r['n'] for r in session.run('MATCH (:Artifact)-[r]->(:Artifact) RETURN type(r) AS kind,count(r) AS n')}
    if nodes != final['node_kinds'] or edges != final['edge_kinds']:
        raise ContextError('Memgraph does not contain the reviewed full generation')
    state = {'version':1,'backend':'memgraph','files':files,'source_snapshots':snapshots,'source_inventory':inventory(ROOT),
             'registry_guard':registry['registry_guard'],
             'reports':{str(p.relative_to(ROOT)):sha(p) for p in reports},
             'freshness_scope':'ordinary filesystem edits; not a hostile writer security boundary',
             'runtime_firmware_graph_complete':False}
    if final.get('source_graph_refresh'):
        state['automatic_refresh_version'] = 1
    state_path = BASE/'state'/('generation-'+str(time.time_ns())+'.json')
    state_path.parent.mkdir(parents=True,exist_ok=True)
    state_path.write_text(json.dumps(state,sort_keys=True,indent=2)+'\n')
    active = {'version':1,'backend':'memgraph','state':str(state_path.relative_to(ROOT)),
              'state_sha256':sha(state_path),'mode':'required_before_reconstruction_subagent'}
    if ACTIVE.exists():
        (out/'previous_ACTIVE.json').write_text(ACTIVE.read_text())
    session.run('MERGE (g:ContextGeneration {id:"active"}) SET g.state="ready",g.digest=$digest',
                digest=active['state_sha256']).consume()
    temporary = ACTIVE.with_suffix('.new')
    temporary.write_text(json.dumps(active,indent=2)+'\n'); temporary.replace(ACTIVE)
    (out/'registration.json').write_text(json.dumps(active,indent=2)+'\n')
    print(json.dumps({'registered':True,'files_bound':len(files),'state':active['state']}))


def query(session,name,seed):
    return {r['id'] for r in session.run(QUERIES[name].cypher,seed=seed)}


def read_nodes(session,ids):
    return {r['id']:{'kind':r['kind'],'label':r['label'],'metadata':json.loads(r['metadata'] or '{}')}
            for r in session.run('UNWIND $ids AS id MATCH(n:Artifact {id:id}) '
                                 'RETURN n.id AS id,n.kind AS kind,n.label AS label,n.metadata AS metadata',ids=sorted(ids))}


def validate_packet(session,out,active,require_ready=True,baseline=False):
    graph_marker(session,active)
    if baseline:
        state_path=inside(ROOT,active['state'])
        if sha(state_path)!=active['state_sha256']:raise ContextError('Generation state changed')
        state=json.loads(state_path.read_text())
        if not (out/'DISPATCH.json').exists():raise ContextError('Baseline expansion requires a dispatched packet')
    else:state = guard(ROOT,active)
    packet = json.loads((out/'context.json').read_text())
    if require_ready and packet.get('state') != 'dispatch_ready':
        raise ContextError('Packet source slicing/finalization has not passed')
    if require_ready:require_nonempty(packet)
    from dedup_work import validate_packet_work
    validate_packet_work(ROOT, packet, str(out.relative_to(ROOT)))
    if packet.get('native_context',{}).get('bodies'):
        marker=session.run('MATCH(g:NativeGeneration {id:"active"}) RETURN g.state AS state,g.digest AS digest').single()
        if not marker or marker['state']!='ready' or marker['digest']!=packet['native_context']['generation_sha256']:
            raise ContextError('Native Memgraph projection is absent, loading or differs from packet')
    if packet['tool_sha256'] != tools():
        raise ContextError('Context operator/policy changed: prepare a new packet')
    if packet['generation_sha256'] != active['state_sha256']:
        raise ContextError('Packet generation is no longer active')
    for name,digest in packet['packet_sha256'].items():
        if sha(out/name) != digest:
            raise ContextError('Packet modified: '+name)
    for path,digest in packet['selected_file_sha256'].items():
        frozen=state.get('source_snapshots',{}).get(path) if baseline else None
        if frozen and sha(inside(ROOT,frozen))==digest:continue
        if sha(inside(ROOT,path)) != digest:
            raise ContextError('Reading input changed: '+path)
    if sha(ROOT/'AGENTS.md') != packet['agents_sha256']:
        raise ContextError('Instructions changed: prepare a new packet')
    return packet


def prepare(session,out,active):
    state = guard(ROOT,active); graph_marker(session,active)
    task = json.loads((out/'request.json').read_text())
    roots = set(); unresolved = []; reading = set(); callers = set(); tests = set(); fixtures = set()
    proof_ids = set(); reasons = {}; mapping_unknown = []
    for item in task['originals']:
        original = item['original']
        name = original['mangled']
        candidates = [dict(r) for r in session.run(
            'MATCH(n:Function) WHERE n.mangled=$name RETURN n.id AS id,n.metadata AS metadata',name=name)]
        known = []
        for row in candidates:
            meta = json.loads(row['metadata'])
            location = meta.get('definition_location',{})
            path = location.get('path') or (meta.get('path') if meta.get('source_definition') else None)
            if path and not path.startswith('/') and (ROOT/path).is_file():
                known.append((row['id'],path))
        hints = {t['source_file'] for t in task['targets'] if t.get('mangled')==name and t.get('source_file')}
        if hints:known = [row for row in known if row[1] in hints]
        if len(known) != 1:
            mapping_unknown.append({'mangled':name,'candidates':known,'reason':'No unique indexed source definition'})
        else:
            roots.add(known[0][0])
        # Current selected record proof links are authoritative in SQLite;
        # graph proof bundles remain historical provenance and do not drive expansion.
        record=item['record'] or {}
        for field in ('validation','behavior_validation'):
            if record.get(field):proof_ids.add('file:uc-library/'+record[field])
    native=make_context(ROOT,out,task['originals'],required=False)
    for item in task['originals']:
        from native_context import target_key
        name=item['original']['mangled']
        if any(m['mangled']==name for m in mapping_unknown) and target_key(item['original']) not in set(native['bodies'])|set(native.get('external_bodies',{})):
            raise ContextError('No source/native body; empty packets forbidden: '+name)
    dependency_roots=set()
    for value in native['nodes'].values():
        binding=value.get('resolution',{})
        if binding.get('strategy')!='external_source':continue
        name=value['metadata'].get('mangled')
        candidates=[dict(r) for r in session.run('MATCH(n:Function) WHERE n.mangled=$name RETURN n.id AS id,n.metadata AS metadata',name=name)]
        known=[r['id'] for r in candidates if json.loads(r['metadata']).get('definition_location',{}).get('path')]
        if len(known)==1:dependency_roots.add(known[0])
    context = set(); call_functions = set()
    for seed in roots|dependency_roots:
        context.update(graph_closure(session,seed,context=True))
        call_functions.update(graph_closure(session,seed))
        callers.update(query(session,'references',seed))
        tests.update(query(session,'tests',seed))
    nodes = read_nodes(session,context|callers|proof_ids|tests)
    for seed in context|callers:
        source = query(session,'source_files',seed)
        for file in source:reasons.setdefault(file,[]).append(seed)
        reading.update(source)
        missing = query(session,'unresolved',seed)
        unresolved.extend({'from':seed,'target':target,'reason':'unresolved dispatch; inspect/escalate'} for target in sorted(missing))
    for test in tests:fixtures.update(query(session,'fixtures',test))
    file_nodes = read_nodes(session,reading|fixtures|proof_ids)
    for item in task['originals']:
        record=item['record'] or {}
        for field in ('validation','behavior_validation'):
            if record.get(field):
                key='file:uc-library/'+record[field]
                file_nodes[key]={'kind':'Proof','label':key.removeprefix('file:'),
                                 'metadata':{'recorded_sha256':record.get(field+'_sha256')}}
    selected = dict(native['selected_file_sha256'])
    for payload in task['work_binding']['unique_payload_dependencies']:
        if sha(inside(ROOT,payload['object_path']))!=payload['content_sha256']:raise ContextError('Payload content object changed')
        selected[payload['object_path']]=payload['content_sha256']
    aliases = {}; source_paths = []
    for path in task.get('declared_source_dependencies',[]):
        file=inside(ROOT,path);expected=state['files'].get(path,{}).get('sha256')
        if not expected or sha(file)!=expected:raise ContextError('Declared source dependency not bound to current graph: '+path)
        selected[path]=expected;source_paths.append(path);reasons[path]=['explicit task adapter dependency']
    for key,value in file_nodes.items():
        path = value['label']
        if path.startswith('/'):
            unresolved.append({'path':path,'reason':'External source boundary'}); continue
        file = inside(ROOT,path)
        if not file.is_file():
            raise ContextError('Required input absent: '+path)
        digest = sha(file)
        expected = state['files'].get(path,{}).get('sha256')
        if key in reading and (not expected or expected!=digest):
            raise ContextError('Required source not hash-bound to graph: '+path)
        if key in fixtures and value['metadata'].get('sha256') != digest:
            raise ContextError('Fixture differs from graph: '+path)
        if key in proof_ids and value['metadata'].get('recorded_sha256') not in (None,digest):
            raise ContextError('Proof differs from registry binding: '+path)
        selected[path]=digest
        if key in reading:aliases.setdefault(digest,[]).append(path)
    for digest,paths in aliases.items():
        source_paths.append(next((p for p in paths if p.startswith('third_party/')),sorted(paths)[0]))
    if unresolved and task['mode']=='reconstruct' and not task.get('uncertainty_work'):
        raise ContextError('Unresolved scope requires explicit uncertainty_work assignment; no silent pruning')
    lines = ['# Subagent context','',task['objective'],'',
             'Scope: current source/build graph and verified ELF evidence. Read ELF_CONTEXT.md. Runtime completeness is not claimed.','',
             '## Original targets','']
    for item in task['originals']:
        o=item['original'];r=item['record'] or {}
        lines.append(f"- `{o['elf']}` / `{o['mangled']}`; `{o['demangled']}`; {o['firmware']}; address {o['address']}; size {o['size']}; section {o['section_json']}")
        if r.get('unresolved'):lines.append('  Unresolved declaration: '+r['unresolved'])
    lines += ['', '## Read first','',*['- `'+p+'`; baseline snapshot `'+state.get('source_snapshots',{}).get(p,p)+'`' for p in sorted(source_paths)],
              '', '## Source functions in call closure','']
    for key in sorted(call_functions):
        value=nodes.get(key)
        if value:lines.append('- `'+key+'` — '+value['label'])
    lines += ['', '## Test, fixture and proof entry points','',
              *['- `'+x+'`' for x in sorted(tests|fixtures|proof_ids)],
              '', '## Unknowns','',json.dumps(unresolved+mapping_unknown,ensure_ascii=False,indent=2),
              '', 'No validation gate is waived. Core comes from pinned official source; original return/layout/hardware claims stay bounded.']
    (out/'CONTEXT.md').write_text('\n'.join(lines)+'\n')
    tasklines=['# Task', '',task['objective'],'','Namespace ownership: `'+task['namespace']+'`',
               'Mode: '+task['mode'], 'Owned files: '+json.dumps(task.get('owned_files',[])),
               '', 'Root owns shared CMake/build files, global readiness ledger and admission.',
               'Research launch pause in AGENTS.md remains in force; this packet does not authorize its release.']
    tasklines += ['', '## Unique work and original coverage', '', json.dumps(task['work_binding'],indent=2),
                  '', 'Validate each covered original separately. Shared work is not shared readiness.']
    (out/'TASK.md').write_text('\n'.join(tasklines)+'\n')
    prompt = ('Read /home/rs/projects/opencs/ai-line-analysis/AGENTS.md first. '
              'Your assigned namespace is '+task['namespace']+'. Read TASK.md, ELF_CONTEXT.md, SOURCE_SLICES.md and CONTEXT.md in '+
              '/home/rs/projects/opencs/ai-line-analysis/'+str(out.relative_to(ROOT))+'. '
              'Respect exact original identities, assigned file ownership and all validation gates. '
              'For reconstruction deliver C++, native/provider fixtures, executable replay and local proof as HANDOFF.json according to docs/worker-handoff.md; read that contract before starting. '
              'Do not expand whole proof bundles by default. If context is missing, request Root to run select_context.py expand with query, seed and reason. '
              'For an in-flight task use --baseline to query the dispatched source generation; use bound source snapshots if workspace files have changed. '
              'Do not treat absent mappings as independence. Do not alter global CMake/readiness/registry. '
              'This assignment has mode '+task['mode']+'.')
    (out/'SUBAGENT_PROMPT.md').write_text(prompt+'\n')
    packet = {'version':1,'state':'selected','tool_sha256':tools(),
              'task_id':task['task_id'],'mode':task['mode'],'backend':'memgraph',
              'generation_sha256':active['state_sha256'],'agents_sha256':sha(ROOT/'AGENTS.md'),
              'task_sha256':sha(out/'request.json'),'selected_file_sha256':selected,
              'roots':sorted(roots),'context_nodes':sorted(context|set(native['nodes'])),'call_functions':sorted(call_functions),
              'source_context_nodes':sorted(context),'native_roots':native['roots'],
              'callers':sorted(callers),'tests':sorted(tests),'fixtures':sorted(fixtures),'proofs':sorted(proof_ids),
              'source_files':sorted(source_paths),'source_aliases':aliases,'inclusion_reasons':reasons,
              'source_snapshots':{p:state.get('source_snapshots',{}).get(p) for p in selected},
              'nodes':dict(nodes,**native['nodes']),
              'unknowns':unresolved+mapping_unknown,'source_runtime_complete':False,
              'native_context':native,
              'originals':task['originals'],
              'work_binding':task['work_binding'],
              'packet_sha256':{p:sha(out/p) for p in ('TASK.md','CONTEXT.md','SUBAGENT_PROMPT.md','request.json','ELF_CONTEXT.md','native-context.json')}}
    packet['slice_translation_units']=[]
    for function in call_functions:
        found=session.run('MATCH(t:TranslationUnit)-[:DEFINES_FUNCTION]->(:Artifact {id:$id}) '
                          'RETURN t.label AS path ORDER BY path LIMIT 1',id=function).single()
        if found:packet['slice_translation_units'].append(found['path'])
    guard(ROOT,active);graph_marker(session,active)
    (out/'context.json').write_text(json.dumps(packet,indent=2)+'\n')
    validate_packet(session,out,active,require_ready=False)
    print(json.dumps({'prepared':True,'source_files':len(source_paths),'context_nodes':len(packet['context_nodes']),
                      'source_functions':len(call_functions),'native_bodies':len(native['bodies']),
                      'native_relations':len(native['edges']),'unknowns':len(packet['unknowns'])}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('register','prepare','finalize','validate','dispatch','expand'))
    p.add_argument('--out',required=True)
    a=p.parse_args();out=inside(ROOT,a.out)
    driver=GraphDatabase.driver(memgraph_uri(ROOT),auth=None)
    with driver.session() as session:
        if a.action=='register':register(session,out)
        else:
            active=json.loads(ACTIVE.read_text())
            if a.action=='prepare':prepare(session,out,active)
            elif a.action=='finalize':
                packet=validate_packet(session,out,active,require_ready=False)
                if packet['state']!='selected':raise ContextError('Already finalized')
                slices=json.loads((out/'source-slices.json').read_text())
                task=json.loads((out/'request.json').read_text())
                if slices['missing_bodies'] and task['mode']=='reconstruct' and not task.get('uncertainty_work'):
                    raise ContextError('Missing source bodies require an explicit uncertainty_work task')
                for item in slices['functions'].values():
                    if sha(inside(ROOT,item['path']))!=item['source_sha256']:
                        raise ContextError('Slice input changed')
                packet['source_slices']=slices
                require_nonempty(packet)
                packet['packet_sha256'].update({p:sha(out/p) for p in ('SOURCE_SLICES.md','source-slices.json')})
                packet['state']='dispatch_ready'
                (out/'context.json').write_text(json.dumps(packet,indent=2)+'\n')
                validate_packet(session,out,active)
                print(json.dumps({'finalized':True,'source_lines':slices['source_lines']}))
            elif a.action in ('validate','dispatch'):
                packet=validate_packet(session,out,active)
                if a.action=='dispatch':
                    destination=out/'DISPATCH.json'
                    if destination.exists():raise ContextError('Dispatch already materialized; validate/reuse its exact payload')
                    task=json.loads((out/'request.json').read_text())
                    payload={'task_name':task['task_id'],'fork_turns':'none',
                             'message':(out/'SUBAGENT_PROMPT.md').read_text()+
                             ' Context manifest SHA-256: '+sha(out/'context.json')}
                    destination.write_text(json.dumps(payload,indent=2)+'\n')
                print(json.dumps({'valid':True,'generation':packet['generation_sha256']}))
            else:
                request=json.loads((out/'expansion-request.json').read_text())
                parent=inside(ROOT,request['parent'])
                packet=validate_packet(session,parent,active,baseline=request.get('view')=='task-baseline')
                if request['seed'] not in set(packet['context_nodes']+packet['callers']+packet['roots']+
                                              list(packet.get('native_context',{}).get('nodes',{}))+
                                              [ 'symbol:'+x['original']['elf']+':'+x['original']['mangled'] for x in packet['originals']]):
                    raise ContextError('Expansion seed is not bound to parent packet')
                if request['seed'].startswith(('native:','native-address:')):
                    c,pointer=open_index(ROOT)
                    try:
                        if pointer['sha256']!=packet['native_context']['generation_sha256']:
                            raise ContextError('Native generation changed; use a new packet')
                        nodes,edges=native_select(c,[request['seed']],request['query'])
                        body=c.execute('SELECT payload FROM bodies WHERE id=?',(request['seed'],)).fetchone()
                        result={'parent_manifest_sha256':sha(parent/'context.json'),'request':request,
                                'nodes':nodes,'edges':edges,'body':json.loads(body[0]) if body else None}
                        if request['query']=='native_body':
                            meta=nodes[request['seed']]['metadata']
                            result['evidence']=make_context(ROOT,out,[{'original':meta,'record':None}])
                        (out/'expansion.json').write_text(json.dumps(result,indent=2)+'\n')
                        print(json.dumps({'expanded':True,'nodes':len(nodes)}));return
                    finally:c.close()
                ids=query(session,request['query'],request['seed']);nodes=read_nodes(session,ids)
                state=json.loads(inside(ROOT,active['state']).read_text())
                for value in nodes.values():
                    path=value['metadata'].get('path') or value['metadata'].get('definition_location',{}).get('path')
                    if path and not path.startswith('/'):
                        expected=state['files'].get(path,{}).get('sha256')
                        snapshot=state.get('source_snapshots',{}).get(path)
                        file=inside(ROOT,snapshot) if request.get('view')=='task-baseline' and snapshot else inside(ROOT,path)
                        if not expected or sha(file)!=expected:raise ContextError('Expansion source stale: '+path)
                        value['source_snapshot']=snapshot
                result={'parent_manifest_sha256':sha(parent/'context.json'),'view':request.get('view','current'),
                        'request':request,'nodes':nodes}
                if request.get('view')!='task-baseline':guard(ROOT,active)
                graph_marker(session,active)
                (out/'expansion.json').write_text(json.dumps(result,indent=2)+'\n')
                print(json.dumps({'expanded':True,'nodes':len(nodes)}))
    driver.close()


if __name__=='__main__':
    try:main()
    except (ContextError,ValueError,KeyError) as exc:raise SystemExit('CONTEXT BLOCKED: '+str(exc))
