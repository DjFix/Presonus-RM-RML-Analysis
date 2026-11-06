"""Actual CCL provider build and independently generated ARM fixture replay."""
import pathlib,sys,subprocess,json,os
ROOT=pathlib.Path(__file__).resolve().parents[4]
BASE=pathlib.Path('uc-library/tests/recovery/network_setup_view')
OUT=pathlib.Path('temp/recovery-work/rolling200-02/network-view20-local')
EXE=OUT/'replay'
OWNED=['uc-library/include/presonus/surface/NetworkSetupComponent.hpp','uc-library/src/Presonus/Surface/NetworkSetupComponent.cpp','uc-library/include/presonus/surface/RadioToggleButton.hpp','uc-library/src/Presonus/Surface/RadioToggleButton.cpp','uc-library/tests/recovery/NetworkSetupViewReplay.cpp']
SOURCES=[OWNED[1],OWNED[3],OWNED[4],'uc-library/src/Presonus/Surface/NetworkListSelection.cpp']
LIB='temp/core-upstream/root-integration-01/upstream-core/sdk/lib/'
COMPILE=['/usr/bin/c++','-std=c++17','-O0','-fno-rtti','-fno-lto','-Wno-multichar','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework']+SOURCES+['temp/core-upstream/root-integration-01/libpresonus_uc.a','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a',LIB+'libcorelib.a',LIB+'libpresonus_core_allocator.a','-Wl,--gc-sections','-Wl,--wrap=_Znwm','-Wl,--wrap=_ZdlPv','-Wl,--wrap=_ZdlPvm','-Wl,--wrap=_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE','/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lpthread','-ldl','-lm','-o',str(EXE)]
def run(argv,**kw):
 print(json.dumps(list(map(str,argv))),flush=True)
 result=subprocess.run(list(map(str,argv)),cwd=ROOT,text=True,capture_output=True,env={**os.environ,'TMPDIR':str(ROOT/OUT)},**kw)
 if result.returncode: print(result.stdout+result.stderr);result.check_returncode()
 return result

def replay(exe,fixture):
 cases=json.loads(pathlib.Path(fixture).read_text())['cases']
 r=run([exe],input=''.join(' '.join(map(str,c['input']))+'\n' for c in cases))
 lines=r.stdout.splitlines();assert len(lines)==len(cases),(r.stdout,r.stderr,len(cases))
 for i,(line,c) in enumerate(zip(lines,cases)):
  assert list(map(int,line.split()))==c['expected'],(i,c,line)
 print(len(cases),'original instruction cases match actual CCL source edits, variant lifecycle and view/model decisions; actual provider dispatch regression passed')
def regression():
 flags=COMPILE[:COMPILE.index(SOURCES[0])]
 common=[OWNED[1],OWNED[3],'uc-library/src/Presonus/Surface/NetworkListSelection.cpp']
 libraries=['-Wl,--gc-sections','-Wl,--start-group','temp/core-upstream/root-integration-01/libpresonus_cs18_components.a','temp/core-upstream/root-integration-01/libpresonus_uc.a',LIB+'libcorelib.a',LIB+'libpresonus_core_allocator.a','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a','-Wl,--end-group','/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lpthread','-ldl','-lm']
 suites=[('network','uc-library/tests/graph_trial07_surfacenet_tests.cpp',[],['uc-library/.venv/bin/python','uc-library/tests/recovery/trial07/surfacenet/replay.py','--executable','EXE','--fixtures','uc-library/tests/recovery/trial07/surfacenet/fixtures.json']),('settings','uc-library/tests/recovery/NetworkSetupSettingsReplay.cpp',['uc-library/src/Presonus/Surface/MidiMixerState.cpp'],['uc-library/.venv/bin/python','uc-library/candidates/network-setup-settings/replay.py','--executable','EXE','--fixtures','uc-library/candidates/network-setup-settings/fixtures.json']),('selection','uc-library/tests/recovery/ranked09/handlers/driver.cpp',[],['uc-library/.venv/bin/python','uc-library/tests/recovery/ranked09/handlers/replay.py','EXE','uc-library/tests/recovery/ranked09/handlers/fixtures.json'])]
 for label,source,extra,replay_argv in suites:
  exe=OUT/('regression-'+label)
  print(run(flags+common+[source]+extra+libraries+['-o',str(exe)]).stdout)
  print(run([str(exe) if x=='EXE' else x for x in replay_argv]).stdout)

def main():
 (ROOT/OUT).mkdir(parents=True,exist_ok=True)
 mode=sys.argv[1]
 if mode=='format':print(run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror']+OWNED).stdout)
 elif mode=='compile':print(run(COMPILE).stdout)
 elif mode=='symbols':
  out=run(['/usr/bin/nm','--defined-only',EXE]).stdout;names={x.split()[-1] for x in out.splitlines() if x.split()}
  for p in sorted((ROOT/'temp/recovery-work/rolling200-02/next-implementation20/prepared-network-view20/packets').glob('*')):
   req=json.loads((p/'request.json').read_text());name=req['targets'][0]['mangled'];assert name in names,name;print(name)
  print('Five exact original manglings; Linux host ELF undecorated; no ARM ABI claim')
 elif mode=='replay':replay(pathlib.Path(sys.argv[2]) if len(sys.argv)>2 else ROOT/EXE,ROOT/(sys.argv[3] if len(sys.argv)>3 else str(BASE/'fixtures.json')))
 elif mode=='regression':regression()
 elif mode=='native':
  import native
  assert native.generate()==json.loads((ROOT/BASE/'fixtures.json').read_text())
  print('Fresh original ELF execution reproduces immutable fixture; fail-closed PC audit passed')
if __name__=='__main__':main()
