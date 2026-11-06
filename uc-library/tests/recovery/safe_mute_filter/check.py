"""Worker-local compile, exact symbol, fixture replay and prior Storm regressions."""
import argparse,importlib.util,json,os,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[4]
BASE=pathlib.Path('uc-library/tests/recovery/safe_mute_filter')
SCRATCH=pathlib.Path('temp/recovery-work/rolling200-02/safe-mute103')
EXE=SCRATCH/'replay'
SOURCES=['uc-library/src/Presonus/StormSafeMuteFilter.cpp','uc-library/src/Presonus/StormMuteGroupComponent.cpp','uc-library/tests/recovery/SafeMuteFilterReplay.cpp']
LIB='temp/core-upstream/root-integration-01/'
COMPILE=['/usr/bin/c++','-std=c++17','-fno-rtti','-Wno-multichar','-Ulinux','-pthread','-DCORE_USE_OPENSSL=1','-Iuc-library/include','-isystem','third_party/ccl-framework','-isystem',LIB+'upstream-core/sdk/include/presonus-core-5',*SOURCES,'-o',str(EXE),'-Wl,-rpath,'+str(ROOT/'temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu'),'-Wl,--start-group',LIB+'libpresonus_rm_components.a',LIB+'upstream-core/sdk/lib/libcorelib.a',LIB+'upstream-core/sdk/lib/libpresonus_core_allocator.a',LIB+'private-glibc29-provider/libpresonus_private_glibc29.a','-Wl,--end-group','-lpng16','-lz','-lssl','-lcrypto','-Ltemp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu','-ldns_sd','-ldl','-lm']
def run(argv,**kw):
 print(json.dumps(argv),flush=True)
 r=subprocess.run(argv,cwd=ROOT,env={**os.environ,'TMPDIR':str(ROOT/SCRATCH)},capture_output=True,text=True,**kw)
 if r.returncode:print(r.stdout+r.stderr);r.check_returncode()
 return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['compile','symbols','replay','regression']);p.add_argument('--executable',default=str(EXE));p.add_argument('--fixtures',default=str(BASE/'fixtures.json'));a=p.parse_args();(ROOT/SCRATCH).mkdir(parents=True,exist_ok=True)
 if a.mode=='compile':print(run(COMPILE).stdout)
 elif a.mode=='symbols':
  names={line.split()[-1] for line in run(['/usr/bin/nm','--defined-only',a.executable]).stdout.splitlines()}
  for method in ['shouldLoad','shouldSave']:
   name='_ZNK8Presonus23StormMuteGroupComponent14SafeMuteFilter10'+method+'EiPKcPv';assert name in names,name;print(name)
  print('Two exact host ELF names; no original return or ARM ABI claim')
 elif a.mode=='replay':
  cases=json.loads((ROOT/a.fixtures).read_text())['cases'];r=run([a.executable],input=''.join(' '.join(map(str,c['input']))+'\n' for c in cases))
  lines=r.stdout.splitlines();assert len(lines)==len(cases),(len(lines),len(cases))
  for i,(c,line) in enumerate(zip(cases,lines)):
   got=list(map(int,line.split()));want=[c['result'],len(c['final'])]+c['final'];assert got==want,(i,c['input'],got,want)
  print(r.stderr,end='');print(len(cases),'native/provider differential cases: return and complete ordered pointer list; real CCL Parameter/IStorageFilter/Vector')
 else:
  old=pathlib.Path('uc-library/tests/recovery/trial07/mutegroup/check.py');spec=importlib.util.spec_from_file_location('prior',ROOT/old);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  argv=module.argv();argv[argv.index('-o')+1]=str(SCRATCH/'prior-storm');print(run(argv).stdout)
  r=run(['uc-library/.venv/bin/python','uc-library/tests/recovery/trial07/mutegroup/replay.py','--executable',str(SCRATCH/'prior-storm'),'--fixtures','uc-library/tests/recovery/trial07/mutegroup/native-fixtures.json']);print(r.stdout)
