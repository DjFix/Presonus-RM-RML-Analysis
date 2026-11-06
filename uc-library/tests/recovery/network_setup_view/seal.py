"""Capture local Linux checks and five exact packet-bound HANDOFF v1 records.
No shared build, readiness ledger or operational registry mutation.
"""
import pathlib,json,hashlib,subprocess,datetime,time,os,collections
ROOT=pathlib.Path(__file__).resolve().parents[4]
BASE=pathlib.Path('uc-library/tests/recovery/network_setup_view')
EVIDENCE=pathlib.Path('evidence/recovery/2026-11-05/rolling200-02/network-view20-local')
PACKETS=pathlib.Path('temp/recovery-work/rolling200-02/next-implementation20/prepared-network-view20/packets')
OUT=pathlib.Path('temp/recovery-work/rolling200-02/network-view20-local')
PY='uc-library/.venv/bin/python'
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
checks=[{'kind':x,'argv':[PY,str(BASE/'check.py'),x],'timeout_seconds':180} for x in ['format','compile','symbols','replay','native','regression']]
(ROOT/EVIDENCE).mkdir(parents=True,exist_ok=True)
logs=[]
for check in checks:
 start=now();tick=time.monotonic();r=subprocess.run(check['argv'],cwd=ROOT,text=True,capture_output=True,timeout=check['timeout_seconds'],env={**os.environ,'TMPDIR':str(ROOT/OUT)})
 log=EVIDENCE/(check['kind']+'.log');(ROOT/log).write_text(r.stdout+r.stderr)
 logs.append({**check,'started':start,'finished':now(),'seconds':time.monotonic()-tick,'returncode':r.returncode,'log':str(log),'sha256':sha(log)})
 print(check['kind'],r.returncode,flush=True)
 assert r.returncode==0,r.stdout+r.stderr
versions={label:subprocess.check_output(argv,cwd=ROOT,text=True).strip() for label,argv in [
 ('formatter',['uc-library/.venv/bin/clang-format','--version']),('compiler',['/usr/bin/c++','--version']),('symbols',['/usr/bin/nm','--version']),('python',[PY,'--version']),('unicorn',[PY,'-c','import unicorn;print(unicorn.__version__)']),('pyelftools',[PY,'-c','import elftools;print(elftools.__version__)']),('ccl-history',['git','-C','third_party/ccl-framework','log','--reverse','--format=%H %P'])]}
assert versions['ccl-history'].splitlines()[0].strip()=='e8cbdea4a4a20e15111f5a690798a259c0374b31'
fixture=json.loads((ROOT/BASE/'fixtures.json').read_text())
assert fixture['audit']['unexpected']==0 and fixture['audit']['Core_body_instructions_executed']==0
requests=[json.loads(p.read_text()) for p in sorted((ROOT/PACKETS).glob('*/request.json'))]
history_path='uc-library/candidates/rolling200_02_review_w05/REVIEW.json'
history=json.loads((ROOT/history_path).read_text())
remarks=[]
for row in history['targets']:
 if row.get('original',{}).get('mangled') in [r['targets'][0]['mangled'] for r in requests]:
  remarks.append({k:row[k] for k in ['native_contract','blockers','bounded_owned_work','declaration_status','validation_domain'] if k in row}|{'mangled':row['original']['mangled']})
