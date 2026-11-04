"""Build owned regression/provider executables with the actual pinned CCL."""
import argparse
import os
from pathlib import Path
import subprocess
p=argparse.ArgumentParser();p.add_argument('--provider-only',action='store_true');a=p.parse_args()
root=Path.cwd();scratch=root/'temp/recovery-work/graph-live-trial-08/mixerbase-worker/final-five-01';scratch.mkdir(exist_ok=True,parents=True)
env=dict(os.environ,TMPDIR=str(scratch))
build=root/'temp/core-upstream/root-integration-01'
core=build/'upstream-core/sdk/lib';deps=root/'temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu'
flags=['c++','-std=c++17','-O2','-fno-rtti','-Wall','-Wextra','-Werror','-pthread','-Ulinux','-Iuc-library/include','-isystem',str(build/'upstream-core/sdk/include/presonus-core-5')]
links=[str(build/'libpresonus_rm_components.a'),str(core/'libcorelib.a'),str(core/'libpresonus_core_allocator.a'),'/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lssl','-lcrypto',str(deps/'libdns_sd.so'),'-ldl',str(build/'private-glibc29-provider/libpresonus_private_glibc29.a'),'-lm','-Wl,-rpath,'+str(deps)]
argv=flags+['uc-library/tests/recovery/trial08/mixerbase/finalfive/provider.cpp','-o',str(scratch/'provider')]+links
print(argv,flush=True);subprocess.run(argv,env=env,check=True)
if not a.provider_only:
 argv=flags+['uc-library/src/Presonus/Mixer/MixerComponentBase.cpp','uc-library/src/Presonus/Mixer/PermissionsComponent.cpp','uc-library/src/Presonus/Mixer/MixerBaseLinks.cpp','uc-library/tests/recovery/trial08/mixerbase/finalfive/tests.cpp','-o',str(scratch/'tests')]+links
 print(argv,flush=True);subprocess.run(argv,env=env,check=True)

if not a.provider_only:
 argv=flags+['uc-library/src/Presonus/Mixer/MixerComponentBase.cpp','uc-library/src/Presonus/Mixer/PermissionsComponent.cpp','uc-library/tests/graph_trial08_mixerbase_tests.cpp','-o',str(scratch/'raw-tests')]+links
 print(argv,flush=True);subprocess.run(argv,env=env,check=True)
