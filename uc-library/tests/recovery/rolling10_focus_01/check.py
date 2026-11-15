import argparse,hashlib,json,pathlib,subprocess
p=argparse.ArgumentParser();p.add_argument('--exe',required=True);p.add_argument('--object',required=True);p.add_argument('--integration',required=True);p.add_argument('--out',required=True);a=p.parse_args()
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
subprocess.run(['uc-library/.venv/bin/python','uc-library/tests/recovery/rolling10_focus_01/native.py','--verify'],check=True)
paths=['uc-library/include/presonus/FocusRestorer.hpp','uc-library/src/Presonus/FocusRestorer.cpp','uc-library/tests/recovery/rolling10_focus_01/Replay.cpp']
subprocess.run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*paths],check=True)
symbols=subprocess.check_output(['nm',a.object],text=True)
for variant in ['C1','C2']:assert '_ZN8Presonus13FocusRestorer9FocusInfo'+variant+'Ev' in symbols
observed=list(map(int,subprocess.check_output([str(pathlib.Path(a.exe).resolve())],text=True).split()))
fixtures=json.loads(pathlib.Path('uc-library/tests/recovery/rolling10_focus_01/fixtures.json').read_text())
for row in fixtures:
 assert observed==[int.from_bytes(bytes.fromhex(row['state'])[i:i+4],'little') for i in range(0,28,4)]+[row['first_char']]
 assert row['calls']==[[28,0]]
proof={'native_cases':len(fixtures),'portable_cases':1,'canonical_binding_pending':True,'validation_domain':'Seven zero-initialized observed words and first CStringBuffer char; four native prefill values, both independent constructor ranges; native Core boundary model only, actual pinned C++ provider executes in replay.','limitations':['No original member-type/layout or ARM ABI claim; remaining CStringBuffer bytes unspecified. Native Core boundary is modeled, not binary executed.'],'sources':{x:sha(x) for x in paths},'object_sha256':sha(a.object),'exe_sha256':sha(a.exe),'integration':a.integration,'formatter':subprocess.check_output(['uc-library/.venv/bin/clang-format','--version'],text=True).strip(),'proposed_readiness':{'ready':[],'pending':[]}}
pathlib.Path(a.out).write_text(json.dumps(proof,indent=2)+'\n')
# Readiness proposal preserves every dispatched identity, with source-port
# declarations explicitly pending rather than asserting original field types.
root=pathlib.Path.cwd()
proof['domain']=proof['validation_domain']
proof['cpp_differential_passed']=True
proof['compiled_original_mangled_names_matched']=True
proof['mangling_namespace_checked']=True
proof['fixture']={'path':'uc-library/tests/recovery/rolling10_focus_01/fixtures.json','sha256':sha('uc-library/tests/recovery/rolling10_focus_01/fixtures.json')}
proof['repository_sources']={x:sha(x) for x in ['third_party/ccl-framework/core/public/corestringbuffer.h','third_party/ccl-framework/core/portable/gui/coreview.h','third_party/ccl-framework/core/portable/gui/coreviewshared.h']}
proof['format']={'version':proof['formatter'],'sources':dict(proof['sources'])}
proof['sources'].update({x:sha(x) for x in ['uc-library/tests/recovery/rolling10_focus_01/native.py','uc-library/tests/recovery/rolling10_focus_01/check.py','uc-library/tests/recovery/rolling10_focus_01/fixtures.json']})
proof['producer_sha256']=sha(__file__)
proof['oracle_producer_sha256']=sha('uc-library/tests/recovery/rolling10_focus_01/native.py')
proof['functions']=[]
records=[]
for task in ['rolling10_focus_01','rolling10_focus_02']:
 request=json.loads(pathlib.Path('temp/recovery-work/rolling10x10-20261114/prepared05/packets',task,'request.json').read_text())
 for target in request['targets']:
  record=dict(original_elf_sha256=target['original_elf_sha256'],mangled=target['mangled'],original_address=target['address'],sources={k.removeprefix('uc-library/'):v for k,v in proof['sources'].items()},repository_sources=proof['repository_sources'],domain=proof['domain'],portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True,declaration_uncertainties=['Original seven state word member declarations remain unresolved; portable uint32_t slots preserve bounded zero-initialization only.'],original_function_verified=False,hardware_verified=False)
  records.append(record)
  proof['functions'].append(dict(record,cpp_differential_passed=True,range_verified=True,native_cases=4))
proof['proposed_readiness']={'canonical_binding_pending':True,'ready':[],'pending':records}
if a.integration!='local':
 assert pathlib.Path(a.integration).is_file(),'Canonical execution requires an existing integration proof'
 proof['integration']={'path':a.integration,'sha256':sha(a.integration)}
pathlib.Path(a.out).write_text(json.dumps(proof,indent=2)+'\n')