domain='1281 original ARM executions: createView9 name/null cases; getObjectForView72 name/type/cached-state combinations; push1176 parameter-present/null, both down states, seven signed integer radio values including INT_MIN/INT_MAX and binary32 rounding boundary, three off values, fourteen bit-pattern current values including signed zero, fractions, subnormals, infinities and signaling/quiet NaNs; D0 and D1 each12 exact native variant executions across null/distinct/shared image+icon and parameter presence. Original libgcc i2f/fcmpeq and transitive arithmetic bodies execute, never modeled results. Host actual pinned CCL edit-call order and raw set bits, icon/image use counts before Control observer detach, D0 real deallocation and D1 nondeallocation; actual nested model, repeated reuse, owned vs borrowed lifetime and true owned model free; actual CCL view-controller TypeInfo/child dispatch/parameter lookup, model changed notifications and selection scrolling. Host-only allocation-failure state checks. Existing immutable network98, settings133 and selection/handlers1008 regression executions.'
limitations=[
 'Portable source port, not ARM32 ABI compatibility: original GUI inheritance, object field declarations, layout, ordinary return declarations and hardware interoperability remain unresolved. createView returns View*, getObjectForView returns void* and push returns void only as explicit CCL-backed source-port declarations. Destructor variant signatures are established; compiled host D1/D2 aliasing does not claim original D2 coverage.',
 'Historical ComponentViewController<PageComponent> fallback is intentionally adapted to actual pinned ComponentViewController<NetworkSetupComponent>. Real Component lookupChild/lookupParameter/findParameter/TypeInfo execute. NetworkSetup uses its existing Component base and composed borrowed parameter owner; no recovered PageComponent or Core implementation is invented.',
 'Native oracle intercepts original CCL constructor/Control destructor, existing app setupListModel, historical controller fallback and libc/operator new/delete entries as explicit boundaries. No Core binary instruction executes. Native D0 genuinely reaches operator delete(this); allocator internals are excluded. Independently observed actual host delete validates source deallocation; a synthetic delete event is never appended.',
 'Native successful allocation, stable valid initialized state and synchronous/no-throw providers are the differential domain. Native EH/unwinding, constructor throws and allocator failure are excluded from ARM execution; host allocation failure is separately tested. Concurrent/reentrant parameter substitution or provider exceptions are excluded.',
 'Actual nested ListModel records its borrowed owner and inherits real CCL model storage/lifecycle; existing setSelected/isItemSelected are reused. No additional native ListModel event-handler reconstruction is claimed. Views must detach before owner/model destruction. Newly allocated models are uniquely owned by this port, externally supplied model pointers remain borrowed. This ownership is intentional source-port state, not native field/layout proof.',
 'Real pinned RadioButton derives actual Button/Control. Default destructor releases actual icon/image references then detaches actual parameter observer; host tests observe final refcounts and counts at detach, not each inline unuse instruction individually. Exact native D0/D1 byte ranges and inline reference writes are separately executed. No behavior claim for native Core destructor internals.',
 'Worker-local proof only. No ready/pending fragment, SQLite mutation, shared integration edit, canonical full Linux build, installed-role/compile-once or final admission is performed by the worker. Root must refresh affected existing source-bound proofs and run global gates. Ordinary methods retain declaration-pending status until independent original return declaration evidence exists.'
]
notes=[]
for req in requests:
 o=req['originals'][0]['original'];destructor='D0Ev' in o['mangled'] or 'D1Ev' in o['mangled']
 notes.append({'date':now(),'elf_sha256':o['elf'],'mangled':o['mangled'],'work_item_id':req['work_binding']['work_item_id'],'status':'local compile/mangling/native-provider validation passed; Root admission pending','original_declaration_verified':destructor,'historical_remarks':[r for r in remarks if r['mangled']==o['mangled']],'observations':limitations,'resolution':'Controller source-port composition reviewed and implemented with actual CCL template; owned real nested model lifetime tested; actual RadioToggleButton with full push and true D0/D1 lifecycle replaces missing concrete subclass. Separate runtime closure context resolved without arithmetic stubs.','retry_condition':'Ordinary returns require independent declaration evidence; EH/ARM layout/hardware remain excluded until new evidence and scoped authorization. Revisit model event callbacks only when selected; no unchanged-blocker retry.','proof':str(EVIDENCE/'proof.json')})
