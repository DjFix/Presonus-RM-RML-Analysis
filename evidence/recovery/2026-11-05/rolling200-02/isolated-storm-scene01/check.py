from pathlib import Path
import subprocess,json,hashlib,sys
R=Path.cwd(); O=R/'evidence/recovery/2026-11-05/rolling200-02/isolated-storm-scene01'; W=R/'temp/recovery-work/rolling200-02/storm-scene-local01'; W.mkdir(parents=True,exist_ok=True)
B=R/'temp/core-upstream/root-integration-01'; logs=[];mode=sys.argv[1]
def run(a):
 a=[str(x) for x in a];p=subprocess.run(a,cwd=R,text=True,capture_output=True);logs.append({'argv':a,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr});(W/(mode+'-commands.json')).write_text(json.dumps(logs,indent=2)+'\n');assert p.returncode==0,p.stderr
 return p.stdout
src=R/'uc-library/src/Presonus/StormMixSceneComponent.cpp';head=R/'uc-library/include/presonus/StormMixSceneComponent.hpp';driver=O/'driver.cpp';formatter=R/'uc-library/.venv/bin/clang-format'
if mode=='format':
 run([formatter,'--version']);run([formatter,'--style=file','--fallback-style=LLVM','--dry-run','--Werror',src,head,driver])
elif mode=='compile':
 for s,o in [(src,W/'scene.o'),(driver,W/'driver.o')]:
  run(['/usr/bin/c++','-std=c++17','-fno-rtti','-O2','-DCORE_USE_OPENSSL=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-Ulinux','-I'+str(R/'uc-library/include'),'-I'+str(B/'upstream-core/sdk/include/presonus-core-5'),'-c',s,'-o',o])
 run(['/usr/bin/c++',W/'scene.o',W/'driver.o','-o',W/'replay',B/'libpresonus_rm_components.a',B/'upstream-core/sdk/lib/libcorelib.a',B/'upstream-core/sdk/lib/libpresonus_core_allocator.a','/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lssl','-lcrypto',R/'temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so','-ldl',B/'private-glibc29-provider/libpresonus_private_glibc29.a','-lm','-pthread','-Wl,-rpath,'+str(R/'temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu')])
 run(['/usr/bin/c++','--version'])
elif mode=='symbols':
 syms=run(['/usr/bin/nm','--defined-only',W/'scene.o']); names={l.split()[-1] for l in syms.splitlines() if l.split()};assert '_ZNK8Presonus22StormMixSceneComponent17createDefaultNameEi' in names
else: raise ValueError(mode)
print(mode+' passed')
