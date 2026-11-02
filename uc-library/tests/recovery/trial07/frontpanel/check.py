#!/usr/bin/env python3
"""Local compile/symbol check; replay accepts canonical built executable separately."""
import argparse, subprocess, os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
SCRATCH=ROOT/'temp/recovery-work/graph-live-trial-07/frontpanel-worker'
CPP=['uc-library/src/Presonus/Panel/FrontPanelComponent.cpp','uc-library/tests/graph_trial07_frontpanel_tests.cpp']
HEADER='uc-library/include/presonus/panel/FrontPanelComponent.hpp'
def run(argv):
 print(' '.join(map(str,argv)),flush=True);subprocess.run(list(map(str,argv)),cwd=ROOT,check=True,env={**os.environ,'TMPDIR':str(SCRATCH)})
def compile_local():
 SCRATCH.mkdir(parents=True,exist_ok=True)
 flags=['-std=c++17','-O2','-fno-lto','-UNDEBUG','-fno-rtti','-pthread','-Ulinux','-DCORE_USE_OPENSSL=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-Iuc-library/include','-Ithird_party/ccl-framework']
 run(['/usr/bin/c++',*flags,'-c',CPP[0],'-o',SCRATCH/'frontpanel.o'])
 build=ROOT/'temp/core-upstream/root-integration-01'
 run(['/usr/bin/c++',*flags,CPP[1],SCRATCH/'frontpanel.o',build/'upstream-core/sdk/lib/libcorelib.a',build/'upstream-core/sdk/lib/libpresonus_core_allocator.a','/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lssl','-lcrypto',ROOT/'temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so','-ldl',build/'private-glibc29-provider/libpresonus_private_glibc29.a','-lm','-o',SCRATCH/'frontpanel-tests'])
def symbols():
 import json
 found=subprocess.check_output(['nm','--defined-only',str(SCRATCH/'frontpanel.o')],text=True,cwd=ROOT)
 for i in range(1,11):
  c=json.loads((ROOT/f'temp/recovery-work/graph-live-trial-07/trial07_frontpanel_{i}-packet/context.json').read_text())
  name=c['originals'][0]['original']['mangled']
  assert any(l.split()[-1]==name for l in found.splitlines()),name
 print(found)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('kind',choices=['compile','symbols','format']);a=p.parse_args()
 if a.kind=='compile':compile_local()
 elif a.kind=='symbols':symbols()
 else:run([ROOT/'uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*CPP,HEADER])