notes_path=EVIDENCE/'NOTES.json';(ROOT/notes_path).write_text(json.dumps(notes,indent=2)+'\n')
files=set(['AGENTS.md','docs/worker-handoff.md','docs/core-framework-lineage.md',history_path,'rootfs/CS18_v13840/home/root/surface',str(notes_path)])
owned=['uc-library/include/presonus/surface/NetworkSetupComponent.hpp','uc-library/src/Presonus/Surface/NetworkSetupComponent.cpp','uc-library/include/presonus/surface/RadioToggleButton.hpp','uc-library/src/Presonus/Surface/RadioToggleButton.cpp','uc-library/tests/recovery/NetworkSetupViewReplay.cpp']
files.update(owned)
files.update(str(p.relative_to(ROOT)) for p in (ROOT/BASE).glob('*') if p.is_file())
files.update(['uc-library/src/Presonus/Surface/NetworkListSelection.cpp','uc-library/src/Presonus/Surface/MidiMixerState.cpp','uc-library/include/presonus/surface/MidiMixerHandler.hpp','uc-library/include/presonus/uc/NetworkItem.hpp','uc-library/include/presonus/delay_timer.hpp','uc-library/tests/graph_trial07_surfacenet_tests.cpp','uc-library/tests/recovery/NetworkSetupSettingsReplay.cpp','uc-library/tests/recovery/ranked09/handlers/driver.cpp','uc-library/tests/recovery/ranked09/handlers/replay.py','uc-library/tests/recovery/ranked09/handlers/fixtures.json','uc-library/tests/recovery/trial07/surfacenet/replay.py','uc-library/tests/recovery/trial07/surfacenet/fixtures.json','uc-library/candidates/network-setup-settings/replay.py','uc-library/candidates/network-setup-settings/fixtures.json'])
files.update(['temp/core-upstream/root-integration-01/'+p for p in ['libpresonus_uc.a','libpresonus_cs18_components.a','upstream-core/sdk/lib/libcorelib.a','upstream-core/sdk/lib/libpresonus_core_allocator.a','private-glibc29-provider/libpresonus_private_glibc29.a']])
for f in ['core/portable/corecomponent.h','core/portable/corecomponent.cpp','core/portable/coreparams.h','core/portable/coreparams.cpp','core/portable/coreparaminfo.h','core/portable/coretypeinfo.h','core/portable/gui/corecontrols.h','core/portable/gui/corecontrols.cpp','core/portable/gui/coreviewcontroller.h','core/portable/gui/coreview.h','core/portable/gui/coreview.cpp','core/portable/gui/corebitmap.h','core/portable/gui/corebitmap.cpp','core/portable/gui/corelistview.h','core/portable/gui/corelistview.cpp','core/public/corevector.h']:
 files.add('third_party/ccl-framework/'+f)
for packet in (ROOT/PACKETS).glob('*'):
 if packet.is_dir():files.update(str(p.relative_to(ROOT)) for p in packet.iterdir() if p.is_file())
for group in ['expand-i2f-44','expand-fcmpeq-44','runtime-closure48']:
 directory=ROOT/'temp/recovery-work/rolling200-02/next-implementation20'/group
 files.update(str(p.relative_to(ROOT)) for p in directory.iterdir() if p.is_file())
for p in (ROOT/'evidence/recovery/2026-11-05/rolling200-02/network-view-plan20').rglob('*'):
 if p.is_file():files.add(str(p.relative_to(ROOT)))
