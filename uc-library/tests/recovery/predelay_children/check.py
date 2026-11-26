"""Per-task validation and immutable handoff sealing for new PreDelay children."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
from native import observe, verify_inputs, PACKET, CONTEXT
TEST=Path('uc-library/tests/recovery/predelay_children')
FIXTURE=TEST/'fixtures.json'
PYTHON='uc-library/.venv/bin/python'
FORMATTER='uc-library/.venv/bin/clang-format'
SDK=Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk')
DOMAIN_DTOR='Three initialized receiver allocations per independently range/RTTI/PLT-verified original. Exact D1 writes genuine Core::Formatter vptr and preserves name/state without deallocation. Exact D0 writes same provider table and reaches verified unsized delete with same receiver once; emulator actually unmaps receiver. Host exact emitted variants use actual PreDelay parent and typed tagged setup: O0 measures provider vptr, O2 normal production teardown measures receiver identity and real unsized deletion count. D2 emitted compiler alias receives no invented original coverage.'
DOMAIN_INIT='Four executions per independently verified original initializer: cold acquire1, two initialized repeats, acquire0 with preinitialized receiver. Exact native receiver name/state/vptr writes, guard calls and D1/object/DSO callback tuple observed. Real host compiler guards, CCL registry, stable static receiver, exact case-sensitive name, inherited real print and actual host atexit execution of recorded D1 with zero static receiver deletion observed.'
LIMITS=['Portable source port only; original source declaration, ARM layout, calling convention and hardware equivalence remain unresolved. Tagged setup has no recovered original constructor identity.', 'Native byte+8 initializer state is preserved explicitly in portable storage with unresolved semantics; inherited parent formatting is reused, not recovered again.', 'Original PreDelay scan override differs from current parent source adaptation and remains outside this bounded proof.', 'Native Core implementations are not executed. Native runtime/provider callbacks are explicit boundaries.', 'O0 physical vptr observation is separate from O2 lifetime-ended store elision; optimized physical vptr equality is not asserted.', 'Initializer compiler order intentionally differs: original ARM acquire/release/atexit/add; genuine current compiler acquire/atexit/release/add. Both traces are retained without claiming equivalence.', 'Host acquire0 test resets a previously initialized guard in a single-threaded test only; concurrency and exception paths excluded. Actual atexit recording trampoline forwards exact D1/object; no synthetic delete event.']
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['capture','format','compile','symbols','native','replay','optimized','seal']);p.add_argument('--task');p.add_argument('--exe',type=Path);p.add_argument('--fixtures',type=Path,default=FIXTURE);p.add_argument('--optimized',action='store_true');args=p.parse_args()
 if args.mode=='capture':dump(args.fixtures,observe());return
 task=next(t for t in CONTEXT['tasks'] if t['id']==args.task);mangled=task['originals'][0]['original']['mangled'];cls=next(c for c in CONTEXT['classes'] if c in mangled);n=int(cls[-1]);init='addClass' in mangled;mode=0 if init else 1 if mangled.endswith('D0Ev') else 2
 source=Path(f'uc-library/src/Presonus/Mixer/{cls}.cpp');headers=[Path(f'uc-library/include/presonus/mixer/{c}.hpp') for c in CONTEXT['classes']];replay=TEST/'Replay.cpp'
 paths=[source,*headers,replay];fmt=[FORMATTER,'--style=file','--fallback-style=LLVM','--dry-run','--Werror',*map(str,paths)]
 scratch=Path('temp/recovery-work/sqlite18-predelay')/task['id'];scratch.mkdir(parents=True,exist_ok=True);obj=scratch/'Target.o';exe=args.exe or scratch/'Replay'
 cxx=['/usr/bin/c++','-std=c++17','-O2' if init else '-O0','-Ulinux','-ffunction-sections','-fdata-sections','-fno-rtti','-fno-sized-deallocation','-Iuc-library/include','-isystem','third_party/ccl-framework']
 compile_argv=[*cxx,'-MD','-MF',str(scratch/'Target.d'),'-c',str(source),'-o',str(obj)]
 wrappers=['-Wl,--wrap='+name for name in (['__cxa_guard_acquire','__cxa_guard_release','__cxa_atexit','_ZdlPv','_ZN4Core17FormatterRegistry3addEPNS_9FormatterE'] if init else ['_ZdlPv'])]
 definitions=[f'-DPREDELAY_CHILD={n}',f'-DPREDELAY_MODE={mode}'];archives=[SDK/'lib/libcorelib.a',SDK/'lib/libpresonus_core_allocator.a']
 link=[*cxx,*definitions,*wrappers,'-Wl,--gc-sections','-MD','-MF',str(scratch/'Replay.d'),str(replay),'uc-library/src/Presonus/Mixer/PreDelayFormatter.cpp',str(obj),*map(str,archives),'-o',str(exe)]
 if args.mode=='format':subprocess.run(fmt,check=True);return
 if args.mode=='compile':
  print(json.dumps(compile_argv),flush=True);subprocess.run(compile_argv,check=True)
  inputs={str(x):sha(x) for x in [obj,*archives]};print(json.dumps(link),flush=True);subprocess.run(link,check=True);assert inputs=={str(x):sha(x) for x in [obj,*archives]};dump(scratch/'link-inputs.json',inputs);return
 fixture=json.loads(args.fixtures.read_text());targets=[t for t in fixture['targets'] if t['task_id']==task['id']]
 if args.mode=='native':assert targets==observe(task['id'])['targets'];print(task['id']+': independent original executions reproduced');return
 def replay_check(executable,optimized=False):
  observed=subprocess.check_output([str(executable)],text=True).splitlines()
  for target in targets:
   expected=[c['output'] for c in target['cases']]
   if init:
    assert expected[0]=='cold acquire,release,atexit,add';expected[0]='cold acquire,atexit,release,add';expected+=['exit 1 0']
   elif optimized:expected=[' '.join(value.split()[:2]) for value in expected]
   assert observed==expected,observed
  print(task['id']+': bounded native/provider replay passed');return observed
 if args.mode=='optimized':
  if init:return
  optimized_object=scratch/'optimized.o';optimized_exe=scratch/'optimized-replay';compile_opt=[x.replace('-O0','-O2') for x in compile_argv];compile_opt[-1]=str(optimized_object)
  link_opt=[str(optimized_object) if x==str(obj) else x.replace('-O0','-O2') for x in link];link_opt[-1]=str(optimized_exe);link_opt.insert(1,'-DFORMATTER_OPTIMIZED=1')
  subprocess.run(compile_opt,check=True);subprocess.run(link_opt,check=True);out=replay_check(optimized_exe,True)
  dump(scratch/'optimized.json',dict(compile_argv=compile_opt,link_argv=link_opt,observations=out,object_sha256=sha(optimized_object),exe_sha256=sha(optimized_exe),domain='Normal O2 ownership/deletion; physical dead-object vptr excluded'));return
 if args.mode=='replay':replay_check(exe,args.optimized);return
 nm=['/usr/bin/nm','--defined-only',str(obj)];output=subprocess.check_output(nm,text=True).splitlines();names={t['original']['mangled'] for t in targets};matched=[line for line in output if line.split()[-1] in names];assert len(matched)==len(names)
 if args.mode=='symbols':print(json.dumps(dict(argv=nm,matched=matched,emitted_aliases=[x for x in output if x.split()[-1].endswith(('D0Ev','D1Ev','D2Ev'))])));return
 observed=replay_check(exe);assert targets==observe(task['id'])['targets'];subprocess.run(fmt,check=True);verify_inputs()
 dependencies={path:sha(path) for path in CONTEXT['canonical_current_reads']};dependencies.update({CONTEXT[key]['path']:CONTEXT[key]['sha256'] for key in ('native_context','protected_old_inputs')})
 sources={str(x.relative_to('uc-library')):sha(x) for x in [source,*headers]};originals=[t['original'] for t in targets];proof=Path(task['proof']);log=scratch/'validation-frozen01.log';domain=DOMAIN_INIT if init else DOMAIN_DTOR
 pending=[dict(original_elf_sha256=o['elf_sha256'],mangled=o['mangled'],cpp_compiled=True,mangling_namespace_checked=True,portable_ready=False,sources=sources,repository_sources=dependencies,validation_domain=domain,declaration_uncertainties=LIMITS) for o in originals]
 dump(proof,dict(task_id=task['id'],originals=originals,native_targets=targets,portable=observed,optimized=None if init else json.loads((scratch/'optimized.json').read_text()),fixture_sha256=sha(args.fixtures),compile_argv=compile_argv,link_argv=link,link_input_hashes=json.loads((scratch/'link-inputs.json').read_text()),object_sha256=sha(obj),exe_sha256=sha(exe),compiled_symbols=dict(argv=nm,matched=matched,all_defined=output),compiled_mangled_names_matched=True,cpp_differential_passed=True,format_check_passed=True,formatted_files={str(x.relative_to('uc-library')):sha(x) for x in paths},format_argv=fmt,formatter_version=subprocess.check_output([FORMATTER,'--version'],text=True).strip(),compiler_version=subprocess.check_output(['/usr/bin/c++','--version'],text=True).splitlines()[0],provider_commit='e8cbdea4a4a20e15111f5a690798a259c0374b31',producer_inputs={str(x):sha(x) for x in (TEST/'native.py',TEST/'check.py',replay)},immutable_validation_log=dict(path=str(log),sha256=sha(log)),proposed_readiness=dict(ready=[],pending=pending)))
 artifacts={source:'source',**{x:'source' for x in headers},replay:'test',TEST/'check.py':'replay',TEST/'native.py':'producer',args.fixtures:'fixture',proof:'proof',log:'proof',PACKET:'packet',**{Path(path):'dependency' for path in dependencies}}
 argv=[PYTHON,'-B',str(TEST/'check.py')];checks=[dict(kind=kind,argv=[*argv,kind,'--task',task['id']],timeout_seconds=120) for kind in ('format','compile','symbols','native','replay')]
 if not init:checks.append(dict(kind='replay',argv=[*argv,'optimized','--task',task['id']],timeout_seconds=120))
 ctest=[*argv,'replay','--task',task['id'],'--exe',f'$<TARGET_FILE:{task["id"]}>','--fixtures',str(args.fixtures)]
 if not init:ctest+=['--optimized']
 handoff=dict(version=1,task_id=task['id'],namespace=task['namespace'],packet_manifest=str(PACKET),originals=originals,artifacts=[dict(path=str(path),kind=kind,sha256=sha(path)) for path,kind in artifacts.items()],checks=checks,validation_domain=domain,limitations=LIMITS,build_integration=dict(partition='common (new '+cls+'.cpp)',public_headers=list(map(str,headers)),test_target=task['id'],link_dependencies=['presonus_uc'],compile_definitions=[x[2:] for x in definitions]+([] if init else ['FORMATTER_OPTIMIZED=1']),compile_options=['-fno-rtti','-fno-sized-deallocation'],link_options=wrappers,ctest_argv=ctest))
 dump(Path(task['handoff']),handoff)
 spec=importlib.util.spec_from_file_location('accept_worker',Path('uc-library/tools/recovery/accept_worker.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.validate(handoff)
 dump(scratch/'preflight.json',dict(unchanged_validate_passed=True,validator_sha256=sha('uc-library/tools/recovery/accept_worker.py'),handoff_sha256=sha(task['handoff'])))
if __name__=='__main__':main()
