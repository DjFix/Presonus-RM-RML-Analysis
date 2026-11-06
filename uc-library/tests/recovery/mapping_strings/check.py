"""Read-only checks; executable accepts CLI cases from original ARM fixture."""
import argparse, json, subprocess, sys, os
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'uc-library/tools/recovery/accept_worker.py').exists())
SOURCES=['uc-library/src/Presonus/ColorMapping.cpp','uc-library/src/Presonus/MappingTablePageName.cpp','uc-library/tests/recovery/MappingStringsReplay.cpp']
HEADERS=['uc-library/include/presonus/ColorMapping.hpp','uc-library/include/presonus/MappingTable.hpp']
SCRATCH='temp/recovery-work/mapping154-validation'
EXE=SCRATCH+'/replay'
def run(argv):
 (ROOT/SCRATCH).mkdir(parents=True,exist_ok=True)
 subprocess.run(argv,cwd=ROOT,check=True,env=dict(os.environ,TMPDIR=str(ROOT/SCRATCH)))
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['format','compile','symbols','replay','native','regression']);p.add_argument('--executable',default=EXE);p.add_argument('--fixtures',default='uc-library/tests/recovery/mapping_strings/fixtures.json');a=p.parse_args()
 if a.mode=='format':run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*SOURCES,*HEADERS])
 elif a.mode=='compile':
  (ROOT/SCRATCH).mkdir(parents=True,exist_ok=True)
  run(['g++','-std=c++17','-O2','-Iuc-library/include','-Ithird_party/ccl-framework',*SOURCES,'-o',EXE])
 elif a.mode=='regression':
  run(['g++','-std=c++20','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework','uc-library/src/Presonus/MappingTable.cpp','uc-library/tests/graph_trial08_mappingtable_tests.cpp','temp/core-upstream/root-integration-01/libpresonus_uc.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a','-lpthread','-ldl','-lrt','-o',SCRATCH+'/mapping-regression'])
  run(['uc-library/.venv/bin/python','uc-library/tests/recovery/trial08/mappingtable/replay.py','--executable',SCRATCH+'/mapping-regression','--fixtures','uc-library/tests/recovery/trial08/mappingtable/fixtures.json'])
 elif a.mode=='symbols':
  out=subprocess.check_output(['nm','--defined-only',EXE],cwd=ROOT,text=True)
  for symbol in ['_ZN8Presonus12ColorMapping14enumFromStringERKN4Core11ConstStringE12RGBLedColors','_ZN8Presonus12MappingTable15extractPageNameEPKcRN4Core13CStringBufferILi32EEES6_']:assert symbol in out,symbol
  print('2 exact original symbols matched')
 elif a.mode=='native':
  import native
  assert native.fixture()==json.loads((ROOT/a.fixtures).read_text());print('Original ARM fixtures reproduced')
 else:
  fixture=json.loads((ROOT/a.fixtures).read_text());cases=fixture['cases'];sequence=[];expected_sequence=[]
  for c in cases:
   args=['color',c['input'],str(c['fallback'])] if c['kind']=='color' else ['null' if c['input'] is None else 'page',c['input'] or '']
   lines=subprocess.check_output([str((ROOT/a.executable).resolve()),*args],text=True).splitlines()
   expected=[str(c['result'])] if c['kind']=='color' else [str(c['result']),c['page'],c['parameter'],c['page_bytes'],c['parameter_bytes']]
   assert lines==expected,(c,lines,expected)
   sequence.extend(args);expected_sequence.extend(expected)
  assert subprocess.check_output([str((ROOT/a.executable).resolve()),*sequence],text=True).splitlines()==expected_sequence
  for item in fixture['palette']['items']:
   lines=subprocess.check_output([str((ROOT/a.executable).resolve()),'palette',str(item['color'])],text=True).splitlines()
   assert lines==[str(item['enumeration']),item['name']],(item,lines)
  print(f'{len(cases)} original ARM vs pinned-provider C++ cases passed')
if __name__=='__main__':main()
