import argparse,hashlib,json,pathlib,subprocess,datetime,os
p=argparse.ArgumentParser();p.add_argument('--exe',required=True);p.add_argument('--object',required=True);p.add_argument('--integration',required=True);p.add_argument('--out',required=True);a=p.parse_args()
TASK=pathlib.Path(__file__).parent.name
BASE='uc-library/tests/recovery/'+TASK
H=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
subprocess.run(['uc-library/.venv/bin/python',BASE+'/native.py','--verify','--provider-exe',a.exe],check=True)
req=json.loads(pathlib.Path('temp/recovery-work/rolling10x10-20261114/prepared-next-flow01/packets',TASK,'request.json').read_text())
paths=['uc-library/include/presonus/surface/FatChannelClipboard.hpp','uc-library/src/Presonus/Surface/FatChannelClipboard.cpp',BASE+'/Replay.cpp']
subprocess.run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*paths],check=True)
fixture=json.loads(pathlib.Path(BASE+'/fixtures.json').read_text())
symbols=subprocess.check_output(['nm',a.object],text=True)
for target in req['targets']:assert target['mangled'] in symbols
output=subprocess.check_output([str(pathlib.Path(a.exe).resolve())],text=True)
assert list(map(int,output.split()))==[x['result'] for x in fixture['cases']]
provider_observations=json.loads(subprocess.check_output([str(pathlib.Path(a.exe).resolve()),'--observe-provider'],text=True));assert provider_observations==fixture['provider_observations']
supplement_path=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/root-review/provider-supplements/focus-ROOT_ADDENDUM.json')
assert H(supplement_path)=='0dbaed25a5c06966e3e1c4bf90f05dad886406639668df86d8c294dfd5bbaf03'
supplement=json.loads(supplement_path.read_text())
assert H(pathlib.Path('/home/rs/projects/opencs/ai-line-analysis')/supplement['plan'])==supplement['plan_sha256']
for name,entry in supplement['read_inputs'].items():
 assert H(name)==entry['sha256'] and H(entry['frozen_read_path'])==entry['sha256']
paths += [name for name in supplement['read_inputs'] if name.startswith('uc-library/') and name not in paths]
sources={x.removeprefix('uc-library/'):H(x) for x in paths+[BASE+'/native.py',BASE+'/check.py',BASE+'/fixtures.json']}
providers={name:H(name) for name in supplement['read_inputs'] if name.startswith('third_party/ccl-framework/core/')}
providers['third_party/ccl-framework/core/portable/coreparams.cpp']=H('third_party/ccl-framework/core/portable/coreparams.cpp')
domain='Seven finite cases over original parameter type key, null object, actual CCL null/unrelated/SLChannel controllers and tags 218/217/-1. Native application body executes against independently observed actual CCL getController and actual supported core_cast provider outcomes. Input object memory unchanged; stack and returned PC checked. Intentional CCL typed cast adapts original RTTI, no original RTTI/ABI claim.'
uncertainties=['Original ordinary method return declaration unencoded and unresolved.','Original class member declarations/layout and ARM ABI not established.']
records=[dict(original_elf_sha256=x['original_elf_sha256'],mangled=x['mangled'],original_address=x['address'],sources=sources,repository_sources=providers,domain=domain,portable_ready=False,declaration_uncertainties=uncertainties,cpp_compiled=True,mangling_namespace_checked=True,original_function_verified=False,hardware_verified=False) for x in req['targets']]
proof=dict(provider_observations=provider_observations,version=1,task_id=TASK,phase='local' if a.integration=='local' else 'canonical',utc_end=datetime.datetime.now(datetime.timezone.utc).isoformat(),session_id=os.getenv('CODEX_THREAD_ID'),sources=sources,repository_sources=providers,domain=domain,cpp_differential_passed=True,compiled_original_mangled_names_matched=True,mangling_namespace_checked=True,functions=[dict(r,cpp_differential_passed=True,range_verified=True,native_cases=len(fixture['cases'])) for r in records],fixture={'path':BASE+'/fixtures.json','sha256':H(BASE+'/fixtures.json')},producer_sha256=H(__file__),oracle_producer_sha256=H(BASE+'/native.py'),executable={'path':a.exe,'sha256':H(a.exe)},objects={a.object:H(a.object)},format={'version':subprocess.check_output(['uc-library/.venv/bin/clang-format','--version'],text=True).strip(),'sources':{x:H(x) for x in paths}},proposed_readiness={'canonical_binding_pending':True,'ready':[],'pending':records},limitations=uncertainties+['Native Core/getController and original runtime dynamic_cast are modeled boundaries, not firmware Core/runtime execution. Invalid Parameter pointers, unknown controller implementations, full IStorageFilter lifecycle/shouldLoad and hardware excluded.'],observations=output)
if a.integration!='local':proof['integration']={'path':a.integration,'sha256':H(a.integration)}
provider_root=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis')
provider_addendum=provider_root/'temp/recovery-work/rolling10x10-20261114/root-review/generation06/provider-link-proposal/PROVIDER_LINK_ADDENDUM.json'
provider_metadata=json.loads(provider_addendum.read_text());proof['archives']={}
for archive in provider_metadata['archives']:
 path=provider_root/archive['path'];assert H(path)==archive['sha256'];proof['archives'][archive['path']]=H(path)
proof['provider_link_provenance']={'path':str(provider_addendum),'sha256':H(provider_addendum),'upstream':provider_metadata['upstream'],'provider_proof':provider_metadata['provider_proof']}
proof['source_supplement']={'path':str(supplement_path),'sha256':H(supplement_path),'plan':supplement['plan'],'plan_sha256':supplement['plan_sha256']}
pathlib.Path(a.out).write_text(json.dumps(proof,indent=2)+'\n')
