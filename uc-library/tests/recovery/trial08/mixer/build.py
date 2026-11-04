"""Standalone local build for the MixerComponent source-port regression."""
import argparse,os,pathlib,subprocess
p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=True)
env=os.environ.copy();env['TMPDIR']=str(out.resolve())
common=['/usr/bin/c++','-std=c++17','-Ulinux','-pthread','-Wno-multichar','-DCORE_USE_OPENSSL=1','-Iuc-library/include','-Ithird_party/ccl-framework']
commands=[]
for source,name in [('uc-library/src/Presonus/Mixer/MixerComponent.cpp','mixer.o'),('uc-library/tests/graph_trial08_mixer_tests.cpp','test.o')]:
 commands.append(common+(['-frtti'] if name=='mixer.o' else ['-fno-rtti'])+['-c',source,'-o',str(out/name)])
base='temp/core-upstream/root-integration-01/'
commands.append(['/usr/bin/c++','-pthread',str(out/'mixer.o'),str(out/'test.o'),base+'libpresonus_rm_components.a',base+'upstream-core/sdk/lib/libcorelib.a',base+'upstream-core/sdk/lib/libpresonus_core_allocator.a','/usr/lib/x86_64-linux-gnu/libpng16.so.16','/usr/lib/x86_64-linux-gnu/libz.so.1','/usr/lib/x86_64-linux-gnu/libssl.so','/usr/lib/x86_64-linux-gnu/libcrypto.so','temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so','-ldl',base+'private-glibc29-provider/libpresonus_private_glibc29.a','-Wl,-rpath,'+str(pathlib.Path('temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu').resolve()),'-lm','-o',str(out/'mixer-tests')])
for command in commands:
 print(command,flush=True);subprocess.run(command,check=True,env=env)
