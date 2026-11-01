#!/usr/bin/env python3
"""Capture fresh worker-local proof and final per-packet HANDOFFs."""
import collections, datetime, hashlib, importlib.metadata, json, os, pathlib, subprocess, time
BASE=pathlib.Path(__file__).resolve().parent
ROOT=BASE.parents[2]
REL=str(BASE.relative_to(ROOT))
SCRATCH=ROOT/'temp/recovery-work/graph-live-trial-05/item-worker'
PY='uc-library/.venv/bin/python'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def hash_(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def save(name,value):(BASE/name).write_text(json.dumps(value,indent=2)+'\n')
def command(argv):
    start=now(); t=time.monotonic();p=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True)
    entry={'argv':argv,'start_utc':start,'end_utc':now(),'duration_seconds':time.monotonic()-t,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
    if p.returncode:save('failed-seal.json',entry);raise RuntimeError(entry)
    return entry

def main():
    started=now(); commands=[]
    commands.append(command([PY,REL+'/oracle.py']))
    for kind in ['format','compile','symbols','replay']:
        commands.append(command([PY,REL+'/check.py',kind]))
    fixtures=json.loads((BASE/'native-fixtures.json').read_text())
    sources=['uc-library/include/presonus/MeterManagerBase.hpp','uc-library/src/Presonus/MeterManagerBase.cpp','uc-library/tests/graph_trial05_item_tests.cpp']
    explicit=['third_party/ccl-framework/core/portable/coreparams.h','third_party/ccl-framework/core/public/corevector.h','third_party/ccl-framework/core/system/corethread.h','uc-library/include/presonus/uc/events.hpp','uc-library/include/presonus/uc/network_manager_services.hpp','uc-library/include/presonus/uc/server.hpp']
    dependencies={}
    for i in [0,1]:
        text=(SCRATCH/f'{i}.d').read_text().replace('\\\n',' ')
        for path in text.split(':',1)[1].split():
            p=pathlib.Path(path); p=p if p.is_absolute() else ROOT/p
            try: relative=str(p.relative_to(ROOT))
            except ValueError: continue
            dependencies[relative]=hash_(relative)
    compiled=json.loads(commands[-1]['stdout'])
    per_symbol=[];originals=[]
    for i in range(1,6):
        packet=f'temp/recovery-work/graph-live-trial-05/trial05_item_{i}-packet/context.json'
        context=json.loads((ROOT/packet).read_text()); original=context['originals'][0]['original']; originals.append(original)
        native=context['native_context']; root=context['native_roots'][0]
        reviewed=[]
        for edge in native['edges']:
            classification='used' if edge['src']==root and edge['kind'] not in ['ELF_TABLE_FUNCTION'] else 'protected'
            if edge['kind']=='ELF_CALLS' and edge.get('metadata',{}).get('target_address')==0xacd0:classification='unknown_exception_path'
            reviewed.append({'edge_identity':{k:edge[k] for k in ['src','dst','kind','site']},'classification':classification,'metadata':edge.get('metadata',{})})
        per_symbol.append({'mangled':original['mangled'],'packet':packet,'observed_phase_complete_utc':now(),'reviewed_edges':reviewed,'protected_dependencies':explicit,'irrelevant_dependencies':['incoming callers are protected; no caller reconstruction','duplicate $a mapping labels are instruction aliases, not extra implementation targets'],'unknown_dependencies':['original return declaration, class layout and inheritance','application virtual declaration/ownership and native scheduler behavior','native exception-unwind paths'],'range_verification':fixtures['ranges'][i-1],'native_cases':sum(c['method']==i for c in fixtures['cases'])})
    limitations=json.loads((BASE/'limitations.json').read_text()) if (BASE/'limitations.json').exists() else [
        'Portable source port only; original non-template return declarations remain pending.',
        'Thread inheritance/storage/atomics/constructor/virtual source-port seams are intentional adaptations, not original ARM layout or ABI.',
        'Server client collection/virtual calls use independent presonus::meter::Environment; those concrete app declarations remain unresolved. Delivery uses an actual borrowed Presonus::UC::INetworkManager::sendEvent provider; native singleton creation/lifetime is intentionally not recreated.',
        'Native original target instructions executed with explicit Core/app/strstr boundary stubs; Core binary implementations never executed/reconstructed.',
        'Core thread/lock/vector providers come from pinned official CCL; native/provided scheduling and termination equivalence is not claimed.',
        'Normal paths with valid mapped data only; no native exceptions, concurrent mutation, invalid pointers or hardware execution.',
        'Actual CCL OS-thread smoke is separate provider evidence, not an original scheduling oracle.',
        'Raw native lock/networkLookup/strstr and stack writes retained but omitted from normalized portable comparison.'
    ]
    proof={'version':1,'session_id':os.environ.get('CODEX_THREAD_ID'),'start_utc':started,'end_utc':now(),'status':'local_compiled_declaration_pending','elf':fixtures['elf'],'elf_sha256':fixtures['elf_sha256'],'ranges':fixtures['ranges'],'commands':commands,'tool_versions':{'unicorn':importlib.metadata.version('unicorn'),'pyelftools':importlib.metadata.version('pyelftools'),'formatter':commands[1]['stdout'].strip()},'source_sha256':{p:hash_(p) for p in sources},'explicit_ccl_dependencies':{p:hash_(p) for p in explicit},'compiled_dependencies':dependencies,'ccl_commit':'e8cbdea4a4a20e15111f5a690798a259c0374b31','ccl_archive':{'path':'temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','sha256':hash_('temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a')},'oracle_producer_sha256':hash_(REL+'/oracle.py'),'replay_producer_sha256':hash_(REL+'/check.py'),'fixture_sha256':hash_(REL+'/native-fixtures.json'),'native_execution_count':len(fixtures['cases']),'portable_replay':compiled,'per_symbol':per_symbol,'limitations':limitations,'global_readiness_admission':False}
    save('proof.json',proof)
    work={'version':1,'session_id':os.environ.get('CODEX_THREAD_ID'),'observed_final_validation_start_utc':started,'observed_final_validation_end_utc':now(),'tool_phases':commands,'previous_exact_tool_logs':str((SCRATCH/'checks.jsonl').relative_to(ROOT)),'per_symbol_context_observations':per_symbol,'context_requests':[{'request':'baseline existing ServerImplementation hasClients/client list/session and network-send provider declarations plus virtual callback slot identities','requested_at_utc':None,'timestamp_note':'Request sent through collaboration before source creation; exact provider event time retained by coordinator, not estimated here.','packet':'trial05_item_3 and trial05_item_5','seed':'native:12d91ba40b2d45e6a687a353684717f9cc0fc03e341c713bc89a5a8daed2320e','state':'closed','resolved_at_utc':now(),'resolution':'Root baseline 00-item/01-item/02-item expansions reviewed. Actual network_manager_services.hpp INetworkManager sendEvent used by borrowed reference; client collection/virtual declarations remain explicit independent Environment. No fake ServerImplementation.','expansion_receipt':'evidence/recovery/2026-11-01/dependency-graph/live-trial-05-10x5/context-expansion-receipts.json','provider_supplement':'evidence/recovery/2026-11-01/dependency-graph/live-trial-05-10x5/provider-context.json'}],'redundant_checks':['format/compile/symbol/replay repeated after adding actual CCL provider smoke and compiler dependency capture; earlier checks retained in scratch log'],'failures':['initial combined context read was client-truncated; target bodies and instructions reread in bounded calls'],'token_accounting':'Coordinator-owned; no estimates'}
    save('work-log.json',work)
    checks=[{'kind':kind,'argv':[PY,REL+'/check.py',kind],'timeout_seconds':120} for kind in ['format','compile','symbols','replay']]
    domain='115 original ARM executions: startup boundary forwarding; both shutdown join outcomes and stop mutation; 96 thread cases with server presence/client predicate, initial stop, 1/2/3/7 ticks, restored running bytes 0/1/27 and alternating phase; 11 client update cases including absent/empty servers, mixed substrings, duplicates, external split, case sensitivity and 99/100/101/110 capacity; 5 sends with empty/single/multiple/99/100 clients, route mutation and delivery traces. Actual CCL OS-thread smoke is separate.'
    integration={'production_partition':'RM','production_sources':[sources[1]],'public_headers':[sources[0]],'test_target':'graph_trial05_item_tests','test_sources':[sources[2]],'link_dependencies':['presonus_rm_components','presonus_core_upstream'],'ctest_argv':[PY,REL+'/check.py','replay','--executable','<TARGET_FILE:graph_trial05_item_tests>','--fixtures',REL+'/native-fixtures.json'],'fixture':REL+'/native-fixtures.json','formatter':'clang-format 23.1.3','note':'Root owns exact shared target name and integration; source appears in one RM OBJECT partition only. Root reports zero cross-binary exact selected-target-name intersections.'}
    artifacts=[('source',sources[0]),('source',sources[1]),('test',sources[2]),('fixture',REL+'/native-fixtures.json'),('replay',REL+'/check.py'),('producer',REL+'/oracle.py'),('producer',REL+'/seal.py'),('proof',REL+'/proof.json'),('evidence',REL+'/work-log.json'),('documentation',REL+'/README.md')]
    artifacts += [('dependency',p) for p in explicit]
    artifacts += [('context_expansion',p) for p in ['evidence/recovery/2026-11-01/dependency-graph/live-trial-05-10x5/provider-context.json','evidence/recovery/2026-11-01/dependency-graph/live-trial-05-10x5/context-expansion-receipts.json']]
    artifacts += [('context_expansion',str(p.relative_to(ROOT))) for stem in ['00-item','01-item','02-item'] for p in sorted((ROOT/'temp/recovery-work/graph-live-trial-05/expansions'/stem).glob('*.json'))]
    artifacts += [('packet',f'temp/recovery-work/graph-live-trial-05/trial05_item_{i}-packet/context.json') for i in range(1,6)]
    final_artifacts=[{'kind':kind,'path':path,'sha256':hash_(path)} for kind,path in artifacts]
    index=[]
    for i,original in enumerate(originals,1):
        target={'elf_sha256':original['elf'],'firmware':original['firmware'],'role':original['role'],'mangled':original['mangled'],'demangled':original['demangled'],'address':original['address'],'size':original['size'],'section':'.text'}
        handoff={'version':1,'task_id':f'trial05_item_{i}','namespace':'Presonus::MeterManagerBase','packet_manifest':f'temp/recovery-work/graph-live-trial-05/trial05_item_{i}-packet/context.json','originals':[target],'artifacts':final_artifacts,'checks':checks,'validation_domain':domain,'limitations':limitations,'build_integration':integration}
        name=f'HANDOFF-{i}.json';save(name,handoff);index.append({'task_id':handoff['task_id'],'path':REL+'/'+name,'sha256':hash_(REL+'/'+name)})
    save('HANDOFF-index.json',{'version':1,'session_id':os.environ.get('CODEX_THREAD_ID'),'handoffs':index,'proof':REL+'/proof.json','build_integration':integration})
    print(json.dumps({'handoffs':index,'local_replay':compiled}))
if __name__=='__main__':main()
