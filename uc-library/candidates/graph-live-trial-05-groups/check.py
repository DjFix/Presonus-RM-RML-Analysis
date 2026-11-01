#!/usr/bin/env python3
import argparse,hashlib,json,os,subprocess,time,datetime
from pathlib import Path
P=Path('uc-library/candidates/graph-live-trial-05-groups')
SCRATCH=Path('temp/recovery-work/graph-live-trial-05/groups-worker');SCRATCH.mkdir(parents=True,exist_ok=True)
SOURCES=['uc-library/src/Presonus/Surface/GroupsPageComponent.cpp','uc-library/include/presonus/surface/GroupsPageComponent.hpp','uc-library/tests/graph_trial05_groups_tests.cpp']
def cmd(argv):
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic()
 env=os.environ.copy();env['TMPDIR']=str(SCRATCH.resolve())
 p=subprocess.run(argv,text=True,capture_output=True,env=env)
 log={'argv':argv,'start_utc':start,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'duration_seconds':time.monotonic()-t,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
 with (SCRATCH/'commands.jsonl').open('a') as f:f.write(json.dumps(log)+'\n')
 if p.returncode:raise RuntimeError(json.dumps(log))
 return p.stdout

def main():
 parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['format','compile','symbols','replay']);parser.add_argument('--executable',default=str(SCRATCH/'replay'));parser.add_argument('--fixtures',default=str(P/'fixtures.json'));a=parser.parse_args()
 if a.mode=='format':print(cmd(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror']+SOURCES))
 elif a.mode=='compile':
  cmd(['/usr/bin/c++','-std=c++17','-fno-rtti','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework','-DCORE_PLATFORM_LINUX=1','-c',SOURCES[0],'-o',str(SCRATCH/'groups.o')])
  cmd(['/usr/bin/c++','-std=c++17','-fno-rtti','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework','-DCORE_PLATFORM_LINUX=1',SOURCES[2],str(SCRATCH/'groups.o'),'temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a','-lpthread','-ldl','-lm','-o',a.executable])
 elif a.mode=='symbols':
  nm=cmd(['/usr/bin/nm','--defined-only',str(SCRATCH/'groups.o')]);missing=[]
  for i in range(1,6):
   c=json.loads(Path(f'temp/recovery-work/graph-live-trial-05/trial05_groups_{i}-packet/context.json').read_text());name=c['work_binding']['covered_occurrences'][0]['original_mangled']
   if name not in nm.split():missing.append(name)
  assert not missing,missing
  print(nm)
 elif a.mode=='replay':
  data=json.loads(Path(a.fixtures).read_text());cases=data['cases']
  start=datetime.datetime.now(datetime.timezone.utc).isoformat();clock=time.monotonic()
  p=subprocess.run([str(Path(a.executable).resolve())],input=''.join(' '.join(map(str,c['input']))+'\n' for c in cases),text=True,capture_output=True)
  with (SCRATCH/'commands.jsonl').open('a') as log:log.write(json.dumps({'argv':[str(Path(a.executable).resolve())],'fixture_path':a.fixtures,'fixture_sha256':hashlib.sha256(Path(a.fixtures).read_bytes()).hexdigest(),'start_utc':start,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'duration_seconds':time.monotonic()-clock,'returncode':p.returncode,'stdout_sha256':hashlib.sha256(p.stdout.encode()).hexdigest(),'stderr':p.stderr})+'\n')
  assert p.returncode==0,(p.returncode,p.stderr)
  lines=p.stdout.splitlines();assert len(lines)==len(cases),(len(lines),len(cases))
  for n,(line,c) in enumerate(zip(lines,cases)):
   actual=list(map(int,line.split()));assert actual==c['output'],(n,c,actual)
  result={'case_count':len(cases),'per_target':{str(i):sum(c['input'][0]==i for c in cases) for i in range(1,6)},'executable':a.executable,'executable_sha256':hashlib.sha256(Path(a.executable).read_bytes()).hexdigest(),'fixture_sha256':hashlib.sha256(Path(a.fixtures).read_bytes()).hexdigest(),'scope':'direct actual ARM fixture comparison of return/state/external traces; no callback mutation'}
  (SCRATCH/'replay-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
