"""Read-only checked actions for the UCNet destructor delivery; no shared edits."""
from pathlib import Path
import sys,subprocess,json,os,hashlib,datetime,time
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent
OUT=R/'temp/recovery-work/ucnet148-local';OUT.mkdir(parents=True,exist_ok=True)
E=R/'evidence/recovery/2026-11-06/rolling200-02/ucnet148';E.mkdir(parents=True,exist_ok=True)
EXE=OUT/'replay';PY='uc-library/.venv/bin/python'
CPP=['uc-library/src/Presonus/NOAA/TCardUCNetHandlerLifecycle.cpp','uc-library/tests/recovery/CardUCNetLifecycleReplay.cpp']
HEADERS=['uc-library/include/presonus/noaa/ucnet_handler.hpp','uc-library/include/presonus/noaa/ucnet_handler_state.hpp']
# Explicit actual providers prevent stale archive selection of new UCNet code.
DEPS=['uc-library/src/Presonus/NOAA/TCardUCNetHandlerIO.cpp','uc-library/src/Presonus/UC/DiceEndPoint.cpp','uc-library/src/Presonus/UC/DataChannel.cpp','uc-library/src/Presonus/UC/DicePacketQueue.cpp','uc-library/src/Presonus/UC/DicePacketQueueLifetime.cpp','uc-library/src/Presonus/UC/PacketQueueOperations.cpp','uc-library/src/Presonus/NOAA/TCardSPIService.cpp','uc-library/src/Presonus/NOAA/TCardSPIPackets.cpp','uc-library/src/Presonus/Panel/input_pin_lifetime.cpp','uc-library/src/surface_panel/InputPin.cpp']
LIB='temp/core-upstream/root-integration-01/'
ARCHIVES=[LIB+'libpresonus_uc.a',LIB+'upstream-core/sdk/lib/libcorelib.a',LIB+'upstream-core/sdk/lib/libpresonus_core_allocator.a',LIB+'private-glibc29-provider/libpresonus_private_glibc29.a']
WRAP=['_Znwm','_ZdlPv','_ZdlPvm','_ZN8Presonus2UC11PacketQueueD2Ev','_ZN8Presonus4NOAA8TCardSPI18unRegisterReceiverEPNS0_14ISysexReceiverE']
FLAGS=['-std=c++17','-fno-rtti','-UNDEBUG','-Wno-multichar','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework']
LINK=['-Wl,--start-group',*ARCHIVES,'-Wl,--end-group','-Wl,--gc-sections','-lpthread','-ldl','-lssl','-lcrypto','/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lm']
def run(argv):
 print(json.dumps(list(map(str,argv))),flush=True)
 p=subprocess.run(list(map(str,argv)),cwd=R,env={**os.environ,'TMPDIR':str(OUT)},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 print(p.stdout,end='');assert p.returncode==0,(p.returncode,p.stdout[-4000:]);return p.stdout

def compile_all(optimized=False):
 objects=[]
 for i,s in enumerate(CPP+DEPS):
  obj=OUT/f'{"opt" if optimized else "normal"}{i}.o';objects.append(str(obj))
  run(['/usr/bin/c++',*FLAGS,'-O3' if optimized and s!=CPP[1] else '-O0','-MMD','-MF',str(obj)+'.d','-c',s,'-o',obj])
 exe=Path(str(EXE)+('-optimized' if optimized else ''))
 run(['/usr/bin/c++',*objects,*LINK,*['-Wl,--wrap='+x for x in WRAP],'-o',exe]);return exe

def replay(exe,fixture):
 data=json.loads(Path(fixture).read_text());count=0
 for c in data['cases']:
  if c.get('probe'):continue
  a=[str(exe),'run',c['variant'],str(c['endpoint']),str(c['populated']),str(c['existing']),str(c['registered']),'0']
  actual=run(a).strip().split();assert actual==c['trace'],(c['id'],actual,c['trace']);count+=1
 for variant in ['D0','D1','D2']:
  for failure in [1,2,3]:
   actual=run([exe,'run',variant,'1','2','0','0',str(failure)]).strip().split()
   # Actual host C++ unwind; native endpoint retention is preserved. D0 host
   # ABI deletes self on throw, unlike observed original application landing.
   expected=['THROW']+(['SPI_DELETE'] if failure>1 else [])+['QO','P','P','QI','P','P']+(['S'] if variant=='D0' else [])
   assert actual==expected,(variant,failure,actual,expected)
 for existing,registered in [(0,0),(1,0),(1,1)]:
  actual=run([exe,'borrowed','D0','0','2',str(existing),str(registered),'0']).strip().split()
  assert actual==(['U'] if existing else [])+['S']
 assert run([exe,'adapter','D0','1','0','0','0','0']).strip()=='ADAPTER'
 print(json.dumps({'native_matched_source_cases':count,'host_exception_cases':9,'borrowed_cases':3,'physical_operations':0}))

if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='format':run(['uc-library/.venv/bin/clang-format','--version']);run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*CPP,*HEADERS])
 elif mode=='compile':compile_all()
 elif mode=='optimized':replay(compile_all(True),T/'fixtures.json')
 elif mode=='symbols':
  out=run(['nm','--defined-only',EXE]);names={s.split()[-1] for s in out.splitlines() if s.split()}
  for variant in ['D0','D1','D2']:assert '_ZN8Presonus4NOAA17TCardUCNetHandler'+variant+'Ev' in names
  print('Three exact original destructor names; host D1/D2 alias is separate from original ranges')
 elif mode=='replay':replay(Path(sys.argv[2]) if len(sys.argv)>2 else EXE,sys.argv[3] if len(sys.argv)>3 else T/'fixtures.json')
 elif mode=='native':
  import native
  assert native.generate()==json.loads((T/'fixtures.json').read_text());print('Fresh native instructions and actual provider executions reproduce fixture')
 elif mode=='regression':
  for source,fixture,wraps in [('uc-library/tests/noaa_ucnet_handler_tests.cpp','uc-library/validation/noaa-ucnet-handler/stdin.txt',['clock_gettime']),('uc-library/tests/recovery/TCardUCNetIdleReplay.cpp','evidence/recovery/2026-11-05/ucnet-idle/fixtures.json',['clock_gettime'])]:
   assert (R/fixture).is_file(),fixture
   exe=OUT/Path(source).stem
   run(['/usr/bin/c++',*FLAGS,CPP[0],source,*DEPS,*LINK,*['-Wl,--wrap='+x for x in wraps],'-o',exe])
   if 'IdleReplay' in source:
    run([PY,'uc-library/candidates/rolling200_02_ucnet_idle_01/replay.py',exe,fixture,'72bc36d5a8f2eda477336ae9270373c07fa7f7f7ad0a06dc9e8cde8afbc1369d'])
   else:run([exe,fixture])
 else:raise SystemExit(mode)
