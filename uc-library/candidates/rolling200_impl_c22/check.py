import sys,subprocess,pathlib,json
base=pathlib.Path('uc-library/candidates/rolling200_impl_c22'); binary='temp/recovery-work/rolling200-implementation01/messenger-replay'
if len(sys.argv) > 2:
 binary=sys.argv[2]
compile=['c++','-std=c++17','-Iuc-library/include','-Ithird_party/ccl-framework','-DCORE_PLATFORM_LINUX=1',str(base/'replay.cpp'),'uc-library/src/Presonus/Link/Messenger.cpp','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','-pthread','-ldl','-Wl,--wrap=_ZdlPvm','-o',binary]
if sys.argv[1]=='compile': subprocess.run(compile,check=True)
elif sys.argv[1]=='symbols':
 s=subprocess.check_output(['nm','--defined-only',binary],text=True)
 symbols={line.split()[-1] for line in s.splitlines() if len(line.split()) >= 3}
 for suffix in ['7releaseEv','C1Ev','C2Ev','D0Ev','D1Ev']:assert '_ZN8Presonus4Link9Messenger'+suffix in symbols
elif sys.argv[1]=='replay':
 actual=json.loads(subprocess.check_output(['uc-library/.venv/bin/python',str(base/'native.py')],text=True));fixture=json.loads((base/'native.json').read_text());assert actual==fixture
 for c in actual['cases']:
  n=c['task'][-2:]
  if n=='01': assert c['release']==1 and c['trace']==[]
  if n in ['02','03']:assert c['word8']==c['word12']==c['release']==0 and [x['pc'] for x in c['trace']]==[0x10e5e8,0x116a38,0x116a38,0x116a38]
  if n in ['04','05']:assert c['singleton']==(0 if c['match'] else 0x800100) and [x['pc'] for x in c['trace']]==([0x10e4cc,0xac10] if n=='04' else [0x10e4cc])
 subprocess.run([binary],check=True)
 print('10 exact-range native cases match sealed fixture; portable provider replay passed; allocator native entry is observation only')
else:raise ValueError(sys.argv[1])
