import argparse,json,subprocess,sys,pathlib,time,datetime
ROOT=pathlib.Path(__file__).resolve().parents[3]
C=ROOT/'uc-library/candidates/graph-live-trial-05-scenes'
S=ROOT/'temp/recovery-work/graph-live-trial-05/scenes-worker'
S.mkdir(exist_ok=True)
sources=['uc-library/src/Presonus/StormMixSceneComponent.cpp','uc-library/tests/graph_trial05_scenes_tests.cpp','uc-library/src/Presonus/DelayTimer.cpp']
files=sources[:2]+['uc-library/include/presonus/StormMixSceneComponent.hpp']
def run(argv):
 t=time.time();p=subprocess.run(argv,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);print(p.stdout,end='');
 with (S/'checks.log').open('a') as f:f.write(json.dumps(argv)+'\n'+p.stdout+'\n')
 with (S/'tool-times.jsonl').open('a') as f:f.write(json.dumps({'argv':argv,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'duration_seconds':time.time()-t,'returncode':p.returncode})+'\n')
 if p.returncode:raise SystemExit(p.returncode)
 return p.stdout
p=argparse.ArgumentParser();p.add_argument('mode');p.add_argument('--executable');a=p.parse_args()
if a.mode=='format':run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror']+files)
elif a.mode=='compile':
 flags=['-std=c++17','-fno-rtti','-pthread','-Ulinux','-DCORE_USE_OPENSSL=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-Iuc-library/include','-Ithird_party/ccl-framework']
 for i,src in enumerate(sources):run(['/usr/bin/c++']+flags+['-c',src,'-o',str(S/f'{i}.o')])
 lib='temp/core-upstream/root-integration-01/'
 run(['/usr/bin/c++','-pthread',str(S/'0.o'),str(S/'1.o'),str(S/'2.o'),lib+'libpresonus_rm_components.a',lib+'upstream-core/sdk/lib/libcorelib.a',lib+'upstream-core/sdk/lib/libpresonus_core_allocator.a','/usr/lib/x86_64-linux-gnu/libpng16.so.16','/usr/lib/x86_64-linux-gnu/libz.so.1','-lssl','-lcrypto','temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so','-ldl',lib+'private-glibc29-provider/libpresonus_private_glibc29.a','-lm','-Wl,-rpath,'+str(ROOT/'temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu'),'-o',str(S/'scenes-test')])
elif a.mode=='symbols':
 symbols=run(['nm','--defined-only',str(S/'0.o')])
 for i in range(1,6):
  manifest=json.loads((ROOT/f'temp/recovery-work/graph-live-trial-05/trial05_scenes_{i}-packet/context.json').read_text())
  for item in manifest['originals']:
   o=item['original']
   name=o.get('mangled',o.get('original_mangled'));assert name in symbols,name
elif a.mode=='replay':
 assert a.executable,'explicit built executable required'
 cases=json.loads((C/'fixtures.json').read_text())['cases']
 for case in cases:
  out=run([a.executable]+list(map(str,case['inputs']))).strip()
  assert out==case['observation'],(case,out)
 print('Matched',len(cases),'native fixture observations')
 run([a.executable,'--provider-smoke'])
else:raise SystemExit(2)
