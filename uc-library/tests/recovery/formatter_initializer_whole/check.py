"""Compile exact original initializer specializations and compare ARM/provider traces."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
from native import observe, PACKET
TEST=Path('uc-library/tests/recovery/formatter_initializer_whole')
FIXTURE=TEST/'fixtures.json'
CONTEXT=json.loads(PACKET.read_text())
PYTHON='uc-library/.venv/bin/python'
FORMATTER='uc-library/.venv/bin/clang-format'
SDK=Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk')
DOMAIN='Exact four original ranges independently executed: cold guard acquire1/init/release/atexit/add; two initialized repeats; acquire0 path with preinitialized receiver. Receiver/name/vptr/state writes and exact native D1/object/DSO callback tuple observed. Portable O2 invokes real compiler guards, pinned CCL registry, identity-stable static instance, inherited parent print, explicit acquire0 injection, real host atexit scheduling and exact D1 execution via recording trampoline; static receiver is never deleted.'
LIMITS=['Intentional compiler-order difference: original ARM releases guard before atexit; genuine current C++ static registers atexit before guard release. Native and host orders are both recorded, not claimed equivalent.', 'Portable source port only; original ARM layout/calling convention not established.', 'T9 native byte+8=8 is preserved as explicitly unresolved initialization state, with no invented formatting meaning.', 'Current PreDelay scan adaptation differs from original vtable override and is outside initializer/teardown coverage.', 'Native guard/registry/atexit callbacks are intercepted boundaries, not native Core executions. Host acquire0 resets a previously initialized guard only in single-threaded test; concurrent guard behavior is excluded.', 'Host atexit recording trampoline forwards the exact registered D1/object; no synthetic destructor or deletion events.']
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,data):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['capture','format','compile','symbols','native','replay','seal']);p.add_argument('--task');p.add_argument('--exe',type=Path);p.add_argument('--fixtures',type=Path,default=FIXTURE);args=p.parse_args()
 if args.mode=='capture':dump(args.fixtures,observe());return
 task=next(t for t in CONTEXT['tasks'] if t['id']==args.task)
 cls='PreDelayFormatterT9' if 'PreDelayFormatterT9' in task['originals'][0]['mangled'] else 'FxReverbNumFormatter';parent='PreDelayFormatter' if cls.startswith('PreDelay') else 'NumberPrepender'
 source=Path(f'uc-library/src/Presonus/Mixer/{cls}.cpp');header=Path(f'uc-library/include/presonus/mixer/{cls}.hpp');initializer=Path('uc-library/include/presonus/mixer/XmenFormatterInitializer.hpp');replay=TEST/'Replay.cpp'
 paths=[source,header,initializer,replay];fmt=[FORMATTER,'--style=file','--fallback-style=LLVM','--dry-run','--Werror',*map(str,paths)]
 scratch=Path('temp/recovery-work/sqlite15-formatter')/task['id'];scratch.mkdir(parents=True,exist_ok=True);obj=scratch/'Initializer.o';exe=scratch/'Replay';exe=args.exe or exe
 cxx=['/usr/bin/c++','-std=c++17','-O2','-Ulinux','-ffunction-sections','-fdata-sections','-fno-rtti','-fno-sized-deallocation','-Iuc-library/include','-isystem','third_party/ccl-framework']
 compile_argv=[*cxx,'-MD','-MF',str(scratch/'Initializer.d'),'-c',str(source),'-o',str(obj)]
 wrappers=['-Wl,--wrap='+name for name in ['__cxa_guard_acquire','__cxa_guard_release','__cxa_atexit','_ZdlPv','_ZN4Core17FormatterRegistry3addEPNS_9FormatterE']]
 case=f'-DFORMATTER_INIT_CLASS={int(cls.startswith("PreDelay"))}'
 archives=[SDK/'lib/libcorelib.a',SDK/'lib/libpresonus_core_allocator.a']
 link=[*cxx,case,*wrappers,'-Wl,--gc-sections','-MD','-MF',str(scratch/'Replay.d'),str(replay),f'uc-library/src/Presonus/Mixer/{parent}.cpp',str(obj),*map(str,archives),'-o',str(exe)]
 if args.mode=='format':subprocess.run(fmt,check=True);return
 if args.mode=='compile':
  print(json.dumps(compile_argv),flush=True);subprocess.run(compile_argv,check=True)
  hashes={str(x):sha(x) for x in [obj,*archives]};print(json.dumps(link),flush=True);subprocess.run(link,check=True);assert hashes=={str(x):sha(x) for x in [obj,*archives]};dump(scratch/'link-inputs.json',hashes);return
 fixture=json.loads(args.fixtures.read_text())
 if args.mode=='native':assert fixture==observe();print('4 native ranges / 16 executions reproduced');return
 targets=[t for t in fixture['targets'] if t['task_id']==task['id']]
 def replay_check():
  observed=subprocess.check_output([str(exe)],text=True).splitlines()
  for target in targets:
   expected=[c['output'] for c in target['cases']]
   assert expected[0]=='cold acquire,release,atexit,add'
   # Documented current compiler source-port ordering difference; native fixture unchanged.
   expected[0]='cold acquire,atexit,release,add'
   assert observed==expected+['exit 1 0'],observed
  print(task['id']+': native call traces and actual provider/atexit observations passed');return observed
 if args.mode=='replay':replay_check();return
 nm=['/usr/bin/nm','--defined-only',str(obj)];output=subprocess.check_output(nm,text=True).splitlines();names={t['original']['mangled'] for t in targets};matched=[line for line in output if line.split()[-1] in names];assert len(matched)==len(names)
 if args.mode=='symbols':print(json.dumps(dict(argv=nm,matched=matched)));return
 observed=replay_check();assert fixture==observe();subprocess.run(fmt,check=True)
 dependencies={path:sha(path) for path in CONTEXT['read_files'] if path not in CONTEXT['owned_files']};dependencies.update({str(initializer):sha(initializer)})
 sources={str(x.relative_to('uc-library')):sha(x) for x in (source,header,initializer)}
 originals=[t['original'] for t in targets];proof=Path(task['proof']);log=scratch/'final-validation-frozen01.log'
 pending=[dict(original_elf_sha256=o['elf_sha256'],mangled=o['mangled'],cpp_compiled=True,mangling_namespace_checked=True,portable_ready=False,sources=sources,repository_sources=dependencies,validation_domain=DOMAIN,declaration_uncertainties=LIMITS) for o in originals]
 dump(proof,dict(task_id=task['id'],originals=originals,native_targets=targets,portable=observed,fixture_sha256=sha(args.fixtures),compile_argv=compile_argv,link_argv=link,link_input_hashes=json.loads((scratch/'link-inputs.json').read_text()),object_sha256=sha(obj),exe_sha256=sha(exe),compiled_symbols=dict(argv=nm,matched=matched,all_defined=output),compiled_mangled_names_matched=True,cpp_differential_passed=True,format_check_passed=True,formatted_files={str(x.relative_to('uc-library')):sha(x) for x in paths},format_argv=fmt,formatter_version=subprocess.check_output([FORMATTER,'--version'],text=True).strip(),compiler_version=subprocess.check_output(['/usr/bin/c++','--version'],text=True).splitlines()[0],intentional_order_difference=dict(native='acquire release atexit add',portable='acquire atexit release add',classification='source port compiler static initialization'),provider_commit='e8cbdea4a4a20e15111f5a690798a259c0374b31',producer_inputs={str(x):sha(x) for x in (TEST/'native.py',TEST/'check.py',replay)},immutable_validation_log=dict(path=str(log),sha256=sha(log)),proposed_readiness=dict(ready=[],pending=pending)))
 artifacts={source:'source',header:'source',initializer:'source',replay:'test',TEST/'check.py':'replay',TEST/'native.py':'producer',args.fixtures:'fixture',proof:'proof',log:'proof',PACKET:'packet',**{Path(path):'dependency' for path in dependencies if path!=str(initializer)}}
 argv=[PYTHON,'-B',str(TEST/'check.py')]
 handoff=dict(version=1,task_id=task['id'],namespace=task['namespace'],packet_manifest=str(PACKET),originals=originals,artifacts=[dict(path=str(path),kind=kind,sha256=sha(path)) for path,kind in artifacts.items()],checks=[dict(kind=kind,argv=[*argv,kind,'--task',task['id']],timeout_seconds=120) for kind in ('format','compile','symbols','native','replay')],validation_domain=DOMAIN,limitations=LIMITS,build_integration=dict(partition='common (existing same-owner class CPP)',public_headers=[str(header),str(initializer)],test_target=task['id'],link_dependencies=['presonus_uc'],compile_definitions=[case[2:]],link_options=wrappers,ctest_argv=[*argv,'replay','--task',task['id'],'--exe',f'$<TARGET_FILE:{task["id"]}>','--fixtures',str(args.fixtures)]))
 dump(Path(task['handoff']),handoff)
 spec=importlib.util.spec_from_file_location('accept_worker',Path('uc-library/tools/recovery/accept_worker.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.validate(handoff)
 dump(scratch/'final-preflight.json',dict(unchanged_validate_passed=True,validator_sha256=sha('uc-library/tools/recovery/accept_worker.py'),handoff_sha256=sha(task['handoff'])))
if __name__=='__main__':main()
