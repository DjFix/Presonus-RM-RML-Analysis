"""Run final owned gates and emit four exact packet handoffs, without admission."""
import datetime, hashlib, importlib.util, json, os, pathlib, subprocess, sys, time
ROOT=pathlib.Path(__file__).resolve().parents[4];os.chdir(ROOT)
EVIDENCE=pathlib.Path('evidence/recovery/2026-11-06/rolling200-03/mapping157')
HERE=pathlib.Path('uc-library/tests/recovery/mapping_item')
EVIDENCE.mkdir(parents=True,exist_ok=True)
def digest(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def write(p,x):pathlib.Path(p).write_text(json.dumps(x,indent=2)+'\n')
def main():
 checks=[];results=[]
 for kind in ['format','compile','symbols','replay','regression']:
  argv=['uc-library/.venv/bin/python',str(HERE/'check.py'),kind]
  checks.append(dict(kind=kind,argv=argv,timeout_seconds=120))
  started=datetime.datetime.now(datetime.timezone.utc).isoformat();before=time.monotonic()
  p=subprocess.run(argv,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  (EVIDENCE/(kind+'.log')).write_text(p.stdout)
  results.append(dict(kind=kind,argv=argv,started_utc=started,seconds=time.monotonic()-before,returncode=p.returncode,log=str(EVIDENCE/(kind+'.log'))))
  print(kind,p.returncode,flush=True)
  assert p.returncode==0,p.stdout
 files=[('source','uc-library/include/presonus/MappingTable.hpp'),('source','uc-library/src/Presonus/MappingTableItem.cpp'),('test','uc-library/tests/recovery/MappingItemReplay.cpp'),('fixture',str(HERE/'fixtures.json')),('replay',str(HERE/'check.py')),('producer',str(HERE/'native.py')),('producer',str(HERE/'seal.py'))]
 deps=['uc-library/include/presonus/panel/control.hpp','uc-library/include/presonus/surface_panel/LEDState.hpp','uc-library/src/Presonus/Panel/control.cpp','uc-library/src/Presonus/Panel/LEDControlLifecycle.cpp','uc-library/src/surface_panel/LEDState.cpp','third_party/ccl-framework/core/public/corestringbuffer.h','third_party/ccl-framework/core/public/corestringtraits.h','third_party/ccl-framework/core/portable/coreparams.h','third_party/ccl-framework/core/portable/coreparams.cpp','third_party/ccl-framework/core/malloc/coremalloc.cpp','temp/core-upstream/root-integration-01/libpresonus_uc.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','rootfs/CS18_v13840/home/root/surface','uc-library/tests/recovery/stabilized01_mapping/driver.cpp','uc-library/tests/recovery/stabilized01_mapping/replay.py','uc-library/tests/recovery/stabilized01_mapping/fixtures.json','uc-library/src/Presonus/MappingTable.cpp','uc-library/src/Presonus/MappingTableConnect.cpp','uc-library/src/Presonus/MappingTableHardwareParameter.cpp']
 files += [('dependency',p) for p in deps]
 files += [('log',str(EVIDENCE/(c['kind']+'.log'))) for c in checks]
 fixture=json.loads((HERE/'fixtures.json').read_text())
 domain='62 original ARM Item executions: 36 blink cases (null/empty/exact tokens/case/whitespace/unknown, each null/rejected/LED receiver), 6 inverse cases (bool x receiver), and 10 C1 + 10 C2 (null/empty/31/32/90 bytes x null/actual borrowed alias). 230 composed C++ cases additionally vary initial blink mode 0/1/2/3/9 and compare exact dispatch trace, all available LED state and inverse on/off to direct actual accepted LED provider invocation. Constructor outputs compare directly with actual pinned CCL CStringBuffer<32>, defaultColor empty, control null, alias preserved. 366 prior MappingTable fixtures replay and three current production users compile.'
 limitations='Portable source port only. Original ordinary return declarations, original full class layout and ARM ABI remain unresolved; void methods selected as bounded source contract. C1/C2 have separate original bodies and separate exact ranges; host generated C1/C2 alias is recorded by nm. ARM provider calls (castTo, LED setters and CStringBuffer) are captures, not original provider execution: no Core machine code executes. C++ provider composition is actual pinned CCL and actual accepted Control/LED sources; it is not whole-firmware differential proof. LED proof domain uses null parameter and no I/O endpoint/timers, initial color17/match0/cache123; provider hardware transmission and parameter-observer paths are not independently revalidated here. Borrowed alias is never deleted. No hardware, firmware update, or host syscall passthrough.'
 versions={name:subprocess.check_output(argv,text=True).splitlines()[0] for name,argv in [('clang_format',['uc-library/.venv/bin/clang-format','--version']),('compiler',['g++','--version']),('nm',['nm','--version']),('python',['uc-library/.venv/bin/python','--version'])]}
 import unicorn
 versions['unicorn']=unicorn.__version__
 artifacts=[dict(kind=k,path=p,sha256=digest(p)) for k,p in files]
 proof=EVIDENCE/'PROOF.json'
 write(proof,dict(version=1,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),checkout=str(ROOT),baseline='3a5d52a2677966b0b6e2e6a662bc0e3b5588965b',elf_sha256=fixture['elf_sha256'],original_ranges=fixture['ranges'],versions=versions,checks=results,inputs=artifacts,validation_domain=domain,limitations=limitations,remarks=[{'status':'resolved','observation':'Initial replay wrapper could not observe vtable self-defined cast relocations using linker wrap. No production issue.','resolution':'Test-only observing subclasses now delegate casts to actual Control/LED providers; exact tag, cast count and accepted/rejected results verified.'},{'status':'resolved','observation':'Initial regression linkage lacked pinned allocator and zlib.','resolution':'Link actual pinned coremalloc.cpp and -lz; all 366 regression fixtures pass.'}],readiness_admitted=False))
 artifacts.append(dict(kind='proof',path=str(proof),sha256=digest(proof)))
 integration={'partition':'CS18 (all four targets client surface; Root verifies partition and global role audits)','production_cpp':['uc-library/src/Presonus/MappingTableItem.cpp'],'public_headers':['uc-library/include/presonus/MappingTable.hpp'],'test_source':'uc-library/tests/recovery/MappingItemReplay.cpp','ctest_argv':['uc-library/.venv/bin/python',str(HERE/'check.py'),'replay'],'canonical_replay_note':'check.py replay accepts optional --driver PATH for canonical CTest executable; wrap the two LED setter symbols shown in check.py and use real provider sources/library. Root owns shared CMake.','link_dependencies':['presonus_uc','corelib','pthread','dl','rt'],'fixtures':str(HERE/'fixtures.json'),'header_integration':'Root must merge Mapping154 changes and reseal affected hashes/replay current-source gates.'}
 for i in range(1,5):
  task=f'rolling200_03_mapping157_{i:02d}';packet=pathlib.Path('temp/recovery-work/rolling200-03/mapping157/prepared157/packets')/task
  request=json.loads((packet/'request.json').read_text());original=request['originals'][0]['original']
  identity=dict(elf_sha256=original['elf'],firmware=original['firmware'],role=original['role'],mangled=original['mangled'],address=original['address'],size=original['size'],section='.text')
  specific=[dict(kind='packet',path=str(packet/'context.json'),sha256=digest(packet/'context.json'))]
  for name in ['TASK.md','ELF_CONTEXT.md','SOURCE_SLICES.md','CONTEXT.md','request.json']:
   path=packet/name;specific.append(dict(kind='packet_context',path=str(path),sha256=digest(path)))
  handoff=pathlib.Path('uc-library/candidates')/task/'HANDOFF.json';handoff.parent.mkdir(parents=True,exist_ok=True)
  data=dict(version=1,task_id=task,namespace='Presonus',packet_manifest=str(packet/'context.json'),originals=[identity],artifacts=artifacts+specific,checks=checks,validation_domain=domain,limitations=limitations,build_integration=integration)
  write(handoff,data)
  spec=importlib.util.spec_from_file_location('accept_worker',ROOT/'uc-library/tools/recovery/accept_worker.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.validate(data)
  print('validate PASS',handoff)
if __name__=='__main__':main()
