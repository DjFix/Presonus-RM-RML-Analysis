"""Current local Linux checks, each with separately retained actual command logs."""
import argparse,importlib.util,json,subprocess,sys,os
from pathlib import Path
TEST=Path(__file__).resolve().parent;os.chdir(TEST.parents[3]);BUILD=Path('temp/recovery-work/page-book-local01')
OWN=['Element','OffscreenElement','FillElement','StaticElement','Page','Book']
SOURCES=[Path('uc-library/src/Presonus/Panel')/(n+'.cpp') for n in OWN]
HEADERS=[Path('uc-library/include/presonus/panel')/(n+'.hpp') for n in OWN]
LINK=['FieldElement','TextEntryElement','LCDManager','KeyInputProvider','BitmapCopy','BitmapFlush','BitmapLifecycle','BitmapText','FontMidData','TinyFontMetrics']
CORE=Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a')
FLAGS=['g++','-std=c++17','-O2','-fno-sized-deallocation','-Ulinux','-Wno-multichar','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework']
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['format','compile','symbols','replay']);p.add_argument('--exe',type=Path);p.add_argument('--task-id');a=p.parse_args();BUILD.mkdir(parents=True,exist_ok=True);commands=[]
 def call(argv):
  argv=list(map(str,argv));r=subprocess.run(argv,text=True,capture_output=True);commands.append(dict(argv=argv,exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr));(BUILD/(a.mode+'.json')).write_text(json.dumps(commands,indent=2)+'\n');assert r.returncode==0,(r.stdout,r.stderr);return r.stdout
 if a.mode=='format':
  print(call(['uc-library/.venv/bin/clang-format','--version']));call(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*HEADERS,*SOURCES,TEST/'Replay.cpp'])
 elif a.mode=='compile':
  objects=[]
  for source in [*SOURCES,*[Path('uc-library/src/Presonus/Panel')/(n+'.cpp') for n in LINK],Path('uc-library/src/surface_panel/BitmapDrawing.cpp'),TEST/'Replay.cpp']:
   obj=BUILD/(source.stem+'.o');call([*FLAGS,'-MMD','-c',source,'-o',obj]);objects.append(obj)
  call(['g++',*objects,CORE,CORE.with_name('libpresonus_core_allocator.a'),CORE.with_name('libpresonus_zlib.a'),'-pthread','-Wl,--gc-sections','-o',BUILD/'Replay'])
 elif a.mode=='symbols':
  syms={line.split()[-1] for line in call(['nm','--defined-only',*[BUILD/(s.stem+'.o') for s in SOURCES]]).splitlines() if line.split()};fixture=json.loads((TEST/'fixtures.json').read_text());assert all(r['original']['mangled'] in syms for r in fixture);print('All35 ABI tasks /70 ELF original names compiled; no original ARM ABI claim.')
 else:
  sys.dont_write_bytecode=True;spec=importlib.util.spec_from_file_location('page_book_native',TEST/'native.py');native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native);target=None
  if a.task_id:target=next(name for name,task in native.TASKS.items() if task==a.task_id)
  actual=native.run(target);expected=json.loads((TEST/'fixtures.json').read_text());expected=[x for x in expected if not target or x['original']['mangled']==target];assert actual==expected
  exe=(a.exe or BUILD/'Replay').resolve();assert call([exe]).strip()=='actual-bitmap-fill-copy-static-cache-ok'
  count=0
  for row in actual:
   for case in row['cases']:
    result=json.loads(call([exe,row['original']['mangled'],case['variant']]));assert result==case['expected'],(row['original']['mangled'],row['original']['role'],case,result);count+=1
  print(f'{len(actual)} separately verified original ranges and {count} native/portable dispatch cases passed; actual offline BitmapDisplay/cache provider passed.')
if __name__=='__main__':main()
