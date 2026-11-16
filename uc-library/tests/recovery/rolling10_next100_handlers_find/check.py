import argparse,datetime,hashlib,importlib.util,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
D=Path(__file__).parent

def _current_canonical_binding(root, obj, exe, integration, source, providers=()):
 from pathlib import Path
 if not integration or Path(integration).resolve() != (root/'uc-library/validation/integration.json').resolve():return None
 assert obj and exe, 'Canonical replay requires explicit actual object and executable'
 import importlib.util
 helper=root/'uc-library/tools/recovery/canonical_compile_bindings.py'
 spec=importlib.util.spec_from_file_location('actual_canonical_bindings',helper);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 value=module.bind(root,Path(obj),source,exe_path=Path(exe),required_provider_sources=providers,required_archive_names=('libcorelib.a','libpresonus_core_allocator.a'))
 unexpected=[p for p in value['files'] if p.startswith('third_party/ccl-framework/') and not p.startswith('third_party/ccl-framework/core/')]
 assert not unexpected, ('Unexpected non-Core CCL inputs',unexpected)
 core={p:h for p,h in value['files'].items() if p.startswith('third_party/ccl-framework/core/')}
 library={p.removeprefix('uc-library/'):h for p,h in value['files'].items() if p.startswith('uc-library/')}
 assert core and source.removeprefix('uc-library/') in library, 'Actual canonical production/Core closure required'
 return {'binding':value,'sources':library,'repository_sources':core,'helper_sha256':hashlib.sha256(helper.read_bytes()).hexdigest()}

def _attach_current_canonical(proof, current):
 if current is None:return
 proof['actual_canonical_compile_binding']=current['binding']
 proof['canonical_producer_helper_sha256']=current['helper_sha256']
 proof['canonical_source_binding_scope']='Current actual Release object/depfile/link/archive inputs; historical frozen dependency expectations retained in original archived producer/proof, not refreshed or relabeled'
 proof['historical_provider_archives']=proof.get('provider_archives')
 proof['provider_archives']={v['path']:v['sha256'] for v in current['binding']['link']['archives']}
 proof['local_compile_defaults']=proof.get('compile_flags')
 proof['actual_canonical_compile_entries']=[x['compile_entry'] for x in current['binding']['objects']]
 proof['actual_canonical_sources']=current['sources']
 proof['actual_canonical_repository_sources']=current['repository_sources']
 for row in [*proof.get('proposed_readiness',{}).get('ready',[]),*proof.get('proposed_readiness',{}).get('pending',[])]:
  row.setdefault('sources',{}).update(current['sources'])
  repository=__import__('pathlib').Path(__file__).resolve().parents[4]
  for p,h in row['sources'].items():
   relative=__import__('pathlib').Path(p)
   assert not relative.is_absolute() and '..' not in relative.parts, ('Invalid library source binding',p)
   assert hashlib.sha256((repository/'uc-library'/relative).read_bytes()).hexdigest()==h, ('Retained library source binding changed outside actual closure',p)
  prior=row.setdefault('repository_sources',{})
  assert all(p.startswith('third_party/ccl-framework/core/') for p in prior), 'Unexpected prior non-Core repository dependency'
  repository=__import__('pathlib').Path(__file__).resolve().parents[4]
  for p,h in prior.items():assert hashlib.sha256((repository/p).read_bytes()).hexdigest()==h, ('Prior verified Core implementation changed',p)
  for p,h in current['repository_sources'].items():
   assert p not in prior or prior[p]==h, ('Conflicting verified Core source binding',p)
  prior.update(current['repository_sources'])

