"""Local compile/symbol checks; no shared build changes."""
import pathlib,subprocess,os,sys,json
ROOT=pathlib.Path(__file__).resolve().parents[5]
os.chdir(ROOT)
SCRATCH=ROOT/'temp/recovery-work/graph-live-trial-08/mappingtable-worker';SCRATCH.mkdir(parents=True,exist_ok=True)
env=dict(os.environ,TMPDIR=str(SCRATCH))
if sys.argv[1]=='compile':
 argv=['g++','-std=c++17','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework','uc-library/src/Presonus/MappingTable.cpp','uc-library/src/Presonus/MappingTableTrial08.cpp','uc-library/tests/graph_trial08_mappingtable_tests.cpp','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','-lpthread','-ldl','-lrt','-o',str(SCRATCH/'test')]
 print(json.dumps(argv),flush=True);subprocess.run(argv,env=env,check=True)
elif sys.argv[1]=='symbols':
 result=subprocess.check_output(['nm','--defined-only',str(SCRATCH/'test')],text=True)
 symbols=set(line.split()[-1] for line in result.splitlines() if line.split())
 expected=['_ZN8Presonus12MappingTable19setControlBlinkModeEPKcS2_','_ZN8Presonus12MappingTable8mapColorERKN4Core5ColorE','_ZN8Presonus12MappingTable17addMainScreenPageEPNS_25IMainScreenPageControllerE','_ZN8Presonus12MappingTable15setPanelControlEPKcPNS_5Panel7ControlES2_','_ZN8Presonus12MappingTable8mapColorEPKc','_ZN8Presonus12MappingTable19connectAltParameterEPKcPN4Core8Portable9ParameterE','_ZN8Presonus12MappingTable24connectTertiaryParameterEPKcPN4Core8Portable9ParameterE','_ZNK8Presonus12MappingTable8findPageEPKc','_ZN8Presonus12MappingTable15setControlColorEPKcS2_','_ZN8Presonus12MappingTable22setControlDefaultColorEPKcS2_b']
 assert set(expected)<=symbols, set(expected)-symbols
 print('\n'.join(expected));print('PASS 10 exact ELF Itanium symbols; Linux object format has no Mach-O decoration')
else:raise SystemExit(2)
