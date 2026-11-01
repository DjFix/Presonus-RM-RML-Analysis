import subprocess,sys,pathlib,json
root=pathlib.Path('uc-library/candidates/graph-live-trial-05-linkcontrol');exe='temp/recovery-work/graph-live-trial-05/linkcontrol-worker/test'
if sys.argv[1]=='compile':
 argv=['/usr/bin/c++','-w','-fno-rtti','-std=c++17','-DNDEBUG','-Ulinux','-Iuc-library/include','-Ithird_party/ccl-framework','uc-library/tests/graph_trial05_linkcontrol_tests.cpp','uc-library/src/Presonus/LinkControl.cpp','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a','-lpng','-lz','-lssl','-lcrypto','-Ltemp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu','-Wl,-rpath,'+str(pathlib.Path('temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu').resolve()),'-ldns_sd','-ldl','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a','-lm','-pthread','-o',exe];subprocess.run(argv,check=True)
else:
 text=subprocess.check_output(['nm','--defined-only',exe],text=True)
 for row in json.loads((root/'range-checks.json').read_text())['ranges']:assert row['mangled'] in text,row
 print('five original names matched; ELF host symbols; ABI pending')
