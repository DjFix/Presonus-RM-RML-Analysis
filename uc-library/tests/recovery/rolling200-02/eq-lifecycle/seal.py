"""Capture worker-local Linux proof and exact per-packet HANDOFF v1 records."""
import datetime,hashlib,json,pathlib,subprocess,os,time
ROOT=pathlib.Path(__file__).resolve().parents[5]
TEST=pathlib.Path('uc-library/tests/recovery/rolling200-02/eq-lifecycle')
EVIDENCE=pathlib.Path('evidence/recovery/2026-11-05/rolling200-02/eq-lifecycle')
PACKETS=pathlib.Path('temp/recovery-work/rolling200-02/next-implementation08/prepared09-eq_lifecycle08/packets')
PY='uc-library/.venv/bin/python';FORMAT='uc-library/.venv/bin/clang-format'
OWNED=['uc-library/include/presonus/mixer_dsp/EQControl.hpp','uc-library/src/Presonus/EQControl.cpp','uc-library/tests/recovery/EQControlLifecycleReplay.cpp']
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
checks=[{'kind':kind,'argv':[PY,str(TEST/'check.py'),kind],'timeout_seconds':120} for kind in ['format','compile','symbols','replay']]+[{'kind':'native','argv':[PY,str(TEST/'oracle.py')],'timeout_seconds':120},{'kind':'regression','argv':[PY,str(TEST/'regression.py')],'timeout_seconds':180}]
(ROOT/EVIDENCE).mkdir(parents=True,exist_ok=True)
logs=[]
for c in checks:
 start=now();tick=time.monotonic()
 r=subprocess.run(c['argv'],cwd=ROOT,text=True,capture_output=True,timeout=c['timeout_seconds'],env={**os.environ,'TMPDIR':str(ROOT/'temp/recovery-work/rolling200-02/eq-lifecycle')})
 log=EVIDENCE/(c['kind']+'.log');(ROOT/log).write_text(r.stdout+r.stderr)
 logs.append({**c,'started':start,'finished':now(),'seconds':time.monotonic()-tick,'returncode':r.returncode,'log':str(log),'log_sha256':sha(log)})
 print(c['kind'],r.returncode,flush=True)
 assert r.returncode==0,r.stdout+r.stderr
versions={}
for key,argv in [('formatter',[FORMAT,'--version']),('compiler',['/usr/bin/c++','--version']),('symbols',['/usr/bin/nm','--version']),('python',[PY,'--version']),('unicorn',[PY,'-c','import unicorn;print(unicorn.__version__)']),('pyelftools',[PY,'-c','import elftools;print(elftools.__version__)']),('ccl-history',['git','-C','third_party/ccl-framework','log','--reverse','--format=%H %P'])]:
 versions[key]=subprocess.check_output(argv,cwd=ROOT,text=True).strip()
