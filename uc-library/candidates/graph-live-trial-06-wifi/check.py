#!/usr/bin/env python3
import argparse,subprocess,json,hashlib,datetime,time
from pathlib import Path
BASE=Path('uc-library/candidates/graph-live-trial-06-wifi')
SCRATCH=Path('temp/recovery-work/graph-live-trial-06/wifi-worker')
SOURCES=['uc-library/src/Presonus/Surface/WifiSetupComponent.cpp','uc-library/include/presonus/surface/WifiSetupComponent.hpp','uc-library/tests/graph_trial06_wifi_tests.cpp']
EXE=SCRATCH/'graph_trial06_wifi_tests'
FLAGS=['-std=c++20','-O2','-DNDEBUG=1','-DCORE_USE_OPENSSL=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-fno-rtti','-pthread','-Ulinux','-Wl,--wrap=_ZN8Presonus10DelayTimer11beginActionEf','-Wl,--wrap=_ZN8Presonus10DelayTimer9endActionEv','-Iuc-library/include','-isystem','third_party/ccl-framework']
def execute(argv,display=True):
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic();p=subprocess.run(argv,text=True,capture_output=True)
 log={'argv':argv,'start':start,'duration_seconds':time.monotonic()-t,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
 with (SCRATCH/'commands.jsonl').open('a') as f:f.write(json.dumps(log)+'\n')
 
 if display:print(p.stdout,end='');print(p.stderr,end='')
 p.check_returncode();return p.stdout
p=argparse.ArgumentParser();p.add_argument('mode',choices=['format','compile','symbols','replay']);p.add_argument('--executable');p.add_argument('--fixtures',default=str(BASE/'fixtures.json'));a=p.parse_args()
if a.mode=='format':
 execute(['uc-library/.venv/bin/clang-format','--version']);execute(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*SOURCES])
elif a.mode=='compile':
 build='temp/core-upstream/root-integration-01/'
 execute(['/usr/bin/c++',*FLAGS,SOURCES[0],SOURCES[2],'-o',str(EXE),build+'libpresonus_cs18_components.a',build+'upstream-core/sdk/lib/libcorelib.a',build+'upstream-core/sdk/lib/libpresonus_core_allocator.a','/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lssl','-lcrypto','temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so','-ldl',build+'private-glibc29-provider/libpresonus_private_glibc29.a','-lm'])
elif a.mode=='symbols':
 out=execute(['/usr/bin/nm','--defined-only',str(EXE)],display=False)
 for i in range(1,11):
  c=json.loads(Path(f'temp/recovery-work/graph-live-trial-06/trial06_wifi_{i}-packet/context.json').read_text());name=c['originals'][0]['original']['mangled'];assert any(line.split()[-1]==name for line in out.splitlines()),name
 print('all ten original mangled identities found; portable ELF x86-64 names only')
else:
 fixtures=json.loads(Path(a.fixtures).read_text())['cases'];exe=a.executable or str(EXE)
 replay_start=datetime.datetime.now(datetime.timezone.utc).isoformat();replay_t=time.monotonic();timings={}
 for i,c in enumerate(fixtures):
  case_t=time.monotonic();argv=[exe];p=subprocess.run(argv,input=' '.join(map(str,c['input']))+'\n',text=True,capture_output=True)
  entry=timings.setdefault(str(c['input'][0]),{'cases':0,'tool_seconds':0});entry['cases']+=1;entry['tool_seconds']+=time.monotonic()-case_t
  if p.returncode or p.stdout!=c['expected']:raise SystemExit(f'case {i} input {c["input"]}\nexpected {c["expected"]!r}\nactual {p.stdout!r}\nstderr {p.stderr}')
 (SCRATCH/'replay-proof.json').write_text(json.dumps({'utc':replay_start,'duration_seconds':time.monotonic()-replay_t,'by_target':timings,'argv':[exe],'executable_sha256':hashlib.sha256(Path(exe).read_bytes()).hexdigest(),'fixture_sha256':hashlib.sha256(Path(a.fixtures).read_bytes()).hexdigest()},indent=2)+'\n')
 print(f'PASS: {len(fixtures)} original ARM/C++ differential state and ordered trace cases')
