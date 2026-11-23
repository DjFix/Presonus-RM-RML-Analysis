import argparse,hashlib,json,subprocess,sys,datetime,shutil,unicorn,elftools
from pathlib import Path
from native import observations,PREFIX,ROOT

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
EXPECTED_INPUTS = {'uc-library/include/presonus/mixer/ChannelComponent.hpp': '1764263cac4cd4395003cff50fc6bddee696f1f3fc4fd1222fe4d8320cbbc118', 'uc-library/include/presonus/mixer/MonoMainComponent.hpp': '5951a6f93db39c8ceb61e06111f8fd853690c2f9405eb3781d36b915a54608d0', 'uc-library/src/Presonus/Mixer/ChannelComponent.cpp': 'c5720d84bd00a65f68fa1ecc3ccf9015687df77cd53a6eb49d245c37e9efb532', 'uc-library/src/Presonus/Mixer/MonoMainComponent.cpp': '7c670dac96bc367d06486b334dd8c10d456aeeaac05ed1a98de14271bd80443e', 'uc-library/tests/recovery/trial10x2_mono_d1/Replay.cpp': 'ca6376aedbaa743f1487869b9978a483148e4f3514ee4980dd1cc78a449c9e3f', 'third_party/ccl-framework/core/portable/corecomponent.h': '3c9507761a27b802d8221eaead5450aa612b85caa9d77b7ac4eb2a4d74aa24cb', 'third_party/ccl-framework/core/portable/corecomponentflags.h': 'ec762b9af8f44333c7c7c6e0dd4b1225691fc9233eadf10d95ec89c65850640c', 'third_party/ccl-framework/core/portable/coreparaminfo.h': '5465baf63065883e6f63d446609ef2feeea513853246c1f04c887be1d25f30f0', 'third_party/ccl-framework/core/portable/coreparams.h': '50784dfb1ff6f3a4ce7134560d8a042b850971f96ebac6476be16326ed2c93cd', 'third_party/ccl-framework/core/portable/coretypeinfo.h': '2c5c4ac61b372f490ad071f6a610f5dbbfe9946b3ac38b25d210a97d637261dc', 'third_party/ccl-framework/core/public/corebasicmacros.h': '9b879c0b7d7c02ba55e881c2cc768f04f60aa2e8d6d2834cf4afe43e6ca5d0ce', 'third_party/ccl-framework/core/public/coreclassmacros.h': 'f67174739f108e57b6fdf4fe0a64a7c9df2a38b69841a97bb6ad8b762652ac77', 'third_party/ccl-framework/core/public/coreclibrary.h': 'be34ea81e1ef1f42c0f66df7584757089e75f1e41df835db2075a21c629f26bc', 'third_party/ccl-framework/core/public/corecontainer.h': 'e0c4482b13494aa0aa1d0a1713276bb42c7cdeb2609df7ab73b1a5be395e280a', 'third_party/ccl-framework/core/public/coreformatter.h': 'cc9215eeea8262be411ed08b2dcda376a2bc2510d5b0cf49b123be82b583d023', 'third_party/ccl-framework/core/public/coreinterpolator.h': 'df53a9ef512006a619b46831a7026380154a0589032290748737b8b2f030a202', 'third_party/ccl-framework/core/public/coremacros.h': 'd2827dfd0182e53757411849b4e582e5a2d4926814a0d21720472432a0ef7829', 'third_party/ccl-framework/core/public/coremalloc.h': '619ed30f6e89ed3bb27c9179819864a7069a123e9c96ad5b950f5494729f14ff', 'third_party/ccl-framework/core/public/coreplatform.h': 'c0c45a8fcce4d694ff6b440a64769c30dcf0a8592c5e24a27d48dc7ac5e854d1', 'third_party/ccl-framework/core/public/corestringbuffer.h': '46de7c2332457b082b9078b75b32ddb8ca35ce01d063fb9b330ffaa7e7acd55c', 'third_party/ccl-framework/core/public/corestringtraits.h': '887b7de884ad52608e4fa3a74c45102b6fbcac863a8b9db4f54618bc2534275f', 'third_party/ccl-framework/core/public/coretypes.h': '42caf0a821eb374df5fe0e8b14b3ea1fa368ce06c025710b47abb5a71f247a68', 'third_party/ccl-framework/core/public/coreuid.h': 'aac2bbacbb5cc1663753e377b851f8d7fed0ccfb7e977dbc02bf5cb2750ad667', 'third_party/ccl-framework/core/public/corevector.h': '49634ef286112cfa48357391a3cdddbee86e76cfe5e820b6b74c6ec913aeed32', 'third_party/ccl-framework/core/portable/corecomponent.cpp': '79fc17cf36a2946eac7293284ce693072a1875844736e4f1d70c48e6757ce7f6', 'third_party/ccl-framework/core/portable/coreparams.cpp': 'd7986b98e2de685b206e0b26303e2dbcfafa56d7290345ac6fa9516bc79502b5'}


