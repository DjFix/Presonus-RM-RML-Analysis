import subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
BUILD=Path('temp/recovery-work/handler-runtime08-local');BUILD.mkdir(parents=True,exist_ok=True)
SOURCES=['uc-library/src/Presonus/NOAA/TCardHandlerEvents.cpp','uc-library/src/Presonus/NOAA/TCardHandlerEventQueue.cpp','uc-library/tests/recovery/TCardHandlerEventsReplay.cpp']
OWNED=['uc-library/include/presonus/noaa/card_handler.hpp','uc-library/include/presonus/noaa/card_handler_state.hpp','uc-library/include/presonus/noaa/card_handler_events.hpp',*SOURCES]
EXE=BUILD/'replay'
def run(a):print('ARGV',a,flush=True);subprocess.run(a,check=True)
if sys.argv[1]=='format':
 run(['uc-library/.venv/bin/clang-format','--version']);run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*OWNED])
if sys.argv[1]=='compile':
 flags=['-std=c++17','-O0','-g','-UNDEBUG','-Ulinux','-fno-rtti','-fno-lto','-pthread','-DCORE_USE_OPENSSL=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-Iuc-library/include','-Itemp/core-upstream/root-integration-01/upstream-core/sdk/include/presonus-core-5']
 objs=[]
 for i,s in enumerate(SOURCES):
  o=str(BUILD/f'{i}.o');run(['g++',*flags,'-c',s,'-o',o]);objs.append(o)
 base='temp/core-upstream/root-integration-01/'
 libs=[base+'libpresonus_rm_components.a',base+'upstream-core/sdk/lib/libcorelib.a',base+'upstream-core/sdk/lib/libpresonus_core_allocator.a',base+'private-glibc29-provider/libpresonus_private_glibc29.a']
 wraps=['clock_gettime','_ZN4Core8Platform13CurrentThread5sleepEj','_ZN4Core8Platform9PosixLock4lockEv','_ZN4Core8Platform9PosixLock6unlockEv','_ZN8Presonus4NOAA12TCardHandler19setPropertyDeferredERKN4Core8PropertyE','_ZN8Presonus4NOAA11TCardRouter4idleEv','_ZN8Presonus4NOAA8TCardSPI6onIdleEb','_ZN8Presonus4NOAA13SysexReceiver7waitAckEx']
 run(['g++','-pthread',*objs,*['-Wl,--wrap='+s for s in wraps],'-Wl,--start-group',*libs,'-Wl,--end-group','-Ltemp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu','-lpng','-lz','-lssl','-lcrypto','-ldns_sd','-ldl','-o',str(EXE)])
if sys.argv[1]=='symbols':
 s=subprocess.check_output(['nm','-S','--defined-only',str(BUILD/'0.o')],text=True);assert any(line.split()[-2:]==['T','_ZN8Presonus4NOAA12TCardHandler11threadEntryEv'] for line in s.splitlines());assert any(line.split()[1:] == ['0000000000000008','b','_ZZN8Presonus4NOAA12TCardHandler11threadEntryEvE15s_LastIdleTicks'] for line in s.splitlines());print(s,end="")
if sys.argv[1]=='replay':
 for case in ['stopped','deadlines','fifo-pools','cadence','signed-wide']:
  run([str(EXE),'uc-library/candidates/rolling200_02_handler_runtime08_01/stdin.txt',case])
