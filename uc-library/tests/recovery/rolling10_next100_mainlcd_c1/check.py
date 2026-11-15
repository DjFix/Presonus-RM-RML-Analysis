import argparse,hashlib,json,pathlib,subprocess,datetime,os,time
p=argparse.ArgumentParser();p.add_argument('--exe',required=True);p.add_argument('--object',required=True);p.add_argument('--integration',required=True);p.add_argument('--out',required=True);p.add_argument('--compat-text-exe');p.add_argument('--compat-stack-exe');a=p.parse_args()
phase_started=datetime.datetime.now(datetime.timezone.utc).isoformat();phase_clock=time.monotonic()
TASK=pathlib.Path(__file__).parent.name
BASE='uc-library/tests/recovery/'+TASK
H=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
subprocess.run(['uc-library/.venv/bin/python',BASE+'/native.py','--verify','--provider-exe',a.exe],check=True)
req=json.loads(pathlib.Path('temp/recovery-work/rolling10x10-20261114/prepared-remaining14-phasea-proposed01/packets',TASK,'request.json').read_text())
paths=['uc-library/include/presonus/MainLCDComponent.hpp','uc-library/src/Presonus/MainLCDComponent.cpp',BASE+'/Replay.cpp']
subprocess.run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*paths],check=True)
fixture=json.loads(pathlib.Path(BASE+'/fixtures.json').read_text())
symbols=subprocess.check_output(['nm',a.object],text=True)
for target in req['targets']:assert target['mangled'] in symbols
output=subprocess.check_output([str(pathlib.Path(a.exe).resolve())],text=True)
assert output.strip()=='owned-default empty-vectors words40,0 checked-unbound stack passed'
actual_provider=json.loads(subprocess.check_output([str(pathlib.Path(a.exe).resolve()),'--observe-provider'],text=True));assert actual_provider==fixture['provider_observations']