p=argparse.ArgumentParser();p.add_argument('--exe',required=True);p.add_argument('--object',required=True);p.add_argument('--integration',required=True);p.add_argument('--out',required=True);a=p.parse_args()
H=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
config={'task_id': 'rolling10_next100_handlers_find', 'sources': {'include/presonus/panel/key_input_provider.hpp': '3af10ca3b42989dcf3f87abfa939181eccb40fe8c72852c0e6ace0a876a9dbdb', 'include/presonus/surface/DAWMixerHandler.hpp': '1ecc89a2734a03d3872b4e0c94633bce178fe9c129f41dceaf8e976a2e8248b9', 'include/presonus/surface/PresetsPageComponent.hpp': '645ec3b9e98f3e4b0c329903582fe5e933d971cd4b77bba9096243cdfedd5ac8', 'tests/recovery/rolling10_next100_handlers_find/Replay.cpp': '56bb9fc348c4db0250493cb7c9766674ea203bae8b11d901c2cda383eedc8b3f', 'src/Presonus/Surface/SLMixerEncoder.cpp': 'ece8b4fe7569bf3ca6b534e87fd6f739aa5ac1485edaecf78941d6e1fde3dafe', 'include/presonus/surface/AssignmentHandlerTable.hpp': '7d0d22f848c487cbd5e546cf8c281ab10424ee793430ef818ce197e6009b9df9', 'tests/recovery/rolling10_next100_handlers_find/native.py': '444e465431248e7d5748cc27d7f56ad4739e71a34aaec7801bdc64ec5fbef144', 'src/Presonus/AssignmentHandlerTable.cpp': '67a634b757d72a021ad6f64690639342a828a3642b20e0ed18720f18fd75b2d9', 'src/Presonus/Surface/DAWMixerActivation.cpp': '31e1479c014704e5fdf7992b11dd3be34214b2724d969cfe877fa3ee986c6b8f', 'tests/recovery/rolling10_next100_handlers_find/fixtures.json': '352ebb70c642df3929869c4063936847d22478eeea3cd880950b8e6e840e8c2a', 'include/presonus/surface/sl_mixer_encoder.hpp': 'd67780433a2d96fbcdebd0e17e6e69afc176b0341112dafa2a34c49b61c9c26d', 'include/presonus/delay_timer.hpp': '3da2b15d6b56b8f921983ea0c97585736dbaa9d3757da8e708bbf81b2f2c9e55', 'include/presonus/color/IColorConverter.hpp': '9246b45055c511e46fdda60178a2f32c53dc31ccfb017bae925c5baa30ecfbc0', 'include/presonus/surface/MappingComponent.hpp': '04dd758718741677674bb6dd54204d58805174b527c5f5459728a55877798c9a'}, 'repository_sources': {'third_party/ccl-framework/core/public/gui/corecolor.h': 'bde1a05f098448b42041d5d66f79753dae4383ec09266d2dba6217a82d643b54', 'third_party/ccl-framework/core/public/coretypes.h': '42caf0a821eb374df5fe0e8b14b3ea1fa368ce06c025710b47abb5a71f247a68', 'third_party/ccl-framework/core/public/coreclassmacros.h': 'f67174739f108e57b6fdf4fe0a64a7c9df2a38b69841a97bb6ad8b762652ac77', 'third_party/ccl-framework/core/portable/corecomponent.h': '3c9507761a27b802d8221eaead5450aa612b85caa9d77b7ac4eb2a4d74aa24cb', 'third_party/ccl-framework/core/public/corestringbuffer.h': '46de7c2332457b082b9078b75b32ddb8ca35ce01d063fb9b330ffaa7e7acd55c', 'third_party/ccl-framework/core/portable/coreparams.h': '50784dfb1ff6f3a4ce7134560d8a042b850971f96ebac6476be16326ed2c93cd', 'third_party/ccl-framework/core/public/coreplatform.h': 'c0c45a8fcce4d694ff6b440a64769c30dcf0a8592c5e24a27d48dc7ac5e854d1', 'third_party/ccl-framework/core/portable/corecomponentflags.h': 'ec762b9af8f44333c7c7c6e0dd4b1225691fc9233eadf10d95ec89c65850640c', 'third_party/ccl-framework/core/portable/coresingleton.h': '2dfdb591516c9b3eb0c124a33a32bd7eb220f2f58a9c42a0e43ddeec454783fe', 'third_party/ccl-framework/core/portable/coreparaminfo.h': '5465baf63065883e6f63d446609ef2feeea513853246c1f04c887be1d25f30f0', 'third_party/ccl-framework/core/public/coreinterpolator.h': 'df53a9ef512006a619b46831a7026380154a0589032290748737b8b2f030a202', 'third_party/ccl-framework/core/public/coreprimitives.h': '7587ed00af9010e37d6a76f0e004bfe919e7d71958d831bb533beabd46daa429', 'third_party/ccl-framework/core/public/corestringtraits.h': '887b7de884ad52608e4fa3a74c45102b6fbcac863a8b9db4f54618bc2534275f', 'third_party/ccl-framework/core/portable/coretypeinfo.h': '2c5c4ac61b372f490ad071f6a610f5dbbfe9946b3ac38b25d210a97d637261dc', 'third_party/ccl-framework/core/public/coreuid.h': 'aac2bbacbb5cc1663753e377b851f8d7fed0ccfb7e977dbc02bf5cb2750ad667', 'third_party/ccl-framework/core/public/coreclibrary.h': 'be34ea81e1ef1f42c0f66df7584757089e75f1e41df835db2075a21c629f26bc', 'third_party/ccl-framework/core/public/coreformatter.h': 'cc9215eeea8262be411ed08b2dcda376a2bc2510d5b0cf49b123be82b583d023', 'third_party/ccl-framework/core/public/corebasicmacros.h': '9b879c0b7d7c02ba55e881c2cc768f04f60aa2e8d6d2834cf4afe43e6ca5d0ce', 'third_party/ccl-framework/core/public/corecontainer.h': 'e0c4482b13494aa0aa1d0a1713276bb42c7cdeb2609df7ab73b1a5be395e280a', 'third_party/ccl-framework/core/public/corevector.h': '49634ef286112cfa48357391a3cdddbee86e76cfe5e820b6b74c6ec913aeed32', 'third_party/ccl-framework/core/public/coremalloc.h': '619ed30f6e89ed3bb27c9179819864a7069a123e9c96ad5b950f5494729f14ff', 'third_party/ccl-framework/core/public/coremacros.h': 'd2827dfd0182e53757411849b4e582e5a2d4926814a0d21720472432a0ef7829'}, 'production_sources': ['uc-library/src/Presonus/AssignmentHandlerTable.cpp'], 'header': 'uc-library/include/presonus/surface/AssignmentHandlerTable.hpp', 'provider_archive_hashes': {'/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a': '3c4f0825acb529fda135587b7ff5cb92ca0100bb417a20c034d3fdef80a93e0c', '/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a': '69892fbcec9a50a140462982073c686a67ca4763dfb5dfa190534d022b78a40d'}, 'phase_start': {'phase': 'worker_reconstruction', 'separate_from_prior_administration': True, 'start_utc': '2026-11-14T10:14:16.771600+00:00', 'session': '01a1d7aa-6709-7753-a04d-a8307aa138b8'}}
canonical_binding=_current_canonical_binding(ROOT,a.object,a.exe,a.integration,config['production_sources'][0],('uc-library/src/Presonus/Surface/DAWMixerHandler.cpp','uc-library/src/Presonus/Surface/DAWMixerActivation.cpp','uc-library/src/Presonus/Surface/SLMixerEncoder.cpp'))
if canonical_binding is None:
 for n,h in config['sources'].items():assert H(ROOT/'uc-library'/n)==h, n
