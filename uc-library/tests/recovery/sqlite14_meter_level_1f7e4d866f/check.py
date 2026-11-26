"""Hash-bound independent native and typed provider replay for MeterLevelControl."""
import argparse,hashlib,json,shlex,subprocess,sys
from pathlib import Path
import native
ROOT=Path(__file__).resolve().parents[4];TEST=Path(__file__).parent.relative_to(ROOT);SCRATCH=Path('temp/recovery-work/sqlite14_meter_level_whole_sol61');SOURCE=Path('uc-library/src/Presonus/Panel/MeterLevelControl.cpp');HEADER=Path('uc-library/include/presonus/panel/meter_level_control.hpp');REPLAY=TEST/'Replay.cpp';FIXTURE=TEST/'fixtures.json'
FORMAT=['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',str(SOURCE),str(HEADER),str(REPLAY)]
SOURCES=[SOURCE,Path("uc-library/src/Presonus/Panel/protocol_comm.cpp"),Path("uc-library/src/Presonus/Panel/uart_protocol.cpp"),Path('uc-library/src/Presonus/Panel/control.cpp'),Path('uc-library/src/surface_panel/MeterControl.cpp'),Path('uc-library/src/surface_panel/DbTable.cpp'),Path('uc-library/src/Presonus/Panel/param_edit_handler.cpp'),Path('uc-library/src/Presonus/DICE/PacketClockGateway.cpp'),Path('uc-library/src/Presonus/Panel/LEDControlLifecycle.cpp'),Path('uc-library/src/surface_panel/LEDState.cpp'),REPLAY]
CORE=Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib');LIBS=[CORE/'libcorelib.a',CORE/'libpresonus_core_allocator.a']
EXE=SCRATCH/'replay'
def bind(p):return dict(path=str(p),sha256=native.sha(p))
def run(args,**kw):
 args=list(map(str,args));print(json.dumps(args),flush=True);return subprocess.run(args,check=True,text=True,capture_output=True,cwd=ROOT,**kw).stdout

def compile():
 SCRATCH.mkdir(parents=True,exist_ok=True);records=[];objects=[]
 for i,s in enumerate(SOURCES):
  o=SCRATCH/f'{i}.o';dep=o.with_suffix('.d');cmd=['/usr/bin/c++','-std=c++17','-fno-fast-math','-ffp-contract=off','-Wall','-Wextra','-Wno-multichar','-Iuc-library/include','-isystem','third_party/ccl-framework','-Ulinux','-MD','-MF',dep,'-c',s,'-o',o]
  try:run(cmd)
  except subprocess.CalledProcessError as e:print(e.stderr);raise
  deps=shlex.split(dep.read_text().replace('\\\n','').split(':',1)[1]);records.append(dict(argv=list(map(str,cmd)),object=bind(o),dependencies=[bind(p) for p in deps]));objects.append(o)
 cmd=['/usr/bin/c++',*objects,*LIBS,'-pthread','-ldl','-lssl','-lcrypto','-lm','-o',EXE]
 try:run(cmd)
 except subprocess.CalledProcessError as e:print(e.stderr);raise
 (SCRATCH/'build.json').write_text(json.dumps(dict(compiles=records,link_argv=list(map(str,cmd)),libraries=[bind(p) for p in LIBS],executable=bind(EXE)),indent=2)+'\n')
def symbols():
 out=run(['/usr/bin/nm','--defined-only',SCRATCH/'0.o']);expected={o['original']['mangled'] for p in native.TASKS for o in json.loads(p.read_text())['originals']};actual={line.split()[-1] for line in out.splitlines() if line.split()[-2]=='T'};assert expected<=actual;return sorted(expected)
def replay(exe=EXE,fixture=FIXTURE):
 d=json.loads(Path(fixture).read_text());rows=d['cases'];keys=['op','mode','value','direction','alt','clip','enabled','disabled','meter','custom','action','tag','offset','primary','notifyalt','repeat'];inputs=''.join(' '.join(str(r['input'][k]) for k in keys)+'\n' for r in rows)
 actual=run([exe],input=inputs).splitlines();assert len(actual)==len(rows)
 for n,(line,row) in enumerate(zip(actual,rows)):
  vs=list(map(int,line.split()));o=row['output'];expected=[o[k] for k in ['level','mode','blank','clip','queued']]+[o.get('return',-999),len(o['messages'])]+[v for m in o['messages'] for v in m]
  assert vs==expected,(n,row,vs,expected)
 print(len(rows),'native/portable cases matched');return len(rows)
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['format','compile','symbols','replay','proof'],nargs='?',default='proof');p.add_argument('--exe',type=Path,default=EXE);p.add_argument('--fixtures',type=Path,default=FIXTURE);a=p.parse_args()
 if a.mode=='format':run(FORMAT);return
 if a.mode=='compile':compile();return
 if a.mode=='symbols':print(symbols());return
 if a.mode=='replay':replay(a.exe,a.fixtures);return
 run(FORMAT);compile();names=symbols();fresh=native.generate();old=json.loads(FIXTURE.read_text());assert fresh==old;count=replay()
 proof=dict(version=1,originals=fresh['originals'],native_case_count=count,portable_case_count=count,compiled_symbols=names,formatter_version=run(['uc-library/.venv/bin/clang-format','--version']).strip(),sources=[bind(SOURCE),bind(HEADER),bind(REPLAY)],fixtures=bind(FIXTURE),producers=[bind(TEST/'native.py'),bind(TEST/'check.py')],build=bind(SCRATCH/'build.json'),boundary_policy=fresh['boundary_policy'],limitations=['Portable source port; unencoded return declarations and original fields/layout/ARM ABI unresolved.','Custom table uses explicit typed source-port binding rather than interpreting original pointer layout.','Native unchanged Control setter and alternate setter boundaries are stubbed; genuine CCL host regression additionally checks changed/unchanged and mode-only setters, alternate notifications, parameter destruction and controller observer cleanup.','Finite normal parameter domain; negative bus index, invalid table/count, null IPanelIO and nonfinite/int32 overflow values excluded; no hardware.'])
 for packet in native.TASKS:
  task=packet.parent.name;out=Path('uc-library/candidates')/task;out.mkdir(parents=True,exist_ok=True);(out/'worker-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
