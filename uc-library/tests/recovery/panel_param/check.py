#!/usr/bin/env python3
"""Local Panel callback checks; canonical CTest may pass --executable."""
import argparse, hashlib, itertools, json, os, subprocess, time
from pathlib import Path
KIND=Path(__file__).parent.name.removeprefix('panel_')
BASE=Path('uc-library/tests/recovery/panel_'+KIND)
WORK=Path('temp/recovery-work/panel-callbacks/'+KIND)
EVIDENCE=Path('evidence/recovery/2026-11-12/panel-callbacks/'+KIND)
CANONICAL=Path('/home/rs/projects/opencs/ai-line-analysis')
BUILD=CANONICAL/'temp/core-upstream/root-integration-01'
SDK=BUILD/'upstream-core/sdk'
SOURCES=['uc-library/include/presonus/panel/PanelComponent.hpp','uc-library/src/Presonus/Panel/PanelComponent.cpp',str(BASE/'Replay.cpp')]
EXTRA=['uc-library/src/Presonus/Panel/PanelComponentLifecycle.cpp']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv):
 argv=list(map(str,argv));t=time.monotonic();r=subprocess.run(argv,text=True,capture_output=True)
 with (WORK/'commands.jsonl').open('a') as f:f.write(json.dumps(dict(argv=argv,elapsed=time.monotonic()-t,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))+'\n')
 if r.returncode:print(r.stdout,r.stderr);r.check_returncode()
 return r.stdout

def compile():
 flags=['/usr/bin/c++','-std=c++17','-O2','-fno-rtti','-fno-lto','-ffunction-sections','-fdata-sections','-UNDEBUG','-Ulinux','-pthread','-Iuc-library/include','-I'+str(SDK/'include/presonus-core-5')]
 objects=[]
 for path in [SOURCES[1],SOURCES[2]]+EXTRA:
  obj=WORK/(Path(path).stem+'.o');run(flags+['-c',path,'-o',obj]);objects.append(obj)
 run(flags+objects+['-Wl,--gc-sections','-Wl,--start-group',BUILD/'libpresonus_rm_components.a',SDK/'lib/libcorelib.a',SDK/'lib/libpresonus_core_allocator.a',BUILD/'private-glibc29-provider/libpresonus_private_glibc29.a','-Wl,--end-group','-pthread','-ldl','-lm','-lz','-o',WORK/'replay'])

def cases():
 if KIND=='idle':
  yield from itertools.product([0,1],[0,1,2,7,31],[0,1])
 else:
  for injected,storable,dirty,msg in itertools.product([0,1],[0,1],[0,1],[-2147483648,-1,0,1,2,3,4,5,2147483647]):
   yield injected,storable,dirty,msg,0,0
   if msg!=3:yield injected,storable,dirty,msg,0,1
  yield from (tuple(x)+(3,1,0) for x in itertools.product([0,1],[0,1],[0,1]))
def replay(executable,fixture):
 rows=[]
 for case in cases():
  # Independent expectation executes the actual pinned CCL method directly on
  # equivalent fresh state. The port path executes the reconstructed app method.
  expected=run([executable,'1',*map(str,case)]);actual=run([executable,'0',*map(str,case)]);assert actual==expected,(case,actual,expected)
  rows.append(dict(input=case,provider=expected,port=actual))
 assert Path(fixture).is_file(), 'Missing bound provider fixture: '+str(fixture)
 assert json.loads(Path(fixture).read_text())['cases']==json.loads(json.dumps(rows))
 (WORK/'provider-comparison.json').write_text(json.dumps(dict(cases=rows,scope='Actual pinned CCL provider and source-port executions; not original firmware Core behavior.'),indent=2)+'\n');print('Real CCL comparisons:',len(rows))
def main():
 p=argparse.ArgumentParser();p.add_argument('kind',choices=['format','compile','symbols','native','replay']);p.add_argument('--executable',default=str(WORK/'replay'));p.add_argument('--fixture',default=str(EVIDENCE/'provider-comparison.json'));a=p.parse_args();WORK.mkdir(parents=True,exist_ok=True);os.environ['TMPDIR']=str(WORK.resolve())
 if a.kind=='format':print(run(['uc-library/.venv/bin/clang-format','--version']));run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*SOURCES])
 elif a.kind=='compile':print(run(['/usr/bin/c++','--version']));compile()
 elif a.kind=='symbols':
  sym=run(['nm','--defined-only',WORK/'PanelComponent.o']);t=json.loads(Path('temp/recovery-work/production-20261112/prepared03/packets/rolling_next_panel_'+KIND+'/request.json').read_text())['targets'][0];assert t['mangled'] in [s.split()[-1] for s in sym.splitlines() if s.split()];print(t['mangled'])
 elif a.kind=='native':
  run(['uc-library/.venv/bin/python',BASE/'native.py','--elf',CANONICAL/'rootfs/RML16AI_Rack_13731/home/root/mixer','--out',WORK/'native'])
  if (EVIDENCE/'native.json').exists():assert sha(WORK/'native/native.json')==sha(EVIDENCE/'native.json')
 else:replay(a.executable,a.fixture)
if __name__=='__main__':main()
