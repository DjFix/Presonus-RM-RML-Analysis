"""Reproduce actual local checks or replay a canonical executable with explicit fixtures.
proof mode executes checks and creates a NEW hash-bound proof; no registry writes.
"""
import argparse,datetime,hashlib,importlib.util,json,pathlib,subprocess,time,os
ROOT=pathlib.Path(__file__).resolve().parents[4];BASE=pathlib.Path(__file__).resolve().parent;TASK=BASE.name
WORK=ROOT/'temp/recovery-work/compact-10x20-20261113/fx-pages-local'/TASK
COMMON=ROOT/'uc-library/tests/recovery/compact20_surface_fx_pages_02'
PRODUCTION=['uc-library/src/Presonus/Surface/'+n+'.cpp' for n in ['FXEditPageComponent','FxPresetsPageComponent','FXHomePageComponent']]
HEADERS=['uc-library/include/presonus/surface/'+n+'.hpp' for n in ['FXEditPageComponent','FxPresetsPageComponent','FXHomePageComponent']]
PROVIDERS=['third_party/ccl-framework/core/portable/corecomponent.h','third_party/ccl-framework/core/portable/corecomponent.cpp','third_party/ccl-framework/core/portable/coreparams.h','third_party/ccl-framework/core/portable/coreparams.cpp','third_party/ccl-framework/core/portable/coreparaminfo.h','third_party/ccl-framework/core/public/corevector.h','third_party/ccl-framework/core/public/corestringtraits.h','third_party/ccl-framework/core/public/corestringbuffer.h']
EXISTING=['uc-library/include/presonus/surface/MixerPageComponent.hpp','uc-library/src/Presonus/Surface/MixerPageComponent.cpp']
FLAGS=['-std=c++20','-O0','-g','-Ulinux','-fno-rtti','-fno-lto','-fno-devirtualize','-fno-devirtualize-speculatively','-fno-fast-math','-ffunction-sections','-fdata-sections','-UNDEBUG','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework']
WRAPS=['_ZdlPv','_ZdlPvm','_ZdaPv','_ZdaPvm','_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE','_ZN4Core8Portable10AliasParam11setOriginalEPNS0_9ParameterE','_ZN4Core8Portable9ComponentD2Ev']
ARCHIVES=['temp/provider-baseline08/'+n for n in ['libpresonus_uc.a','libcorelib.a','libpresonus_core_allocator.a']]
LINK=['-Wl,--gc-sections','-Wl,--start-group',*ARCHIVES,'-Wl,--end-group',*['-Wl,--wrap='+n for n in WRAPS],'/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lpthread','-ldl','-lm']
def H(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def bindings(paths):return {str(pathlib.Path(p)):H(ROOT/p) for p in paths}
def run(argv,input=None):
 print(json.dumps(list(map(str,argv))),flush=True);before=time.monotonic();started=datetime.datetime.now(datetime.timezone.utc).isoformat();v=subprocess.run(list(map(str,argv)),cwd=ROOT,input=input,capture_output=True,text=True,timeout=180,env={**os.environ,'TMPDIR':str(WORK)})
 item={'argv':list(map(str,argv)),'start_utc':started,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'seconds':time.monotonic()-before,'returncode':v.returncode,'stdout':v.stdout,'stderr':v.stderr};commands.append(item)
 if v.returncode:raise RuntimeError(json.dumps(item))
 return v.stdout
commands=[]
def fmt():
 version=run([ROOT/'uc-library/.venv/bin/clang-format','--version']).strip();run([ROOT/'uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*PRODUCTION,*HEADERS,COMMON/'Replay.cpp',BASE/'Replay.cpp']);return version

def compile_cpp():
 WORK.mkdir(parents=True,exist_ok=True);objects=[]
 for i,p in enumerate([*PRODUCTION,str((BASE/'Replay.cpp').relative_to(ROOT))]):
  obj=WORK/f'unit{i}.o';run(['c++',*FLAGS,'-MMD','-MF',WORK/f'unit{i}.d','-c',p,'-o',obj]);objects.append(obj)
 run(['c++',*objects,*LINK,'-o',WORK/'replay']);return objects

def symbols(exe,fixture):
 names={x.split()[-1] for x in run(['nm','--defined-only',exe]).splitlines() if x.split()}
 for target in fixture['ranges']:assert target['mangled'] in names,target['mangled']
 return [x['mangled'] for x in fixture['ranges']]

def native():
 module=BASE/'native.py';run([ROOT/'uc-library/.venv/bin/python',module,'--verify'])

def replay(exe,fixture):
 lines=[];expected=[];task=int(TASK.rsplit('_',1)[1]);provider_inputs=[]
 for c in fixture['cases']:
  if c['kind']=='url':lines.append(f"U {c['index']} {c['prefix_length']}");provider_inputs.append(f"P {c['observation']['expected']['argument']} {c['prefix_length']}")
  elif c['kind']=='disconnect':lines.append(' '.join(map(str,['D',4,len(c['types']),0,0,*c['types']])));expected.append(c['observation']['expected'])
  else:lines.append(f"D {task} {c['observed_count']} {c['mappable_count']} {c['alias_count']}");expected.append(c['observation']['expected'])
 outputs=run([exe],input='\n'.join(lines)+'\n').splitlines();assert len(outputs)==len(lines),(outputs,lines)
 if provider_inputs:
  provider_outputs=run([exe],input='\n'.join(provider_inputs)+'\n').splitlines();assert outputs==provider_outputs,(outputs,provider_outputs)
  assert all(c['observation']['expected']['format']=='fx/ch%d' and c['observation']['expected']['returns_destination'] for c in fixture['cases']);assert all(x.endswith(' 1') for x in outputs)
 else:
  for c,line,want in zip(fixture['cases'],outputs,expected):assert list(map(int,line.split()))==want,(c,line,want)
 return {'cases':len(lines),'portable_observations':outputs,'direct_pinned_provider_observations':provider_outputs if provider_inputs else [],'native_application_comparison':True,'real_CCL_owned_children_and_parameters_deallocated':not provider_inputs and task!=4,'native_Core_executed':False,'native_allocator_internals_executed':False}

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['format','compile','symbols','native','replay','proof']);p.add_argument('--executable',default=str(WORK/'replay'));p.add_argument('--fixtures',default=str(BASE/'fixtures.json'));p.add_argument('--fixture-sha256');p.add_argument('--proof-output');p.add_argument('--object',action='append',default=[]);p.add_argument('--integration-proof');p.add_argument('--linked-archive',action='append',default=[]);o=p.parse_args();WORK.mkdir(parents=True,exist_ok=True);fixture=json.loads(pathlib.Path(o.fixtures).read_text());assert fixture['task_id']==TASK
 if o.fixture_sha256:assert H(o.fixtures)==o.fixture_sha256
 if o.mode=='format':print(fmt())
 elif o.mode=='compile':print(compile_cpp())
 elif o.mode=='symbols':print(symbols(o.executable,fixture))
 elif o.mode=='native':native();print('Native exact range observations reproduced')
 elif o.mode=='replay':print(json.dumps(replay(o.executable,fixture)))
 else:
  assert o.proof_output and not pathlib.Path(o.proof_output).exists(),'NEW proof output required'
  local_executable=pathlib.Path(o.executable).resolve()==(WORK/'replay').resolve()
  if not local_executable:
   assert o.integration_proof and pathlib.Path(o.integration_proof).is_file(),'External/canonical executable requires fresh integration proof'
   assert o.object and all(pathlib.Path(q).is_file() for q in o.object),'Actual canonical compiled objects required'
  native();version=fmt();
  if pathlib.Path(o.executable).resolve()==(WORK/'replay').resolve():compile_cpp()
  compiler=run(['c++','--version']).splitlines()[0];names=symbols(o.executable,fixture);observed=replay(o.executable,fixture)
  task=int(TASK.rsplit('_',1)[1]);uncertainties=['Original ordinary method return declaration is unencoded and unresolved.'] if task in [4,12] else []
  sources=bindings([*PRODUCTION,*HEADERS,*EXISTING,str((COMMON/'Replay.cpp').relative_to(ROOT)),str((COMMON/'native.py').relative_to(ROOT)),str((BASE/'Replay.cpp').relative_to(ROOT)),str((BASE/'native.py').relative_to(ROOT)),str((BASE/'check.py').relative_to(ROOT)),str(pathlib.Path(o.fixtures).resolve().relative_to(ROOT))]);provider=bindings(PROVIDERS)
  records=[dict(original_elf_sha256=x['original_elf_sha256'],mangled=x['mangled'],sources={p.removeprefix('uc-library/'):h for p,h in sources.items() if p.startswith('uc-library/')},repository_sources=provider,domain='Valid initialized portable source model; stable borrowed vectors, normal nonthrowing provider cleanup; exact native application boundaries. No original constructor/layout/ARM ABI/hardware or Core binary behavior claim.',portable_ready=not uncertainties,declaration_uncertainties=uncertainties,cpp_compiled=True,mangling_namespace_checked=True) for x in fixture['ranges']]
  proof={'version':1,'task_id':TASK,'phase':'actual native/portable local proof' if not o.integration_proof else 'fresh canonical executable replay','provider_thread_id':os.getenv('CODEX_THREAD_ID'),'compiler_version':compiler,'implementation_start_utc':'2026-11-13T17:24:22Z','development_notes':['First link attempt failed because -lpng development symlink was absent; corrected to existing system libpng16.so.16. No production/provider change.','Initial proof/source producers preserved in task-local scratch before final command logging was added.'],'utc_end':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cpp_differential_passed':True,'compiled_original_mangled_names_matched':True,'mangling_namespace_checked':True,'domain':records[0]['domain'],'compiled_symbols':names,'pinned_CCL_commit':'e8cbdea4a4a20e15111f5a690798a259c0374b31','functions':[dict(x,domain=records[0]['domain'],cpp_differential_passed=True,mangling_namespace_checked=True,range_verified=True,native_cases=len(fixture['cases'])) for x in fixture['ranges']],'fixture':{'path':str(pathlib.Path(o.fixtures).resolve().relative_to(ROOT)),'sha256':H(o.fixtures)},'sources':sources,'repository_sources':provider,'producer_sha256':H(__file__),'oracle_producer_sha256':H(COMMON/'native.py'),'executable':{'path':str(o.executable),'sha256':H(o.executable)},'objects':{str(q):H(q) for q in (o.object or [WORK/f'unit{i}.o' for i in range(4)]) if pathlib.Path(q).is_file()},'archives':bindings(ARCHIVES) if local_executable else {str(q):H(q) for q in o.linked_archive},'archive_binding_scope':'Actual worker baseline linkage' if local_executable else 'Only explicitly supplied canonical linked archives; actual executable/objects/integration proof bound separately. Worker baseline not attributed to canonical binary.','format':{'version':version,'sources':bindings([*PRODUCTION,*HEADERS,str((COMMON/'Replay.cpp').relative_to(ROOT)),str((BASE/'Replay.cpp').relative_to(ROOT))])},'commands':commands,'observations':observed,'proposed_readiness':{'canonical_binding_pending':True,'ready':[] if uncertainties else records,'pending':records if uncertainties else []},'limitations':['Independent initialized source-port model, original constructors excluded.','Native providers are observed models; original allocator internals and native Core bodies are not executed.','Native D0 actual delete boundary is observed; host real delete/storage/CCL child and parameter cleanup is separately forwarded and checked.','Exceptions, concurrent/reentrant vector mutation and hardware excluded.','AliasParam::cast uses actual CCL typed-object system in place of firmware C++ RTTI.'],'integration':{'path':o.integration_proof,'sha256':H(o.integration_proof)} if o.integration_proof else None}
  q=pathlib.Path(o.proof_output);q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(proof,indent=2)+'\n');print(q)
