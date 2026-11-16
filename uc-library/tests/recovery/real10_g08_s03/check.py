"""Exact task replay; supplied canonical object/executable never fall back to scratch."""
from pathlib import Path
import argparse,subprocess,hashlib,json,datetime,time,os,importlib.util
R=Path(__file__).resolve().parents[4];C=Path('/home/rs/projects/opencs/ai-line-analysis');OUT=R/'temp/recovery-work/real10_g08-phase06';OUT.mkdir(parents=True,exist_ok=True)
FLAGS=['-std=c++17','-UNDEBUG','-Wno-multichar','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework','-O0']
LIB=C/'temp/core-upstream/root-integration-01'
ARCHIVES=[LIB/'libpresonus_uc.a',LIB/'upstream-core/sdk/lib/libcorelib.a',LIB/'upstream-core/sdk/lib/libpresonus_core_allocator.a',LIB/'private-glibc29-provider/libpresonus_private_glibc29.a']
HEADERS=['uc-library/include/presonus/panel/AlertBook.hpp','uc-library/include/presonus/panel/FrontPanelComponent.hpp']
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv):
 start=time.monotonic();p=subprocess.run(list(map(str,argv)),cwd=R,env={**os.environ,'TMPDIR':str(OUT)},capture_output=True,text=True);row={'argv':list(map(str,argv)),'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'seconds':time.monotonic()-start,'returncode':p.returncode,'output':p.stdout+p.stderr};print(json.dumps(row),flush=True)
 with (OUT/'COMMANDS.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
 return p.stdout
def main(task='real10_g08_s03'):
 parser=argparse.ArgumentParser();parser.add_argument('mode',nargs='?',default='replay');parser.add_argument('--exe',type=Path);parser.add_argument('--object',type=Path);parser.add_argument('--integration',type=Path);parser.add_argument('--out',type=Path);a=parser.parse_args()
 slot=task[-3:];fader=slot=='s04';test=R/f'uc-library/tests/recovery/{task}';fixture=test/'fixtures.json'
 sources=['uc-library/src/Presonus/Panel/FrontPanelComponent.cpp','uc-library/src/Presonus/Panel/FrontPanelLifecycle.cpp','uc-library/src/Presonus/Panel/PanelComponent.cpp','uc-library/src/Presonus/Panel/PanelComponentLifecycle.cpp','uc-library/tests/recovery/real10_g08_s04/Replay.cpp'] if fader else ['uc-library/src/Presonus/Panel/AlertBook.cpp','uc-library/tests/recovery/real10_g08_s03/Replay.cpp']
 exe=OUT/('fader-replay' if fader else 'alert-replay');obj=OUT/('fader0.o' if fader else 'alert0.o')
 if a.mode=='format':
  run([R/'uc-library/.venv/bin/clang-format','--version']);run([R/'uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*([sources[0],sources[-1]]),HEADERS[1 if fader else 0]]);return
 if a.mode=='compile':
  objects=[]
  for i,s in enumerate(sources):
   o=OUT/f'{"fader" if fader else "alert"}{i}.o';objects.append(o);run(['/usr/bin/c++',*FLAGS,*(['-fno-rtti'] if not fader and s==sources[-1] else []),'-MMD','-MF',str(o)+'.d','-c',s,'-o',o])
  run(['/usr/bin/c++',*objects,'-Wl,--start-group',*ARCHIVES,'-Wl,--end-group','-Wl,--gc-sections',*(['-Wl,--wrap=clock_gettime'] if not fader else []),'-lpthread','-ldl','-lssl','-lcrypto','/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lm','-o',exe]);return
 if a.mode=='native':
  path=R/('uc-library/tests/recovery/real10_g08_s04/native.py' if fader else 'uc-library/tests/recovery/real10_g08_s03/native.py');spec=importlib.util.spec_from_file_location('oracle',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);d=module.generate(task);fixture.parent.mkdir(parents=True,exist_ok=True);fixture.write_text(json.dumps(d,indent=2)+'\n');print('native cases',len(d['cases']));return
 if a.exe is not None or a.object is not None:
  assert a.exe is not None and a.object is not None,'Canonical mode requires both supplied executable and production object'
  exe=a.exe;obj=a.object
 d=json.loads(fixture.read_text());assert d['task']==task
 symbols=run(['nm','--defined-only',obj]);assert d['range']['mangled'] in {line.split()[-1] for line in symbols.splitlines() if line.split()}
 if a.mode=='symbols':return
 for c in d['cases']:
  argv=[exe,str(c['has36']),str(c['has38']),*[f'{x:x}' for x in c['bits']]] if fader else [exe,'deactivate' if slot=='s02' else 'setup',str(c['selection']),str(c['duplicate']),str(c['shape']),str(c['nanoseconds']),str(c['mode'])]
  output=run(argv)
  if slot=='s02':assert output.startswith(c['calls'][0][1]),'DebugPrint output differs from original literal'
  observed=json.loads(output.strip().splitlines()[-1]);assert observed==c['expected'],(task,c,observed)
 src={str(Path(s).relative_to('uc-library')):digest(R/s) for s in [*sources[:-1],HEADERS[1 if fader else 0]]}
 entry={'original_elf_sha256':d['range']['original_elf_sha256'],'mangled':d['range']['mangled'],'sources':src,'cpp_compiled':True,'mangling_namespace_checked':True,'portable_ready':False,'declaration_uncertainties':['Original ordinary return declaration, full inheritance and layout remain unresolved; real pinned source-port providers used.'],'validation_domain':d['domain']}
 proof={'version':1,'task':task,'success':True,'functions':[dict(entry,success=True,domain=d['domain'],native_cases=len(d['cases']),cpp_cases=len(d['cases']))],'proposed_readiness':{'ready':[],'pending':[entry]},'repository_sources':{p:digest(R/p) for p in ['third_party/ccl-framework/core/portable/corecomponent.cpp','third_party/ccl-framework/core/portable/coreparams.cpp','third_party/ccl-framework/core/public/corevector.h','third_party/ccl-framework/core/system/coretime.h','third_party/ccl-framework/core/platform/shared/posix/coretime.posix.h']},'executable_sha256':digest(exe),'object_sha256':digest(obj),'fixture_sha256':digest(fixture),'formatter_version':run([R/'uc-library/.venv/bin/clang-format','--version']).strip()}
 if a.integration:assert a.integration.is_file();proof['integration_sha256']=digest(a.integration)
 if a.out:a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(proof,indent=2)+'\n')
 print(json.dumps({'task':task,'success':True,'cases':len(d['cases'])}))
if __name__=='__main__':main()
