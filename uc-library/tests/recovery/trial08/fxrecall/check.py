"""Local build/symbol/native checks; no operational proofs used by replay."""
import argparse,json,os,subprocess
from pathlib import Path
from oracle import run
ROOT=Path(__file__).resolve().parents[5]
SCRATCH=ROOT/'temp/recovery-work/graph-live-trial-08/fxrecall-worker'
SOURCES=['uc-library/src/Presonus/Panel/FXPresetRecallComponentTrial08.cpp','uc-library/tests/graph_trial08_fxrecall_tests.cpp']
p=argparse.ArgumentParser();p.add_argument('kind',choices=['compile','symbols','native']);a=p.parse_args();os.chdir(ROOT)
if a.kind=='compile':
 SCRATCH.mkdir(parents=True,exist_ok=True)
 cmd=['/usr/bin/c++','-std=c++17','-frtti','-Ulinux','-DNDEBUG','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework',*SOURCES,'temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a','/usr/lib/x86_64-linux-gnu/libpng16.so.16','/usr/lib/x86_64-linux-gnu/libz.so.1','/usr/lib/x86_64-linux-gnu/libssl.so','/usr/lib/x86_64-linux-gnu/libcrypto.so','temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so','-ldl','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a','-lm','-pthread','-o',str(SCRATCH/'replay')]
 print(json.dumps(cmd),flush=True);subprocess.run(cmd,env={**os.environ,'TMPDIR':str(SCRATCH)},check=True)
elif a.kind=='symbols':
 text=subprocess.check_output(['/usr/bin/nm','--defined-only',str(SCRATCH/'replay')],text=True)
 names=['_ZN8Presonus5Panel23FXPresetRecallComponent6onIdleEv','_ZNK8Presonus5Panel23FXPresetRecallComponent10getSlotNumEv','_ZN8Presonus5Panel23FXPresetRecallComponent12cacheUpdatedERNS0_15PresetNameCacheEiPKcS5_','_ZNK8Presonus5Panel23FXPresetRecallComponent11isSlotEmptyEj','_ZNK8Presonus5Panel23FXPresetRecallComponent16isChildParameterERKN4Core8Portable9ParameterE','_ZN8Presonus5Panel23FXPresetRecallComponent12paramChangedEPN4Core8Portable9ParameterEi','_ZNK8Presonus5Panel23FXPresetRecallComponent11getFileNameEjRN4Core8Portable8FileNameE','_ZNK8Presonus5Panel23FXPresetRecallComponent9getFxNameERN4Core8Portable9ParameterEj','_ZN8Presonus5Panel23FXPresetRecallComponent4initEv','_ZN8Presonus5Panel23FXPresetRecallComponent12updateFxNameEv']
 defined={line.split()[-1] for line in text.splitlines()}
 for name in names:assert name in defined,name;print(name)
else:
 fixtures=json.loads((Path(__file__).parent/'fixtures.json').read_text())
 for c in fixtures:
  actual=run(c)
  if c['method']=='getSlotNum' and actual['return']>=2**31:actual['return']-=2**32
  assert actual==c['expected'],(c,actual)
 print('PASS independent original ARM replay',len(fixtures))
