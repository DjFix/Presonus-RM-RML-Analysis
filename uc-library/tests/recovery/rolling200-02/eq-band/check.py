"""Local compile, exact symbols, native/provider differential replay."""
import argparse,json,pathlib,subprocess,os
ROOT=pathlib.Path(__file__).resolve().parents[5]
BASE=pathlib.Path('uc-library/tests/recovery/rolling200-02/eq-band')
SCRATCH=pathlib.Path('temp/recovery-work/rolling200-02/eq-band')
EXE=SCRATCH/'replay'
SOURCES=['uc-library/src/Presonus/EQControl.cpp','uc-library/src/Presonus/EQControlBiquad.cpp','uc-library/src/Presonus/EQControlBandParams.cpp','uc-library/tests/recovery/EQBandObserverReplay.cpp']
COMPILE=['/usr/bin/c++','-std=c++20','-O0','-fno-rtti','-ffunction-sections','-fdata-sections','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework']+SOURCES+['temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a','-lz','-Wl,--gc-sections','-Wl,--wrap=_ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE','-Wl,--wrap=_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE','-o',str(EXE)]
def run(argv,**kwargs):
 print(json.dumps(argv),flush=True)
 r=subprocess.run(argv,cwd=ROOT,env={**os.environ,'TMPDIR':str(ROOT/SCRATCH)},text=True,capture_output=True,**kwargs)
 if r.returncode:print(r.stdout+r.stderr);r.check_returncode()
 return r
def expected(c):
 mode,nonnull,index,count,*slots=c['input'];old=slots[:6]
 members=[0]*12
 if mode==0:
  for v in old:
   if v:members[v-1]+=1
 if mode==2:
  for v in old:
   if v:members[v-1]+=count
 for row in c['trace']:members[row[1]-1]+=1 if row[0] else -1
 result=[len(c['trace'])]+[v for row in c['trace'] for v in row]+[v for band in c['final'] for v in band]+c['dirty']+members
 if nonnull:
  for i,n in enumerate(members):
   dirty=[0]*count
   if n:
    for band,slots in enumerate(c['final']):
     if i+1 in slots:dirty[band]=1;break
   result+=dirty
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['compile','symbols','replay']);p.add_argument('--executable',default=str(EXE));p.add_argument('--fixtures',default='evidence/recovery/2026-11-05/rolling200-02/eq-band/native.json');a=p.parse_args()
 if a.mode=='compile':
  (ROOT/SCRATCH).mkdir(parents=True,exist_ok=True);r=run(COMPILE);print(r.stdout+r.stderr)
 elif a.mode=='symbols':
  r=run(['/usr/bin/nm','--defined-only',a.executable]);names={x.split()[-1] for x in r.stdout.splitlines()}
  for name in ['_ZN8Presonus9EQControl10BandParams14removeObserverEPS0_','_ZN8Presonus9EQControl10BandParams11addObserverEPS0_','_ZN8Presonus9EQControl7setBandEiNS0_10BandParamsE']:assert name in names,name;print(name)
  print('3 exact original symbols; host ELF no decoration, no original ARM ABI claim')
 else:
  cases=json.loads((ROOT/a.fixtures).read_text())['cases']
  r=run([a.executable],input=''.join(' '.join(map(str,c['input']))+'\n' for c in cases))
  lines=r.stdout.splitlines();assert len(lines)==len(cases),(len(lines),len(cases),r.stderr)
  for i,(c,line) in enumerate(zip(cases,lines)):
   got=list(map(int,line.split()));want=expected(c)
   assert got==want,(i,c['input'],got,want)
  print(len(cases),'native/provider differential cases; call order, copy phase, dirty byte, actual CCL membership and changed() callback effects')
if __name__=='__main__':main()
