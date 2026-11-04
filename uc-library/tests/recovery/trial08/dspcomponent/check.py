import os,pathlib,subprocess,sys,json
root=pathlib.Path(__file__).resolve().parents[5]
os.chdir(root)
out=pathlib.Path('temp/recovery-work/graph-live-trial-08/dspcomponent-worker');out.mkdir(exist_ok=True,parents=True);os.environ['TMPDIR']=str(out.resolve())
source='uc-library/src/Presonus/DspComponent.cpp';test='uc-library/tests/graph_trial08_dspcomponent_tests.cpp';exe=str(out/'replay')
if sys.argv[1]=='compile':
 subprocess.run(['c++','-std=c++17','-O3','-DNDEBUG','-frtti','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework',source,test,'temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a','-ldl','-lpthread','-o',exe],check=True)
 subprocess.run(['c++','-std=c++17','-O3','-DNDEBUG','-frtti','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework','-c',source,'-o',str(out/'source.o')],check=True)
elif sys.argv[1]=='symbols':
 text=subprocess.check_output(['nm','--defined-only',str(out/'source.o')],text=True);rows=json.loads((out/'ranges.json').read_text())
 for row in rows:assert row['mangled'] in text,row
 print('10 selected mangled names match; emitted C2 has no validation credit')
elif sys.argv[1]=='replay':
 for fixture in ['native-simple.json','native-control.json']:
  subprocess.run([sys.executable,'uc-library/tests/recovery/trial08/dspcomponent/replay.py','--executable',exe,'--fixture','uc-library/tests/recovery/trial08/dspcomponent/'+fixture],check=True)
else:raise SystemExit(2)
