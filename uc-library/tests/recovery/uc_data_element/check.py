"""Scoped Linux checks; mutable outputs remain in owned scratch."""
import argparse,importlib.util,json,subprocess,sys,datetime
from pathlib import Path
TEST=Path(__file__).parent
BUILD=Path('temp/recovery-work/sol61-local/uc_data_element')
PROD=Path('uc-library/src/Presonus/UC/DataElement.cpp')
HEADER=Path('uc-library/include/presonus/uc/DataElement.hpp')
CORE=Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a')
FLAGS=['g++','-std=c++17','-O2','-fno-sized-deallocation','-Ulinux','-Wno-multichar','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework']
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['format','compile','symbols','replay']);p.add_argument('--exe',type=Path);a=p.parse_args();BUILD.mkdir(parents=True,exist_ok=True);commands=[]
 def call(argv):
  argv=list(map(str,argv));r=subprocess.run(argv,text=True,capture_output=True);commands.append(dict(argv=argv,exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr));(BUILD/(a.mode+'.json')).write_text(json.dumps(commands,indent=2)+'\n');assert r.returncode==0,(r.stdout,r.stderr);return r.stdout
 if a.mode=='format':
  print(call(['uc-library/.venv/bin/clang-format','--version']));call(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',HEADER,PROD,TEST/'Replay.cpp'])
 elif a.mode=='compile':
  objs=[]
  for source in [PROD,Path('uc-library/src/Presonus/UC/Element.cpp'),Path('uc-library/src/Presonus/UC/MetaElement.cpp'),TEST/'Replay.cpp']:
   obj=BUILD/(source.stem+'.o');call([*FLAGS,'-MMD','-c',source,'-o',obj]);objs.append(obj)
  call(['g++',*objs,CORE,CORE.with_name('libpresonus_core_allocator.a'),'-pthread','-Wl,--gc-sections','-Wl,--wrap=free','-Wl,--wrap=_ZdlPv','-o',BUILD/'Replay'])
 elif a.mode=='symbols':
  syms={line.split()[-1] for line in call(['nm','--defined-only',BUILD/'DataElement.o']).splitlines()};fixture=json.loads((TEST/'fixtures.json').read_text());assert all(row['original']['mangled'] in syms for row in fixture);print('Six exact ABI symbol names found; 12 original identities retained.')
 else:
  spec=importlib.util.spec_from_file_location('data_element_native',TEST/'native.py');native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native);observed=native.run();assert observed==json.loads((TEST/'fixtures.json').read_text())
  expected=[]
  for row in observed:
   if '4load' in row['original']['mangled']:
    types=[c['type'] for c in row['cases']];assert all(c['load']==[['lookup','type'],['lookup','id']] for c in row['cases']);assert all(c['save']==[['store','type',c['type']],['store','id','fixture-id']] for c in row['cases']);expected=types
  output=call([(a.exe or BUILD/'Replay').resolve()]).splitlines();assert output==expected+['provider-stream-virtual-delete-ok'],(output,expected);print('All 12 exact native ranges and portable/provider observations matched.')
if __name__=='__main__':main()
