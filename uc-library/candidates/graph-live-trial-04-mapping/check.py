#!/usr/bin/env python3
import argparse,json,pathlib,subprocess,sys
BASE=pathlib.Path('uc-library/candidates/graph-live-trial-04-mapping')
SOURCES=['uc-library/include/presonus/MappingTable.hpp','uc-library/src/Presonus/MappingTable.cpp','uc-library/tests/graph_trial04_mapping_tests.cpp']
EXE='temp/recovery-work/graph-live-trial-04/mapping-worker/replay'
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['format','compile','symbols','replay']);p.add_argument('--executable',default=EXE);a=p.parse_args()
 if a.mode=='format': subprocess.run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*SOURCES],check=True)
 elif a.mode=='compile': subprocess.run(['/usr/bin/c++','-std=c++17','-DNDEBUG','-Ulinux','-Iuc-library/include','-Ithird_party/ccl-framework',*SOURCES[1:],'-o',EXE],check=True)
 elif a.mode=='symbols':
  out=subprocess.check_output(['nm','--defined-only',a.executable],text=True);names={l.split()[-1] for l in out.splitlines() if l.split()}
  for row in json.loads((BASE/'scope.json').read_text()): assert row['original']['mangled'] in names,row
  print('5 original mangled identities present; no ABI assertion')
 else:
  fixtures=json.loads((BASE/'native-boundary-fixtures.json').read_text())['cases'];out=subprocess.check_output([a.executable],text=True).splitlines();assert len(out)==len(fixtures)==20
  for line,f in zip(out,fixtures):
   task,found,flag,result,call,callflag,seen=line.split();assert task==f['task_id'].split('_')[-1];assert int(found)==bool(f['found']);assert int(flag)==f['flag']
   if task=='1': assert int(result)==bool(f['r0_observed']);assert call=='none' and seen=='0'
   else:
    mutations=[x for x in f['trace'] if x['call'].startswith('set')]
    assert call==(mutations[0]['call'] if mutations else 'none')
    assert int(seen)==bool(mutations)
    assert int(callflag)==(mutations[0]['flag'] if mutations and mutations[0]['flag'] is not None else -1)
  print('20 C++ versus original ARM boundary cases passed; dependency implementations excluded')
if __name__=='__main__':main()
