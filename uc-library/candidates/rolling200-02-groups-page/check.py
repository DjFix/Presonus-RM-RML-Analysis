"""Noninteractive isolated checks. No registry, CMake or canonical proof writes."""
import datetime,hashlib,json,os,shlex,subprocess,sys,time
from pathlib import Path
BASE=Path('uc-library/candidates/rolling200-02-groups-page');WORK=Path('temp/recovery-work/rolling200-02/groups-page');OUT=Path('evidence/recovery/2026-11-05/rolling200-02/groups-page')
FORMAT=['uc-library/include/presonus/surface/GroupsPageComponent.hpp','uc-library/src/Presonus/Surface/GroupsPageComponent.cpp',str(BASE/'replay.cpp')]
SOURCES=[FORMAT[1],'uc-library/src/Presonus/Surface/GroupsPageRecovery.cpp']
ARCHIVES=['temp/core-upstream/root-integration-01/libpresonus_uc.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a']
FLAGS=['-std=c++17','-O0','-g','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework']
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
LOG=OUT/'checks'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ');LOG.mkdir(parents=True)
def run(argv,name,input=None):
 t=time.monotonic();start=datetime.datetime.now(datetime.timezone.utc).isoformat();env=os.environ.copy();env['TMPDIR']=str(WORK.resolve());p=subprocess.run(argv,input=input,text=True,capture_output=True,env=env);(LOG/(name+'.stdout')).write_text(p.stdout);(LOG/(name+'.stderr')).write_text(p.stderr);(LOG/(name+'.json')).write_text(json.dumps(dict(argv=argv,producer_sha256=sha(__file__),source_sha256={p:sha(p) for p in FORMAT+SOURCES},start_utc=start,end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),seconds=time.monotonic()-t,returncode=p.returncode,stdout_sha256=hashlib.sha256(p.stdout.encode()).hexdigest(),stderr_sha256=hashlib.sha256(p.stderr.encode()).hexdigest()),indent=2)+'\n');assert p.returncode==0,(argv,p.returncode,p.stderr[-4000:]);return p.stdout
mode=sys.argv[1]
if mode=='format':
 print(run(['uc-library/.venv/bin/clang-format','--version'],'version'));run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*FORMAT],'format')
elif mode=='compile':
 print(run(['c++','--version'],'compiler').splitlines()[0]);objects=[]
 for i,source in enumerate(SOURCES):
  obj=str(WORK/f'unit{i}.o');objects.append(obj);run(['c++',*FLAGS,'-finstrument-functions','-MMD','-MF',str(WORK/f'unit{i}.d'),'-c',source,'-o',obj],f'compile{i}')
 replay_obj=str(WORK/'replay.o');run(['c++',*FLAGS,'-MMD','-MF',str(WORK/'replay.d'),'-c',str(BASE/'replay.cpp'),'-o',replay_obj],'replay-compile')
 run(['c++','-rdynamic',replay_obj,*objects,*ARCHIVES,'/usr/lib/x86_64-linux-gnu/libpng16.so.16','-lz','-lssl','-lcrypto','temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so','-pthread','-ldl','-lm','-Wl,-rpath,'+str(Path('temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu').resolve()),'-o',str(WORK/'replay')],'link')
elif mode=='symbols':
 out=run(['nm','--defined-only',str(WORK/'unit0.o')],'symbols');names={l.split()[-1] for l in out.splitlines() if l.split()};required=[]
 for i in range(1,5):
  p=Path(f'temp/recovery-work/rolling200-02/implementation-plan01/packets-isolated-groups_page02/packets/rolling200_02_impl_w02_0{i}/request.json');n=json.loads(p.read_text())['targets'][0]['mangled'];assert n in names,n;required.append(n)
 (OUT/'symbols.json').write_text(json.dumps(dict(originals=required,namespace_and_encoded_signature_verified=True,object_format='ELF64 x86_64, no leading decoration',original_return_declarations_verified=False,original_arm_abi_verified=False),indent=2)+'\n');print('four original encoded identities match')
elif mode=='replay':
 native=json.loads((OUT/'native.json').read_text());data=(OUT/'inputs.txt').read_text();assert data==''.join(' '.join(map(str,c['input']))+'\n' for c in native['cases']);actual=run([str(WORK/'replay')],'replay',input=data).splitlines();assert len(actual)==len(native['cases']),(len(actual),len(native['cases']))
 for i,(line,c) in enumerate(zip(actual,native['cases'])):
  a=shlex.split(line);b=shlex.split(c['output']);op=c['input'][0]
  if op!=4:a=list(map(float,a));b=list(map(float,b))
  assert a==b,(i,c['input'],b,a)
 result=dict(cases=len(actual),per_method={str(op):sum(c['input'][0]==op for c in native['cases']) for op in range(1,5)},native_sha256=sha(OUT/'native.json'),inputs_sha256=sha(OUT/'inputs.txt'),executable_sha256=sha(WORK/'replay'),compared=['direct original application-boundary entry ordering','selectGroup selection before doselect','own paramChanged tag1009 resulting value','onObserveredParamChange all group tag603 values and mapping tag6','addGroup resulting bounded names and bit-exact numeric603/646 values'],excluded=['original return declarations, ARM layout/ABI, hardware','nested existing-provider call ordering from original binaries','absent tag600 child is original-invalid domain, independently preserved native/portable negative witness'])
 (OUT/'replay.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
else:raise SystemExit('mode must be format/compile/symbols/replay')
