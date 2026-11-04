"""Local compile and original-name checks. Runtime replay uses fixtures only."""
import argparse,os,subprocess,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
SCRATCH=ROOT/'temp/recovery-work/graph-live-trial-08/stormpanel-worker'
BASE=ROOT/'temp/core-upstream/root-integration-01'
SOURCE='uc-library/src/Presonus/Panel/StormFrontPanelComponent.cpp'
TEST='uc-library/tests/graph_trial08_stormpanel_tests.cpp'
p=argparse.ArgumentParser();p.add_argument('mode',choices=['compile','symbols']);a=p.parse_args()
os.chdir(ROOT);os.environ['TMPDIR']=str(SCRATCH);SCRATCH.mkdir(parents=True,exist_ok=True)
if a.mode=='compile':
 argv=['/usr/bin/c++','-std=c++17','-fno-rtti','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework',TEST,SOURCE,str(BASE/'libpresonus_rm_components.a'),str(BASE/'upstream-core/sdk/lib/libcorelib.a'),str(BASE/'upstream-core/sdk/lib/libpresonus_core_allocator.a'),'/usr/lib/x86_64-linux-gnu/libpng16.so.16','/usr/lib/x86_64-linux-gnu/libz.so.1','-lssl','-lcrypto','temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so','-ldl',str(BASE/'private-glibc29-provider/libpresonus_private_glibc29.a'),'-lm','-o',str(SCRATCH/'replay-test')]
 print(json.dumps(argv),flush=True);subprocess.run(argv,check=True)
 argv=['/usr/bin/c++','-std=c++17','-Iuc-library/include','-c',SOURCE,'-o',str(SCRATCH/'stormpanel.o')];print(json.dumps(argv),flush=True);subprocess.run(argv,check=True)
else:
 symbols=subprocess.check_output(['/usr/bin/nm','--defined-only',str(SCRATCH/'stormpanel.o')],text=True)
 originals=json.loads((ROOT/'uc-library/tests/recovery/trial08/stormpanel/native-fixtures.json').read_text())['originals']
 names={line.split()[-1] for line in symbols.splitlines() if line.strip()}
 for o in originals:
  assert o['mangled'] in names,o['mangled'];print(o['mangled'])
 print('PASS: ten exact Itanium names; ELF host object has no extra leading decoration')
