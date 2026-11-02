"""Local acceptance compilation; production registration remains Root-owned."""
import argparse,json,os,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
env=dict(os.environ,TMPDIR=str(out.resolve()))
root=Path('temp/core-upstream/root-integration-01')
common=['/usr/bin/c++','-std=c++17','-fno-rtti','-DNDEBUG=1','-DCORE_USE_OPENSSL=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-Wno-multichar','-Iuc-library/include','-isystem',str(root/'upstream-core/sdk/include/presonus-core-5'),'-pthread','-Ulinux']
commands=[]
for source,name in [('uc-library/src/Presonus/Surface/NetworkSetupComponent.cpp','network.o'),('uc-library/tests/graph_trial07_surfacenet_tests.cpp','tests.o')]:
 commands.append(common+['-c',source,'-o',str(out/name)])
commands.append(['/usr/bin/c++','-pthread',str(out/'network.o'),str(out/'tests.o'),str(root/'libpresonus_cs18_components.a'),str(root/'upstream-core/sdk/lib/libcorelib.a'),str(root/'upstream-core/sdk/lib/libpresonus_core_allocator.a'),'/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lssl','-lcrypto','temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so','-ldl',str(root/'private-glibc29-provider/libpresonus_private_glibc29.a'),'-lm','-o',str(out/'replay')])
for cmd in commands:
 start=time.time();print(json.dumps({'argv':cmd,'start':start}),flush=True);subprocess.run(cmd,check=True,env=env);print(json.dumps({'duration_seconds':time.time()-start,'exit_code':0}),flush=True)
