"""Read-only bound inputs; repeatable isolated format/compile/symbol/native/replay checks."""
import argparse,datetime,hashlib,json,os,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
DIR='uc-library/tests/recovery/daw_map_construction'
SCRATCH=ROOT/'temp/recovery-work/daw_maps183-local'
EVIDENCE=ROOT/'evidence/recovery/2026-11-06/rolling200-03/daw-maps183-fix01'
SOURCE='uc-library/src/Presonus/DAWTimeMapsConstruction.cpp'
MAPS='uc-library/src/Presonus/DAWTimeMaps.cpp'
HEADER='uc-library/include/presonus/DAWTimeInfo.hpp'
TEST='uc-library/tests/recovery/DAWTimeMapsConstructionReplay.cpp'
PYTHON='uc-library/.venv/bin/python'
FORMAT='uc-library/.venv/bin/clang-format'
CAPTURE=False
LINK=['-Wl,--start-group','temp/core-upstream/root-integration-01/libpresonus_cs18_components.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a','-Wl,--end-group','-pthread','-ldl','/usr/lib/x86_64-linux-gnu/libpng16.so.16','/usr/lib/x86_64-linux-gnu/libz.so.1','-lssl','-lcrypto','temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a','-lm']
FLAGS=['/usr/bin/c++','-std=c++17','-fno-lto','-fno-rtti','-Ulinux','-Wno-multichar','-Iuc-library/include','-isystem','third_party/ccl-framework']
def run(argv,label):
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();t=time.monotonic()
 r=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True,env={**os.environ,'TMPDIR':str(SCRATCH)})
 result=dict(argv=argv,start_utc=start,duration_seconds=time.monotonic()-t,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
 ((EVIDENCE if CAPTURE else SCRATCH)/(label+'.json')).write_text(json.dumps(result,indent=2)+'\n');
 if label!='nm':print(r.stdout,end='')
 print(r.stderr,end='')
 if r.returncode:raise SystemExit(r.returncode)
 return r.stdout
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('kind',choices=['format','compile','symbols','oracle','replay','regression']);p.add_argument('--executable');p.add_argument('--capture',action='store_true');a=p.parse_args();CAPTURE=a.capture
 SCRATCH.mkdir(parents=True,exist_ok=True);EVIDENCE.mkdir(parents=True,exist_ok=True)
 if a.kind=='format':
  run([FORMAT,'--version'],'formatter-version');run([FORMAT,'--style=file','--fallback-style=LLVM','--dry-run','--Werror',HEADER,SOURCE,MAPS,TEST],'format')
 elif a.kind=='compile':
  run([f for f in FLAGS if f!='-fno-rtti']+['-O3','-DNDEBUG','-DCORE_USE_OPENSSL=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-MD','-MF',str(SCRATCH/'production.d'),'-c',SOURCE,'-o',str(SCRATCH/'production.o')],'compile-production')
  run([f for f in FLAGS if f!='-fno-rtti']+['-O3','-DNDEBUG','-DCORE_USE_OPENSSL=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-MD','-MF',str(SCRATCH/'maps.d'),'-c',MAPS,'-o',str(SCRATCH/'maps.o')],'compile-maps')
  run(FLAGS+['-std=c++20','-O0','-UNDEBUG',TEST,str(SCRATCH/'production.o'),str(SCRATCH/'maps.o')]+LINK+['-o',str(SCRATCH/'replay')],'compile-replay')
 elif a.kind=='symbols':
  result=run(['/usr/bin/nm','--defined-only',str(SCRATCH/'production.o')],'nm')
  for packet in sorted((ROOT/'temp/recovery-work/rolling200-03/daw_maps183/prepared183/packets').iterdir()):
   target=json.loads((packet/'request.json').read_text())['targets'][0]['mangled'];assert any(line.split()[-1]==target for line in result.splitlines()),target
  print('4 exact Linux ELF mangles; C1/C2 source aliases do not imply original range aliasing')
 elif a.kind=='oracle':
  run([PYTHON,DIR+'/native.py','--out',str(SCRATCH/'fixtures-fresh.json')],'native-oracle')
  assert (ROOT/DIR/'fixtures.json').read_bytes()==(SCRATCH/'fixtures-fresh.json').read_bytes()
  fixture=json.loads((SCRATCH/'fixtures-fresh.json').read_text())
  for case in fixture['cases']:
   delta=16 if 'TimeSignatureMap' in case['mangled'] else 64
   assert len(case['trace'])==1 and case['trace'][0]['r0']==0 and case['trace'][0]['r1']==delta
   words=[int.from_bytes(bytes.fromhex(case['state'])[i:i+4],'little') for i in range(0,20,4)]
   assert words[1:]==[0,0,0,delta]
   assert bytes.fromhex(case['state'])[20:]==bytes([case['seed']])*44
   assert [w[0] for w in case['writes']]==[0,12,4,8,16]
   assert case['returned_this'] is (None if case['mode']=='exception_boundary' else True)
 elif a.kind=='replay':run([a.executable or str(SCRATCH/'replay')],'provider-map-replay')
 elif a.kind=='regression':
  archive='temp/core-upstream/root-integration-01/libpresonus_uc.a'
  cs18='temp/core-upstream/root-integration-01/libpresonus_cs18_components.a'
  core='temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a'
  allocator='temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a'
  # Fresh owned objects override the baseline maps inside physical role archives.
  common=[str(SCRATCH/'production.o'),str(SCRATCH/'maps.o')]
  run(FLAGS+['uc-library/tests/recovery/ranked09/maps/driver.cpp']+common+['-o',str(SCRATCH/'borrowed-maps')],'compile-borrowed-maps')
  run([PYTHON,'uc-library/tests/recovery/ranked09/maps/replay.py',str(SCRATCH/'borrowed-maps'),'uc-library/tests/recovery/ranked09/maps/fixtures.json'],'regression-borrowed-maps')
  link=['-Wl,--start-group',archive,cs18,core,allocator,'-Wl,--end-group','-pthread','-ldl','/usr/lib/x86_64-linux-gnu/libpng16.so.16','/usr/lib/x86_64-linux-gnu/libz.so.1','-lssl','-lcrypto','temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a']
  run(FLAGS+['uc-library/tests/recovery/reconstruction-200-01/large01_w05/driver.cpp']+common+link+['-o',str(SCRATCH/'events-regression')],'compile-events-regression')
  run([PYTHON,'uc-library/tests/recovery/reconstruction-200-01/large01_w05/replay.py','--executable',str(SCRATCH/'events-regression'),'--fixtures','uc-library/tests/recovery/reconstruction-200-01/large01_w05/fixtures.json'],'regression-events')
  run(FLAGS+['uc-library/tests/graph_trial08_timeinfo_tests.cpp']+common+link+['-o',str(SCRATCH/'timeinfo-regression')],'compile-timeinfo-regression')
  run([PYTHON,'uc-library/tests/recovery/trial08/timeinfo/replay.py','--executable',str(SCRATCH/'timeinfo-regression'),'--fixtures','uc-library/tests/recovery/trial08/timeinfo/native-fixtures.json'],'regression-timeinfo')
