"""Reproducible local compile/symbol/original-source differential replay."""
import argparse,copy,datetime,hashlib,json,os,pathlib,subprocess,sys,time
BASE=pathlib.Path(__file__).parent
SOURCES=['uc-library/src/Presonus/UUX/FirmwareUpdater.cpp','uc-library/src/Presonus/UUX/FirmwareUpdaterPaths.cpp','uc-library/src/Presonus/UUX/FirmwareUpdaterDispatch.cpp','uc-library/src/Presonus/UUX/FirmwareUpdaterHostProcess.cpp','uc-library/src/Presonus/Surface/FirmwareUpdateLifecycle.cpp','uc-library/src/Presonus/Surface/FirmwareUpdateCallbacks.cpp','uc-library/src/application/SimpleReader.cpp','uc-library/src/common/FirmwareCallbackText.cpp']
FORMATTED=['uc-library/include/presonus/uux/FirmwareUpdaterPaths.hpp','uc-library/include/presonus/surface_update/FirmwareUpdateComponent.hpp',SOURCES[0],SOURCES[4],str(BASE/'Replay.cpp')]
WRAPS=['_ZN4Core8Platform15PosixFileStreamC1EP8_IO_FILE','_ZN4Core8Platform15PosixFileStreamD1Ev','_ZNK4Core8Portable9Component17getParameterByTagEi','_ZN4Core8Portable9Component12paramChangedEPNS0_9ParameterEi','_ZN4Core8Portable16BackgroundWorker7addTaskEPNS0_14BackgroundTaskE','_ZN4Core8Portable16BackgroundWorker9terminateEv','_ZN4Core8Portable9ComponentD2Ev','_Znwm','_ZdlPv','_ZdlPvm','_ZN4Core8Platform15PosixFileSystem12getDirectoryERNS_8Portable8FileNameENS0_11IFileSystem7DirTypeE','_ZN4Core8Platform13CurrentThread5sleepEj']
CORE_FILES=['third_party/ccl-framework/core/portable/corecomponent.h','third_party/ccl-framework/core/portable/corecomponent.cpp','third_party/ccl-framework/core/portable/coreworker.h','third_party/ccl-framework/core/portable/coreworker.cpp','third_party/ccl-framework/core/portable/coreparams.h','third_party/ccl-framework/core/portable/coreparams.cpp','third_party/ccl-framework/core/portable/corefile.h','third_party/ccl-framework/core/portable/corefile.cpp','third_party/ccl-framework/core/portable/coreattributes.h','third_party/ccl-framework/core/portable/coreattributes.cpp','third_party/ccl-framework/core/portable/corepersistence.h','third_party/ccl-framework/core/portable/corepersistence.cpp','third_party/ccl-framework/core/public/corestringbuffer.h','third_party/ccl-framework/core/system/coretime.h','third_party/ccl-framework/core/platform/shared/posix/corefilesystem.posix.cpp']
def H(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def run(argv,logs):
 start=time.monotonic();p=subprocess.run([str(x) for x in argv],text=True,capture_output=True,timeout=300,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'})
 logs.append(dict(argv=[str(x) for x in argv],exit_code=p.returncode,seconds=time.monotonic()-start,stdout=p.stdout,stderr=p.stderr))
 if p.returncode:raise RuntimeError(json.dumps(logs[-1],indent=2))
 return p.stdout

def compile(a,logs):
 b=pathlib.Path(a.build_dir);b.mkdir(parents=True,exist_ok=True);os.environ['TMPDIR']=str(b.resolve());core=pathlib.Path(a.core_build)
 flags=['c++','-std=c++17','-Wno-multichar','-fno-rtti','-fPIC','-g','-Iuc-library/include','-Ithird_party/ccl-framework','-Itemp/tool-env/curl-dev/root/usr/include/x86_64-linux-gnu']
 san=['-fsanitize=address'] if a.sanitize else []
 wraps=['-Wl,--wrap='+s for s in WRAPS];objects=[]
 for src in SOURCES:
  obj=b/(pathlib.Path(src).stem+'.o');run(flags+san+['-c',src,'-o',obj],logs);objects.append(obj)
 archives=[core/'artifacts/linux/Release/libcorelib.a',core/'libpresonus_core_allocator.a',core/'libpresonus_png.a',core/'libpresonus_zlib.a']
 run(['c++',*san,'-shared',*wraps,*objects,*archives,'/usr/lib/x86_64-linux-gnu/libcurl.so.4.8.0','-pthread','-ldl','-o',b/'updater.so'],logs)
 run(flags+san+wraps+[BASE/'Replay.cpp','-rdynamic',b/'updater.so','-Wl,-rpath,'+str(b.resolve()),*archives[:2],'-pthread','-ldl','-o',b/'Replay'],logs)
 return dict(objects={str(p):H(p) for p in objects},archives={str(p):H(p) for p in archives},executable={'path':str(b/'Replay'),'sha256':H(b/'Replay')},library={'path':str(b/'updater.so'),'sha256':H(b/'updater.so')})
def symbols(a,fixture,logs):
 b=pathlib.Path(a.build_dir);text=run(['nm',b/'FirmwareUpdater.o',b/'FirmwareUpdateLifecycle.o'],logs)
 for o in fixture['ranges']:assert o['mangled'] in text,o['mangled']
 return {'compiled_original_mangled_names_matched':True,'original_identities':len(fixture['ranges'])}
def normalized(v):
 v=copy.deepcopy(v)
 for c in v['calls']:
  if c[:2]==['open','/offline/response']:c[0]='archive'
  if c[0] in ['host-new','new']:c[:]=['task-allocation']
 return v

def replay(a,fixture,logs):
 b=pathlib.Path(a.build_dir);exe=pathlib.Path(a.exe) if a.exe else b/'Replay';library=pathlib.Path(a.library) if a.library else b/'updater.so';rows=[]
 for case in fixture['cases']:
  original=case['original'];argv=[exe,library,original['mangled'],'13840' if original['elf'].startswith('304c') else '13731']+[key+'='+str(int(v) if isinstance(v,bool) else v) for key,v in case['input'].items()]
  actual=json.loads(run(argv,logs));assert normalized(actual)==normalized(case['observed']),json.dumps({'case':case,'host':actual},indent=2)
  rows.append({'original':original,'input':case['input'],'observed':actual})
 wide=json.loads(run([exe,library,'_ZL19curlRequestCallbackPvjjS_','13840','bridge_wide=1'],logs));assert wide=={'calls':[],'result':0}
 return {'differential_cases':len(rows),'observations':rows,'independent_host_bridge_wide_rejection':wide,'normalization':'Only allocation-size ABI difference (native32 vs real host56) and actual pinned archive fopen event vs native archive boundary are normalized. Raw native/host observations retained; no result/data/ordering normalization.'}

def main():
 p=argparse.ArgumentParser();p.add_argument('--mode',choices=['format','compile','symbols','replay','all'],required=True);p.add_argument('--build-dir',default='temp/recovery-work/updater-build-final');p.add_argument('--core-build',default='/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/build');p.add_argument('--sanitize',action='store_true');p.add_argument('--task-id');p.add_argument('--exe');p.add_argument('--library');p.add_argument('--out',required=True);a=p.parse_args();logs=[]
 report={'version':1,'utc_start':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mode':a.mode,'commands':logs,'sources':{s:H(s) for s in SOURCES+FORMATTED+[str(BASE/'native.py'),str(BASE/'check.py'),str(BASE/'fixtures.json')]},'repository_sources':{s:H(s) for s in CORE_FILES}}
 try:
  if a.mode in ['format','all']:
   run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*FORMATTED],logs);report['formatter_version']=run(['uc-library/.venv/bin/clang-format','--version'],logs).strip()
  if a.mode in ['compile','all']:report['build']=compile(a,logs)
  fixture=json.loads((BASE/'fixtures.json').read_text())
  if a.task_id:
   fixture['cases']=[c for c in fixture['cases'] if c['task']==a.task_id];assert fixture['cases']
   identities={(c['original']['elf'],c['original']['mangled']) for c in fixture['cases']}
   fixture['ranges']=[o for o in fixture['ranges'] if (o['elf'],o['mangled']) in identities]
  if a.mode in ['symbols','all']:report['symbols']=symbols(a,fixture,logs)
  if a.mode in ['replay','all']:report['replay']=replay(a,fixture,logs)
  report['success']=True
 except BaseException as exc:report['success']=False;report['failure']=repr(exc);raise
 finally:
  report['utc_end']=datetime.datetime.now(datetime.timezone.utc).isoformat();pathlib.Path(a.out).write_text(json.dumps(report,indent=2)+'\n')
 print(a.mode,'PASS')
if __name__=='__main__':main()
