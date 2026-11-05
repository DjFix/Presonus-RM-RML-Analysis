"""Capture local checks/proof and one exact packet HANDOFF per original identity."""
import datetime,hashlib,json,pathlib,subprocess,os,importlib.util
ROOT=pathlib.Path(__file__).resolve().parents[5]
TEST=pathlib.Path('uc-library/tests/recovery/rolling200-02/eq-band')
EVIDENCE=pathlib.Path('evidence/recovery/2026-11-05/rolling200-02/eq-band')
PACKETS=pathlib.Path('temp/recovery-work/rolling200-02/implementation-plan01/packets-current-eq-band03-01/packets')
OWNED=['uc-library/include/presonus/mixer_dsp/EQControl.hpp','uc-library/src/Presonus/EQControlBandParams.cpp','uc-library/tests/recovery/EQBandObserverReplay.cpp']
PY='uc-library/.venv/bin/python';FORMAT='uc-library/.venv/bin/clang-format'
def sha(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
checks=[{'kind':'format','argv':[FORMAT,'--style=file','--fallback-style=LLVM','--dry-run','--Werror']+OWNED,'timeout_seconds':120}]+[{'kind':kind,'argv':[PY,str(TEST/'check.py'),kind],'timeout_seconds':120} for kind in ['compile','symbols','replay']]+[{'kind':'native','argv':[PY,str(TEST/'oracle.py')],'timeout_seconds':120},{'kind':'regression','argv':[PY,str(TEST/'regression.py')],'timeout_seconds':120}]
logs=[]
for c in checks:
 started=now();r=subprocess.run(c['argv'],cwd=ROOT,text=True,capture_output=True,env={**os.environ,'TMPDIR':str(ROOT/'temp/recovery-work/rolling200-02/eq-band')},timeout=c['timeout_seconds'])
 log=EVIDENCE/(c['kind']+'.log');(ROOT/log).write_text(r.stdout+r.stderr)
 logs.append({**c,'started':started,'finished':now(),'exit_code':r.returncode,'log':str(log),'log_sha256':sha(log)})
 print(c['kind'],r.returncode,flush=True);assert r.returncode==0,r.stderr+r.stdout
versions={}
for key,argv in [('format',[FORMAT,'--version']),('compiler',['/usr/bin/c++','--version']),('symbols',['/usr/bin/nm','--version']),('python',[PY,'--version']),('unicorn',[PY,'-c','import unicorn;print(unicorn.__version__)']),('pyelftools',[PY,'-c','import elftools;print(elftools.__version__)']),('ccl-root-history',['git','-C','third_party/ccl-framework','log','--reverse','--format=%H %P'])]:versions[key]=subprocess.check_output(argv,cwd=ROOT,text=True).strip()
assert versions['ccl-root-history'].splitlines()[0].strip()=='e8cbdea4a4a20e15111f5a690798a259c0374b31'
native=json.loads((ROOT/EVIDENCE/'native.json').read_text())
limitations=['Portable source port only: original ordinary return declarations remain unresolved (provisional void); all three identities compiled declaration-pending. No ARM ABI, GUI inheritance, original object layout or hardware interoperability claim.','Explicit semantic conversion: native [type,gain,Q,frequency,enabled,extra] -> portable [slot3,gain,q,frequency,slot4,slot5]. Existing positional contains/zeroParam are deliberately unchanged; legacy positional helper users must continue their explicit conversion.','Stable count, valid allocated memory, borrowed parameters and owner survive synchronous operations. Provider add/remove do not reenter/resize or mutate bindings; allocation failure, concurrent mutations, partial bindings excluded. setBand throws before effects on incomplete portable bindings, a source-port guard outside native equivalence domain.','Native oracle executes application instruction ranges and stubs only the external CCL Parameter add/remove boundaries; no Core binary reconstruction. Compiled replay transparently wraps calls to real pinned CCL providers, inspects actual observerList membership and calls changed() through real EQ portableObserver adapter.','Null owner is forwarded as null to provider add/remove and inspected for membership, but never notified: CCL signal requires nonnull observer. No original observer null-notification semantics claimed.','Native PC/write guards restrict execution to exact three bodies and explicit provider boundaries, stack writes and selected band/dirty writes. Portable memory layout is not compared byte-for-byte; semantic state and phase snapshots are exact.']
domain='224 independent original ARM cases: 44 helper cases (each helper 22) across null/non-null owner, each singleton raw slot, all-null/distinct/duplicate/mixed pointers; 180 setBand cases with counts 0/1/3, index -1/0/last/count, old/new null/distinct/duplicates/shared pointers. Compare exact forwarded call order including duplicates, null preservation, old snapshot at remove/new snapshot at add with pre-dirty byte, all six final slots and dirty bytes, actual CCL membership multiplicity and real changed()->EQ dirty effects. Existing 1038 observer/zeroParam/control, 17 curve-boundary, 46 curve-response and 274 historical getter/provider regressions replay unchanged fixtures.'
files=set(OWNED)
files.update(str(p.relative_to(ROOT)) for p in (ROOT/TEST).glob('*.py'))
files.update(['uc-library/src/Presonus/EQControl.cpp','uc-library/src/Presonus/EQControlBiquad.cpp','rootfs/CS18_v13840/home/root/surface','third_party/ccl-framework/core/portable/coreparams.h','third_party/ccl-framework/core/portable/coreparams.cpp','third_party/ccl-framework/core/public/corevector.h','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a',str(EVIDENCE/'native.json')])
for group in ['eq-control','eq-curves']:
 files.update(str(p.relative_to(ROOT)) for p in (ROOT/TEST.parent/group).glob('*') if p.is_file())
for p in (ROOT/'uc-library/tests/recovery/trial08/eq').glob('*'):
 if p.is_file():files.add(str(p.relative_to(ROOT)))
files.update(['uc-library/tests/graph_trial08_eq_tests.cpp','uc-library/src/DSP/BiquadMethods.cpp','uc-library/src/DSP/BiquadIncremental.cpp','uc-library/src/DSP/BiquadSine.cpp'])
for n in ['01','02','03']:
 for f in ['context.json','native-context.json','request.json','TASK.md','ELF_CONTEXT.md','SOURCE_SLICES.md','CONTEXT.md']:files.add(str(PACKETS/f'rolling200_02_eq_band_{n}'/f))
files.update(x['log'] for x in logs)
source_hashes={f:sha(f) for f in sorted(files)}
proof={'version':1,'scope':'worker local Linux, not readiness admission','created':now(),'cwd':str(ROOT),'base_commit':'d548724a88fbb82e34f7a43b1c56081c6afda7c9','versions':versions,'ranges':native['ranges'],'source_sha256':source_hashes,'commands':logs,'validation_domain':domain,'limitations':limitations,'native_case_counts':{'removeObserver':22,'addObserver':22,'setBand':180},'formatting_verified':True,'compiled':True,'mangling_verified':True,'native_behavior_verified':True,'original_declaration_verified':False,'original_arm_abi_verified':False,'hardware_verified':False}
proof_path=EVIDENCE/'proof.json';(ROOT/proof_path).write_text(json.dumps(proof,indent=2)+'\n');files.add(str(proof_path))
for n in ['01','02','03']:
 packet=PACKETS/f'rolling200_02_eq_band_{n}'
 req=json.loads((ROOT/packet/'request.json').read_text());o=req['originals'][0]['original']
 out=pathlib.Path('uc-library/candidates')/req['task_id'];(ROOT/out).mkdir(parents=True,exist_ok=True)
 notes={'date':now(),'elf_sha256':o['elf'],'mangled':o['mangled'],'work_item_id':req['work_binding']['work_item_id'],'status':'compiled-declaration-pending; local native/provider replay passed','observations':limitations,'proof':str(proof_path),'retry_condition':'Independent original return declaration evidence for promotion; Root integration/admission required. Revisit mutation/lifetime exclusions only with new supporting evidence.'}
 notes_path=out/'NOTES.json';(ROOT/notes_path).write_text(json.dumps(notes,indent=2)+'\n')
 artifacts=[{'kind':'source' if f in OWNED or f.endswith('.cpp') or f.endswith('.hpp') else 'fixture' if f.endswith('native.json') else 'proof' if f==str(proof_path) else 'packet' if f==str(packet/'context.json') else 'dependency','path':f,'sha256':sha(f)} for f in sorted(files|{str(notes_path)})]
 handoff={'version':1,'task_id':req['task_id'],'namespace':'Presonus::EQControl','packet_manifest':str(packet/'context.json'),'originals':[{'elf_sha256':o['elf'],'firmware':o['firmware'],'role':o['role'],'mangled':o['mangled'],'address':o['address'],'size':o['size'],'section':'.text'}],'artifacts':artifacts,'checks':checks,'validation_domain':domain,'limitations':limitations,'build_integration':{'production_partition':'common; existing src/Presonus/EQControlBandParams.cpp already listed exactly once in cmake/ProductionSourceGroups.cmake; no new CPP','public_headers':['include/presonus/mixer_dsp/EQControl.hpp'],'test_targets':['EQBandObserverReplay'],'link_dependencies':['actual pinned corelib','presonus_core_allocator','zlib'],'link_options':['--wrap=_ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE','--wrap=_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE'],'ctest_argv':[PY,str(TEST/'check.py'),'replay','--executable','<canonical-built-EQBandObserverReplay>','--fixtures',str(EVIDENCE/'native.json')],'fixture_sha256':sha(EVIDENCE/'native.json'),'notes':'Root owns CMake, full canonical Linux/role/install/compile-once gates and guarded SQLite pending admission. No ready/pending fragment produced by worker; this is worker HANDOFF only.'}}
 (ROOT/out/'HANDOFF.json').write_text(json.dumps(handoff,indent=2)+'\n')
print('Three exact packet HANDOFF v1 records sealed with final shared source hashes.')