def load_current_transition(args):
 if not (args.current_source_transition or args.current_source_transition_sha256):return {},None
 assert args.current_source_transition and args.current_source_transition_sha256
 receipt=Path(args.current_source_transition)
 assert digest(receipt)==args.current_source_transition_sha256
 data=json.loads(receipt.read_text())
 assert data['version']==1 and 'trial10x2_mono_d1' in data['tests']
 assert set(data['current_sources'])=={'uc-library/include/presonus/mixer/ChannelComponent.hpp', 'uc-library/src/Presonus/Mixer/ChannelComponent.cpp'}
 for ref in data['previous_worker_proofs'].values():
  assert digest(ref['path'])==ref['sha256']
 return data['current_sources'],dict(path=str(receipt),sha256=args.current_source_transition_sha256)

def current_input(path,historical,changes):
 if path not in changes:return historical
 row=changes[path]
 assert historical==row['previous_sha256']
 assert digest(row['previous_frozen_read_path'])==historical
 assert digest(row['current_frozen_read_path'])==row['current_sha256']
 return row['current_sha256']

def main():
 p=argparse.ArgumentParser();p.add_argument('--exe',required=True);p.add_argument('--object',required=True);p.add_argument('--integration',required=True);p.add_argument('--out',required=True);p.add_argument('--record-fixture',action='store_true');p.add_argument('--current-source-transition');p.add_argument('--current-source-transition-sha256');a=p.parse_args()
 changes,transition=load_current_transition(a)
 assert set(changes)<=set(EXPECTED_INPUTS)
 for path,expected in EXPECTED_INPUTS.items():assert digest(ROOT/path)==current_input(path,expected,changes),path
 supplement=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/trial10x2-20261115/root-review/provider-supplement')
 manifest=supplement/'PROVIDERS.json';approval=supplement/'ROOT_APPROVAL.json'
 assert digest(manifest)=='0e4fc25d3383ae8609932b7e25c4d28bac3ee92b9435c11e8d63b61cd29f0c18'
 providers=json.loads(manifest.read_text());assert json.loads(approval.read_text())['approved']
 used_archives={}
 for name in ['libcorelib.a','libpresonus_core_allocator.a']:
  entry=providers['archives'][name];assert digest(entry['frozen_read_path'])==entry['sha256'];used_archives[entry['frozen_read_path']]=entry['sha256']
 for path,expected in EXPECTED_INPUTS.items():
  if path in providers['read_inputs']:
   sealed=providers['read_inputs'][path];assert expected==sealed['sha256'];assert digest(sealed['frozen_read_path'])==expected
 exe=Path(a.exe).resolve();obj=Path(a.object).resolve();integration=Path(a.integration)
 assert exe.is_file() and obj.is_file() and integration.is_file()
 native=observations(exe)
 fixture=Path(__file__).with_name('fixtures.json')
 if a.record_fixture:fixture.write_text(json.dumps(native,indent=2)+'\n')
 assert native==json.loads(fixture.read_text())
 nm=subprocess.check_output(['nm','--defined-only',str(obj)],text=True)
 for v in ['D0','D1','D2']:assert PREFIX+v+'Ev' in nm
 disassembly=subprocess.check_output(['objdump','-dr',str(obj)],text=True)
 d0=disassembly.split('<'+PREFIX+'D0Ev>:')[1].split('\n\n')[0]
 assert '_ZdlPv' in d0 and '_ZdlPvm' not in d0
 # Canonical exe is inspected as well: prevents passing worker object beside
 # an unrelated supplied product binary.
 exedis=subprocess.check_output(['objdump','-d',str(exe)],text=True)
 ed0=exedis.split('<'+PREFIX+'D0Ev>:')[1].split('\n\n')[0]
 assert '_ZdlPv' in ed0 and '_ZdlPvm' not in ed0
 results=[]
 for case in native['cases']:
  argv=[str(exe),case['variant'],str(case['children'])]
  actual=subprocess.check_output(argv,text=True).strip()
  assert actual==case['provider_observation'],(argv,actual,case)
  results.append(dict(argv=argv,observation=actual))
 sourcepaths=['uc-library/include/presonus/mixer/MonoMainComponent.hpp','uc-library/src/Presonus/Mixer/MonoMainComponent.cpp','uc-library/include/presonus/mixer/ChannelComponent.hpp','uc-library/src/Presonus/Mixer/ChannelComponent.cpp']
 dependencies=subprocess.check_output(['c++','-std=c++17','-Wno-multichar','-fno-rtti','-fno-sized-deallocation','-Iuc-library/include','-Ithird_party/ccl-framework','-MM','uc-library/tests/recovery/trial10x2_mono_d1/Replay.cpp','uc-library/src/Presonus/Mixer/MonoMainComponent.cpp','uc-library/src/Presonus/Mixer/ChannelComponent.cpp'],text=True)
 dep_paths=sorted(set(x for x in dependencies.replace('\\\n',' ').split() if not x.endswith(':') and x!='\\'))
 dep_hashes={x:digest(ROOT/x) for x in dep_paths}
 sources={x.removeprefix('uc-library/'):h for x,h in dep_hashes.items() if x.startswith('uc-library/')}
 repository_sources={x:h for x,h in dep_hashes.items() if not x.startswith('uc-library/')}
 for x in ['third_party/ccl-framework/core/portable/corecomponent.cpp','third_party/ccl-framework/core/portable/coreparams.cpp']:
  repository_sources[x]=digest(ROOT/x)
 domain='4 nontrivial states per exact original D1/D0: 1,2,4,8 owned real CCL children, two real parameters per node, observed parameter destruction notifications and child destruction; borrowed ChannelState/level preserved; D1 no receiver free, D0 one actual unsized free. Native vptr writes, receiver return, SP restoration, untouched remaining bytes and exact call order.'
 limits=['Portable source/provider lifecycle equivalence in bounded translated state only; original full constructor/layout/inheritance/EH/ARM ABI/hardware unresolved.','Native Core is not executed; actual pinned source provider intentionally substituted. Borrowed ChannelState and level parameter survive.','D2 compiled alias is checked but no separate D2 original is credited by either assignment.']
 entries=[]
 for r in native['ranges']:
  entries.append(dict(original_elf_sha256=native['elf_sha256'],mangled=r['mangled'],original_address=r['address'],portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True,original_declaration_verified=False,original_arm_abi_verified=False,hardware_verified=False,canonical_binding_pending=True,sources=sources,repository_sources=repository_sources,domain=domain,validation_domain=domain,declaration_uncertainties=limits+['Original class inheritance/full declaration unresolved; native base call translated to reviewed actual portable ChannelComponent/CCL provider, not native base binary equivalence.']))
 formatpaths=[ROOT/x for x in ['uc-library/include/presonus/mixer/MonoMainComponent.hpp','uc-library/src/Presonus/Mixer/MonoMainComponent.cpp','uc-library/tests/recovery/trial10x2_mono_d1/Replay.cpp']]
 subprocess.run([str(ROOT/'uc-library/.venv/bin/clang-format'),'--style=file','--fallback-style=LLVM','--dry-run','--Werror',*map(str,formatpaths)],check=True)
 tool_versions={x:subprocess.check_output([x,'--version'],text=True).splitlines()[0] for x in ['c++','nm','objdump',str(ROOT/'uc-library/.venv/bin/clang-format')]}
 proof=dict(runtime_versions=dict(python=sys.version,unicorn=unicorn.__version__,pyelftools=elftools.__version__),provider_archive_hashes=used_archives,provider_supplement={str(manifest):digest(manifest),str(approval):digest(approval)},version=1,task_id='trial10x2_mono',canonical_binding_pending=True,cpp_differential_passed=True,compiled_original_mangled_names_matched=True,mangling_namespace_checked=True,functions=[dict(x,range_verified=True,cpp_differential_passed=True,native_cases=4) for x in entries],proposed_readiness=dict(ready=[],pending=entries),sources=sources,repository_sources=repository_sources,format=dict(version=tool_versions[str(ROOT/'uc-library/.venv/bin/clang-format')],sources={str(x.relative_to(ROOT)):digest(x) for x in formatpaths}),tool_versions=tool_versions,tool_hashes={x:digest(shutil.which(x)) for x in ['c++','nm','objdump']},producer_sha256=digest(__file__),oracle_producer_sha256=digest(Path(__file__).with_name('native.py')),fixture_sha256=digest(fixture),created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),validation_domain=domain,passed=True,behavior_passed=True,case_count=len(results),native=native,product=results,object=dict(path=str(obj),sha256=digest(obj)),executable=dict(path=str(exe),sha256=digest(exe)),integration=dict(path=str(integration),sha256=digest(integration)),producers=[dict(path=str(x.relative_to(ROOT)),sha256=digest(x)) for x in [Path(__file__),Path(__file__).with_name('native.py'),fixture]],symbols=nm,d0_object_disassembly=d0,d0_executable_disassembly=ed0,argv=sys.argv,limitations=['Portable source/provider lifecycle equivalence in bounded translated state only; original full constructor/layout/inheritance/EH/ARM ABI/hardware unresolved.','Native Core is not executed; actual pinned source provider is intentionally substituted. Borrowed ChannelState and level parameter survive.'])
 if transition:proof['current_source_transition']=transition
 Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(proof,indent=2)+'\n');print('PASS 8 original ARM executions and 8 product/provider lifecycle comparisons; D0 actual unsized free, nontrivial owned children/parameters, borrowed parameter preserved')
if __name__=='__main__':main()
