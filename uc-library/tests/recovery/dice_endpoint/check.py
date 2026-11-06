from pathlib import Path
import sys,subprocess,json,os
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent
OUT=R/'temp/recovery-work/dice-endpoint22-local';OUT.mkdir(parents=True,exist_ok=True)
EXE=OUT/'replay'
CPP=['uc-library/src/Presonus/UC/DiceEndPoint.cpp','uc-library/src/Presonus/UC/DataChannel.cpp','uc-library/tests/recovery/DiceEndPointReplay.cpp']
DEPS=['uc-library/src/Presonus/UC/DicePacketQueue.cpp','uc-library/src/Presonus/UC/DicePacketQueueLifetime.cpp','uc-library/src/Presonus/UC/PacketQueueOperations.cpp']
HEADERS=['uc-library/include/presonus/uc/DiceEndPoint.hpp','uc-library/include/presonus/uc/DataChannel.hpp']
LIB='temp/core-upstream/root-integration-01/upstream-core/sdk/lib/'
WRAP=['_ZN8Presonus2UC11PacketQueue5writeEPKci','_ZN8Presonus2UC15DicePacketQueue8peakMIDIEPhRh','_ZN8Presonus2UC15DicePacketQueue8readMIDIEPhRh','_ZN8Presonus2UC15DicePacketQueue9writeMIDIEPKh','_ZN8Presonus2UC11PacketQueue5flushEv']
COMPILE=['/usr/bin/c++','-std=c++17','-fno-rtti','-Wno-multichar','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework',*CPP,*DEPS,LIB+'libcorelib.a',LIB+'libpresonus_core_allocator.a',*[f'-Wl,--wrap={s}' for s in WRAP],'-Wl,--gc-sections','-lpthread','-ldl','-o',str(EXE)]
def run(a):
 print(json.dumps(list(map(str,a))),flush=True);subprocess.run(a,cwd=R,check=True,env={**os.environ,'TMPDIR':str(OUT)})
def replay(exe,fixture):
 d=json.loads(Path(fixture).read_text())
 for c in d['cases']:
  actual=subprocess.check_output([str(exe),'run',c['input'],str(c['negative']),str(c['preload'])],text=True,cwd=R).splitlines()
  assert actual==c['trace'],(c['id'],next(((i,a,b) for i,(a,b) in enumerate(zip(actual,c['trace'])) if a!=b),(len(actual),len(c['trace']))))
 run([str(exe),'lifecycle']);print(f"{len(d['cases'])} source executions match independent exact ARM/native provider traces")
if __name__=='__main__':
 mode=sys.argv[1]
 if mode=='format':run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*CPP,*HEADERS])
 elif mode=='compile':run(COMPILE)
 elif mode=='symbols':
  out=subprocess.check_output(['nm','--defined-only',str(EXE)],text=True);names={x.split()[-1] for x in out.splitlines() if x.split()}
  for p in sorted((R/'temp/recovery-work/rolling200-02/next-implementation65/prepared-dice65-v2/packets').glob('rolling200_02_dice_endpoint22_*')):
   for o in json.loads((p/'request.json').read_text())['originals']:assert o['original']['mangled'] in names,o
  print('\n'.join(x for x in out.splitlines() if 'DiceEndPoint' in x or 'DataChannelD' in x));print('Linux ELF exact names; host constructor C1/C2 alias explicitly permitted; no native D2 credit')
 elif mode=='sanitizer':
  argv=COMPILE[:];argv[1:1]=['-fsanitize=undefined','-fno-sanitize-recover=all','-g'];argv[-1]+='-ubsan';run(argv);replay(Path(argv[-1]),T/'fixtures.json')
 elif mode=='optimized':
  # Match canonical Release production TUs and -O0 replay driver independently.
  objects=[]
  for index,cpp in enumerate([*CPP,*DEPS]):
   obj=OUT/f'optimized-{index}.o';objects.append(str(obj))
   run(['/usr/bin/c++','-std=c++20','-fno-lto','-fno-rtti','-Wno-multichar','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework','-O0' if cpp==CPP[-1] else '-O3','-DNDEBUG','-c',cpp,'-o',str(obj)])
  exe=OUT/'replay-optimized'
  run(['/usr/bin/c++',*objects,LIB+'libcorelib.a',LIB+'libpresonus_core_allocator.a',*[f'-Wl,--wrap={s}' for s in WRAP],'-Wl,--gc-sections','-lpthread','-ldl','-o',str(exe)])
  names={x.split()[-1] for x in subprocess.check_output(['nm','--defined-only',str(exe)],text=True).splitlines() if x.split()}
  for original in json.loads((T/'fixtures.json').read_text())['ranges']:assert original['mangled'] in names
  replay(exe,T/'fixtures.json')
 elif mode=='regression':
  evidence='evidence/recovery/2026-11-06/rolling200-02/dice-endpoint22/'
  for driver,fixture,wraps in [
   ('graph_trial04_datachannel_tests.cpp','uc-library/candidates/graph-live-trial-04-datachannel/fixtures.txt',[]),
   ('dice_packet_queue_lifetime_tests.cpp',evidence+'dice-packet-queue-continuation-fixtures.txt',['_Znwm','_ZdlPv','_ZdlPvm','__cxa_atexit']),
   ('packet_queue_operations_tests.cpp',evidence+'packet-queue-operations-fixtures.txt',['_Znwm','_ZdlPv','_ZdlPvm','pthread_mutex_lock','pthread_mutex_unlock'])]:
   exe=OUT/driver.replace('.cpp','')
   argv=['/usr/bin/c++','-std=c++17','-UNDEBUG','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework','uc-library/src/Presonus/UC/DataChannel.cpp',*DEPS,'uc-library/tests/'+driver,LIB+'libcorelib.a',LIB+'libpresonus_core_allocator.a',*[f'-Wl,--wrap={x}' for x in wraps],'-lpthread','-ldl','-o',str(exe)]
   run(argv);run([str(exe),fixture])
 elif mode=='replay':replay(Path(sys.argv[2]) if len(sys.argv)>2 else EXE,sys.argv[3] if len(sys.argv)>3 else T/'fixtures.json')
 elif mode=='native':
  import native
  assert native.generate()==json.loads((T/'fixtures.json').read_text());print('Fresh exact ARM execution/provider observations reproduce fixtures')
 else:raise SystemExit(mode)
