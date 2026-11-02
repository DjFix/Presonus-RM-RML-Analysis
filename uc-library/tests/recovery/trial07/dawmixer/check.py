#!/usr/bin/env python3
"""Local reproducible checks; outputs are scratch, never production inputs."""
import argparse,datetime,hashlib,json,os,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
SCRATCH=ROOT/'temp/recovery-work/graph-live-trial-07/dawmixer-worker'
SRC='uc-library/src/Presonus/Surface/DAWMixerHandler.cpp'
HDR='uc-library/include/presonus/surface/DAWMixerHandler.hpp'
TEST='uc-library/tests/graph_trial07_dawmixer_tests.cpp'
DIR='uc-library/tests/recovery/trial07/dawmixer'
PYTHON='uc-library/.venv/bin/python'
FORMAT='uc-library/.venv/bin/clang-format'
FLAGS=['/usr/bin/c++','-std=c++17','-fno-lto','-fno-rtti','-pthread','-Ulinux','-Wno-multichar','-DCORE_USE_OPENSSL=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-Iuc-library/include','-isystem','third_party/ccl-framework']
LINK=['temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a','/usr/lib/x86_64-linux-gnu/libpng16.so.16','/usr/lib/x86_64-linux-gnu/libz.so.1','/usr/lib/x86_64-linux-gnu/libssl.so','/usr/lib/x86_64-linux-gnu/libcrypto.so','temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so','-ldl','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a','-lm']
def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def run(argv,label):
 start=stamp();t=time.monotonic();r=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True,env={**os.environ,'TMPDIR':str(SCRATCH)})
 record={'argv':argv,'start_utc':start,'end_utc':stamp(),'duration_seconds':time.monotonic()-t,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
 (SCRATCH/(label+'.json')).write_text(json.dumps(record,indent=2)+'\n');print(r.stdout,end='');print(r.stderr,end='')
 if r.returncode:raise SystemExit(r.returncode)
 return r.stdout
p=argparse.ArgumentParser();p.add_argument('kind',choices=['format','compile','symbols','oracle','replay']);a=p.parse_args()
SCRATCH.mkdir(parents=True,exist_ok=True)
if a.kind=='format':
 run([FORMAT,'--version'],'formatter-version')
 run([FORMAT,'--style=file','--fallback-style=LLVM','--dry-run','--Werror',SRC,HDR,TEST],'format')
elif a.kind=='compile':
 run(FLAGS+['-MMD','-MF',str(SCRATCH/'production.d'),'-c',SRC,'-o',str(SCRATCH/'production.o')],'compile-production')
 run(FLAGS+['-MMD','-MF',str(SCRATCH/'test.d'),TEST,str(SCRATCH/'production.o')]+LINK+['-o',str(SCRATCH/'replay')],'compile-replay')
elif a.kind=='symbols':
 text=run(['/usr/bin/nm','--defined-only',str(SCRATCH/'production.o')],'nm')
 for i in range(1,11):
  j=json.loads((ROOT/f'temp/recovery-work/graph-live-trial-07/trial07_dawmixer_{i}-packet/context.json').read_text())
  original=j['originals'][0]['original'];name=original['mangled']
  assert any(line.split()[-1]==name for line in text.splitlines()),name
 print('All ten ELF mangled names match compiled Linux symbols exactly.')
elif a.kind=='oracle':
 run([PYTHON,DIR+'/native_oracle.py','--out',str(SCRATCH/'fixtures-fresh.json')],'native-oracle')
 assert (ROOT/(DIR+'/fixtures.json')).read_bytes()==(SCRATCH/'fixtures-fresh.json').read_bytes()
elif a.kind=='replay':run([PYTHON,DIR+'/replay.py','--executable',str(SCRATCH/'replay'),'--fixtures',DIR+'/fixtures.json'],'differential-replay')
