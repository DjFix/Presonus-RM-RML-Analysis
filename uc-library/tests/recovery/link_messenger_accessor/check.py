import argparse,json,subprocess
from pathlib import Path
BASE=Path('uc-library/tests/recovery/link_messenger_accessor')
CPP='uc-library/src/Presonus/Link/Messenger.cpp'
TEST='uc-library/tests/recovery/LinkMessengerAccessorReplay.cpp'
HEAD='uc-library/include/presonus/link/Messenger.hpp'
EXE='temp/recovery-work/rolling200-03/messenger01/local/accessor'
LIB='temp/core-upstream/root-integration-01/upstream-core/sdk/lib/'
WRAPS=['_Znwm','_ZdlPv','_ZdlPvm','_ZN4Core8Platform9PosixLockC1Ev','_ZN4Core8Platform9PosixLockD1Ev','_ZN4Core8Portable9Deletable11addInstanceEPS1_']
COMPILE=['/usr/bin/c++','-std=c++17','-O0','-fno-rtti','-Wno-multichar','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework',CPP,TEST,LIB+'libcorelib.a',LIB+'libpresonus_core_allocator.a','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a','-Wl,--gc-sections',*['-Wl,--wrap='+x for x in WRAPS],'-lpthread','-ldl','-lm','-o',EXE]
def run(argv):
 print(json.dumps(argv),flush=True);subprocess.run(argv,check=True)
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['format','compile','symbols','native','replay','regression']);p.add_argument('--executable',default=EXE);p.add_argument('--fixtures',default=str(BASE/'fixtures.json'));a=p.parse_args()
 if a.mode=='format':run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',CPP,HEAD,TEST])
 if a.mode=='compile':Path(EXE).parent.mkdir(parents=True,exist_ok=True);run(COMPILE)
 if a.mode=='symbols':
  text=subprocess.check_output(['nm','--defined-only',a.executable],text=True)
  assert any(line.split()[-1]=='_ZN8Presonus4Link12getMessengerEv' for line in text.splitlines());print('exact original symbol matched')
 if a.mode=='native':
  from native import observations
  observed=observations();assert observed==json.loads(Path(a.fixtures).read_text());print('4 native app-body cases matched')
 if a.mode=='regression':
  binary=str(Path(EXE).parent/'messenger-regression')
  for mode in ['compile','symbols','replay']:run(['uc-library/.venv/bin/python','uc-library/candidates/rolling200_impl_c22/check.py',mode,binary])
 if a.mode=='replay':
  fixture=json.loads(Path(a.fixtures).read_text());assert len(fixture['cases'])==4
  for mode in ['normal','allocation-failure','construction-failure']:run([str(Path(a.executable).resolve()),mode])
  print('3 isolated portable processes, 303 user-side calls plus 3 registration probes; actual CCL exit destruction')
if __name__=='__main__':main()
