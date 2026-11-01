import pathlib,json,hashlib,datetime,os,subprocess
B=pathlib.Path('uc-library/candidates/graph-live-trial-05-page');S=pathlib.Path('temp/recovery-work/graph-live-trial-05/page-worker');now=datetime.datetime.now(datetime.timezone.utc).isoformat()
def hash(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def put(p,d):pathlib.Path(p).write_text(json.dumps(d,indent=2)+'\n')
fixture=json.loads((B/'fixtures.json').read_text());checks=[json.loads((S/(n+'.json')).read_text()) for n in ['format','compile','symbols','replay']]
log=json.loads((B/'work-log.json').read_text());next(x for x in log['phases'] if x['name']=='context-request').update(status='resolved',resolution_utc=now,resolution='Root authorized independent borrowed Bindings uncertainty_work after no existing production MainLCD provider found; expansions32..35 inspected')
log['phases'].append(dict(name='implementation-and-local-validation',status='complete',checks=checks));log['limitations']=['Initial request/reading UTC timestamps not instrumented; provider session retained. No estimated times substituted.','Exact source edit phase start not instrumented; format/compile/symbol/replay have timed commands.']
log['context_receipts']=[x for x in json.load(open('evidence/recovery/2026-11-01/dependency-graph/live-trial-05-10x5/context-expansion-receipts.json')) if x['worker']=='page'];put(B/'work-log.json',log)
source=['uc-library/include/presonus/PageComponent.hpp','uc-library/src/Presonus/PageComponent.cpp'];test='uc-library/tests/graph_trial05_page_tests.cpp'
limitations=['All five unencoded original return declarations remain unresolved; chosen portable returns void*, bool, void are not original declaration proof.','Borrowed owner and Bindings references are intentional independent source-port storage, not original fields/inheritance/layout/ownership.','External owner cast slot and three MainLCD calls are boundary stubs in native oracle and test doubles in C++; dependency implementations, real UI/text input lifecycle and hardware are unverified.','Stop return register is excluded because original return declaration unknown; ordered calls and boolean argument are compared.','No ARM ABI compatibility or readiness admission claimed.','Core dependency implementations remain pinned upstream and excluded from binary reconstruction. This scoped page port calls the unresolved application screen boundary; no fake Core or MainLCD production class is introduced.']
proof=dict(version=1,session_id=os.environ.get('CODEX_THREAD_ID'),sealed_utc=now,elf_sha256=fixture['elf_sha256'],ranges=fixture['ranges'],native_execution=dict(producer=str(B/'oracle.py'),sha256=hash(B/'oracle.py'),unicorn='2.1.4',started=fixture['started'],finished=fixture['finished'],case_count=len(fixture['cases']),memory_observations='all nonstack writes recorded; none observed; original stack frame writes excluded'),fixture=dict(path=str(B/'fixtures.json'),sha256=hash(B/'fixtures.json')),portable_execution=checks,formatted_sources={p:hash(p) for p in source+[test]},compiler_version=subprocess.check_output(['c++','--version'],text=True).splitlines()[0],formatter_version=subprocess.check_output(['uc-library/.venv/bin/clang-format','--version'],text=True).strip(),limitations=limitations)
put(B/'proof.json',proof)
shared=[]
for kind,paths in [('source',source),('test',[test]),('fixture',[str(B/'fixtures.json')]),('replay',[str(B/'replay.py')]),('proof',[str(B/'proof.json')]),('producer',[str(B/'oracle.py'),str(B/'check.py'),str(B/'seal.py')]),('context',[str(B/'context-observations.json'),str(B/'work-log.json')])]:
 for p in paths:shared.append(dict(kind=kind,path=p,sha256=hash(p)))
shared.append(dict(kind='dependency',path='rootfs/CS18_v13840/home/root/surface',sha256=hash('rootfs/CS18_v13840/home/root/surface')))
for n in range(1,6):
 p=f'temp/recovery-work/graph-live-trial-05/trial05_page_{n}-packet/context.json';shared.append(dict(kind='packet',path=p,sha256=hash(p)))
for n in [32,33,34,35]:
 p=pathlib.Path(f'temp/recovery-work/graph-live-trial-05/expansions/{n}-page')
 for name in ['expansion.json','native-context.json','ELF_CONTEXT.md']:
  if (p/name).exists():shared.append(dict(kind='dependency',path=str(p/name),sha256=hash(p/name)))
index=[]
for n,r in enumerate(fixture['ranges'],1):
 packet=f'temp/recovery-work/graph-live-trial-05/trial05_page_{n}-packet/context.json'
 original=dict(elf_sha256=fixture['elf_sha256'],firmware='CS18AI surface 13840',role='client',mangled=r['mangled'],address=r['address'],size=r['size'],section='.text')
 d=dict(version=1,task_id=f'trial05_page_{n}',namespace='Presonus::PageComponent',packet_manifest=packet,originals=[original],artifacts=shared,checks=[dict(kind=k,argv=['uc-library/.venv/bin/python',str(B/'check.py'),k],timeout_seconds=120) for k in ['format','compile','symbols','replay']],validation_domain=f"{sum(x['n']==n for x in fixture['cases'])} original ARM cases for target; combined 135 native/C++ cases cover owner null/present, cast screen null/present, current page equal/different, editing false/true, cancel false/true, seven class IDs; ordered external call targets/receiver/arguments compared directly. No nonstack native writes observed.",limitations=limitations,build_integration=dict(production_partition='CS18',sources=[source[1]],public_headers=[source[0]],test_target='graph_trial05_page_tests',test_sources=[test],link_dependencies=['presonus_uc_client'],ctest_argv=['uc-library/.venv/bin/python',str(B/'replay.py'),'--executable','$<TARGET_FILE:graph_trial05_page_tests>','--fixtures',str(B/'fixtures.json')],fixture_sha256=hash(B/'fixtures.json')))
 path=B/f'packet-{n}'/'HANDOFF.json';path.parent.mkdir(exist_ok=True);put(path,d);index.append(dict(task_id=d['task_id'],path=str(path),sha256=hash(path)))
put(B/'HANDOFF-INDEX.json',dict(version=1,session_id=os.environ.get('CODEX_THREAD_ID'),handoffs=index))
print(json.dumps(index))