files.update(c['log'] for c in logs)
proof_path=EVIDENCE/'proof.json'
proof={'version':1,'created':now(),'cwd':str(ROOT),'worker_thread_id':os.environ.get('CODEX_THREAD_ID'),'session_id':os.environ.get('CODEX_SESSION_ID'),'base_commit':'13c6cf5303f330db4c359986439577d611b65c85','scope':'worker-local native/provider-validated portable source port; not global integration or readiness admission','versions':versions,'elf':fixture['elf'],'elf_sha256':fixture['elf_sha256'],'ranges':fixture['ranges'],'original_range_provenance':fixture['range_provenance'],'source_sha256':{f:sha(f) for f in sorted(files)},'commands':logs,'fixture_sha256':sha(BASE/'fixtures.json'),'native_case_counts':dict(collections.Counter(str(c['input'][0]) for c in fixture['cases'])),'validation_domain':domain,'limitations':limitations,'formatting_verified':True,'compiled':True,'mangling_verified':True,'namespace_signature_verified':True,'namespace_signature_scope':'exact original mangled names and parameter/member/variant identities; ordinary original return declarations unproven','native_behavior_verified':True,'native_behavior_scope':'bounded original app/runtime instructions with explicit native provider boundaries vs actual upstream CCL portable execution','original_declaration_verified':False,'per_function_declarations':[{'mangled':r['targets'][0]['mangled'],'verified':i in [3,4],'scope':'destructor no-parameter variant' if i in [3,4] else 'ordinary return unresolved; CCL-backed source-port declaration'} for i,r in enumerate(requests)],'original_arm_abi_verified':False,'hardware_verified':False,'history_source':{'path':history_path,'sha256':sha(history_path)},'development_observations':[{'observation':'Initial replay compile had a test-only Bitmap name ambiguity; next link used unavailable -lpng development symlink.','resolution':'Renamed test probe and selected existing canonical libpng16.so.16 path; final compile/symbol/replay checks pass.'},{'observation':'i2f/fcmpeq initial packet lacked runtime helper bodies and closure.','resolution':'Root supplied baseline hash-bound expansions plus verified transitive runtime-closure48; every executed PC is now in explicit target/runtime range or intercepted entry, zero unexpected PCs.'}]}
(ROOT/proof_path).write_text(json.dumps(proof,indent=2)+'\n');files.add(str(proof_path))
for req in requests:
 o=req['originals'][0]['original'];packet=PACKETS/req['task_id'];dest=ROOT/'uc-library/candidates'/req['task_id'];dest.mkdir(parents=True,exist_ok=True)
 def kind(f):
  if f==str(proof_path):return 'proof'
  if f==str(BASE/'fixtures.json'):return 'fixture'
  if f==str(BASE/'check.py'):return 'replay'
  if f in owned:return 'test' if '/tests/' in f else 'source'
  if f==str(packet/'context.json'):return 'packet'
  return 'dependency'
 handoff={'version':1,'task_id':req['task_id'],'namespace':req['namespace'],'packet_manifest':str(packet/'context.json'),'originals':[{'elf_sha256':o['elf'],'firmware':o['firmware'],'role':o['role'],'mangled':o['mangled'],'address':o['address'],'size':o['size'],'section':'.text'}],'artifacts':[{'kind':kind(f),'path':f,'sha256':sha(f)} for f in sorted(files)],'checks':checks,'validation_domain':domain,'limitations':limitations,'build_integration':{'production_partition':'Existing NetworkSetupComponent.cpp remains CS18 OBJECT partition; add src/Presonus/Surface/RadioToggleButton.cpp exactly once to CS18 OBJECT partition based on CS18-only original symbols. Existing shared NetworkListSelection.cpp unchanged.','public_headers':['include/presonus/surface/NetworkSetupComponent.hpp','include/presonus/surface/RadioToggleButton.hpp'],'test_targets':['NetworkSetupViewReplay'],'test_sources':['tests/recovery/NetworkSetupViewReplay.cpp'],'compile_options':['-fno-rtti','-fno-lto'],'link_dependencies':['presonus_cs18_components','presonus_uc','actual pinned corelib','presonus_core_allocator','presonus_private_glibc29','PNG','zlib','pthread','dl','m'],'link_options':['--wrap=_Znwm','--wrap=_ZdlPv','--wrap=_ZdlPvm','--wrap=_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE'],'ctest_argv':[PY,str(BASE/'check.py'),'replay','<canonical-built-NetworkSetupViewReplay>',str(BASE/'fixtures.json')],'fixture_sha256':sha(BASE/'fixtures.json'),'notes':'Root owns shared build, full Linux CTest, role/install/compile-once audits, source proof refresh, guarded SQLite dry-run/admission and tracker. No ready/pending fragment is provided; D0/D1 have exact destructor declaration evidence while ordinary methods remain return-declaration pending.'}}
 (dest/'HANDOFF.json').write_text(json.dumps(handoff,indent=2)+'\n')
print('Five exact packet HANDOFF v1 records sealed with final source hashes')
