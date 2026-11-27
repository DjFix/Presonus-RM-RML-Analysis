import argparse,hashlib,json,pathlib,subprocess,datetime,os,sys
p=argparse.ArgumentParser();p.add_argument('--exe',required=True);p.add_argument('--object',required=True);p.add_argument('--integration',required=True);p.add_argument('--out',required=True);a=p.parse_args()
TASK=pathlib.Path(__file__).parent.name
BASE='uc-library/tests/recovery/'+TASK
H=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
subprocess.run(['uc-library/.venv/bin/python',BASE+'/native.py','--verify','--provider-exe',a.exe],check=True)
req=json.loads(pathlib.Path('temp/recovery-work/rolling10x10-20261114/prepared-next-flow01/packets',TASK,'request.json').read_text())
paths=['uc-library/include/presonus/surface_update/FirmwareUpdateComponent.hpp','uc-library/src/Presonus/Surface/FirmwareUpdateCallbacks.cpp',BASE+'/Replay.cpp']
subprocess.run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*paths],check=True)
fixture=json.loads(pathlib.Path(BASE+'/fixtures.json').read_text())
symbols=subprocess.check_output(['nm',a.object],text=True)
for target in req['targets']:assert target['mangled'] in symbols
output=subprocess.check_output([str(pathlib.Path(a.exe).resolve())],text=True)
assert output.splitlines()==['firmwareupdate 1 1 0 1 1','firmwareUpdate 0 1']
actual_provider=json.loads(subprocess.check_output([str(pathlib.Path(a.exe).resolve()),'--observe-provider'],text=True));assert actual_provider==fixture['provider_observations']

paths+=['uc-library/include/presonus/surface_update/CallbackText.hpp']
sources={x.removeprefix('uc-library/'):H(x) for x in paths+[BASE+'/native.py',BASE+'/check.py',BASE+'/fixtures.json']}
providers={x:H(x) for x in ['third_party/ccl-framework/core/portable/corecomponent.h','third_party/ccl-framework/core/portable/corecomponent.cpp','third_party/ccl-framework/core/portable/coreworker.h','third_party/ccl-framework/core/portable/coreworker.cpp','third_party/ccl-framework/core/system/corethread.h']}
domain='Constructor-only normal successful allocation: each original C1/C2 132-byte range independently executed with four prefills, exact name and native vptr/worker/zero writes and call ordering recorded. Independent actual pinned Component/BackgroundWorker observation and host runtime-forwarded new/delete allocation+free smoke. Existing callback overload retains original source-port name and no worker allocation. No thread/task/update/flash operations.'
uncertainties=['Native +0x94 task-word meaning/type remains unresolved; portable explicit uint32_t independent of callback progress parameter.','Original class member declarations/layout and ARM ABI not established.']
records=[dict(original_elf_sha256=x['original_elf_sha256'],mangled=x['mangled'],original_address=x['address'],sources=sources,repository_sources=providers,domain=domain,portable_ready=False,declaration_uncertainties=uncertainties,cpp_compiled=True,mangling_namespace_checked=True,original_function_verified=False,hardware_verified=False) for x in req['targets']]
proof=dict(provider_observations=actual_provider,version=1,task_id=TASK,phase='local' if a.integration=='local' else 'canonical',utc_end=datetime.datetime.now(datetime.timezone.utc).isoformat(),session_id=os.getenv('CODEX_THREAD_ID'),sources=sources,repository_sources=providers,domain=domain,cpp_differential_passed=True,compiled_original_mangled_names_matched=True,mangling_namespace_checked=True,functions=[dict(r,cpp_differential_passed=True,range_verified=True,native_cases=sum(case['variant'] in r['mangled'] for case in fixture['cases'])) for r in records],fixture={'path':BASE+'/fixtures.json','sha256':H(BASE+'/fixtures.json')},producer_sha256=H(__file__),oracle_producer_sha256=H(BASE+'/native.py'),executable={'path':a.exe,'sha256':H(a.exe)},objects={a.object:H(a.object)},format={'version':subprocess.check_output(['uc-library/.venv/bin/clang-format','--version'],text=True).strip(),'sources':{x:H(x) for x in paths}},proposed_readiness={'canonical_binding_pending':True,'ready':[],'pending':records},limitations=uncertainties+['Original Core/runtime allocator bodies excluded; constructor normal-path boundaries modeled from actual host observations. Original exception/EH landing pads, secondary interfaces/layout and binary ABI not reconstructed. No device/update/task execution.'],observations=output)
if a.integration!='local':proof['integration']={'path':a.integration,'sha256':H(a.integration)}
provider_root=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis')
provider_addendum=provider_root/'temp/recovery-work/rolling10x10-20261114/root-review/generation06/provider-link-proposal/PROVIDER_LINK_ADDENDUM.json'
provider_metadata=json.loads(provider_addendum.read_text())
sys.path.insert(0,str(provider_root/'uc-library/tools/recovery'))
from pinned_codec_replay_binding_curl_scope import validate_archives
historical_archives={archive['path']:archive['sha256'] for archive in provider_metadata['archives']}
archive_binding=validate_archives(provider_root,a.exe,a.integration,historical_archives,transitive_provider={'path': 'evidence/recovery/2026-11-27/scoped-ready/firmware-curl-closure-successor03/TRANSITIVE-CURL-CODEC-BINDING03.json', 'sha256': 'f0d074259b00816889dce3cc3220a4045fba8ef1cb76b533448e757fde97c646'})
proof['archives']=archive_binding['archives']
proof['dynamic_codec_provider']=archive_binding.get('dynamic_codec_provider')
proof['codec_behavior_exercised']=False
proof['dynamic_codec_scope']='Constructor fields/lifetime only; no codec behavior or exclusive runtime symbol origin claimed. Four pinned implementation archives remain exact bound.'
proof['historical_provider_archives']=archive_binding['historical']
proof['provider_archive_transition']=archive_binding['transition']
proof['provider_link_provenance']={'path':str(provider_addendum),'sha256':H(provider_addendum),'upstream':provider_metadata['upstream'],'provider_proof':provider_metadata['provider_proof']}
proof['native_runtime_models']='Native allocator returns valid abstract storage; real host runtime new/delete wrappers forward and observe actual allocation/deallocation. Native Core constructors not executed.'
proof['runtime']={'path':'/usr/lib/x86_64-linux-gnu/libstdc++.so.6.0.33','sha256':H('/usr/lib/x86_64-linux-gnu/libstdc++.so.6.0.33')}
pathlib.Path(a.out).write_text(json.dumps(proof,indent=2)+'\n')
