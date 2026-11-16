"""Deterministic supplied-executable/object replay, with explicit task selector."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,os,datetime,time
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent
CANON=Path('/home/rs/projects/opencs/ai-line-analysis')
OUT=R/'temp/recovery-work/real10_g08-local';OUT.mkdir(parents=True,exist_ok=True)
PY=str(R/'uc-library/.venv/bin/python')
SOURCES=['uc-library/src/Presonus/Panel/Fat24FrontPanelComponent.cpp','uc-library/src/Presonus/Panel/RogueFrontPanelComponent.cpp','uc-library/src/Presonus/Panel/FrontPanelLifecycle.cpp','uc-library/src/Presonus/Panel/PanelComponent.cpp','uc-library/src/Presonus/Panel/PanelComponentLifecycle.cpp','uc-library/tests/recovery/real10_g08_s07/Replay.cpp']
HEADERS=['uc-library/include/presonus/panel/Fat24FrontPanelComponent.hpp','uc-library/include/presonus/panel/RogueFrontPanelComponent.hpp','uc-library/include/presonus/panel/FrontPanelComponent.hpp']
FLAGS=['-std=c++17','-UNDEBUG','-Wno-multichar','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework','-O0']
LIB=CANON/'temp/core-upstream/root-integration-01'
ARCHIVES=[LIB/'libpresonus_uc.a',LIB/'upstream-core/sdk/lib/libcorelib.a',LIB/'upstream-core/sdk/lib/libpresonus_core_allocator.a',LIB/'private-glibc29-provider/libpresonus_private_glibc29.a']
EXE=OUT/'replay'
def run(argv):
 start=time.monotonic();p=subprocess.run(list(map(str,argv)),cwd=R,env={**os.environ,'TMPDIR':str(OUT)},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 print(json.dumps({'argv':list(map(str,argv)),'seconds':time.monotonic()-start,'status':p.returncode,'output':p.stdout}),flush=True)
 if p.returncode:raise RuntimeError(p.stdout)
 return p.stdout
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def obj(task):return OUT/('source1.o' if task.endswith('s09') else 'source0.o')
def main(task='real10_g08_s07'):
 parser=argparse.ArgumentParser();parser.add_argument('mode',nargs='?',default='replay');parser.add_argument('--exe',type=Path);parser.add_argument('--object',type=Path);parser.add_argument('--integration',type=Path);parser.add_argument('--out',type=Path);a=parser.parse_args()
 fixture=R/f'uc-library/tests/recovery/{task}/fixtures.json'
 if a.mode=='format':
  run([R/'uc-library/.venv/bin/clang-format','--version']);run([R/'uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*SOURCES[:3],SOURCES[-1],*HEADERS]);return
 if a.mode=='compile':
  objects=[]
  for i,s in enumerate(SOURCES):
   o=OUT/f'source{i}.o';objects.append(o);run(['/usr/bin/c++',*FLAGS,'-MMD','-MF',str(o)+'.d','-c',s,'-o',o])
  run(['/usr/bin/c++',*objects,'-Wl,--start-group',*ARCHIVES,'-Wl,--end-group','-Wl,--gc-sections','-Wl,--wrap=_Znwm','-Wl,--wrap=_ZdlPv','-Wl,--wrap=_ZdlPvm','-Wl,--wrap=core_malloc','-Wl,--wrap=core_realloc','-Wl,--wrap=core_free','-lpthread','-ldl','-lssl','-lcrypto','/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lm','-o',EXE]);return
 req=json.loads((CANON/'temp/recovery-work/reconstruction10x10-20261116/prepared-main/packets'/task/'request.json').read_text());target=req['targets'][0]
 if a.mode=='native':
  import native
  d=native.generate(task,a.exe or EXE);fixture.write_text(json.dumps(d,indent=2)+'\n');print('native fixture cases',len(d['cases']));return
 binary=a.exe or EXE;objectfile=a.object or obj(task)
 symbols=run(['nm','--defined-only',objectfile]);assert target['mangled'] in {x.split()[-1] for x in symbols.splitlines() if x.split()}
 if a.mode=='symbols':return
 d=json.loads(fixture.read_text());assert d['task']==task and d['range']['mangled']==target['mangled']
 for c in d['cases']:
  observed=json.loads(run([binary,c['kind'],c['variant'],str(c['populated'])]));assert observed==c['expected'],(observed,c)
 proof={'task':task,'success':True,'functions':[{'original_elf_sha256':target['original_elf_sha256'],'mangled':target['mangled'],'domain':d['domain'],'native_cases':len(d['cases']),'cpp_cases':len(d['cases']),'success':True}], 'binary_sha256':digest(binary),'object_sha256':digest(objectfile),'fixture_sha256':digest(fixture),'integration':str(a.integration) if a.integration else None,'format_version':run([R/'uc-library/.venv/bin/clang-format','--version']).strip()}
 sources={str(Path(x).relative_to('uc-library')):digest(R/x) for x in SOURCES[:3]+HEADERS}
 proof['proposed_readiness']={'ready':[],'pending':[{'original_elf_sha256':target['original_elf_sha256'],'mangled':target['mangled'],'sources':sources,'cpp_compiled':True,'mangling_namespace_checked':True,'portable_ready':False,'declaration_uncertainties':['Original inheritance, class layout and native multiple-interface declarations unresolved; portable class uses real FrontPanel base.'],'validation_domain':d['domain']}]}
 proof['repository_sources']={x:digest(R/x) for x in ['third_party/ccl-framework/core/portable/corecomponent.cpp','third_party/ccl-framework/core/portable/coreattributes.cpp','third_party/ccl-framework/core/public/corevector.h','third_party/ccl-framework/core/public/coreallocator.h']}
 if a.integration:
  assert a.integration.is_file();proof['integration_sha256']=digest(a.integration)
 if a.out:a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(proof,indent=2)+'\n')
 print(json.dumps(proof))
if __name__=='__main__':main()
