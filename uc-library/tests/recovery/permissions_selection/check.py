#!/usr/bin/env python3
import argparse,hashlib,json,os,subprocess,time
from pathlib import Path
BASE=Path('uc-library/tests/recovery/permissions_selection')
WORK=Path('temp/recovery-work/permissions-selection19')
EVIDENCE=Path('evidence/recovery/2026-11-06/rolling200-02/permissions-selection19')
SDK=Path('temp/core-upstream/root-integration-01/upstream-core/sdk')
PACKETS=Path('temp/recovery-work/rolling200-02/next-implementation61/prepared-permissions61/packets')
SOURCES=['uc-library/include/presonus/mixer/PermissionsComponent.hpp','uc-library/src/Presonus/Mixer/PermissionsComponent.cpp','uc-library/include/presonus/mixer/MixerComponentBase.hpp','uc-library/src/Presonus/Mixer/MixerComponentBase.cpp','uc-library/include/presonus/uc/ClientSubscription.hpp','uc-library/src/Presonus/UC/ClientSubscription.cpp','uc-library/tests/recovery/PermissionsSelectionReplay.cpp']
def run(argv):
 argv=list(map(str,argv));print(json.dumps(argv),flush=True);t=time.monotonic();r=subprocess.run(argv,capture_output=True,text=True)
 with (WORK/'commands.jsonl').open('a') as f:f.write(json.dumps(dict(argv=argv,seconds=time.monotonic()-t,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))+'\n')
 if r.returncode:print(r.stdout,r.stderr,flush=True);r.check_returncode()
 return r.stdout

def compile_check(sanitize=False):
 flags=['/usr/bin/c++','-std=c++17','-O1' if sanitize else '-O2','-fno-lto','-ffunction-sections','-fdata-sections','-UNDEBUG','-fno-rtti','-pthread','-Ulinux','-Iuc-library/include','-I'+str(SDK/'include/presonus-core-5')]
 if sanitize:flags+=['-fsanitize=address,undefined','-fno-sanitize=vptr','-fno-omit-frame-pointer']
 suffix='-san' if sanitize else '';objects=[]
 for source in SOURCES[1::2]+[SOURCES[-1]]:
  if not source.endswith('.cpp'):continue
  obj=WORK/(Path(source).stem+suffix+'.o');run(flags+['-c',source,'-o',obj]);objects.append(obj)
 run(flags+objects+['-Wl,--gc-sections','-Wl,--start-group','temp/core-upstream/root-integration-01/libpresonus_rm_components.a',SDK/'lib/libcorelib.a',SDK/'lib/libpresonus_core_allocator.a','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a','-Wl,--end-group','-pthread','-ldl','-lm','-lz','-o',WORK/('replay'+suffix)])
def replay(executable,fixture):
 rows=json.loads(Path(fixture).read_text())['cases'];batch=WORK/('files-'+str(time.time_ns()));batch.mkdir()
 for row in rows:
  c=row['input'];clients=';'.join('null' if v is None else '|'.join(map(str,v)) for v in c['clients'])
  argv=[executable,c['op'],str(c['id']),c['selected'],clients,str(c['old']),c['type'],c['file'],str(batch/str(row['id']))]
  actual=json.loads(run(argv).splitlines()[-1]);assert actual==row['observed'],(row['id'],c,actual,row['observed'])
 # Source-port invariant is additional, not credited as a native case.
 assert json.loads(run([executable,'invariant','0','null','','0','none','absent',str(batch.resolve())])) is True
 print('Passed',len(rows),'independent native/provider cases plus explicit source-port count invariant.')
def regressions():
 import importlib.util
 flags=['/usr/bin/c++','-std=c++17','-O2','-fno-lto','-ffunction-sections','-fdata-sections','-fno-rtti','-pthread','-Ulinux','-Iuc-library/include','-I'+str(SDK/'include/presonus-core-5')]
 for name,source in [('readonly','PermissionsReadonlyReplay'),('lists','PermissionsListsReplay'),('lifecycle','PermissionsExportLifecycleReplay')]:
  obj=WORK/(source+'.o');exe=WORK/name;run(flags+['-c','uc-library/tests/recovery/'+source+'.cpp','-o',obj]);extra=[]
  if name=='lists':
   link=WORK/'LinkableComponent.o';run(flags+['-c','uc-library/src/Presonus/LinkableComponent.cpp','-o',link]);extra.append(link)
  run(flags+[WORK/'PermissionsComponent.o',WORK/'ClientSubscription.o',WORK/'MixerComponentBase.o',obj]+extra+['-Wl,--gc-sections','-Wl,--start-group','temp/core-upstream/root-integration-01/libpresonus_rm_components.a',SDK/'lib/libcorelib.a',SDK/'lib/libpresonus_core_allocator.a','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a','-Wl,--end-group','-pthread','-ldl','-lm','-lz','-o',exe])
  if name=='readonly':print(run([exe,'evidence/recovery/2026-11-05/permissions-readonly01/native-fixture.txt']))
  else:
   f='uc-library/candidates/'+('rolling200_02_permissions_lists' if name=='lists' else 'permissions_export_lifecycle')+'/checks.py';spec=importlib.util.spec_from_file_location(name,f);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.WORK=WORK;module.replay(str(exe),'evidence/recovery/2026-11-05/'+('permissions-lists01' if name=='lists' else 'permissions-export-lifecycle01')+'/native-fixtures.json')

def main():
 p=argparse.ArgumentParser();p.add_argument('kind',choices=['format','compile','symbols','native','replay','sanitizers','regressions']);p.add_argument('--executable',default=str(WORK/'replay'));p.add_argument('--fixture',default=str(BASE/'fixtures.json'));a=p.parse_args();WORK.mkdir(parents=True,exist_ok=True);os.environ['TMPDIR']=str(WORK.resolve())
 if a.kind=='format':run(['uc-library/.venv/bin/clang-format','--version']);run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror']+SOURCES)
 elif a.kind=='compile':run(['/usr/bin/c++','--version']);compile_check()
 elif a.kind=='symbols':
  symbols=set()
  for s in SOURCES[1::2]:
   if s.endswith('.cpp'):symbols.update(line.split()[-1] for line in run(['nm','--defined-only',WORK/(Path(s).stem+'.o')]).splitlines() if line.split())
  for packet in sorted(PACKETS.iterdir()):
   for t in json.loads((packet/'request.json').read_text())['targets']:assert t['mangled'] in symbols;print(t['original_elf_sha256'],t['mangled'])
 elif a.kind=='native':
  out=WORK/('native-'+str(time.time_ns()));run(['uc-library/.venv/bin/python',BASE/'native.py','--out',out])
  assert (out/'fixtures.json').read_bytes()==(BASE/'fixtures.json').read_bytes()
  for n in ['native-traces.jsonl','native-proof.json']:assert (out/n).read_bytes()==(EVIDENCE/n).read_bytes(),n
 elif a.kind=='regressions':regressions()
 elif a.kind=='replay':replay(a.executable,a.fixture)
 else:compile_check(True);replay(str(WORK/'replay-san'),a.fixture)
if __name__=='__main__':main()