assert versions['ccl-history'].splitlines()[0].strip()=='e8cbdea4a4a20e15111f5a690798a259c0374b31'
native=json.loads((ROOT/EVIDENCE/'native.json').read_text())
domain='360 independent original ARM lifecycle executions, 120 per exact D0/D1/D2 identity. Counts0/1/3, all-null/distinct/repeated/mixed parameters, empty/amplitude+pixel/per-band+shared/output/all resource masks, both tagged borrowed and owned rectangle construction. Exact removal order including duplicates and authoritative type vector; actual deallocation callsite for D0 only; reverse per-band free/ref snapshots, default/background final unuse, owned bitmap virtual delete. Host real pinned CCL membership and changed() callbacks, ParamList destruction with 540 owned HPF destruction signals, shared BitmapReference counts without deleting borrowed images, owned Control primary-detach and borrowed Control survival. Immutable constructor50, band224, control1038, curve-boundary17 and curve-response46 and historical getter/provider274 regressions.'
limitations=[
 'Intentional portable C++ source model: original GUI inheritance, original class field declarations, layout, allocator array cookies and ARM ABI interoperability are unresolved/excluded; no hardware validation. Destructor names/signatures and compiler ABI variants are exact; no invented ordinary variant methods or ordinary return declarations.',
 'Stable valid allocated state and synchronous no-throw provider cleanup; fully bound parameter/type mappings; borrowed parameters, images and control/view/providers survive EQ destruction. Concurrent/reentrant state mutation, provider throws, original EH/ARM unwinding and partial native initialization are outside execution domain. Native EH cleanup is retained in full range evidence but not executed.',
 'Native oracle executes only original EQ destructor and bound existing app BandParams helper ranges. Real original native provider and allocator call targets are intercepted as explicit boundaries; no Core binary body is executed or reconstructed. Bitmap receiver vtable data and exact D0 symbol target are verified from original ELF; native bitmap deallocation is a virtual-call boundary observation. Host real pinned CCL bitmap destructor/deallocation executes independently.',
 'Source hpfParameterOwner exposes the same ParamList through a reference; that reference is usable only before destruction begins. Early owner.reset destroys real ParamList at native cleanup phase, then shared refs release, then constructorState.reset destroys interpolators and owned Control while EQ observer is still alive. This phased ownership is an intentional adaptation; borrowed tagged state is never destroyed.',
 'Native array-container allocator details are not compared with std::vector host container overhead. Compare semantic owning amplitude/pixel/per-band free checkpoints, original observer calls and shared-image state, with host concrete actual frees. Shared refs unuse rather than delete; borrowed BackgroundPainter pointers are removed through real CCL Vector.removeAll without pointee ownership. No recovered BackgroundPainter implementation is claimed.',
 'Worker-local proof and commit are not canonical full Linux integration/readiness admission. Root must replay full tests, installed-role/compile-once, active-source and SQLite gates, refreshing impacted existing constructor/getter/curve proof hashes. No ready/pending fragment is generated here.'
]
files=set(OWNED)|{str(EVIDENCE/'native.json'),'rootfs/CS18_v13840/home/root/surface','docs/worker-handoff.md','docs/core-framework-lineage.md','AGENTS.md'}
files.update(str(p.relative_to(ROOT)) for p in (ROOT/TEST).glob('*.py'))
files.update(['uc-library/src/Presonus/EQControlBandParams.cpp','uc-library/src/Presonus/EQControlBiquad.cpp','uc-library/src/Presonus/Dsp/EqSourceProviders.cpp','uc-library/include/presonus/mixer_dsp/EqSourceProviders.hpp','uc-library/include/presonus/dsp/biquad_calc.hpp','uc-library/src/mixer_dsp/Logarithm.cpp','uc-library/src/DSP/BiquadMethods.cpp','uc-library/src/DSP/BiquadIncremental.cpp','uc-library/src/DSP/BiquadSine.cpp','uc-library/tests/recovery/EQConstructorsReplay.cpp','uc-library/tests/recovery/EQBandObserverReplay.cpp','evidence/recovery/2026-11-05/rolling200-02/eq-band/native.json','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a'])
for f in ['core/portable/coreparams.h','core/portable/coreparams.cpp','core/portable/coreparaminfo.h','core/portable/gui/corebitmap.h','core/portable/gui/corebitmap.cpp','core/portable/gui/corecontrols.h','core/portable/gui/corecontrols.cpp','core/portable/gui/coreview.h','core/portable/gui/coreview.cpp','core/portable/gui/coreviewshared.h','core/portable/gui/coregraphics.h','core/portable/gui/coregraphics.cpp','core/public/coreinterpolator.h','core/public/coreinterpolator.cpp','core/public/corevector.h']:
 files.add('third_party/ccl-framework/'+f)
files.add('uc-library/tests/graph_trial08_eq_tests.cpp')
files.update(str(p.relative_to(ROOT)) for p in (ROOT/'uc-library/tests/recovery/trial08/eq').glob('*') if p.is_file())
for group in ['eq-constructors','eq-band','eq-control','eq-curves']:
 files.update(str(p.relative_to(ROOT)) for p in (ROOT/TEST.parent/group).glob('*') if p.is_file())
for n in range(1,4):
 packet=PACKETS/f'rolling200_02_eq_lifecycle_{n:02d}'
 for name in ['context.json','request.json','TASK.md','ELF_CONTEXT.md','SOURCE_SLICES.md','CONTEXT.md','native-context.json']:
  files.add(str(packet/name))
for group in ['expand09-eq-remove-observer','expand09-eq-lifecycle-data']:
 files.update(str(p.relative_to(ROOT)) for p in (ROOT/PACKETS.parent.parent/group).glob('*') if p.is_file())