if canonical_binding is None:
 for n,h in config['repository_sources'].items():assert H(ROOT/n)==h,n
for n,h in config['provider_archive_hashes'].items():assert H(n)==h,n
spec=importlib.util.spec_from_file_location('native_handler_oracle',D/'native.py');native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native);observed=native.observations();fixture=json.loads((D/'fixtures.json').read_text());assert observed==fixture
symbols=subprocess.check_output(['nm','--defined-only',a.object],text=True);assert native.NAME in symbols
provider=subprocess.check_output([str(Path(a.exe).resolve()),'--observe-provider'],text=True);assert provider.strip()==bytes.fromhex(fixture['literals'][1]['hex']).rstrip(bytes([0])).decode()
payload=''.join(c['query']+' '+str(len(c['names']))+' '+' '.join(c['names'])+'\n' for c in fixture['cases']);output=subprocess.check_output([str(Path(a.exe).resolve())],input=payload,text=True);lines=output.splitlines();assert len(lines)==len(fixture['cases'])
for case,line in zip(fixture['cases'],lines):assert list(map(int,line.split()))==[case['result'],len(case['calls']),*case['calls']],(case,line)
formatpaths=[ROOT/n for n in config['production_sources']+[config['header'],str((D/'Replay.cpp').relative_to(ROOT))]]
subprocess.run([str(ROOT/'uc-library/.venv/bin/clang-format'),'--style=file','--fallback-style=LLVM','--dry-run','--Werror',*map(str,formatpaths)],check=True)
limits=[fixture['limitations'],'Original ordinary static pointer return spelling is unresolved; portable AssignmentHandler* is provisional. DAWMixer current port is standalone: test-only bridge delegates real getName, never asserts original inheritance.','Only abstract-interface fixture names/nulls plus actual DAWMixer provider; no other app provider behavior or lifecycle readiness.']
domain='72 exact original findHandler ARM executions: empty/multi/duplicate-first handlers; null and empty query/name normalization, prefix and case-sensitive UTF8 byte strings; getName call order/early exit, restored SP, stack-only writes. Actual original DAWMixer getName executes for P receivers; independent compiled actual DAWMixer source provider observed and table results/call order compared.'
sources=dict(config['sources']);sources[str((D/'check.py').relative_to(ROOT/'uc-library'))]=H(__file__)
entry=dict(original_elf_sha256=native.SHA,mangled=native.NAME,original_address=0x75dc0,portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True,original_declaration_verified=False,original_arm_abi_verified=False,hardware_verified=False,canonical_binding_pending=True,sources=sources,repository_sources=config['repository_sources'],domain=domain,validation_domain=domain,declaration_uncertainties=limits)
proof=dict(version=1,task_id=config['task_id'],canonical_binding_pending=True,cpp_differential_passed=True,compiled_original_mangled_names_matched=True,mangling_namespace_checked=True,functions=[dict(entry,range_verified=True,cpp_differential_passed=True,native_cases=len(fixture['cases']))],native=observed,provider_observation=provider,portable_observations=output,objects={a.object:H(a.object)},executable=dict(path=a.exe,sha256=H(a.exe)),integration=dict(path=a.integration,sha256=H(a.integration)),sources=sources,repository_sources=config['repository_sources'],provider_archive_hashes=config['provider_archive_hashes'],format=dict(version=subprocess.check_output([str(ROOT/'uc-library/.venv/bin/clang-format'),'--version'],text=True).strip(),sources={str(p.relative_to(ROOT)):H(p) for p in formatpaths}),producer_sha256=H(__file__),oracle_producer_sha256=H(D/'native.py'),fixture_sha256=H(D/'fixtures.json'),validation_domain=domain,limitations=limits,proposed_readiness=dict(ready=[],pending=[entry]),session=dict(start=config['phase_start'],end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),current_session=os.getenv('CODEX_THREAD_ID')))
_attach_current_canonical(proof,canonical_binding)
Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(proof,indent=2)+'\n');print('72 native/provider cases passed; pending original return declaration')
