#!/usr/bin/env python3
"""Build scoped source and differential replay without changing shared build files."""
import argparse,json,os,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out',default='temp/recovery-work/network-item-settings');a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
env=dict(os.environ,TMPDIR=str(out.resolve()))
flags=['c++','-std=c++17','-fno-rtti','-Wno-multichar','-ffunction-sections','-fdata-sections','-Iuc-library/include','-Ithird_party/ccl-framework','-Itemp/core-upstream/root-integration-01/upstream-core/sdk/include/presonus-core-5']
obj=str(out/'NetworkSetupComponent.o');exe=str(out/'replay')
cmds=[flags+['-c','uc-library/src/Presonus/Surface/NetworkSetupComponent.cpp','-o',obj],flags+['uc-library/tests/recovery/NetworkItemSettingsReplay.cpp',obj,'uc-library/src/Presonus/UC/NetworkItem.cpp','-Wl,--gc-sections','-Wl,--start-group']+[f'temp/core-upstream/root-integration-01/{x}' for x in ['libpresonus_cs18_components.a','libpresonus_uc.a','upstream-core/sdk/lib/libcorelib.a','upstream-core/sdk/lib/libpresonus_core_allocator.a','private-glibc29-provider/libpresonus_private_glibc29.a']]+['-Wl,--end-group','-lpthread','-ldl','-lz','-o',exe]]
for i,cmd in enumerate(cmds):
 print(json.dumps({'argv':cmd}),flush=True);r=subprocess.run(cmd,text=True,capture_output=True,env=env);(out/f'compile-{i}.log').write_text(r.stdout+r.stderr);print(r.stdout+r.stderr,end='');assert r.returncode==0
print(json.dumps({'object':obj,'executable':exe,'passed':True}))