files.update(x['log'] for x in logs)
proof_path=EVIDENCE/'proof.json'
proof={'version':1,'created':now(),'cwd':str(ROOT),'base_commit':'95e1a9fc26b3d6909f272c1618ad842bb8c878b5','worker_thread_id':os.environ.get('CODEX_THREAD_ID'),'parent_session_id':os.environ.get('CODEX_SESSION_ID'),'scope':'worker-local successful portable lifecycle source port; no readiness admission','versions':versions,'native_input':{'elf':native['elf'],'sha256':native['elf_sha256'],'ranges':native['ranges'],'bitmap_vtable':native['bitmap_vtable']},'source_sha256':{f:sha(f) for f in sorted(files)},'commands':logs,'validation_domain':domain,'limitations':limitations,'native_case_counts':{'D0':120,'D1':120,'D2':120},'formatting_verified':True,'compiled':True,'mangling_verified':True,'namespace_signature_verified':True,'native_behavior_verified':True,'original_declaration_verified':True,'original_declaration_scope':'Destructor void/no parameter signature and native D0/D1/D2 variants only; no original class field/inheritance/layout recovery claim','original_arm_abi_verified':False,'hardware_verified':False,'development_history':[{'observation':'Initial oracle setup referenced an unavailable historical helper packet; Root baseline expansion supplied exact helper and now oracle reads that expansion. No empty packet or guessed helper bytes used.','resolution':'Resolved before native fixture generation.'},{'observation':'First regression run stopped after constructor50 because immutable eq-band/native.json absent from isolated repo.','resolution':'Root supplied exact original fixture hash8b50b71fc1d7d1f0a4cbf5dff4daad450e6b62f5e6125890f6aba4d650d7d944; unchanged replay now passes.'}]}
(ROOT/proof_path).write_text(json.dumps(proof,indent=2)+'\n');files.add(str(proof_path))
for n in range(1,4):
 packet=PACKETS/f'rolling200_02_eq_lifecycle_{n:02d}';req=json.loads((ROOT/packet/'request.json').read_text());o=req['originals'][0]['original'];out=pathlib.Path('uc-library/candidates')/req['task_id'];(ROOT/out).mkdir(parents=True,exist_ok=True)
 notes={'date':now(),'elf_sha256':o['elf'],'mangled':o['mangled'],'work_item_id':req['work_binding']['work_item_id'],'status':'compiled; local native/provider lifecycle validation passed; Root integration/admission pending','observations':limitations,'proof':str(proof_path),'resolution':'Explicit virtual destructor with phased ownership replaces implicit member destruction. Actual hpf ParamList dies while observer and Control live. Native D0 instruction executes genuine deallocation request; source free is actual intercepted allocator call.','retry_condition':'Revisit excluded EH/partial-state/hardware domains only with new evidence and explicit scope. No original return declaration blocker for destructor; original class inheritance/layout remain unclaimed.'}
 notes_path=out/'NOTES.json';(ROOT/notes_path).write_text(json.dumps(notes,indent=2)+'\n')
 def kind(f):
  if f==str(proof_path):return 'proof'
  if f==str(EVIDENCE/'native.json'):return 'fixture'
  if f==str(TEST/'check.py'):return 'replay'
  if f.startswith('uc-library/tests/') and f.endswith('.cpp'):return 'test'
  if f in OWNED or f.startswith('uc-library/src/'):return 'source'
  if f==str(packet/'context.json'):return 'packet'
  return 'dependency'
 artifacts=[{'kind':kind(f),'path':f,'sha256':sha(f)} for f in sorted(files|{str(notes_path)})]
 handoff={'version':1,'task_id':req['task_id'],'namespace':'Presonus::EQControl','packet_manifest':str(packet/'context.json'),'originals':[{'elf_sha256':o['elf'],'firmware':o['firmware'],'role':o['role'],'mangled':o['mangled'],'address':o['address'],'size':o['size'],'section':'.text'}],'artifacts':artifacts,'checks':checks,'validation_domain':domain,'limitations':limitations,'build_integration':{'production_partition':'Existing src/Presonus/EQControl.cpp in CS18 OBJECT partition; read-only BandParams helper remains common; no new production CPP','public_headers':['include/presonus/mixer_dsp/EQControl.hpp'],'test_targets':['EQControlLifecycleReplay'],'test_sources':['tests/recovery/EQControlLifecycleReplay.cpp'],'link_dependencies':['pinned actual corelib','presonus_core_allocator','presonus_private_glibc29','zlib','pthread','dl','m'],'link_options':['--wrap=_ZdlPv','--wrap=_ZdlPvm','--wrap=_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE'],'ctest_argv':[PY,str(TEST/'check.py'),'replay','--executable','<canonical-built-EQControlLifecycleReplay>','--fixtures',str(EVIDENCE/'native.json')],'fixture_sha256':sha(EVIDENCE/'native.json'),'notes':'Real provider/allocator interception test only; production no fake Core classes. Root must refresh existing source-bound proofs affected by canonical header/constructor change, then full Linux/role/install/compile-once and guarded SQLite integration. No shared CMake/registry edit.'}}
 (ROOT/out/'HANDOFF.json').write_text(json.dumps(handoff,indent=2)+'\n')
print('Three exact lifecycle HANDOFF v1 records sealed with final shared-source hashes.')
