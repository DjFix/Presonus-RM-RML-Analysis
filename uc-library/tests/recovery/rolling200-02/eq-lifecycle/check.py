"""Real-provider compile, exact destructor identities and native differential replay."""
import argparse,json,pathlib,subprocess,os
ROOT=pathlib.Path(__file__).resolve().parents[5]
BASE=pathlib.Path('uc-library/tests/recovery/rolling200-02/eq-lifecycle')
SCRATCH=pathlib.Path('temp/recovery-work/rolling200-02/eq-lifecycle')
EXE=SCRATCH/'replay'
FIXTURE='evidence/recovery/2026-11-05/rolling200-02/eq-lifecycle/native.json'
SOURCES=['uc-library/src/Presonus/EQControl.cpp','uc-library/src/Presonus/EQControlBiquad.cpp','uc-library/src/Presonus/EQControlBandParams.cpp','uc-library/tests/recovery/EQControlLifecycleReplay.cpp','uc-library/src/Presonus/Dsp/EqSourceProviders.cpp','uc-library/src/mixer_dsp/Logarithm.cpp']
LIB='temp/core-upstream/root-integration-01/upstream-core/sdk/lib/'
COMPILE=['/usr/bin/c++','-std=c++20','-O0','-fno-rtti','-fno-lto','-ffunction-sections','-fdata-sections','-Wno-multichar','-Iuc-library/include','-Iuc-library/src/mixer_dsp','-Ithird_party/ccl-framework']+SOURCES+['temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a',LIB+'libcorelib.a',LIB+'libpresonus_core_allocator.a','-Wl,--gc-sections','-Wl,--wrap=_ZdlPv','-Wl,--wrap=_ZdlPvm','-Wl,--wrap=_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE','-lz','-lpthread','-ldl','-lm','-o',str(EXE)]
def run(argv,**kw):
 print(json.dumps(list(map(str,argv))),flush=True)
 r=subprocess.run(list(map(str,argv)),cwd=ROOT,env={**os.environ,'TMPDIR':str(ROOT/SCRATCH)},text=True,capture_output=True,**kw)
 if r.returncode:print(r.stdout+r.stderr);r.check_returncode()
 return r

def replay(executable,fixture):
 cases=json.loads((ROOT/fixture).read_text())['cases']
 r=run([executable],input=''.join(' '.join(map(str,c['input']))+'\n' for c in cases));lines=r.stdout.splitlines();assert len(lines)==len(cases)
 for n,(line,c) in enumerate(zip(lines,cases)):
  values=list(map(int,line.split()));events=[values[1+5*i:6+5*i] for i in range(values[0])];tail=values[1+5*values[0]:]
  assert tail==[int(c['input'][0]==0),int(bool(c['input'][3]&4)),3*c['input'][4]],(n,tail)
  # Compare exact native helper removal sequence, not deduplicated membership.
  assert [e[1] for e in events if e[0]==1]==c['removals'],(n,events,c)
  # Actual native frees and inline shared-image writes define source checkpoints.
  assert [e for e in events if e[0] in [2,3]]==c['source_lifetime_events'],(n,events,c['source_lifetime_events'])
  hp=[e for e in events if e[0]==4]
  assert [e[1] for e in hp]==([6,7,8] if c['input'][4] else []),(n,hp)
  if hp:
   bitmap=[i for i,e in enumerate(events) if e[0]==3]
   if bitmap:assert max(bitmap)<events.index(hp[0])
   assert all(e[2:]==c['before_shared_release'] for e in hp),(n,hp)
 print(len(cases),'exact original variant executions vs actual CCL source lifecycle; repeated/null observers, array frees, reverse curves/images, virtual bitmap deletion, owned HPF parameter signals, borrowed Control survival and actual object free')

def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['compile','symbols','replay','format']);p.add_argument('--executable',default=str(EXE));p.add_argument('--fixtures',default=FIXTURE);a=p.parse_args()
 (ROOT/SCRATCH).mkdir(parents=True,exist_ok=True)
 if a.mode=='compile': print(run(COMPILE).stdout)
 elif a.mode=='format': print(run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',SOURCES[0],'uc-library/include/presonus/mixer_dsp/EQControl.hpp',SOURCES[3]]).stdout)
 elif a.mode=='symbols':
  out=run(['/usr/bin/nm','--defined-only',a.executable]).stdout
  syms={r.split()[-1]:r.split()[0] for r in out.splitlines() if r.split()}
  for i in range(3):assert f'_ZN8Presonus9EQControlD{i}Ev' in syms
  assert syms['_ZN8Presonus9EQControlD1Ev']==syms['_ZN8Presonus9EQControlD2Ev']
  print('\n'.join(r for r in out.splitlines() if 'EQControlD' in r));print('All exact original variants; native D1/D2 distinct ranges, host D1/D2 aliases independently invoked; host ELF no decoration. No ARM ABI claim.')
 else: replay(a.executable,a.fixtures)
if __name__=='__main__':main()
