import argparse,hashlib,importlib.util,json,subprocess,sys,time,datetime
from pathlib import Path
from native import TASKS,PACKETS
TEST=Path('uc-library/tests/recovery/meter_manager_family');SCRATCH=Path('temp/recovery-work/meter_manager_family');SCRATCH.mkdir(parents=True,exist_ok=True)
CANON=Path('/home/rs/projects/opencs/ai-line-analysis');SDK=CANON/'temp/core-upstream/root-integration-01/upstream-core/sdk';EXE=SCRATCH/'Replay'
SOURCES=['uc-library/src/Presonus/MeterManagerBase.cpp','uc-library/src/Presonus/MeterManager.cpp']
HEADERS=['uc-library/include/presonus/MeterManagerBase.hpp','uc-library/include/presonus/MeterManager.hpp','uc-library/include/presonus/MeterBallistics.hpp']
FORMAT=['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*SOURCES,*HEADERS,str(TEST/'Replay.cpp')]
CXX=['/usr/bin/c++','-std=c++17','-O2','-Ulinux','-DPRESONUS_HAS_UPSTREAM_CORE=1','-DCORE_USE_OPENSSL=1','-DNDEBUG=1','-Iuc-library/include','-isystem',str(SDK/'include/presonus-core-5')]
CLOSURE=Path('temp/recovery-work/rolling-c001-20261124/packeting/sqlite-cycle02/meter_external_transport_sol61/ACTUAL-APP-LINK-CLOSURE.json')
LINK=CXX+json.loads(CLOSURE.read_text())['sources']+[SOURCES[1],str(TEST/'Replay.cpp'),str(SDK/'lib/libcorelib.a'),str(SDK/'lib/libpresonus_core_allocator.a'),str(CANON/'temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a'),'-lssl','-lcrypto','-ldl','-lm','-pthread','-o',str(EXE)]
RECORDS=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv):
 start=time.time();r=subprocess.run(argv,text=True,capture_output=True);log=SCRATCH/(str(time.time_ns())+'.log');log.write_text(r.stdout+r.stderr);RECORDS.append(dict(argv=argv,start_unix=start,elapsed_seconds=time.time()-start,exit_code=r.returncode,log=str(log),log_sha256=sha(log)))
 if r.returncode:raise RuntimeError((argv,r.returncode,r.stdout,r.stderr))
 return r.stdout

def replay():
 fixture=json.loads((TEST/'fixtures.json').read_text())
 for c in fixture['cases']:
  a=c['input'];o=c['observed']
  if a['kind']=='roster':
   got=list(map(int,run([str(EXE),'roster',str(a['index']),str(a['selector']),str(a['meterkind']),a['population']]).split()));expected=[o['roster'],*o['counts'],int(o['allocated']),o['position'],o['mode']];assert got==expected,(a,got,expected)
  elif a['kind']=='external':
   for width in [1,2]:
    got=list(map(int,run([str(EXE),'external',str(a['count']),str(a['selector']),str(width),str(a['result'])]).split()));expected=[*o['routes'],int(bool(a['count'] and a['result'])),a['count']]
    for t in o['trace'][1:]:
     # Decode exact initialized native envelope members into actual codec bytes.
     _,tag,size,ra,rb,key,source,count,records,aa,bb,cc=t
     payload=list(key.to_bytes(4,'big')+source.to_bytes(2,'little')+count.to_bytes(2,'little')+bytes([records])+aa.to_bytes(2,'little')+bb.to_bytes(2,'little')+cc.to_bytes(2,'little'))
     expected += [tag,size,ra,rb,*payload]
    assert got==expected,(a,width,got,expected)
  else:assert run([str(EXE),'noop']).strip()=='noop-pass'
 for width in [1,2]:assert run([str(EXE),'negative','1','0',str(width),'1']).strip()=='negative-pass'
 print(json.dumps(dict(passed=True,native_cases=len(fixture['cases']),portable_cases=len(fixture['cases'])+24+2)))

DOMAIN='RM13731 exact four native entries; 554 original executions. All selector branches -1/0..9, kind0/1/3/4, indices0/1/3/12, empty/full/null distinct owning roster entries, fixed offsets1/2/1/2 and selector1 offset1. Nonnegative inputs and bounded signed sums, stable/no concurrency, allocation success and initialized decay-table path. CCL negative static-error pointer observed zero. Empty/1/3 external clients, selectors-1/0/65536/65537, ignored real send success/failure, both typed Meter8/16 owners, initialized perm members, ordered fanout routes. Unbound/mismatched mutable provenance and retained owner lifetime checked.'
LIMITS=['Portable source port; original class layout/inheritance/ARM ABI and unencoded ordinary returns unresolved. getMeterMaid pointer/getProperty-release void/external void are explicit portable choices. No hardware or original constructor/lifecycle credit.', 'Native allocator succeeds; native CCL append and lock/network dispatch are explicit provider boundaries. Actual MeterMaid/Ballistics native constructor instructions execute with already initialized decay-table guard. Original allocation failure/unwind and decay-table first initialization excluded.', 'Native perm object has uninitialized padding/tail outside written members; host zero-initializes independent typed storage. Only native initialized members and resulting used wire payload are compared; no claim for original padding.', 'MutableMeterOrigins shared ownership and tagged source-port constructors are independent adaptations. Caller serializes bindings, mutation and dispatch. All roster pointers must be null or distinct uniquely owned live objects. No original owning-roster destructor claim.', 'Sender connection.hpp read is exact approved hash; later sender canonical integration requires new dependency replay/reseal. No sender metadata/claim mutation. Existing accepted MeterPeak artifact bytes unchanged.']

