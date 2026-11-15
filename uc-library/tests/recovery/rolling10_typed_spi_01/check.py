import argparse,hashlib,json,pathlib,subprocess,datetime,os
p=argparse.ArgumentParser();p.add_argument('--exe',required=True);p.add_argument('--object',required=True);p.add_argument('--integration',required=True);p.add_argument('--out',required=True);a=p.parse_args()
TASK=pathlib.Path(__file__).parent.name
BASE='uc-library/tests/recovery/'+TASK
H=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
subprocess.run(['uc-library/.venv/bin/python',BASE+'/native.py','--verify'],check=True)
req=json.loads(pathlib.Path('temp/recovery-work/rolling10x10-20261114/prepared06/packets',TASK,'request.json').read_text())
paths=['uc-library/include/presonus/panel/SPIControl.hpp','uc-library/src/Presonus/Panel/SPIControl.cpp',BASE+'/Replay.cpp']
subprocess.run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*paths],check=True)
fixture=json.loads(pathlib.Path(BASE+'/fixtures.json').read_text())
symbols=subprocess.check_output(['nm',a.object],text=True)
for target in req['targets']:assert target['mangled'] in symbols
output=subprocess.check_output([str(pathlib.Path(a.exe).resolve())],text=True)
rows=output.splitlines();assert len(rows)==len(fixture['cases'])+1 and rows[-1]=='0'
for line,case in zip(rows,fixture['cases']):
 calls=case['calls'];assert list(map(int,line.split()))==[case['after'],len(calls),calls[0]['level'] if calls else 0]

addendum_path=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/root-review/generation06/addenda-proposal-spi/rolling10_focus.json')
assert H(addendum_path)=='5713cb46524b97c9daf0b8fe2caf7e371f7150930802e81507aa93007c3512c0'
addendum=json.loads(addendum_path.read_text())
owned={'uc-library/include/presonus/panel/SPIControl.hpp','uc-library/src/Presonus/Panel/SPIControl.cpp'}
for path,entry in addendum['files'].items():
 assert H(entry['frozen_read_path'])==entry['sha256']
 if path not in owned: assert H(path)==entry['sha256']
paths += [path for path in addendum['files'] if path.startswith('uc-library/') and path not in paths and path not in owned]
sources={x.removeprefix('uc-library/'):H(x) for x in paths+[BASE+'/native.py',BASE+'/check.py',BASE+'/fixtures.json']}
providers={path:H(path) for path in addendum['files'] if path.startswith('third_party/ccl-framework/core/')}
domain='9 native/portable SPI cases: equal/change signed32 values including extremes, unchanged null IO, actual inherited IPanelIO broadcast default. Native executes actual provider; portable entry instrumentation observes updated state and actual dispatch count while provider executes unchanged. Other transport methods never invoked, unknown IO overrides/hardware excluded.'
uncertainties=['Original ordinary method return declaration unencoded and unresolved.','Original class member declarations/layout and ARM ABI not established.']
records=[dict(original_elf_sha256=x['original_elf_sha256'],mangled=x['mangled'],original_address=x['address'],sources=sources,repository_sources=providers,domain=domain,portable_ready=False,declaration_uncertainties=uncertainties,cpp_compiled=True,mangling_namespace_checked=True,original_function_verified=False,hardware_verified=False) for x in req['targets']]
proof=dict(version=1,task_id=TASK,phase='local' if a.integration=='local' else 'canonical',utc_end=datetime.datetime.now(datetime.timezone.utc).isoformat(),session_id=os.getenv('CODEX_THREAD_ID'),sources=sources,repository_sources=providers,domain=domain,cpp_differential_passed=True,compiled_original_mangled_names_matched=True,mangling_namespace_checked=True,functions=[dict(r,cpp_differential_passed=True,range_verified=True,native_cases=len(fixture['cases'])) for r in records],fixture={'path':BASE+'/fixtures.json','sha256':H(BASE+'/fixtures.json')},producer_sha256=H(__file__),oracle_producer_sha256=H(BASE+'/native.py'),executable={'path':a.exe,'sha256':H(a.exe)},objects={a.object:H(a.object)},format={'version':subprocess.check_output(['uc-library/.venv/bin/clang-format','--version'],text=True).strip(),'sources':{x:H(x) for x in paths}},proposed_readiness={'canonical_binding_pending':True,'ready':[],'pending':records},limitations=uncertainties+['No Core binary execution, fake broadcast callback, hardware or unknown override behavior. Caller-owned live Control/IO and empty timer/parameter state for bounded lifecycle.'],observations=output)
if a.integration!='local':proof['integration']={'path':a.integration,'sha256':H(a.integration)}
proof['source_addendum']={'path':str(addendum_path),'sha256':H(addendum_path),'scope':'Read-only baseline dependencies; owned edited SPI outputs separately bound to current source hashes.'}
proof['owned_baselines']={path:H(pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared06/snapshot')/path) for path in owned}
proof['instrumentation']='Actual C++ provider function-entry instrumentation only; does not replace provider implementation or return.'
provider_root=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis')
provider_addendum=provider_root/'temp/recovery-work/rolling10x10-20261114/root-review/generation06/provider-link-proposal/PROVIDER_LINK_ADDENDUM.json'
provider_metadata=json.loads(provider_addendum.read_text())
proof['archives']={}
for archive in provider_metadata['archives']:
 path=provider_root/archive['path']
 assert H(path)==archive['sha256'],'Approved provider archive changed'
 proof['archives'][archive['path']]=H(path)
proof['provider_link_provenance']={'path':str(provider_addendum),'sha256':H(provider_addendum),'upstream':provider_metadata['upstream'],'provider_proof':provider_metadata['provider_proof'],'scope':'Actual SDK archives read and linked by local argv; hashes rechecked for every local or canonical proof invocation.'}
pathlib.Path(a.out).write_text(json.dumps(proof,indent=2)+'\n')
