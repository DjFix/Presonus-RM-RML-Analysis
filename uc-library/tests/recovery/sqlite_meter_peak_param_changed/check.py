import argparse,hashlib,json,subprocess,sys,time
from pathlib import Path
from native import observe,PACKET,TASK
ROOT=Path.cwd(); CANON=Path('/home/rs/projects/opencs/ai-line-analysis')
TEST=Path('uc-library/tests/recovery')/TASK;SCRATCH=Path('temp/recovery-work')/TASK;SCRATCH.mkdir(parents=True,exist_ok=True)
EXE=SCRATCH/'Replay';OBJ=SCRATCH/'MeterPeakControl.o';SOURCE=Path('uc-library/src/Presonus/Panel/MeterPeakControl.cpp');HEADER=Path('uc-library/include/presonus/panel/meter_peak_control.hpp')
FORMAT=['uc-library/.venv/bin/clang-format','--style=file','--fallback-style=LLVM','--dry-run','--Werror',str(SOURCE),str(HEADER),str(TEST/'Replay.cpp')]
BUILD=CANON/'temp/core-upstream/root-integration-01';SDK=BUILD/'upstream-core/sdk'
CXX=['/usr/bin/c++','-std=c++17','-O2','-ffunction-sections','-fdata-sections','-Ulinux','-fno-rtti','-fno-sized-deallocation','-DPRESONUS_HAS_UPSTREAM_CORE=1','-DCORE_USE_OPENSSL=1','-DNDEBUG=1','-Iuc-library/include','-isystem',str(SDK/'include/presonus-core-5')]
COMPILE=CXX+['-MD','-MF',str(SCRATCH/'MeterPeakControl.d'),'-c',str(SOURCE),'-o',str(OBJ)]
ARCHIVES=[BUILD/'libpresonus_uc.a',*[SDK/'lib'/n for n in ['libcorelib.a','libpresonus_core_allocator.a','libpresonus_png.a','libpresonus_zlib.a']],BUILD/'private-glibc29-provider/libpresonus_private_glibc29.a']
LINK=CXX+['-Wl,--gc-sections',str(TEST/'Replay.cpp'),str(OBJ),*map(str,ARCHIVES),'-lssl','-lcrypto','-ldl','-lm','-pthread','-o',str(EXE)]
RECORDS=[]
def run(argv):
 started=time.time();stamp=time.time_ns();r=subprocess.run(argv,text=True,capture_output=True);log=SCRATCH/(str(stamp)+'.log');log.write_text(r.stdout+r.stderr)
 RECORDS.append(dict(argv=argv,start_unix=started,elapsed_seconds=time.time()-started,exit_code=r.returncode,log=str(log),log_sha256=hashlib.sha256(log.read_bytes()).hexdigest()))
 if r.returncode:raise RuntimeError((argv,r.returncode,r.stdout,r.stderr))
 return r.stdout
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def replay(fixtures):
 for c in fixtures['cases']:
  a=c['input'];argv=[str(EXE),a['kind'],str(a['tag']),str(a['last']),str(a.get('offset',0)),str(a.get('value',0)),str(a.get('message',0)),a.get('mode','direct'),a.get('table','input')]
  output=run(argv);tokens=output.split();words=[]
  for t in tokens:
   if t.endswith('O'):break
   words.append(int(t))
  encoded=tokens[len(words):];i=0
  assert words[i]==c['level'],(a,output,c);i+=1
  count=words[i];i+=1;assert words[i:i+count]==list(map(int,c['queue'])),(a,output,c);i+=count
  count=words[i];i+=1;expected=[b for packet in c['packets'] for b in packet[:3]]
  assert count==len(c['packets']) and words[i:]==expected,(a,output,c)
  zero=c
  if a.get('byte3',0):
   wanted=dict(a,byte3=0)
   zero=next(v for v in fixtures['cases'] if v['role']==c['role'] and v['input']==wanted)
  assert encoded==zero['encoded'],(a,output,zero)
  if a.get('message')==5:assert c['parameter_pointer']==0 and 'removeObserver' in c['calls'],c
 print(json.dumps(dict(task=TASK,cases=len(fixtures['cases']),passed=True)))