def seal():
 fixture=json.loads((TEST/'fixtures.json').read_text());symbols=run(['/usr/bin/nm','--defined-only',str(EXE)]);formatter=run(['uc-library/.venv/bin/clang-format','--version']).strip();compiler=run(['/usr/bin/c++','--version']).splitlines()[0]
 for task in TASKS:
  packet=PACKETS/task/'CONTEXT.json';ctx=json.loads(packet.read_text());candidate=Path('uc-library/candidates')/task;candidate.mkdir(parents=True,exist_ok=True);proof=candidate/'worker-proof.json'
  targets=[x['original'] for x in ctx['originals']];assert all(t['mangled'] in symbols for t in targets)
  proof.write_text(json.dumps(dict(version=1,task_id=task,worker_session_id=__import__('os').environ.get('CODEX_THREAD_ID','unavailable'),sealed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),original_execution=dict(argv=['uc-library/.venv/bin/python',str(TEST/'native.py')],fixture=str(TEST/'fixtures.json'),fixture_sha256=sha(TEST/'fixtures.json'),producer_sha256=sha(TEST/'native.py'),ranges=targets,fixture_native_cases=len(fixture['cases']),native_boundaries=fixture['native_boundaries'],native_constructor_domain=fixture['constructor'],static_error_address=fixture['static_error_address'],static_error_value=0),formatter_version=formatter,compiler_version=compiler,formatted_source_hashes={p:sha(p) for p in SOURCES+HEADERS+[str(TEST/'Replay.cpp')]},command_records=RECORDS,compiled_symbols=symbols,link_provider_scope=dict(closure=str(CLOSURE),sources=json.loads(CLOSURE.read_text())['sources'],core_archive=str(SDK/'lib/libcorelib.a'),core_archive_sha256=sha(SDK/'lib/libcorelib.a'),gc_sections=False),validation_domain=DOMAIN,limitations=LIMITS),indent=2)+'\n')
  paths={}
  for p in SOURCES+HEADERS:paths[p]='source'
  paths[str(TEST/'Replay.cpp')]='test';paths[str(TEST/'native.py')]='test';paths[str(TEST/'check.py')]='replay';paths[str(TEST/'fixtures.json')]='fixture';paths[str(proof)]='proof';paths[str(packet)]='packet'
  for p in ctx['read_files']:
   if Path(p).is_file() and p not in paths:paths[p]='dependency'
  # Bind immutable execution log snapshots; future checks write fresh unique files.
  for r in RECORDS:paths[r['log']]='log'
  artifacts=[dict(kind=k,path=p,sha256=sha(p)) for p,k in paths.items()]
  checks=[dict(kind='format',argv=FORMAT,timeout_seconds=120)]+[dict(kind=k,argv=['uc-library/.venv/bin/python',str(TEST/'check.py'),'--'+k],timeout_seconds=600) for k in ['compile','symbols','replay']]
  handoff=dict(version=1,task_id=task,namespace=ctx['task']['namespace'],packet_manifest=str(packet),originals=[dict(elf_sha256=t['elf'],**{k:t[k] for k in ['firmware','role','mangled','address','size','section']}) for t in targets],artifacts=artifacts,checks=checks,validation_domain=DOMAIN,limitations=LIMITS,build_integration=dict(production_partition='common; existing MeterManagerBase.cpp plus new MeterManager.cpp exactly once',public_headers=HEADERS,test_targets=['meter_manager_family'],link_dependencies=['27 existing common provider CPP units in ACTUAL-APP-LINK-CLOSURE.json','pinned official CCL corelib+allocator','private glibc29 provider; ssl crypto dl m pthread'],ctest_argv=['uc-library/.venv/bin/python',str(TEST/'check.py'),'--replay','--executable','<canonical executable>'],fixture=str(TEST/'fixtures.json'),affected_existing_replays=['all MeterManagerBase/MeterBallistics consumers require fresh current-header proof'],constructor_credit=0))
  hp=candidate/'HANDOFF.json';hp.write_text(json.dumps(handoff,indent=2)+'\n')
  spec=importlib.util.spec_from_file_location('accept_worker',Path('uc-library/tools/recovery/accept_worker.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.validate(handoff)
  receipt=candidate/'preflight.json';receipt.write_text(json.dumps(dict(handoff_sha256=sha(hp),validator='uc-library/tools/recovery/accept_worker.py',validator_sha256=sha('uc-library/tools/recovery/accept_worker.py'),validate='passed',all_artifact_hashes_rechecked=True),indent=2)+'\n')
  print(task,'frozen',sha(hp))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--compile',action='store_true');p.add_argument('--symbols',action='store_true');p.add_argument('--replay',action='store_true');p.add_argument('--seal-existing',action='store_true');p.add_argument('--executable');a=p.parse_args()
 if a.executable:EXE=Path(a.executable)
 if a.compile or a.seal_existing:run(FORMAT);run(LINK)
 if a.symbols or a.seal_existing:
  symbols=run(['/usr/bin/nm','--defined-only',str(EXE)])
  for t in TASKS:
   for o in json.loads((PACKETS/t/'CONTEXT.json').read_text())['originals']:assert o['original']['mangled'] in symbols
 if a.replay or a.seal_existing:replay()
 if a.seal_existing:seal()
