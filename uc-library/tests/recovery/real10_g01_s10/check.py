import argparse,datetime,hashlib,json,os,subprocess,time,importlib.util
from pathlib import Path
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent;TASK=T.name
O=R/'temp/recovery-work'/TASK;O.mkdir(exist_ok=True,parents=True)
SOURCE='uc-library/src/Presonus/Surface/MonitorPageComponent.cpp'
HEADER='uc-library/include/presonus/surface/MonitorPageComponent.hpp'
DRIVER=str((T/'Replay.cpp').relative_to(R))
SUPPORT=['uc-library/src/Presonus/Surface/MixerPageComponent.cpp'] if TASK!='real10_g01_s10' and 'ChannelInfo' not in SOURCE else []
OWNED=[SOURCE,HEADER,DRIVER]
FLAGS=['/usr/bin/c++','-std=c++17','-O2','-ffunction-sections','-fdata-sections','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework']
if TASK!='real10_g01_s10':FLAGS+=['-fno-sized-deallocation']
CANON=Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01')
SDK=CANON/'upstream-core/sdk/lib'
ARCHIVES=[SDK/'libcorelib.a',SDK/'libpresonus_core_allocator.a']
if 'GroupsEdit' in SOURCE:ARCHIVES=[CANON/'libpresonus_cs18_components.a',CANON/'libpresonus_uc.a',*ARCHIVES]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv,**kw):
 argv=list(map(str,argv));start=datetime.datetime.now(datetime.timezone.utc).isoformat();clock=time.monotonic()
 p=subprocess.run(argv,cwd=R,capture_output=True,env={**os.environ,'TMPDIR':str(O)},**kw)
 with (O/'commands.jsonl').open('a') as f:f.write(json.dumps(dict(argv=argv,start_utc=start,end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),duration_seconds=time.monotonic()-clock,returncode=p.returncode))+'\n')
 print(json.dumps(argv),flush=True)
 if p.returncode:print(p.stdout.decode(),p.stderr.decode());p.check_returncode()
 return p.stdout.decode()
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['format','compile','symbols','native','replay','proof']);p.add_argument('--exe');p.add_argument('--object');p.add_argument('--integration');p.add_argument('--out');a=p.parse_args()
 if a.mode=='proof' and not all([a.exe,a.object,a.integration,a.out]):p.error('proof requires --exe --object --integration --out')
 canonical_started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()
 canonical_mode=bool(a.integration and Path(a.integration).resolve()==(R/'uc-library/validation/integration.json').resolve())
 canonical_compile_binding=None
 obj=Path(a.object) if a.object else O/'production.o';exe=Path(a.exe) if a.exe else O/'replay'
 if canonical_mode:
  helper=R/'uc-library/tools/recovery/canonical_compile_bindings.py'
  spec=importlib.util.spec_from_file_location('canonical_compile_bindings',helper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  canonical_compile_binding=module.bind(R,obj,SOURCE,exe_path=exe)
  canonical_transition=module.load_transition(R,'temp/recovery-work/reconstruction10x10-20261116/workflow/checker-canonical-audit/review02/CANONICAL_BINDING_TRANSITION.json')
 if a.mode=='format':run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*OWNED]);return
 if a.mode=='compile':
  objects=[obj,O/'driver.o']+[O/f'support{k}.o' for k in range(len(SUPPORT))]
  for source,target in zip([SOURCE,DRIVER,*SUPPORT],objects):run([*FLAGS,'-MMD','-MF',str(target)+'.d','-c',source,'-o',target])
  run(['/usr/bin/c++',*objects,'-Wl,--gc-sections','-Wl,--start-group',*ARCHIVES,'-Wl,--end-group','-lz','-lpthread','-ldl','-lm','-o',exe]);return
 import native
 native.EXE=exe
 symbols=run(['nm','--defined-only',obj]);assert native.NAME in {x.split()[-1] for x in symbols.splitlines() if x.split()}
 deallocation_disassembly=None
 if 'D0Ev' in native.NAME:
  deallocation_disassembly=run(['objdump','-dr','--disassemble='+native.NAME,obj]);assert '_ZdlPv' in deallocation_disassembly and '_ZdlPvm' not in deallocation_disassembly
 if a.mode=='symbols':return
 fixture=json.loads((T/'fixtures.json').read_text())
 fresh=native.generate() if a.mode in ['native','proof'] else None
 if fresh is not None:assert fresh==fixture,'native/provider observations changed'
 if a.mode=='native':return
 lines=run([exe],input=''.join(c['stdin']+'\n' for c in fixture['cases']).encode()).splitlines();assert lines==[c['stdout'] for c in fixture['cases']],(lines,fixture['cases'])
 print(len(lines),'native/provider differential cases pass')
 if a.mode=='replay':return
 run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*OWNED])
 files=set(OWNED+SUPPORT+['third_party/ccl-framework/core/portable/corecomponent.cpp','third_party/ccl-framework/core/portable/coreparams.cpp'])|{str((T/n).relative_to(R)) for n in ['native.py','check.py','fixtures.json']}
 for dep in ([] if canonical_mode else O.glob('*.o.d')):
  files.update(x for x in dep.read_text().replace('\\\n',' ').split(':',1)[1].split() if (R/x).is_file())
 if canonical_mode:files.update(canonical_compile_binding['files'])
 hashes={f:sha(R/f) for f in sorted(files)}
 limits=['Original inheritance/layout/member organization and ARM ABI remain unresolved. This is a portable source lifecycle/dispatch model using actual CCL.', 'No native Core body executed. Native app call ordering and receiver writes are observed; actual provider cleanup and parameter behavior are independently executed in host CCL. No EH/concurrency/hardware coverage.', 'Original ordinary return declarations remain unverified. Constructors/tags and borrowed source-port state are independent convenience contracts. Only selected exact ELF identity gets credit.']
 if 'GroupsEdit' in SOURCE:limits+=['Tagged owning state is the lifecycle replay domain; existing reference constructor continues to borrow and preserves its state. Empty secondary ParamList; original AssignItem type/layout unresolved, three portable fields retained.']
 pending=dict(original_elf_sha256=native.SHA,mangled=native.NAME,portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True,sources={k.removeprefix('uc-library/'):v for k,v in hashes.items() if k.startswith('uc-library/') and not k.startswith('uc-library/tests/')},repository_sources={k:v for k,v in hashes.items() if k.startswith('third_party/ccl-framework/core/')},domain=fixture['domain'],declaration_uncertainties=limits,canonical_binding_pending=True)
 proof=dict(version=1,task_id=TASK,session_id=os.environ.get('CODEX_THREAD_ID'),environment_session_id=os.environ.get('CODEX_SESSION_ID'),created=datetime.datetime.now(datetime.timezone.utc).isoformat(),phase_timestamps=({'canonical_producer_started_utc':canonical_started_utc,'canonical_observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'historical_worker_timing':'Not supplied to canonical producer; retained in original hash-bound worker proof, never fabricated'} if canonical_mode else json.loads((R/'temp/recovery-work/real10_g01/session.json').read_text())),compiled=True,formatting_verified=True,mangling_verified=True,behavior_verified=True,native_behavior_verified=True,original_declaration_verified=False,original_arm_abi_verified=False,hardware_verified=False,canonical_binding_pending=True,validation_domain=fixture['domain'],limitations=limits,ranges=fixture['ranges'],elf_sha256=native.SHA,source_sha256=hashes,archive_sha256={str(x):sha(x) for x in ARCHIVES},compiled_symbols=symbols,object_sha256=sha(obj),executable_sha256=sha(exe),formatter_version=run(['uc-library/.venv/bin/clang-format','--version']).strip(),compiler_version=run(['/usr/bin/c++','--version']).splitlines()[0],compile_flags=FLAGS,proposed_readiness=dict(ready=[],pending=[pending]),integration=dict(path=a.integration,sha256=sha(a.integration)),fresh_native_execution=dict(elf_sha256=fresh['elf_sha256'],ranges=fresh['ranges'],case_count=len(fresh['cases']),observations_sha256=hashlib.sha256(json.dumps(fresh,sort_keys=True).encode()).hexdigest(),producer_sha256=sha(T/'native.py'),unicorn_version=__import__('unicorn').__version__,executed_at=datetime.datetime.now(datetime.timezone.utc).isoformat()))
 if canonical_mode:
  proof['canonical_compile_binding']=canonical_compile_binding
  proof['canonical_binding_transition']=canonical_transition
  proof['canonical_producer_helper']={'path':'uc-library/tools/recovery/canonical_compile_bindings.py','sha256':sha(R/'uc-library/tools/recovery/canonical_compile_bindings.py')}
 proof['deleting_destructor_disassembly']=deallocation_disassembly
 proof['check_log']=str((O/'commands.jsonl').relative_to(R))
 Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
