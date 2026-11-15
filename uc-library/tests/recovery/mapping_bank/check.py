"""Standalone checks: real source providers; shared build remains read-only."""
import json,os,subprocess,sys
from pathlib import Path
import native
R=Path(__file__).resolve().parents[4];os.chdir(R)
KIND='mapping_bank'
T=Path('uc-library/tests/recovery')/KIND
OUT=Path('temp/recovery-work')/(KIND+'-local');OUT.mkdir(parents=True,exist_ok=True)
EXE=OUT/'Replay'
BUILD=Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01')
SOURCES=['uc-library/src/Presonus/Surface/MappingComponent.cpp', 'uc-library/src/Presonus/Surface/MappingInputRoutes.cpp', 'uc-library/src/Presonus/Surface/MappingRadioRoutes.cpp', 'uc-library/src/Presonus/Surface/MappingMeterRouting.cpp', 'uc-library/src/Presonus/Surface/MappingRadioValidation.cpp']
FORMAT=['uc-library/src/Presonus/Surface/MappingComponent.cpp', 'uc-library/include/presonus/surface/MappingComponent.hpp', 'uc-library/tests/recovery/mapping_bank/Replay.cpp']
FLAGS=['/usr/bin/c++','-std=c++17','-O2','-g','-fno-rtti','-fno-lto','-fno-fast-math','-ffp-contract=off','-ffunction-sections','-fdata-sections','-DNDEBUG','-Wno-multichar','-pthread','-Ulinux','-DCORE_USE_OPENSSL=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-Iuc-library/include','-Ithird_party/ccl-framework']
def run(argv,**kw):
 print(json.dumps(list(map(str,argv))),flush=True)
 p=subprocess.run(list(map(str,argv)),capture_output=True,env={**os.environ,'TMPDIR':str(R/OUT)},**kw)
 if p.stdout:print(p.stdout.decode(),end='')
 if p.stderr:print(p.stderr.decode(),end='',file=sys.stderr)
 p.check_returncode();return p

def main():
 mode=sys.argv[1]
 if mode=='format':
  run(['uc-library/.venv/bin/clang-format','--version'])
  run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*FORMAT])
 elif mode=='compile':
  sdk=BUILD/'upstream-core/sdk'
  run([*FLAGS,*SOURCES,str(T/'Replay.cpp'),'-Wl,--wrap=_ZNK4Core8Portable9Component17getParameterByTagEi','-Wl,--gc-sections','-Wl,--start-group',str(BUILD/'libpresonus_uc.a'),str(sdk/'lib/libcorelib.a'),str(sdk/'lib/libpresonus_core_allocator.a'),'-Wl,--end-group','-lpthread','-ldl','-lrt','-lz','/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lssl','-lcrypto',str(BUILD/'private-glibc29-provider/libpresonus_private_glibc29.a'),'-o',EXE])
 elif mode=='symbols':
  output=subprocess.check_output(['/usr/bin/nm','--defined-only',str(EXE)],text=True);names={l.split()[-1] for l in output.splitlines() if l.split()};assert native.NAME in names;print(native.NAME)
 elif mode=='native':
  observed=native.generate();assert observed==json.loads((T/'fixtures.json').read_text());print('fresh original ARM observations verified')
 elif mode=='replay':
  fixture=json.loads((T/'fixtures.json').read_text());assert native.generate()==fixture
  exe=Path(sys.argv[2]) if len(sys.argv)>2 else EXE
  if KIND=='mapping_bank':
   expected={c['input']:c['result'] for c in fixture['cases']}
   rows=[f"O {value} {result}" for value,result in expected.items()]
   for mask in range(16):
    first=next((i for i in range(4) if mask&(1<<i)),-1)
    rows.append(f"R {mask} {expected[first]}")
   run([exe],input=('\n'.join(rows)+'\n').encode())
  else:
   assert fixture['cases'][0]['trace']==[['Core::Portable::Component::onIdle'],['checkNetworkScanning']]
   rows=[];wanted=[]
   for expired in [0,1]:
    for phase in [0,1]:
     for children in [0,1,3]:
      rows.append(f'{expired} {phase} {children}')
      wanted.extend(f'CHILD {i}' for i in range(children))
      if expired:wanted.extend(['SCAN 0' if not phase else 'LIST 1 0 1 2','BEGIN 3212836864'])
      wanted.append(f'STATE {int(not phase) if expired else phase} {expired}')
   output=run([exe],input=('\n'.join(rows)+'\n').encode()).stdout.decode().splitlines()
   assert output==wanted,(output,wanted)
   print('12 real CCL child-order and Wifi timer/phase cases; native two-provider call order')
 else:raise SystemExit(mode)
if __name__=='__main__':main()
