"""Fresh scoped GR/base proof; no canonical CMake, registry or historical writes."""
import argparse,datetime,hashlib,json,os,shlex,struct,subprocess,sys,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
PROJECT=Path('/home/rs/projects/opencs/ai-line-analysis')
PACKETS=Path('temp/recovery-work/rolling-c001-20261124/packeting/sqlite-cycle02/gr_five_sol61/custom-packet02/tasks')
SCRATCH=Path('temp/recovery-work/gr-five-implementation01')
COMMON=Path('uc-library/tests/recovery/sqlite_grfive_24f6e99aab28')
SDK=PROJECT/'temp/core-upstream/root-integration-01/upstream-core/sdk'
PRIVATE=PROJECT/'temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a'
LIBS=[SDK/'lib/libcorelib.a',SDK/'lib/libpresonus_core_allocator.a',SDK/'lib/libpresonus_png.a',SDK/'lib/libpresonus_zlib.a',PRIVATE]
PROD=[Path(f'uc-library/src/Presonus/{n}.cpp') for n in ['MeterBallistics','MeterMaid','GRMeterMaid']]
HEADERS=[Path(f'uc-library/include/presonus/{n}.hpp') for n in ['MeterBallistics','MeterMaid','GRMeterMaid']]
FLAGS=['-std=c++20','-O2','-DNDEBUG=1','-DPRESONUS_HAS_UPSTREAM_CORE=1','-DCORE_USE_OPENSSL=1','-Ulinux','-fno-rtti','-fno-sized-deallocation','-fno-fast-math','-ffp-contract=off','-ffunction-sections','-fdata-sections','-Wno-multichar','-pthread','-Iuc-library/include','-isystem',str(SDK/'include/presonus-core-5'),'-isystem',str(SDK/'include/presonus-core-codecs')]
LINK=['-Wl,--gc-sections','-lpthread','-ldl','-lm','-lssl','-lcrypto']
LOGS=[]
def digest(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def bind(p):return dict(path=str(p),sha256=digest(p))
def run(argv,payload=None):
 argv=list(map(str,argv));start=time.monotonic();r=subprocess.run(argv,cwd=ROOT,input=payload,text=True,capture_output=True);row=dict(argv=argv,seconds=time.monotonic()-start,returncode=r.returncode);LOGS.append(row)
 print(json.dumps(row),flush=True)
 if r.stderr:print(r.stderr,file=sys.stderr,end='')
 if r.returncode:print(r.stdout);r.check_returncode()
 return r.stdout

def format_check(task):
 files=PROD+HEADERS+[Path(f'uc-library/tests/recovery/{t}/Replay.cpp') for t in sorted(p.name for p in (ROOT/PACKETS).iterdir())]
 version=run(['uc-library/.venv/bin/clang-format','--version']).strip();run(['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',*files]);return dict(version=version,files=[bind(p) for p in files])
def compile_one(source,out):
 snapshot=Path('temp/recovery-work/gr-five-implementation01/consumer-compile-commands-captured01.json')
 assert digest(snapshot)=='c7cb61bf72d13984a9bec09a6d6dfe5e9338db7ee6e2f14c79913c7c61f98be6'
 rows=json.loads(snapshot.read_text());actual=[r for r in rows if r['file']==str(PROJECT/source)]
 flags=FLAGS if not actual or '-fno-rtti' in shlex.split(actual[0]['command']) else [f for f in FLAGS if f!='-fno-rtti']
 run(['c++',*flags,'-MMD','-MF',str(out)+'.d','-c',source,'-o',out]);return out

def compile_task(task):
 dest=SCRATCH/task;dest.mkdir(parents=True,exist_ok=True);objects=[compile_one(s,dest/f'production{i}.o') for i,s in enumerate(PROD)];objects.append(compile_one(Path('uc-library/tests/recovery')/task/'Replay.cpp',dest/'replay.o'))
 run(['c++',*objects,*LIBS,*(['-Wl,--wrap=_ZdlPv'] if task not in ('sqlite_grfive_2237d43a26c6','sqlite_grfive_24f6e99aab28','sqlite_grfive_70e55547f68d') else []),*LINK,f'-Wl,-Map,{dest}/link.map','-o',dest/'replay'])
 return dest

def symbols(task,dest):
 d=json.loads((ROOT/PACKETS/task/'CONTEXT.json').read_text());want={r['original']['mangled'] for r in d['originals']};symbols=set()
 for i in range(3):symbols.update(line.split()[-1] for line in run(['nm','--defined-only',dest/f'production{i}.o']).splitlines() if len(line.split())>=3)
 assert want<=symbols,(want-symbols)
 if any('GRMeterMaidD0' in n for n in want):
  out=run(['objdump','-dr','--disassemble=_ZN8Presonus11GRMeterMaidD0Ev',dest/'production2.o']);assert '_ZdlPv' in out and '_ZdlPvm' not in out
 return sorted(want)

def expected_level(c):
 tags={'isClipped':0,'setClipped':1,'setSignal':2,'setMeter':3,'setPeak':4};effects=[v for n,b in c['effects'] for v in (tags[n],b)];calls=[v for x in c['parameter_calls'] for v in (x[1]+(4 if x[0]=='get' else 0),x[2])]
 return c['output']+[len(effects)//2]+effects+[len(calls)//2]+calls

def deps(paths):
 result=set()
 for path in paths:
  raw=Path(str(path)+'.d').read_text().replace('\\\n',' ');result.update(shlex.split(raw.split(':',1)[1]))
 return [bind(p) for p in sorted(result)]

def consumers():
 dest=SCRATCH/'consumer-reproof01';dest.mkdir(parents=True,exist_ok=True)
 task=json.loads((ROOT/PACKETS/'sqlite_grfive_07153ad67d97/CONTEXT.json').read_text())
 # Preserve the accepted frozen source baseline; only the six owned paths change.
 for path,old in task['canonicalSDK_reads'].items():assert digest(PROJECT/path)==old,('stale SDK read',path)
 for path,old in task['task']['sources'].items():
  if Path(path) not in PROD+HEADERS:assert digest(path)==old,('stale read',path)
 assert digest(PRIVATE)==task['provider_archive']['sha256']
 sources=[Path(p) for p in task['task']['sources'] if p.endswith('.cpp') and '/tests/' not in p]+[PROD[2]]
 objects=[compile_one(p,dest/f'provider{i}.o') for i,p in enumerate(sources)]
 archive=dest/'libcurrent_meter_consumers.a';run(['ar','rcs',archive,*objects])
 obligations=[]
 # Three production TUs are themselves compilation obligations, not executable fixtures.
 for p in [PROD[0],PROD[1],Path('uc-library/src/Presonus/MeterManagerBase.cpp')]:
  i=sources.index(p);obligations.append(dict(kind='production_compile',source=bind(p),object=bind(objects[i])))
 for n in range(7,21):
  test=Path(f'uc-library/tests/recovery/cycle20_g02_s{n:02}');obj=compile_one(test/'Replay.cpp',dest/f'consumer{n}.o');exe=dest/f'consumer{n}'
  run(['c++',obj,archive,*LIBS,*(['-Wl,--wrap=_ZdlPv'] if n in (19,20) else []),*LINK,'-o',exe]);j=json.loads((ROOT/test/'fixtures.json').read_text());lines=[];expected=[]
  for row in j['originals']:
   for c in row['cases']:
    if n==7: inp=[row['role'],*c['input_bits']];out=[row['role'],*c['outputs']]
    elif n in (16,17,18):inp=[int(c['bound']),c['input_bits']];out=[c['result']]
    else:
     inp=list(c['input']);out=c['output']
     if n in (11,12):inp=[int(inp[0]),*[struct.unpack('<I',struct.pack('<f',v))[0] for v in inp[1:]]]
     else:inp=[int(v) if isinstance(v,bool) else v for v in inp]
    lines.append(' '.join(map(str,inp)));expected.append(' '.join(map(str,out)))
  result=run([exe.resolve()],'\n'.join(lines)+'\n').splitlines();assert result==expected,('consumer mismatch',n,next((i for i,x in enumerate(zip(result,expected)) if x[0]!=x[1]),None))
  obligations.append(dict(kind='fixture_replay',source=bind(test/'Replay.cpp'),fixture=bind(test/'fixtures.json'),executable=bind(exe),cases=len(result)))
 test=Path('uc-library/tests/recovery/sqlite03_meter_manager_delete_owned_roster/Replay.cpp');obj=compile_one(test,dest/'roster.o');exe=dest/'roster'
 run(['c++',obj,archive,*LIBS,'-Wl,--wrap=_ZdlPv','-Wl,--wrap=_ZdlPvm','-Wl,--wrap=_ZdaPv','-Wl,--wrap=_ZdaPvm',*LINK,'-o',exe]);fixture=Path('temp/recovery-work/gr-five-implementation01/roster-provider-fixture01/fixtures.json');assert digest(fixture)=='f630f632ff1d77002b97a2d7885f6558972e1935939fa2a9ad06d8975a5a1733';cases=json.loads(fixture.read_text())['cases']
 for c in cases:assert run([exe.resolve(),c['slots'],str(c['capacity'])]).splitlines()==c['events']
 obligations.append(dict(kind='roster_replay',source=bind(test),executable=bind(exe),fixture=bind(fixture),cases=len(cases)))
 assert len(obligations)==18
 receipt=dict(obligations=obligations,provider_archive=bind(archive),private_archive=bind(PRIVATE),CCL_archives=[bind(p) for p in LIBS[:-1]],dependencies=deps(objects+[dest/f'consumer{n}.o' for n in range(7,21)]+[obj]),sourcebaseline_transition=bind('temp/recovery-work/rolling-c001-20261124/packeting/sqlite-cycle02/gr_five_sol61/SOURCE-BASELINE-TRANSITION02.json'),historical_proofs_relabelled=False)
 return receipt

def replay(task,dest,exe=None,consumer=True):
 test=Path('uc-library/tests/recovery')/task;packet=PACKETS/task/'CONTEXT.json';sealed=json.loads((ROOT/test/'fixtures.json').read_text());actual=json.loads(run(['uc-library/.venv/bin/python',test/'native.py',packet]));assert actual==sealed
 rows=actual['originals'];method=rows[0]['target']['mangled'];level='setLevel' in method;idle='idleSetLevel' in method;level=level or idle;payload=[];expected=[]
 if level:
  arg='idle' if idle else 'base' if 'MeterBallistics' in method else 'gr'
  for row in rows:
   for c in row['cases']:payload.append(c['input']);expected.append(expected_level(c))
 else:
  arg=method[-4:-2]
  for row in rows:
   for c in row['cases']:
    payload.append([c['seed'],int(c.get('bound',False))])
    if arg[0]=='C':expected.append(c['state']+[0,0,0,0]+[c['getter_differential'][n]['constructed_null'] for n in ['_ZNK8Presonus15MeterBallistics13getDecayDeltaEv','_ZNK8Presonus15MeterBallistics17getPeakDecayDeltaEv']])
    else:expected.append([int(c['deleted']),int(c['bound']),1])
 executable=exe or dest/'replay';result=run([executable.resolve(),arg],''.join(' '.join(map(str,p))+'\n' for p in payload)).splitlines();assert len(result)==len(expected)
 for i,(line,want) in enumerate(zip(result,expected)):assert list(map(int,line.split()))==want,('differential mismatch',i,payload[i],line,want)
 direct=run([executable.resolve(),'direct']) if idle else None
 print('PASS',task,len(expected),'cases',flush=True)
 return dict(originals=actual,case_count=len(expected),executable=bind(executable),direct_base_regression=direct,consumer_reproof=consumers() if idle and consumer else None)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['format','compile','symbols','replay','proof']);parser.add_argument('--task',default='sqlite_grfive_24f6e99aab28');parser.add_argument('--exe',type=Path);parser.add_argument('--no-consumers',action='store_true');parser.add_argument('--read-transition',type=Path);parser.add_argument('--read-transition-sha256');parser.add_argument('--canonical-object-dir',type=Path);a=parser.parse_args();os.chdir(ROOT);start=datetime.datetime.now(datetime.timezone.utc).isoformat();f=format_check(a.task)
 dest=SCRATCH/a.task
 if a.canonical_object_dir:
  assert a.mode=='replay' and a.exe and a.no_consumers and a.read_transition and a.read_transition_sha256
  dest=a.canonical_object_dir.resolve();assert dest.is_relative_to(ROOT/'temp') and dest.is_dir()
 if a.mode=='format':return
 if a.mode in ('compile','proof'):compile_task(a.task)
 if a.mode=='compile':return
 sy=symbols(a.task,dest)
 if a.mode=='symbols':return
 observation=replay(a.task,dest,a.exe,not a.no_consumers)
 packet_data=json.loads((ROOT/PACKETS/a.task/'CONTEXT.json').read_text())
 owned=set(map(str,PROD+HEADERS))
 read_transition=None
 if a.read_transition or a.read_transition_sha256:
  assert a.mode=='replay' and a.exe and a.no_consumers and a.canonical_object_dir
  assert a.read_transition and a.read_transition_sha256 and digest(a.read_transition)==a.read_transition_sha256
  read_transition=json.loads(a.read_transition.read_text());assert read_transition['version']==1
  original=ROOT/PACKETS/a.task/'CONTEXT.json';assert read_transition['contexts'][a.task]==dict(path=str(original.relative_to(ROOT)),sha256=digest(original))
  approved=read_transition['accepted_Connection_generation'];assert digest(ROOT/approved['path'])==approved['sha256']
  assert set(read_transition['read_transitions'])=={'uc-library/include/presonus/uc/connection.hpp','uc-library/include/presonus/uc/event_factory.hpp','uc-library/include/presonus/uc/network_activity_manager.hpp','uc-library/include/presonus/uc/network_manager_services.hpp','uc-library/include/presonus/uc/socket_channel.hpp','uc-library/src/Presonus/UC/basic_connection.cpp'}
 for path,h in packet_data['task']['sources'].items():
  if path in owned:continue
  if read_transition and path in read_transition['read_transitions']:
   row=read_transition['read_transitions'][path];assert row['previous_sha256']==h
   assert digest(ROOT/row['previous_frozen']['path'])==row['previous_frozen']['sha256']==h
   assert digest(ROOT/row['current_frozen']['path'])==row['current_frozen']['sha256']==row['current_sha256']==digest(path)
   owner=row['accepted_current_source_owner_review'];assert owner==read_transition['accepted_Connection_generation'] and digest(ROOT/owner['path'])==owner['sha256']
  else:assert digest(path)==h,('stale packet read',path)
 for path,h in packet_data['canonicalSDK_reads'].items():assert digest(PROJECT/path)==h,('stale SDK',path)
 if read_transition:
  receipt=dict(task=a.task,original_checker_source='Preservedoriginalcheck.py; attributedcanonicalpostreadguardsuccessor',original_context=read_transition['contexts'][a.task],read_transition=dict(path=str(a.read_transition),sha256=a.read_transition_sha256),native_and_portable=observation,format=f,canonical_symbols=sy,actual_executable=bind(a.exe),actual_object_dir=str(dest),read_bindings={path:digest(path) for path in packet_data['task']['sources'] if path not in owned},SDK_bindings={path:digest(PROJECT/path) for path in packet_data['canonicalSDK_reads']},old_proofs_relabelled=False,readiness_admitted=False)
  output=dest/'canonical-current67-replay.json';assert not output.exists();output.write_text(json.dumps(receipt,indent=2)+'\n')
 if a.mode=='proof':
  proof=dict(task_id=a.task,physical_root=str(ROOT),start_utc=start,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),session_id=os.environ.get('CODEX_THREAD_ID'),format=f,compiled_mangled_names_matched=True,mangled_names=sy,cpp_differential_passed=True,native_and_portable=observation,sources=[bind(p) for p in PROD+HEADERS],dependencies=deps([dest/f'production{i}.o' for i in range(3)]+[dest/'replay.o']),archives=[bind(p) for p in LIBS],external_CCL_commit=run(['git','-C','third_party/ccl-framework','rev-parse','HEAD']).strip(),sourcebaseline_transition=bind('temp/recovery-work/rolling-c001-20261124/packeting/sqlite-cycle02/gr_five_sol61/SOURCE-BASELINE-TRANSITION02.json'),compiler=run(['c++','--version']).splitlines()[0],native_versions=run(['uc-library/.venv/bin/python','-c','import unicorn,elftools; print(unicorn.__version__,elftools.__version__)']).strip(),commands=LOGS,checker=bind(COMMON/'check.py'),native_producer=bind(Path('uc-library/tests/recovery')/a.task/'native.py'),fixture=bind(Path('uc-library/tests/recovery')/a.task/'fixtures.json'),readiness_admitted=False)
  out=Path('uc-library/candidates')/a.task;out.mkdir(parents=True,exist_ok=True);p=out/'worker-proof.json';assert not p.exists(),'Do not overwrite a frozen proof';p.write_text(json.dumps(proof,indent=2)+'\n')
if __name__=='__main__':main()
