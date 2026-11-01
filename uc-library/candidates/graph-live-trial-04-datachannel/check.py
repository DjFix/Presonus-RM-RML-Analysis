"""Read-only-input acceptance checks; scratch compilation is explicitly isolated."""
import json,subprocess,sys,time,datetime
from pathlib import Path
BASE=Path('uc-library/candidates/graph-live-trial-04-datachannel')
SCRATCH=Path('temp/recovery-work/graph-live-trial-04/datachannel-worker')
SOURCES=['uc-library/include/presonus/uc/DataChannel.hpp','uc-library/src/Presonus/UC/DataChannel.cpp','uc-library/tests/graph_trial04_datachannel_tests.cpp']
EXE=str(SCRATCH/'replay')
def run(argv):
 t=time.monotonic(); p=subprocess.run(argv,text=True,capture_output=True); record={'argv':argv,'started':datetime.datetime.now(datetime.timezone.utc).isoformat(),'duration_seconds':time.monotonic()-t,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}; print(json.dumps(record));
 if p.returncode: raise SystemExit(p.returncode)
 return p.stdout
mode=sys.argv[1]
if mode=='format': run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*SOURCES])
elif mode=='compile': run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-Iuc-library/include','-isystem','temp/core-upstream/root-integration-01/upstream-core/sdk/include/presonus-core-5',SOURCES[1],SOURCES[2],'-o',EXE,'temp/core-upstream/root-integration-01/libpresonus_uc.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a','/usr/lib/x86_64-linux-gnu/libpng16.so.16','/usr/lib/x86_64-linux-gnu/libz.so.1','/usr/lib/x86_64-linux-gnu/libssl.so','/usr/lib/x86_64-linux-gnu/libcrypto.so','temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so','-ldl','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a','-lm','-pthread','-Wl,-rpath,'+str(Path('temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu').resolve())])
elif mode=='symbols':
 out=run(['nm','--defined-only',EXE]); names={line.split()[-1] for line in out.splitlines() if line.split()}
 for i in range(1,6):
  request=json.loads(Path(f'temp/recovery-work/graph-live-trial-04/trial04_datachannel_{i}-packet/request.json').read_text())
  for original in request['originals']: assert original['original']['mangled'] in names
elif mode=='replay': run([EXE,str(BASE/'fixtures.txt')])
else: raise ValueError(mode)
