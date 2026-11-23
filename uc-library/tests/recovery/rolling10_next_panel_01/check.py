import argparse,hashlib,json,pathlib,subprocess,datetime,os,sys
p=argparse.ArgumentParser();p.add_argument('--exe',required=True);p.add_argument('--object',required=True);p.add_argument('--integration',required=True);p.add_argument('--out',required=True);a=p.parse_args()
TASK=pathlib.Path(__file__).parent.name
BASE='uc-library/tests/recovery/'+TASK
H=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
subprocess.run(['uc-library/.venv/bin/python',BASE+'/native.py','--verify'],check=True)
req=json.loads(pathlib.Path('temp/recovery-work/rolling10x10-20261114/prepared06/packets',TASK,'request.json').read_text())
paths=['uc-library/include/presonus/panel/BeastFrontPanelComponent.hpp','uc-library/src/Presonus/Panel/BeastFrontPanelComponent.cpp',BASE+'/Replay.cpp']
subprocess.run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*paths],check=True)
fixture=json.loads(pathlib.Path(BASE+'/fixtures.json').read_text())
symbols=subprocess.check_output(['nm',a.object],text=True)
for target in req['targets']:assert target['mangled'] in symbols
from elftools.elf.elffile import ELFFile
with open(a.object,'rb') as object_file:
 elf=ELFFile(object_file); compiled={s.name:s for s in elf.get_section_by_name('.symtab').iter_symbols()}
 for payload in fixture['payloads'].values():
  symbol=compiled[payload['mangled']];assert symbol['st_info']['bind']=='STB_LOCAL' and symbol['st_size']==payload['size']
  section=elf.get_section(symbol['st_shndx']);start=symbol['st_value']-section['sh_addr'];data=section.data()[start:start+symbol['st_size']]
  assert hashlib.sha256(data).hexdigest()==payload['sha256']

output=subprocess.check_output([str(pathlib.Path(a.exe).resolve())],text=True)
rows=output.splitlines();assert len(rows)==len(fixture['cases'])
for got,case in zip(rows,fixture['cases']):
 tokens=list(map(int,got.split()))
 if case['group'] in [0,1,2]:
  expected=[case['count']]+fixture['payloads'][str(case['first'])]['words']+fixture['payloads'][str(case['second'])]['words']
 else:expected=[case['count'],1,1]
 assert tokens==expected

paths+=['uc-library/include/presonus/mixer/MixerComponentBase.hpp']
sources={x.removeprefix('uc-library/'):H(x) for x in paths+[BASE+'/native.py',BASE+'/check.py',BASE+'/fixtures.json']}
providers={x:H(x) for x in ['third_party/ccl-framework/core/portable/coreparams.h','third_party/ccl-framework/core/portable/coreparams.cpp','third_party/ccl-framework/core/portable/coreparaminfo.h','third_party/ccl-framework/core/public/corevector.h']}
domain='Valid output references; all three groups plus four default selectors, full six original data-symbol payloads checked word-for-word with symbol extents and offsets; default references/count unchanged.'
uncertainties=['Original ordinary method return declaration unencoded and unresolved.','Original class member declarations/layout and ARM ABI not established.']
records=[dict(original_elf_sha256=x['original_elf_sha256'],mangled=x['mangled'],original_address=x['address'],sources=sources,repository_sources=providers,domain=domain,portable_ready=False,declaration_uncertainties=uncertainties,cpp_compiled=True,mangling_namespace_checked=True,original_function_verified=False,hardware_verified=False) for x in req['targets']]
proof=dict(version=1,task_id=TASK,phase='local' if a.integration=='local' else 'canonical',utc_end=datetime.datetime.now(datetime.timezone.utc).isoformat(),session_id=os.getenv('CODEX_THREAD_ID'),sources=sources,repository_sources=providers,domain=domain,cpp_differential_passed=True,compiled_original_mangled_names_matched=True,mangling_namespace_checked=True,functions=[dict(r,cpp_differential_passed=True,range_verified=True,native_cases=len(fixture['cases'])) for r in records],fixture={'path':BASE+'/fixtures.json','sha256':H(BASE+'/fixtures.json')},producer_sha256=H(__file__),oracle_producer_sha256=H(BASE+'/native.py'),executable={'path':a.exe,'sha256':H(a.exe)},objects={a.object:H(a.object)},format={'version':subprocess.check_output(['uc-library/.venv/bin/clang-format','--version'],text=True).strip(),'sources':{x:H(x) for x in paths}},proposed_readiness={'canonical_binding_pending':True,'ready':[],'pending':records},limitations=uncertainties+['Original Core/libc bodies excluded; native external calls modeled. Hardware, overflow, concurrent mutation and unterminated names excluded.'],observations=output)
if a.integration!='local':proof['integration']={'path':a.integration,'sha256':H(a.integration)}
provider_root=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis')
provider_addendum=provider_root/'temp/recovery-work/rolling10x10-20261114/root-review/generation06/provider-link-proposal/PROVIDER_LINK_ADDENDUM.json'
provider_metadata=json.loads(provider_addendum.read_text())
sys.path.insert(0,str(provider_root/'uc-library/tools/recovery'))
from pinned_codec_replay_binding import validate_archives
historical_archives={archive['path']:archive['sha256'] for archive in provider_metadata['archives']}
archive_binding=validate_archives(provider_root,a.exe,a.integration,historical_archives)
proof['archives']=archive_binding['archives']
proof['historical_provider_archives']=archive_binding['historical']
proof['provider_archive_transition']=archive_binding['transition']
proof['provider_link_provenance']={'path':str(provider_addendum),'sha256':H(provider_addendum),'upstream':provider_metadata['upstream'],'provider_proof':provider_metadata['provider_proof']}
pathlib.Path(a.out).write_text(json.dumps(proof,indent=2)+'\n')
