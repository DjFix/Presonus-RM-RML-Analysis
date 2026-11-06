"""Local actual-provider compile, exact symbol and differential replay."""
import argparse,json,os,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[4]
BASE=pathlib.Path('uc-library/tests/recovery/scene_filter')
SCRATCH=pathlib.Path('temp/recovery-work/rolling200-02/scene133')
EXE=SCRATCH/'replay'
SOURCES=['uc-library/src/Presonus/Mixer/SceneFilter.cpp','uc-library/src/Presonus/Mixer/ChannelComponent.cpp','uc-library/src/Presonus/Mixer/FilterGroupComponent.cpp','uc-library/src/Presonus/Mixer/FXBusComponent.cpp','uc-library/src/Presonus/Mixer/MasterSectionComponent.cpp','uc-library/src/Presonus/Mixer/NetworkSelectComponent.cpp','uc-library/src/Presonus/Mixer/PermissionsComponent.cpp','uc-library/tests/recovery/SceneFilterReplay.cpp']
LIB='temp/core-upstream/root-integration-01/'
COMPILE=['/usr/bin/c++','-std=c++17','-fno-rtti','-Wno-multichar','-Ulinux','-pthread','-DCORE_USE_OPENSSL=1','-Iuc-library/include','-isystem','third_party/ccl-framework','-isystem',LIB+'upstream-core/sdk/include/presonus-core-5',*SOURCES,'-o',str(EXE),'-Wl,-rpath,'+str(ROOT/'temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu'),'-Wl,--start-group',LIB+'libpresonus_rm_components.a',LIB+'libpresonus_uc.a',LIB+'upstream-core/sdk/lib/libcorelib.a',LIB+'upstream-core/sdk/lib/libpresonus_core_allocator.a',LIB+'private-glibc29-provider/libpresonus_private_glibc29.a','-Wl,--end-group','-lpng16','-lz','-lssl','-lcrypto','-Ltemp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu','-ldns_sd','-ldl','-lm']
def run(argv,**kw):
 print(json.dumps(argv),flush=True)
 r=subprocess.run(argv,cwd=ROOT,env={**os.environ,'TMPDIR':str(ROOT/SCRATCH)},capture_output=True,text=True,**kw)
 if r.returncode:print(r.stdout+r.stderr);r.check_returncode()
 return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['compile','symbols','replay','regressions']);p.add_argument('--executable',default=str(EXE));p.add_argument('--fixtures',default=str(BASE/'fixtures.json'));a=p.parse_args();(ROOT/SCRATCH).mkdir(parents=True,exist_ok=True)
 if a.mode=='compile':print(run(COMPILE).stdout)
 elif a.mode=='regressions':
  driver='uc-library/tests/graph_trial07_channel_tests.cpp';exe=str(SCRATCH/'channel-regression')
  argv=COMPILE.copy();start=argv.index(SOURCES[0]);stop=argv.index('-o');argv[start:stop]=['uc-library/src/Presonus/Mixer/ChannelComponent.cpp',driver];argv[argv.index('-o')+1]=exe
  run(argv)
  print(run(['uc-library/.venv/bin/python','uc-library/tests/recovery/trial07/channel/replay.py','--executable',exe,'--fixtures','uc-library/tests/recovery/trial07/channel/native-fixtures.json']).stdout)
  for mode in ['compile','symbols','replay']:
   print(run(['uc-library/.venv/bin/python','uc-library/tests/recovery/filter_group_configured/check.py',mode]).stdout)
 elif a.mode=='symbols':
  names={line.split()[-1] for line in run(['/usr/bin/nm','--defined-only',a.executable]).stdout.splitlines()}
  for p in sorted((ROOT/'temp/recovery-work/rolling200-02/next-implementation133/prepared133/packets').glob('*')):
   for target in json.loads((p/'request.json').read_text())['targets']:
    assert target['mangled'] in names,target['mangled'];print(target['mangled'])
 else:
  fixture=json.loads((ROOT/a.fixtures).read_text());cases=fixture['cases'];refresh=fixture['refresh']
  inputs=['D '+' '.join(map(str,c['input'])) for c in cases]
  for c in refresh:
   variant,values,present,cache,missing=c['input']
   # Complete cache retention is independently exercised by lifecycle().
   if cache:continue
   inputs.append('R '+' '.join(map(str,[variant,present,cache,missing,*values])))
  r=run([a.executable],input='\n'.join(inputs)+'\n');lines=r.stdout.splitlines();assert len(lines)==len(inputs),(len(lines),len(inputs))
  for i,(c,line) in enumerate(zip(cases,lines)):assert int(line)==c['result'],(i,c,line)
  offset=len(cases)
  for c,line in zip([c for c in refresh if not c['input'][3]],lines[offset:]):
   fault,mask=map(int,line.split());assert bool(fault)==c['fault'],(c,line)
   if not fault:assert mask==c['mask'],(c,line)
  print(r.stderr,end='');print(len(inputs),'exact application ARM/provider cases and typed hierarchy/lifecycle checks')
