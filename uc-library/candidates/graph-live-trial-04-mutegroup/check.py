import subprocess,sys,json
from pathlib import Path
base=Path('uc-library/candidates/graph-live-trial-04-mutegroup');scratch=Path('temp/recovery-work/graph-live-trial-04/mutegroup-worker');scratch.mkdir(parents=True,exist_ok=True)
sources=['uc-library/src/Presonus/MuteGroupBase.cpp','uc-library/include/presonus/MuteGroupBase.hpp','uc-library/tests/graph_trial04_mutegroup_tests.cpp']
mode=sys.argv[1]
if mode=='format':cmd=['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror']+sources
elif mode=='compile':cmd=['c++','-std=c++17','-fno-rtti','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework',sources[0],sources[2],'temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','-lpthread','-ldl','-o',str(scratch/'replay')]
elif mode=='symbols':
 out=subprocess.check_output(['nm','--defined-only',str(scratch/'replay')],text=True);names={line.split()[-1] for line in out.splitlines() if line.split()}
 for i in range(1,6):
  p=json.loads(Path(f'temp/recovery-work/graph-live-trial-04/trial04_mutegroup_{i}-packet/request.json').read_text());assert p['targets'][0]['mangled'] in names
 print('all five original ELF names present; matching names do not establish returns/layout/ABI');sys.exit()
else:raise ValueError(mode)
subprocess.run(cmd,check=True)
