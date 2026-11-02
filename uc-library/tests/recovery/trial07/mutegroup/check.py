#!/usr/bin/env python3
"""Scoped build and symbol checks. Writes only assigned worker scratch."""
import argparse,subprocess,json,hashlib,time,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[5]
SCRATCH=ROOT/'temp/recovery-work/graph-live-trial-07/mutegroup-worker'
SOURCE=['uc-library/src/Presonus/StormMuteGroupComponent.cpp','uc-library/tests/graph_trial07_mutegroup_tests.cpp']
def argv():
 lib='temp/core-upstream/root-integration-01/'
 return ['/usr/bin/c++','-std=c++17','-fno-rtti','-Wno-multichar','-Ulinux','-pthread','-DCORE_USE_OPENSSL=1','-Iuc-library/include','-isystem','third_party/ccl-framework','-isystem',lib+'upstream-core/sdk/include/presonus-core-5',*SOURCE,'-o',str(SCRATCH/'replay'),'-Wl,-rpath,'+str(ROOT/'temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu'),'-Wl,--start-group',lib+'libpresonus_rm_components.a',lib+'upstream-core/sdk/lib/libcorelib.a',lib+'upstream-core/sdk/lib/libpresonus_core_allocator.a',lib+'private-glibc29-provider/libpresonus_private_glibc29.a','-Wl,--end-group','-lpng16','-lz','-lssl','-lcrypto','-Ltemp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu','-ldns_sd','-ldl','-lm']
def main():
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['compile','symbols']);a=p.parse_args();SCRATCH.mkdir(parents=True,exist_ok=True)
 command=argv() if a.mode=='compile' else ['/usr/bin/nm','--defined-only',str(SCRATCH/'replay')]
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic();r=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,timeout=120);elapsed=time.monotonic()-tick
 (SCRATCH/(a.mode+'.log')).write_text(r.stdout+r.stderr)
 record={'argv':command,'start_utc':start,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'duration_seconds':elapsed,'exit_code':r.returncode}
 if a.mode=='symbols' and r.returncode==0:
  symbols={line.split()[-1] for line in r.stdout.splitlines() if line.strip()};originals=[]
  for i in range(1,11):
   d=json.loads((ROOT/f'temp/recovery-work/graph-live-trial-07/trial07_mutegroup_{i}-packet/context.json').read_text());name=d['originals'][0]['original']['mangled'];assert name in symbols,name;originals.append(name)
  record['matching_originals']=originals;record['decoration']='Linux ELF: no extra leading underscore';record['scope']='encoded original method identities only; unencoded returns/layout/ARM ABI unresolved'
 (SCRATCH/(a.mode+'-result.json')).write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2));raise SystemExit(r.returncode)
if __name__=='__main__':main()