def seal(fixture):
 candidate=Path('uc-library/candidates')/TASK;candidate.mkdir(parents=True,exist_ok=True)
 ctx=json.loads(PACKET.read_text());proof=candidate/'worker-proof.json'
 deps=[p for p in ctx['read_files'] if Path(p).is_file()]
 proof.write_text(json.dumps(dict(version=1,task_id=TASK,original_execution=fixture['proofs'],native_producer_sha256=sha(TEST/'native.py'),fixture_sha256=sha(TEST/'fixtures.json'),replay_producer_sha256=sha(TEST/'Replay.cpp'),check_producer_sha256=sha(TEST/'check.py'),successful_check_exit_code=0,command_records=RECORDS,python_version=sys.version,unicorn_version=__import__('unicorn').__version__,compiler_version=run(['/usr/bin/c++','--version']).splitlines()[0],symbol_tool_version=run(['/usr/bin/nm','--version']).splitlines()[0],worker_session_id=__import__('os').environ.get('CODEX_THREAD_ID','unavailable'),sealed_utc=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),portable_cases=len(fixture['cases']),source_sha256=sha(SOURCE),header_sha256=sha(HEADER),formatter=run(['uc-library/.venv/bin/clang-format','--version']).strip(),symbols=run(['/usr/bin/nm','--defined-only',str(OBJ)]),commands=[FORMAT,COMPILE,LINK],limitations=LIMITS),indent=2)+'\n')
 artifacts=[]
 for p in dict.fromkeys([str(SOURCE),str(HEADER),str(TEST/'Replay.cpp'),str(TEST/'native.py'),str(TEST/'check.py'),str(TEST/'fixtures.json'),str(proof),str(PACKET),*deps]):artifacts.append(dict(kind='packet' if p==str(PACKET) else 'source',path=p,sha256=sha(p)))
 argv=['uc-library/.venv/bin/python',str(TEST/'check.py')]
 handoff=dict(version=1,task_id=TASK,namespace=ctx['task']['namespace'],packet_manifest=str(PACKET),originals=[dict(elf_sha256=o['original']['elf'],**{k:o['original'][k] for k in ['firmware','role','mangled','address','size','section']}) for o in ctx['originals']],artifacts=artifacts,checks=[dict(kind=k,argv=FORMAT if k=='format' else argv+['--'+k],timeout_seconds=600) for k in ['format','compile','symbols','replay']],validation_domain=DOMAIN,limitations=LIMITS,build_integration=dict(production_partition='common existing MeterPeakControl.cpp',public_headers=[str(HEADER)],test_targets=[TASK],affected_existing_replays=['sqlite02_meterpeakcontrol_complete_construct','sqlite02_meterpeakcontrol_base_construct','sqlite02_meterpeakcontrol_complete_destroy','sqlite02_meterpeakcontrol_deleting_destroy','sqlite02_meterpeakcontrol_cast_type'],link_dependencies=['presonus_uc','pinned CCL'],ctest_argv=['uc-library/.venv/bin/python',str(TEST/'check.py'),'--replay','--executable','<canonical target executable>'],fixture=str(TEST/'fixtures.json')))
 (candidate/'HANDOFF.json').write_text(json.dumps(handoff,indent=2)+'\n')
DOMAIN='Both original ELF entries, verified actual section ranges, unsigned broadcast gate/wrap/cache; composed native parameter->broadcast->transmit; actual Linux Control, CCL NumericParam, genuine DbTable default/override and shared deferred vector, direct IO capture and actual production UART encoder. Nonchanged/destroyed messages, negative tags, threshold boundaries, signed extreme wrapping, deferred empty/duplicate/room/full and genuine CCL growth.'
LIMITS=['Portable source model; original ARM object layout and unencoded return declarations unresolved; no hardware.', 'Native provider boundaries: Parameter getValue, removeObserver, float comparison and vector resize. Other target and base Control instructions execute unchanged. Portable executes actual CCL provider, no fake Core classes.', 'Native transmit initializes only bytes0..2 and leaves byte3 uninitialized. With fixed bytes [79,35,16], native byte3 seeds 0/5/171/255 produce original encoder outputs 2300O/2305O/230BO/230FO in both roles. Portable explicitly zeros byte3: a safe deterministic source-port adaptation, not general behavioral equivalence. All established bytes are compared; encoded fourth nibble equivalence is bounded to native zero seed. No hardware encoding fidelity claim.', 'Valid attached IO and live control queue pointers required. Default tables configured by callers; no claim of original startup configuration. DbTable count bounded to 0..16.']
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--compile',action='store_true');p.add_argument('--symbols',action='store_true');p.add_argument('--replay',action='store_true');p.add_argument('--seal',action='store_true');p.add_argument('--seal-existing',action='store_true');p.add_argument('--executable');a=p.parse_args()
 if a.executable:EXE=Path(a.executable)
 if a.compile or a.seal or a.seal_existing:run(FORMAT);run(COMPILE);run(LINK)
 if a.symbols or a.seal or a.seal_existing:
  symbols=run(['/usr/bin/nm','--defined-only',str(OBJ)]);ctx=json.loads(PACKET.read_text());assert all(o['original']['mangled'] in symbols for o in ctx['originals'])
 if a.seal:
  fixture=observe();(TEST/'fixtures.json').write_text(json.dumps(fixture,indent=2)+'\n');replay(fixture);seal(fixture)
 elif a.seal_existing:
  fixture=json.loads((TEST/'fixtures.json').read_text());replay(fixture);seal(fixture)
 elif a.replay:replay(json.loads((TEST/'fixtures.json').read_text()))
