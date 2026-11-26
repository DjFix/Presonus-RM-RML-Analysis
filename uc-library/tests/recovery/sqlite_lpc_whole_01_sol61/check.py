"""Scoped format/build/symbol and independent ARM/portable differential replay."""
import json,subprocess,sys,os,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(Path(__file__).parent))
from native import generate
TEST=Path(__file__).parent.relative_to(ROOT)
SCRATCH=ROOT/'temp/recovery-work/sqlite-issued/lpc-validation'
SRC=Path('uc-library/src/Presonus/LPCProgrammer.cpp')
HEADER=Path('uc-library/include/presonus/application/LPCProgrammerGeometry.hpp')
SDK=Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib')
CXX=['/usr/bin/c++','-std=c++20','-Ulinux','-DCORE_USE_OPENSSL=1','-pthread','-Iuc-library/include','-isystem','third_party/ccl-framework']
PROVIDERS=[f'uc-library/src/Presonus/LPCProgrammer{x}.cpp' for x in ['CommandInfo','Geometry','Handshake','ImageGeometry','Input','Transport']]
WRAP=['__printf_chk','printf','fflush','write','read','open','close','tcgetattr','tcsetattr','tcflush','clock_gettime','usleep','_ZdlPv','_ZdlPvm']
def run(argv,**kw):
 print(json.dumps(list(map(str,argv))),flush=True)
 return subprocess.run(list(map(str,argv)),cwd=ROOT,check=True,text=True,capture_output=True,**kw)
CORE_SHA="5a2c8bbb20d8d194ff4f5047118696afa918a046b01739c4257416044e83f5f3"
def build():
 assert hashlib.sha256((SDK/"libcorelib.a").read_bytes()).hexdigest()==CORE_SHA,"compiled Core provider changed"
 SCRATCH.mkdir(parents=True,exist_ok=True);os.environ['TMPDIR']=str(SCRATCH)
 run([*CXX,'-c',SRC,'-o',SCRATCH/'production.o'])
 run([*CXX,TEST/'Replay.cpp',*PROVIDERS,SDK/'libcorelib.a','-Wl,'+','.join('--wrap='+s for s in WRAP),'-o',SCRATCH/'replay'])
def expected(n,c):
 events=[]
 for e in n['events']:
  if e[0]=='wait':continue
  if e[0]=='progress':events.append('progress '+e[1].encode().hex()+' '+str(e[2]))
  else:events.append(' '.join(map(str,e)))
 if 'output' in n:events.append('output '+n['output'])
 if 'state' in n:events.append('state '+' '.join(map(str,n['state'])))
 if 'block' in n:events.append('block '+n['block'])
 if 'ret' in n:events.append('ret '+str(n['ret']))
 return events

def replay(fixtures,exe):
 rows=json.loads(Path(fixtures).read_text())['rows']
 for i,row in enumerate(rows):
  c=row['case'];args=[exe,c['method'],*[str(c[x]) for x in ['size','a','b','d','first','sectors','destination','listener','port']],c['text'],c['mangled']]
  stdin=str(len(c['responses']))+'\n'+'\n'.join(c['responses'])+'\n'
  p=subprocess.run(list(map(str,args)),input=stdin,text=True,capture_output=True,cwd=ROOT,timeout=30)
  if p.returncode:raise AssertionError((i,c,p.returncode,p.stderr[-1000:]))
  actual=[s[1:] for s in p.stdout.splitlines() if s.startswith('@')]
  want=expected(row['native']['client'],c)
  if c.get('guard'):
   assert actual[-1]=='ret 0',(i,actual[-3:])
   assert actual[:-1]==want[:len(actual)-1],(i,actual[-3:],want[-3:])
   states=row['native']['client']['tail_state'];assert states[0]['r7']==0 and states[0]['tail_minus_one']==0xffffffff
   assert [x['counter'] for x in states[1:]]==[1,2,3] and all(x['bound']==0xffffffff for x in states[1:])
   continue
  if actual!=want:
   mismatch=next((n for n,(a,b) in enumerate(zip(actual,want)) if a!=b),min(len(actual),len(want)))
   raise AssertionError((i,c['method'],c['size'],c['responses'][:5],mismatch,actual[max(0,mismatch-2):mismatch+3],want[max(0,mismatch-2):mismatch+3],p.stderr[-500:]))
 print('portable cases',len(rows),'passed')
def main(task=None):
 global TEST,SCRATCH
 if task is None and "--cohort" not in sys.argv:task="sqlite_lpc_whole_01_sol61"
 if task:
  TEST=Path('uc-library/tests/recovery')/task
  SCRATCH=ROOT/'temp/recovery-work/sqlite-issued/lpc-validation'/task
 mode=sys.argv[1] if len(sys.argv)>1 else 'all'
 SCRATCH.mkdir(parents=True,exist_ok=True)
 fixtures=SCRATCH/'native.json'
 format_files=[SRC,HEADER,TEST/'Replay.cpp',Path('uc-library/tests/recovery/sqlite_lpc_whole_01_sol61/Replay.cpp')]
 if mode in ['all','format']:run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*dict.fromkeys(format_files)])
 if mode in ['all','compile']:build()
 if mode in ['all','symbols']:
  text=run(['/usr/bin/nm','--defined-only',SCRATCH/'production.o']).stdout
  for p in sorted((ROOT/'temp/recovery-work/sqlite-issued/packet-current').glob('sqlite_lpc_whole_*')):
   name=json.loads((p/'CONTEXT.json').read_text())['originals'][0]['original']['mangled'];assert any(l.split()[-1]==name for l in text.splitlines()),name
 if mode in ['all','native']:
  generate(fixtures,task)
  sealed=ROOT/TEST/'fixtures.json'
  if sealed.exists():assert json.loads(fixtures.read_text())==json.loads(sealed.read_text()),'fresh native oracle differs from sealed fixture'
 if mode in ['all','replay']:replay(fixtures,SCRATCH/'replay')
if __name__=='__main__':main()
