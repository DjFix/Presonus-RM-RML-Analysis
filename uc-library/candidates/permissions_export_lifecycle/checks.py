#!/usr/bin/env python3
import argparse,hashlib,json,os,subprocess,time
from pathlib import Path
BASE=Path('uc-library/candidates/permissions_export_lifecycle')
WORK=Path('temp/recovery-work/permissions-export-lifecycle-local01')
EVIDENCE=Path('evidence/recovery/2026-11-05/permissions-export-lifecycle01')
SDK=Path('temp/core-upstream/root-integration-01/upstream-core/sdk')
SOURCES=['uc-library/include/presonus/mixer/PermissionsComponent.hpp','uc-library/src/Presonus/Mixer/PermissionsComponent.cpp','uc-library/tests/recovery/PermissionsExportLifecycleReplay.cpp','uc-library/candidates/permissions_export_lifecycle/header_consumer.cpp']
PACKETS=Path('temp/recovery-work/rolling200-02/next-implementation08/prepared09-permissions_lifecycle08/packets')
def run(argv):
 argv=list(map(str,argv));print(json.dumps(argv),flush=True);t=time.monotonic();r=subprocess.run(argv,capture_output=True,text=True)
 with (WORK/'commands.jsonl').open('a') as f:f.write(json.dumps(dict(argv=argv,seconds=time.monotonic()-t,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))+'\n')
 if r.returncode:print(r.stdout,r.stderr,flush=True);r.check_returncode()
 return r.stdout

def compile_check(sanitize=False):
 flags=['/usr/bin/c++','-std=c++17','-O1' if sanitize else '-O2','-fno-lto','-ffunction-sections','-fdata-sections','-UNDEBUG','-fno-rtti','-pthread','-Ulinux','-Iuc-library/include','-I'+str(SDK/'include/presonus-core-5')]
 if sanitize:flags+=['-fsanitize=address,undefined','-fno-sanitize=vptr','-fno-omit-frame-pointer']
 suffix='-san' if sanitize else ''
 run(flags+['-c',SOURCES[3],'-o',WORK/('HeaderConsumer'+suffix+'.o')])
 objects=[]
 for source,name in [(SOURCES[1],'PermissionsComponent'),('uc-library/src/Presonus/UC/ServerComponent.cpp','ServerComponent'),(SOURCES[2],'Replay')]:
  obj=WORK/(name+suffix+'.o');run(flags+['-c',source,'-o',obj]);objects.append(obj)
 run(flags+objects+['-Wl,--gc-sections','-Wl,--start-group','temp/core-upstream/root-integration-01/libpresonus_rm_components.a',SDK/'lib/libcorelib.a',SDK/'lib/libpresonus_core_allocator.a','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a','-Wl,--end-group','-pthread','-ldl','-lm','-lz','-o',WORK/('replay'+suffix)])

def replay(executable,fixture):
 rows=json.loads(Path(fixture).read_text())['cases']
 for row in rows:
  c=row['input'];op=c['op'];argv=[executable,str(op),c['mix'] if op==0 else str(int(c['selected'])),c['other'] if op==0 else str(int(c['vector']))]
  result=json.loads(run(argv))
  if op==0:
   assert result['prefix']==row['observed']['prefix'],(row['id'],c,result,row['observed'])
   assert result['sanitized_suffix'] and result['stable_storage']
  else:
   assert all(result.values()),(row['id'],result)
   events=row['observed']['events'];expected=([['selected','delete']] if c['selected'] else [])+[['vector','destroy'],['component','destroy']]+([['object','delete']] if op==1 else [])
   assert events==expected,(row['id'],events)
   assert row['observed']['selected_cleared'] and row['observed']['object_deleted']==(op==1)
 print('Passed',len(rows),'native/provider cases; deterministic prefix only, sanitized suffix is an intentional adaptation; lifecycle actual selected/array/child/parameter/object deallocation separately observed.')

def main():
 p=argparse.ArgumentParser();p.add_argument('kind',choices=['format','compile','symbols','native','replay','sanitizers']);p.add_argument('--executable',default=str(WORK/'replay'));p.add_argument('--fixture',default=str(EVIDENCE/'native-fixtures.json'));a=p.parse_args();WORK.mkdir(parents=True,exist_ok=True);os.environ['TMPDIR']=str(WORK.resolve())
 if a.kind=='format':run(['uc-library/.venv/bin/clang-format','--version']);run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror']+SOURCES)
 elif a.kind=='compile':run(['/usr/bin/c++','--version']);compile_check()
 elif a.kind=='symbols':
  symbols={line.split()[-1] for line in run(['nm','--defined-only',WORK/'PermissionsComponent.o']).splitlines() if line.split()}
  for packet in sorted(PACKETS.iterdir()):
   symbol=json.loads((packet/'request.json').read_text())['targets'][0]['mangled'];assert symbol in symbols;print(symbol)
 elif a.kind=='native':
  out=WORK/('native-'+str(time.time_ns()));run(['uc-library/.venv/bin/python',BASE/'native_oracle.py','--out',out])
  for name in ['native-fixtures.json','native-traces.jsonl','native-proof.json']:assert (out/name).read_bytes()==(EVIDENCE/name).read_bytes(),name
 elif a.kind=='replay':replay(a.executable,a.fixture)
 else:compile_check(True);replay(str(WORK/'replay-san'),a.fixture)
if __name__=='__main__':main()
