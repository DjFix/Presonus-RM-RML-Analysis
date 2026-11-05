from pathlib import Path
import subprocess,json,hashlib
R=Path.cwd();O=R/'evidence/recovery/2026-11-05/rolling200-02/storm-mute-isolated01';B=R/'temp/core-upstream/root-integration-01';logs=[]
def run(a):
 p=subprocess.run(a,cwd=R,text=True,capture_output=True);logs.append({'argv':a,'exit':p.returncode,'stdout':p.stdout,'stderr':p.stderr});(O/'COMMANDS.json').write_text(json.dumps(logs,indent=2)+'\n');assert p.returncode==0,p.stderr
 return p.stdout
sources=[R/'uc-library/src/Presonus/StormMuteGroupComponent.cpp',O/'driver.cpp'];headers=[R/'uc-library/include/presonus/StormMuteGroupComponent.hpp'];formatter=str(R/'uc-library/.venv/bin/clang-format');run([formatter,'--version']);run([formatter,'--style=file','--fallback-style=LLVM','--dry-run','--Werror',*[str(p) for p in sources+headers]])
objs=[]
for i,s in enumerate(sources):
 o=O/(str(i)+'.o');objs.append(str(o));run(['/usr/bin/c++','-std=c++17','-fno-rtti','-O2','-DCORE_USE_OPENSSL=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-Ulinux','-I'+str(R/'uc-library/include'),'-I'+str(B/'upstream-core/sdk/include/presonus-core-5'),'-c',str(s),'-o',str(o)])
run(['/usr/bin/c++',*objs,'-o',str(O/'replay'),str(B/'libpresonus_rm_components.a'),str(B/'upstream-core/sdk/lib/libcorelib.a'),str(B/'upstream-core/sdk/lib/libpresonus_core_allocator.a'),'/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lssl','-lcrypto',str(R/'temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so'),'-ldl',str(B/'private-glibc29-provider/libpresonus_private_glibc29.a'),'-lm','-pthread','-Wl,-rpath,'+str(R/'temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu')])
syms=run(['/usr/bin/nm','--defined-only',*objs[:1]]);names={l.split()[-1] for l in syms.splitlines() if l.split()}
for n in ['_ZNK8Presonus23StormMuteGroupComponent17createDefaultNameEi']:assert n in names,n
(O/'COMPILE_SYMBOLS.json').write_text(json.dumps({'passed':True,'original_functions':1,'source_hashes':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources+headers},'scope':'Isolated copied canonical sources; not shared production integration or admission.'},indent=2)+'\n');print('Actual C++ compiled; one exact original function symbol matches')
