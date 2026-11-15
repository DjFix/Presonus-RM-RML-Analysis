"""Local lifecycle gates; explicit canonical inputs are always used when supplied."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,subprocess,time
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent;TASK=T.name
O=R/'temp/recovery-work'/TASK;O.mkdir(parents=True,exist_ok=True)
MANIFEST=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/trial10x2-20261115/root-review/provider-supplement/PROVIDERS.json')
MANIFEST_SHA='0e4fc25d3383ae8609932b7e25c4d28bac3ee92b9435c11e8d63b61cd29f0c18'
HEADER='uc-library/include/presonus/panel/GambitPanelComponent.hpp';SOURCE='uc-library/src/Presonus/Panel/GambitPanelComponent.cpp'
OWNED=[HEADER,SOURCE,str((T/'Replay.cpp').relative_to(R))]
FLAGS=['/usr/bin/c++','-std=c++17','-O0','-fno-rtti','-fno-sized-deallocation','-Wno-multichar','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework']
COMMANDS=[]
TRANSITIVE=MANIFEST.with_name('COMPILER_TRANSITIVE_HEADERS.json')
TRANSITIVE_SHA='4fcea37e6ec6a3ab4d7d2bf49ec246ad66d5b11c6765ad5fa8e6d7a905b9a82e'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv,**kw):
 argv=list(map(str,argv));before=time.monotonic();p=subprocess.run(argv,cwd=R,capture_output=True,env={**os.environ,'TMPDIR':str(O)},**kw)
 out=p.stdout.decode();err=p.stderr.decode();COMMANDS.append(dict(argv=argv,returncode=p.returncode,seconds=time.monotonic()-before,stdout=out,stderr=err));print(json.dumps(argv),flush=True)
 assert p.returncode==0,(out,err);return out

def bindings(transition_path=None, transition_sha=None):
 assert bool(transition_path)==bool(transition_sha),'Both canonical transition arguments required'
 current={};transition=None
 if transition_path:
  assert sha(transition_path)==transition_sha
  transition=json.loads(Path(transition_path).read_text());baseline=transition['baseline_provider_manifest']
  assert baseline==dict(path=str(MANIFEST),sha256=MANIFEST_SHA)
  accepted=transition['accepted_root_bindings'];assert sha(accepted['path'])==accepted['sha256']
  assert transition['receipts']
  for receipt in transition['receipts']:
   assert sha(receipt['path'])==receipt['sha256']
   actual=json.loads(Path(receipt['path']).read_text())
   assert actual['returncode']==0 and json.loads(actual['stdout'])['local_acceptance_passed']
   assert actual['task_id']==receipt['task_id'] and actual['handoff_sha256']==receipt['handoff_sha256']
  current=transition['current_sources']
  assert set(current)=={'uc-library/include/presonus/surface_panel/ControlHelpers.hpp'}
  for path,b in current.items():
   assert sha(b['previous_frozen_read_path'])==b['previous_sha256']
   assert sha(b['current_frozen_read_path'])==b['current_sha256'] and sha(R/path)==b['current_sha256']

 assert sha(MANIFEST)==MANIFEST_SHA
 assert sha(TRANSITIVE)==TRANSITIVE_SHA
 m=json.loads(MANIFEST.read_text());approval=MANIFEST.with_name('ROOT_APPROVAL.json');a=json.loads(approval.read_text())
 for v in m['archives'].values():assert sha(v['frozen_read_path'])==v['sha256']
 for v in m['system_libraries']:assert sha(v['path'])==v['sha256']
 read=json.loads((R/'temp/recovery-work/trial10x2-20261115/READ_INPUTS-prepared01-trial10x2_gambit.json').read_text())
 for path,v in {**m['read_inputs'],**read,**json.loads(TRANSITIVE.read_text())['read_inputs']}.items():
  if path.startswith(('uc-library/include/','uc-library/src/','third_party/')):
   assert sha(v['frozen_read_path'])==v['sha256']
   if path in current:assert v['sha256']==current[path]['previous_sha256'] and v['frozen_read_path']==current[path]['previous_frozen_read_path']
   if (R/path).is_file():assert sha(R/path)==(current[path]['current_sha256'] if path in current else v['sha256']),path
 return m,approval,transition

def symbols(obj,exe):
 import native
 txt=run(['nm','--defined-only',obj]);names={l.split()[-1] for l in txt.splitlines() if l.split()}
 assert native.NAME in names
 dis=run(['objdump','-dr','--disassemble=_ZN8Presonus5Panel20GambitPanelComponentD0Ev',obj])
 assert '_ZdlPv' in dis and '_ZdlPvm' not in dis,'D0 must call genuine unsized global delete'
 exe_dis=run(['objdump','-d','--disassemble=_ZN8Presonus5Panel20GambitPanelComponentD0Ev',exe])
 assert '__wrap__ZdlPv' in exe_dis and '__wrap__ZdlPvm' not in exe_dis
 return txt,dis,exe_dis

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['format','compile','symbols','native','replay','proof']);p.add_argument('--exe');p.add_argument('--object');p.add_argument('--integration');p.add_argument('--out');p.add_argument('--canonical-transition');p.add_argument('--canonical-transition-sha');a=p.parse_args()
 if a.canonical_transition or a.canonical_transition_sha:assert a.exe and a.object and a.integration,'Transition requires explicit supplied canonical inputs'
 exe=Path(a.exe) if a.exe else O/'replay';obj=Path(a.object) if a.object else O/'production.o'
 if a.mode=='format':print(run(['uc-library/.venv/bin/clang-format','--version']));run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*OWNED]);return
 m,approval,transition=bindings(a.canonical_transition,a.canonical_transition_sha)
 if a.mode=='compile':
  assert not a.exe and not a.object,'Compile only owned scratch; explicit canonical inputs are read-only'
  run([*FLAGS,'-MMD','-MF',str(obj)+'.d','-c',SOURCE,'-o',obj]);driver=O/'replay.o';run([*FLAGS,'-MMD','-MF',str(driver)+'.d','-c',T/'Replay.cpp','-o',driver])
  run(['/usr/bin/c++',obj,driver,'-Wl,--start-group',*m['default_link_order'][1:],'-Wl,--end-group','-Wl,--gc-sections','-Wl,--wrap=_ZdlPv','-Wl,--wrap=_ZdlPvm','-lpthread','-o',exe]);(O/'compile-commands.json').write_text(json.dumps(COMMANDS,indent=2)+'\n');return
 run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*OWNED])
 syms,dis,exe_dis=symbols(obj,exe)
 if a.mode=='symbols':return
 import native
 fresh=native.generate(exe)
 if a.mode=='native':print(json.dumps(fresh,indent=2));return
 fixture=json.loads((T/'fixtures.json').read_text());assert fresh==fixture,'Fresh native/provider execution differs'
 for case in fresh['cases']:
  obs=list(map(int,run([exe,'product',native.VARIANT,str(case['n'])]).split()));assert obs==case['observation'],(case,obs)
 print('Four original ARM/provider/product lifecycle comparisons pass; populated parameter/child/task vectors and actual frees observed')
 if a.mode=='replay' and not a.out:return
 assert a.out
 files=set(OWNED)|{str((T/n).relative_to(R)) for n in ['native.py','check.py','fixtures.json']}
 # Fresh source dependency query, independent of worker compile caches. It
 # binds current source closure; it does not prove a supplied binary was built
 # from those bytes. Root's canonical integration evidence provides that link.
 dependency_queries=[]
 for source in [SOURCE,str((T/'Replay.cpp').relative_to(R))]:
  argv=[*FLAGS,'-MM','-MT','current_source_dependencies',source]
  output=run(argv)
  dependencies=[]
  for name in output.replace('\\\n',' ').split(':',1)[1].split():
   q=Path(name)
   if q.is_absolute():
    assert q.is_relative_to(R),'Unexpected external application dependency: '+name
    name=str(q.relative_to(R))
   assert (R/name).is_file(),name
   dependencies.append(name);files.add(name)
  dependency_queries.append(dict(argv=argv,stdout=output,source=source,dependencies=dependencies))
 read=json.loads((R/'temp/recovery-work/trial10x2-20261115/READ_INPUTS-prepared01-trial10x2_gambit.json').read_text())
 compiled_bindings={k:v for k,v in {**m['read_inputs'],**read,**json.loads(TRANSITIVE.read_text())['read_inputs']}.items() if k in files}
 assert all(f in compiled_bindings or f in OWNED or f in {str((T/n).relative_to(R)) for n in ['native.py','check.py','fixtures.json']} for f in files),'Unbound compiler dependency'
 for path,b in compiled_bindings.items():assert sha(R/path)==b['sha256'] and sha(b['frozen_read_path'])==b['sha256']
 app={f.removeprefix('uc-library/'):sha(R/f) for f in sorted(files) if f.startswith('uc-library/')}
 provider={k:v['sha256'] for k,v in {**m['read_inputs'],**json.loads(TRANSITIVE.read_text())['read_inputs']}.items() if k.startswith('third_party/')}
 domain='Normal independent tagged Gambit source-port objects with actual canonical Rack/Panel/CCL lifecycles: 1,3,17,65 real owned CCL parameters and owned virtual Component children, nonempty CCL borrowed-task vector; every parameter freed exactly once, all children destroyed, borrowed task untouched; D1 keeps self storage, D0 real unsized self delete exactly once. Each exact original range executed separately, native four vptr writes and base/delete call order observed. Actual host source provider runs synchronously at translated native boundaries.'
 limits=['Original complete constructor, derived members/inheritance/layout/vtables/EH and ARM ABI unresolved; independent SourcePortConstruction tag is not an original constructor claim.','Host RackPanelComponent provider and CCL 5.0 source-preferred behavior intentionally replace boundary implementations; no original base binary behavior or native object-construction equivalence claim.','Only valid normal destruction; null, corrupt, concurrent, exception and hardware cases excluded. Unused borrowed dependency service methods abort if touched; no fake cleanup implementation.','Native vptr offsets/values are observed only; portable compiler emits host vptr layout and return convention. D2 emitted host alias receives no new original identity credit.']
 entry=dict(original_elf_sha256=native.SHA,mangled=native.NAME,sources=app,repository_sources=provider,domain=domain,declaration_uncertainties=limits,portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True,canonical_binding_pending=True)
 proof=dict(version=1,task_id=TASK,session_id='/root/trial10x2_gambit',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),compiled=True,cpp_compiled=True,compiled_mangled_names_matched=True,mangling_namespace_checked=True,cpp_differential_passed=True,formatting_verified=True,native_behavior_verified=True,fresh_native_execution=True,original_declaration_verified=False,original_arm_abi_verified=False,hardware_verified=False,portable_ready=False,canonical_binding_pending=True,domain=domain,limitations=limits,sources=app,repository_sources=provider,source_sha256={f:sha(R/f) for f in sorted(files)},ranges=[fresh['range']],native_observations=fresh,canonical_binding_transition=dict(path=a.canonical_transition,sha256=a.canonical_transition_sha,record=transition) if transition else None,provider_manifest=dict(path=str(MANIFEST),sha256=sha(MANIFEST)),compiler_transitive_binding=dict(path=str(TRANSITIVE),sha256=sha(TRANSITIVE),record=json.loads(TRANSITIVE.read_text())),provider_approval=dict(path=str(approval),sha256=sha(approval)),provider_archives=m['archives'],object=dict(path=str(obj),sha256=sha(obj)),executable=dict(path=str(exe),sha256=sha(exe)),compiled_dependency_bindings=compiled_bindings,native_provider_commands=[[str(exe),'provider',native.VARIANT,str(c['n'])] for c in fresh['cases']],compiled_symbols=syms,d0_object_disassembly=dis,d0_executable_disassembly=exe_dis,formatter_version=run(['uc-library/.venv/bin/clang-format','--version']).strip(),compiler_version=run(['/usr/bin/c++','--version']).splitlines()[0],unicorn_version=__import__('unicorn').__version__,binary_provenance=dict(mode='supplied_binary_inspection_and_execution' if a.exe or a.object else 'worker_local_binary_inspection_and_execution',current_source_closure_scope='Fresh GCC -MM binds current source inputs only; canonical integration must bind supplied build provenance',worker_compile_history=None if a.exe or a.object else (dict(path=str(O/'compile-commands.json'),sha256=sha(O/'compile-commands.json'),scope='Historical local build commands; not evidence supplied canonical binary was compiled by this replay') if (O/'compile-commands.json').exists() else None)),fresh_dependency_queries=dependency_queries,commands=COMMANDS,tool_inputs={f:sha(f) for f in ['/usr/bin/c++','/usr/bin/nm','/usr/bin/objdump']},integration=dict(path=a.integration,sha256=sha(a.integration)) if a.integration else None,proposed_readiness=dict(ready=[],pending=[entry]))
 Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
