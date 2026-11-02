#!/usr/bin/env python3
"""Worker-local compile and exact original mangling checks; no shared build writes."""
import argparse,json,subprocess,datetime,hashlib
from pathlib import Path
SCRATCH=Path('temp/recovery-work/graph-live-trial-07/mapping-worker')
EXE=SCRATCH/'graph_trial07_mapping_tests'
SOURCES=['uc-library/src/Presonus/Surface/MappingComponent.cpp','uc-library/tests/graph_trial07_mapping_tests.cpp','uc-library/src/Presonus/Surface/MappingInputRoutes.cpp','uc-library/src/Presonus/Surface/MappingRadioRoutes.cpp','uc-library/src/Presonus/Surface/MappingMeterRouting.cpp','uc-library/src/Presonus/Surface/MappingRadioValidation.cpp','uc-library/src/Presonus/DelayTimer.cpp']
def compile_cmd():
 root=Path.cwd();build=root/'temp/core-upstream/root-integration-01'; sdk=build/'upstream-core/sdk'
 return ['/usr/bin/c++','-std=c++17','-O2','-g','-fno-rtti','-fno-lto','-Wl,--wrap=_ZN8Presonus7Surface16MappingComponent16verifyRadioParamEPN4Core8Portable9ParameterE','-fno-fast-math','-ffp-contract=off','-pthread','-Ulinux','-DCORE_USE_OPENSSL=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-Iuc-library/include','-I'+str(sdk/'include/presonus-core-5')]+SOURCES+['-o',str(EXE),str(sdk/'lib/libcorelib.a'),str(sdk/'lib/libpresonus_core_allocator.a'),'/usr/lib/x86_64-linux-gnu/libpng16.so.16','/usr/lib/x86_64-linux-gnu/libz.so.1','/usr/lib/x86_64-linux-gnu/libssl.so','/usr/lib/x86_64-linux-gnu/libcrypto.so',str(root/'temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so'),'-ldl',str(build/'private-glibc29-provider/libpresonus_private_glibc29.a'),'-lm','-Wl,-rpath,'+str(root/'temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu')]
def main():
 p=argparse.ArgumentParser();p.add_argument('kind',choices=['compile','symbols']);a=p.parse_args()
 if a.kind=='compile':
  cmd=compile_cmd();print(json.dumps(cmd));subprocess.run(cmd,check=True)
 else:
  out=subprocess.check_output(['/usr/bin/nm','--defined-only',str(EXE)],text=True);names={l.split()[-1] for l in out.splitlines() if l.split()}
  for i in range(1,11):
   c=json.loads(Path(f'temp/recovery-work/graph-live-trial-07/trial07_mapping_{i}-packet/context.json').read_text())
   for entry in c['originals']:
    o=entry['original']
    n=o.get('mangled',o.get('original_mangled')); assert n in names,n;print(n)
  helper='_ZN8Presonus7Surface16MappingComponent16verifyRadioParamEPN4Core8Portable9ParameterE'
  assert helper in names,helper
  assert '__wrap_'+helper in names,'test wrapper missing'
  print('Actual canonical helper and test-only wrapper symbols both present:',helper)
  print('PASS ten exact ELF manglings; Linux ELF has no Mach-O decoration; no ARM ABI claim')
if __name__=='__main__':main()
