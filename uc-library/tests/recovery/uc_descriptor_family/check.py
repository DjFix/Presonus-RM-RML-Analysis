"""Descriptor-family bounded replay and immutable v1 handoff producer."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import time
import sys
import unicorn
import elftools
from native import observe, task_contexts, sha, verify, PACKETS, SUPPLEMENT
TEST=Path('uc-library/tests/recovery/uc_descriptor_family')
PY='uc-library/.venv/bin/python'
FORMAT='uc-library/.venv/bin/clang-format'
HEADERS=[Path('uc-library/include/presonus/uc')/n for n in ('element.hpp','ParamRangeElement.hpp','StringElement.hpp','StringListElement.hpp')]
SOURCES=[Path('uc-library/src/Presonus/UC')/n for n in ('ElementValueParsing.cpp','ParamRangeElement.cpp','StringElement.cpp','StringListElement.cpp')]
PROVIDERS=[Path('uc-library/src/Presonus/UC')/n for n in ('Element.cpp','MetaElement.cpp','ParamRange.cpp')]
SDK=Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk')
ARCHIVES=[SDK/'lib/libcorelib.a',SDK/'lib/libpresonus_core_allocator.a']
ARCHIVE_HASHES={'/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a': '5a2c8bbb20d8d194ff4f5047118696afa918a046b01739c4257416044e83f5f3', '/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a': '69892fbcec9a50a140462982073c686a67ca4763dfb5dfa190534d022b78a40d'}
DOMAIN='Each original ELF section/range independently verified. Original ARM whole target bodies, nested original parse and ParamRange constructor and numeric conversion helpers executed. Explicit libc sscanf/strchr/memory boundaries and real pinned CCL CString32/64/128 source-provider bridge. Missing/empty/malformed/leading-hex/high-bit signed64 scalar inputs; finite int-representable steps; all individual scalar presence bits across selected combinations/default fallback; real attribute load/save order; 127-byte string truncation; valid nonnull typed children in real current owning Element order; C1/C2 ranges and original Element base and zero/one/three-owned-child D1/D0 lifecycle/deallocation paths separately observed. Host actual owning Element/metadata/ParamRange/CCL storage and original emitted symbols replayed.'
LIMITS=['Portable source port only: original ordinary return spelling, field layout, ARM ABI, allocator interoperability and hardware remain unresolved. All methods remain declaration-pending.', 'Native Element attribute methods remain explicit modeled boundaries. Original Element constructor/destructor bodies and actual child D0 dispatch execute; genuine CCL Vector resize(0) is the source-provider boundary for destruction. Host uses genuine current Element and MetaElement implementations. Native Core bodies excluded; real pinned source CString bridge substitutes providers. Native libc scanner uses host libc; locale-sensitive/nonfinite/overflow scan behavior is excluded.', 'StringListElement::getString equivalence is only valid-index nonnull StringElement children. Native invalid-index/static error pointer tokens are recorded without dereference; host throws for invalid indices. Null/non-StringElement children excluded by typed ownership contract.', 'Integer steps conversion equivalence bounded to finite double values within int range. Excluded nonfinite/out-of-range d2iz semantics. Exact original parameter return declarations remain unresolved even where source-compatible bool load/save is needed.', 'C++ convenience range/presence/text and ElementAccess childCount/childAt accessors are independent source-port adapters with zero original credit.']
def dump(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n')
def main():
 for path,digest in ARCHIVE_HASHES.items():assert sha(path)==digest,('Changed pinned provider archive',path)
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['capture','format','compile','symbols','providers','native','replay','seal']);p.add_argument('--task');p.add_argument('--exe',type=Path);p.add_argument('--fixtures',type=Path,default=TEST/'fixtures.json');a=p.parse_args()
 contexts=task_contexts();context=next((c for c in contexts if c['task']['id']==a.task),contexts[0]);task=context['task'];scratch=Path('temp/recovery-work/uc-descriptor-family')/task['id'];scratch.mkdir(parents=True,exist_ok=True);exe=a.exe or scratch/'Replay';obj=scratch/'Descriptors.o'
 fmt=[FORMAT,'--style=file','--fallback-style=LLVM','--dry-run','--Werror',*map(str,[*HEADERS,*SOURCES,TEST/'Replay.cpp'])]
 cxx=['/usr/bin/c++','-std=c++17','-O0','-Ulinux','-fno-sized-deallocation','-Iuc-library/include','-isystem','third_party/ccl-framework']
 compile_commands=[[*cxx,'-c',str(s),'-o',str(scratch/(s.stem+'.o'))] for s in SOURCES]
 link=[*cxx,str(TEST/'Replay.cpp'),*map(str,PROVIDERS),*[str(scratch/(s.stem+'.o')) for s in SOURCES],'-Wl,--wrap=_ZdlPv','-Wl,--wrap=_ZN8Presonus2UC7ElementD2Ev',*map(str,ARCHIVES),'-o',str(exe)]
 if a.mode=='format':subprocess.run(fmt,check=True);return
 if a.mode=='compile':
  for cmd in [*compile_commands,link]:print(json.dumps(cmd),flush=True);subprocess.run(cmd,check=True)
  return
 if a.mode=='providers':
  # Exact pinned CString constructor/copy and append contracts, independent of
  # descriptor C++ bodies. Guard against cancellation by later append writes.
  def run(cap,kind,text,initial=None):
   args=[str(exe),'provider',str(cap),kind,text.encode().hex() or '-']
   if initial is not None:args.append(initial.encode().hex() or '-')
   out=subprocess.check_output(args,text=True).strip();return '' if out=='-' else bytes.fromhex(out).decode()
  for cap in (32,64,128):
   assert run(cap,'text','')==''
   assert run(cap,'text','abc')=='abc'
   assert run(cap,'text','x'*200)=='x'*(cap-1)
  assert run(32,'int','7','prefix:')=='prefix:7'
  assert run(32,'double','4607182418800017408','prefix:')=='prefix:1.000000'
  print('Pinned CString32/64/128 empty/text/truncation and CString32 existing-buffer append provider contracts passed');return
 if a.mode=='capture':dump(a.fixtures,observe(exe));return
 fixture=json.loads(a.fixtures.read_text());targets=[x for x in fixture['targets'] if x['task_id']==task['id']]
 assert len(targets)==len(context['originals'])
 if a.mode=='native':
  fresh=observe(exe,task['id']);assert fresh['targets']==targets;print(task['id']+': exact original executions reproduced');return
 if a.mode=='replay':
  n=0
  for t in targets:
   for case in t['cases']:
    got=subprocess.check_output([str(exe),*case['argv']],text=True).strip();assert got==case['output'],(t['original']['mangled'],case['argv'],got,case['output']);n+=1
  assert subprocess.check_output([str(exe),'lifetime'],text=True).strip()=='3'
  print(task['id']+': '+str(n)+' original/provider-to-portable cases passed; actual owning Element destroyed all 3 positive typed children');return
 nm=['/usr/bin/nm','--defined-only',*[str(scratch/(s.stem+'.o')) for s in SOURCES]];names={x['original']['mangled'] for x in targets}
 if a.mode=='symbols':
  output=subprocess.check_output(nm,text=True).splitlines();matched=[x for x in output if x.split() and x.split()[-1] in names];assert {x.split()[-1] for x in matched}==names
  print(json.dumps(dict(argv=nm,matched=matched)));return
 verify();logs=[];checks=[]
 for mode in ('format','compile','symbols','providers','native','replay'):
  cmd=[PY,'-B',str(TEST/'check.py'),mode,'--task',task['id']];start=time.monotonic();r=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);logs.append(dict(argv=cmd,returncode=r.returncode,seconds=time.monotonic()-start,output=r.stdout));assert r.returncode==0,r.stdout;checks.append(dict(kind='replay' if mode in ('native','providers') else mode,argv=cmd,timeout_seconds=180))
 # Re-read compiled symbol evidence after local checks, before immutable sealing.
 output=subprocess.check_output(nm,text=True).splitlines();matched=[x for x in output if x.split() and x.split()[-1] in names]
 log=scratch/'validation-frozen03.json';assert not log.exists(),'Use a new explicit frozen log generation; do not overwrite historical validation'
 dump(log,logs)
 dependencies={p:sha(p) for p in task['sources'] if p not in task['owned_files']};dependencies[str(SUPPLEMENT)]=sha(SUPPLEMENT);dependencies['temp/recovery-work/uc-descriptor-family/provider-correction03/DEFECT.json']='078c8f0fcbc4a2d5f7b4c067217fe12ffce98e54c22b06542297075ef06a09a7'
 sources={str(p.relative_to('uc-library')):sha(p) for p in [*HEADERS,*SOURCES]}
 originals=[dict(elf_sha256=o['elf'],firmware=o['firmware'],role=o['role'],mangled=o['mangled'],address=o['address'],size=o['size'],section=o['section'],file_offset=o['file_offset'],range_sha256=o['range_sha256']) for o in [x['original'] for x in targets]]
 proof=Path('uc-library/candidates')/task['id']/'worker-proof.json';handoff=proof.with_name('HANDOFF.json')
 pending=[dict(original_elf_sha256=o['elf_sha256'],mangled=o['mangled'],cpp_compiled=True,mangling_namespace_checked=True,portable_ready=False,sources=sources,repository_sources=dependencies,validation_domain=DOMAIN,declaration_uncertainties=LIMITS) for o in originals]
 dump(proof,dict(task_id=task['id'],originals=originals,native_targets=targets,oracle_producer_inputs={str(TEST/'native.py'):sha(TEST/'native.py'),str(TEST/'Replay.cpp'):sha(TEST/'Replay.cpp')},replay_producer_inputs={str(TEST/'check.py'):sha(TEST/'check.py')},runtime_versions=dict(python=sys.version,unicorn=unicorn.__version__,pyelftools=elftools.__version__),validation_domain=DOMAIN,limitations=LIMITS,fixture_sha256=sha(a.fixtures),compiled_mangled_names_matched=True,cpp_differential_passed=True,format_check_passed=True,formatted_files={str(p.relative_to('uc-library')):sha(p) for p in [*HEADERS,*SOURCES,TEST/'Replay.cpp']},formatter_version=subprocess.check_output([FORMAT,'--version'],text=True).strip(),compiler_version=subprocess.check_output(['/usr/bin/c++','--version'],text=True).splitlines()[0],provider_commit='e8cbdea4a4a20e15111f5a690798a259c0374b31',provider_archives={str(p):sha(p) for p in ARCHIVES},format_argv=fmt,compile_argv=compile_commands,link_argv=link,compiled_symbols=dict(argv=nm,matched=matched,all_defined=output),exe_sha256=sha(exe),immutable_validation_log=dict(path=str(log),sha256=sha(log)),proposed_readiness=dict(ready=[],pending=pending)))
 packet=PACKETS/task['id']/'CONTEXT.json';artifacts={p:'source' for p in [*HEADERS,*SOURCES]};artifacts.update({TEST/'Replay.cpp':'test',TEST/'check.py':'replay',TEST/'native.py':'producer',a.fixtures:'fixture',proof:'proof',log:'proof',packet:'packet'});artifacts.update({Path(p):'dependency' for p in dependencies})
 data=dict(version=1,task_id=task['id'],namespace=task['namespace'],packet_manifest=str(packet),originals=originals,artifacts=[dict(path=str(p),kind=k,sha256=sha(p)) for p,k in artifacts.items()],checks=checks,validation_domain=DOMAIN,limitations=LIMITS,build_integration=dict(partition='common',production_sources=list(map(str,SOURCES)),public_headers=list(map(str,HEADERS)),test_target='uc_descriptor_family_replay',link_dependencies=['presonus_uc'],link_options=['-Wl,--wrap=_ZdlPv','-Wl,--wrap=_ZN8Presonus2UC7ElementD2Ev'],compile_options=['-fno-sized-deallocation'],ctest_argv=[PY,'-B',str(TEST/'check.py'),'replay','--task',task['id'],'--exe','$<TARGET_FILE:uc_descriptor_family_replay>','--fixtures',str(a.fixtures)]))
 dump(handoff,data)
 spec=importlib.util.spec_from_file_location('accept_worker',Path('uc-library/tools/recovery/accept_worker.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.validate(data)
 dump(scratch/'preflight.json',dict(unchanged_validate_passed=True,validator_sha256=sha('uc-library/tools/recovery/accept_worker.py'),handoff_sha256=sha(handoff)))
 print(str(handoff))
if __name__=='__main__':main()
