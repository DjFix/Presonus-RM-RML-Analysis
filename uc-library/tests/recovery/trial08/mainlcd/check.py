"""Local compile/symbol checks; scratch is confined to this worker."""
import argparse,subprocess,os,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
os.chdir(ROOT)
SCRATCH=ROOT/'temp/recovery-work/graph-live-trial-08/mainlcd-worker'
os.environ['TMPDIR']=str(SCRATCH)
EXE=SCRATCH/'mainlcd-tests'
CPP='uc-library/src/Presonus/MainLCDComponent.cpp'
TEST='uc-library/tests/graph_trial08_mainlcd_tests.cpp'
wraps=['_ZN4Core8Portable9TextInput9isEditingEPNS0_8RootViewE','_ZN4Core8Portable9TextInput4stopEPNS0_8RootViewEb','_ZN4Core8Portable9Component6onIdleEv']
flags=['-std=c++17','-O2','-DNDEBUG','-fno-lto','-frtti','-pthread','-Ulinux','-DCORE_USE_OPENSSL=1','-Iuc-library/include','-Ithird_party/ccl-framework']
def run(argv):
 print(json.dumps(argv),flush=True);subprocess.run(argv,check=True)
def compile():
 run(['/usr/bin/c++',*flags,'-c',CPP,'-o',str(SCRATCH/'mainlcd.o')])
 run(['/usr/bin/c++',*flags,'-c',TEST,'-o',str(SCRATCH/'tests.o')])
 run(['/usr/bin/c++',str(SCRATCH/'mainlcd.o'),str(SCRATCH/'tests.o'),'-o',str(EXE),*[f'-Wl,--wrap={x}' for x in wraps],'-Wl,--start-group','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a','-Wl,--end-group','/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lssl','-lcrypto',str(ROOT/'temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so'),'-ldl','-lm','-pthread',f'-Wl,-rpath,{ROOT}/temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu'])
def symbols():
 output=subprocess.check_output(['/usr/bin/nm','--defined-only',str(SCRATCH/'mainlcd.o')],text=True)
 fixture=json.loads((ROOT/'uc-library/tests/recovery/trial08/mainlcd/native-fixtures.json').read_text())
 for record in fixture['range_checks']:
  symbol=record['original']['mangled'];assert symbol in [x.split()[-1] for x in output.splitlines()],symbol
 print('10 exact original ELF mangled symbols present; Linux ELF has no Mach-O decoration')
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['compile','symbols']);args=ap.parse_args();globals()[args.mode]()