paths+=['uc-library/src/Presonus/MainLCDPageStack.cpp','uc-library/include/presonus/PageComponent.hpp']
supplement_path=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/root-review/provider-supplements/mainlcd-compatibility/ROOT_ADDENDUM.json')
assert H(supplement_path)=='610a5ed5d89b9875e03785f4aa290d15e0ca29a7432a06211d2a874750a014b9'
supplement=json.loads(supplement_path.read_text());assert H(pathlib.Path('/home/rs/projects/opencs/ai-line-analysis')/supplement['plan'])==supplement['plan_sha256']
for name,entry in supplement['read_inputs'].items():assert H(name)==entry['sha256'] and H(entry['frozen_read_path'])==entry['sha256']
if a.integration!='local':assert a.compat_text_exe and a.compat_stack_exe,'Canonical proof requires current canonical compatibility executables'
text_exe=a.compat_text_exe or 'temp/recovery-work/mainlcd-phasea/text-compat'
stack_exe=a.compat_stack_exe or 'temp/recovery-work/mainlcd-phasea/stack-compat'
text_fixture=supplement['read_inputs']['uc-library/tests/recovery/trial08/mainlcd/native-fixtures.json']['frozen_read_path']
stack_fixture=supplement['read_inputs']['uc-library/tests/recovery/ranked09/lcd/fixtures.json']['frozen_read_path']
compat_commands=[['uc-library/.venv/bin/python','uc-library/tests/recovery/trial08/mainlcd/replay.py','--executable',text_exe,'--fixtures',text_fixture],['uc-library/.venv/bin/python','uc-library/tests/recovery/ranked09/lcd/replay.py','--exe',stack_exe,'--fixtures',stack_fixture]]
compat_outputs=[subprocess.check_output(argv,text=True) for argv in compat_commands]
paths += [name for name in supplement['read_inputs'] if name.startswith('uc-library/') and name not in paths]
sources={x.removeprefix('uc-library/'):H(x) for x in paths+[BASE+'/native.py',BASE+'/check.py',BASE+'/fixtures.json']}
providers={x:H(x) for x in ['third_party/ccl-framework/core/portable/corecomponent.h','third_party/ccl-framework/core/portable/corecomponent.cpp','third_party/ccl-framework/core/public/corevector.h','third_party/ccl-framework/core/portable/gui/coreview.h']}
providers.update({name:H(name) for name in supplement['read_inputs'] if name.startswith('third_party/ccl-framework/core/')})
domain='Normal original MainLCD C1/C2 constructor ranges individually checked and executed with four prefills each; exact empty Component name, actual CCL view/page vector zero resize and inline stack initialization. Owned initialized State is authoritative. Explicit unbound Application adaptation and old borrowed API compatibility checked separately; no original application flow claim.'
uncertainties=['Native +0x8c (40) and +0xf4 (0) word meanings/types remain unresolved; explicit portable uint32_t storage does not establish original declaration.','Original class member declarations/layout and ARM ABI not established.']
records=[dict(original_elf_sha256=x['original_elf_sha256'],mangled=x['mangled'],original_address=x['address'],sources=sources,repository_sources=providers,domain=domain,portable_ready=False,declaration_uncertainties=uncertainties,cpp_compiled=True,mangling_namespace_checked=True,original_function_verified=False,hardware_verified=False) for x in req['targets']]
proof=dict(provider_observations=actual_provider,version=1,task_id=TASK,phase='local' if a.integration=='local' else 'canonical',utc_end=datetime.datetime.now(datetime.timezone.utc).isoformat(),session_id=os.getenv('CODEX_THREAD_ID'),sources=sources,repository_sources=providers,domain=domain,cpp_differential_passed=True,compiled_original_mangled_names_matched=True,mangling_namespace_checked=True,functions=[dict(r,cpp_differential_passed=True,range_verified=True,native_cases=sum(case['variant'] in r['mangled'] for case in fixture['cases'])) for r in records],fixture={'path':BASE+'/fixtures.json','sha256':H(BASE+'/fixtures.json')},producer_sha256=H(__file__),oracle_producer_sha256=H(BASE+'/native.py'),executable={'path':a.exe,'sha256':H(a.exe)},objects={a.object:H(a.object)},format={'version':subprocess.check_output(['uc-library/.venv/bin/clang-format','--version'],text=True).strip(),'sources':{x:H(x) for x in paths[:3]}},proposed_readiness={'canonical_binding_pending':True,'ready':[],'pending':records},limitations=uncertainties+['Original Core normal-path constructor/vector boundaries modeled using actual source-provider observations; no Core binary recovery. Original exception/EH, secondary interfaces, destructor/layout/ARM ABI and full application behavior unproven. Unbound app exceptions are explicit portable adaptation.'],observations=output)
if a.integration!='local':proof['integration']={'path':a.integration,'sha256':H(a.integration)}
proof['archives']={}
for archive in supplement['pinned_providers']:
 assert H(archive['frozen_read_path'])==archive['sha256']
 proof['archives'][archive['frozen_read_path']]=H(archive['frozen_read_path'])
proof['provider_link_provenance']=supplement['provider_provenance']
proof['compatibility_supplement']={'path':str(supplement_path),'sha256':H(supplement_path),'plan':supplement['plan'],'plan_sha256':supplement['plan_sha256']}
proof['compatibility']={'text_api_cases':80,'stack_alias_cases':60,'commands':compat_commands,'outputs':compat_outputs,'executables':{text_exe:H(text_exe),stack_exe:H(stack_exe)},'fixtures':{text_fixture:H(text_fixture),stack_fixture:H(stack_fixture)},'scope':'Fresh portable regression against preserved historical ARM oracle fixtures; no claim of newly executing prior 140 original ARM cases. New actual native execution covers constructor ranges only.'}
proof['phase_accounting']={'proof_start_utc':phase_started,'proof_elapsed_seconds':time.monotonic()-phase_clock,'proof_end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Native/provider/format/symbol/portable proof; compiler timings recorded separately by maintained acceptance.'}
proof['native_provider_scope']='Native Core constructors/vector methods not executed; actual separate source-provider observations feed bounded native interfaces.'
proof['runtime']={'path':'/usr/lib/x86_64-linux-gnu/libstdc++.so.6.0.33','sha256':H('/usr/lib/x86_64-linux-gnu/libstdc++.so.6.0.33')}
pathlib.Path(a.out).write_text(json.dumps(proof,indent=2)+'\n')
