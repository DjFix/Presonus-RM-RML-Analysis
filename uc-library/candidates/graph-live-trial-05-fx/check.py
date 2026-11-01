#!/usr/bin/env python3
import argparse,datetime,hashlib,json,os,pathlib,subprocess,time
ROOT=pathlib.Path(__file__).resolve().parents[3];BASE=pathlib.Path(__file__).parent
SCRATCH=ROOT/'temp/recovery-work/graph-live-trial-05/fx-worker';SCRATCH.mkdir(parents=True,exist_ok=True)
SOURCES=['uc-library/src/Presonus/Mixer/FXComponent.cpp','uc-library/include/presonus/mixer/FXComponent.hpp','uc-library/tests/graph_trial05_fx_tests.cpp']
def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def command(argv):
 start=stamp();t=time.monotonic();r=subprocess.run(argv,cwd=ROOT,env={**os.environ,'TMPDIR':str(SCRATCH)},text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 entry={'argv':argv,'started_utc':start,'ended_utc':stamp(),'duration_seconds':time.monotonic()-t,'returncode':r.returncode,'output':r.stdout}
 with (SCRATCH/'commands.jsonl').open('a') as f:f.write(json.dumps(entry)+'\n')
 print(r.stdout,end='');r.check_returncode();return r.stdout

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['format','compile','symbols','replay']);p.add_argument('--executable',default=str(SCRATCH/'fx-tests'));p.add_argument('--fixtures',default=str(BASE/'fixtures.json'));a=p.parse_args()
 if a.mode=='format':
  command(['uc-library/.venv/bin/clang-format','--version']);command(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*SOURCES])
 elif a.mode=='compile':
  b='temp/core-upstream/root-integration-01'
  command(['/usr/bin/c++','-std=c++17','-O2','-fno-rtti','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework',SOURCES[0],SOURCES[2],f'{b}/upstream-core/sdk/lib/libcorelib.a',f'{b}/upstream-core/sdk/lib/libpresonus_core_allocator.a','/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lssl','-lcrypto','temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so','-ldl',f'{b}/private-glibc29-provider/libpresonus_private_glibc29.a','-lm','-o',a.executable])
 elif a.mode=='symbols':
  output=command(['/usr/bin/nm','--defined-only',a.executable]);symbols={line.split()[-1] for line in output.splitlines() if line.split()}
  for i in range(1,6):
   req=json.loads((ROOT/f'temp/recovery-work/graph-live-trial-05/trial05_fx_{i}-packet/request.json').read_text());assert req['targets'][0]['mangled'] in symbols
  print('All five original encoded identities present; Linux ELF no decoration.')
 elif a.mode=='replay':
  doc=json.loads(pathlib.Path(a.fixtures).read_text());started=stamp();begin=time.monotonic();case_runs=[]
  for i,case in enumerate(doc['cases']):
   before=stamp();tick=time.monotonic()
   r=subprocess.run([a.executable,*map(str,case['args'])],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env={**os.environ,'LD_LIBRARY_PATH':str(ROOT/'temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu')})
   case_runs.append({'case':i,'argv':[a.executable,*map(str,case['args'])],'started_utc':before,'ended_utc':stamp(),'duration_seconds':time.monotonic()-tick,'returncode':r.returncode,'actual':r.stdout.strip()})
   assert r.returncode==0,(i,r.stderr)
   assert r.stdout.strip()==case['output'],(i,case['args'],r.stdout,case['output'])
  (SCRATCH/'replay-run.json').write_text(json.dumps({'started_utc':started,'ended_utc':stamp(),'duration_seconds':time.monotonic()-begin,'fixture_sha256':hashlib.sha256(pathlib.Path(a.fixtures).read_bytes()).hexdigest(),'executable_sha256':hashlib.sha256(pathlib.Path(a.executable).read_bytes()).hexdigest(),'cases':case_runs},indent=2)+'\n')
  print(f"PASS: {len(doc['cases'])} original fixture cases matched actual C++ result/state/app and parameter traces")
if __name__=='__main__':main()
