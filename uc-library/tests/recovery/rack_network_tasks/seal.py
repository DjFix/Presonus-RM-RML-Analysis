"""Replay final source and seal six independently identified worker handoffs."""
import datetime,hashlib,json,pathlib,subprocess,sys,time,importlib.util
ROOT=pathlib.Path(__file__).resolve().parents[4];sys.path.insert(0,str(pathlib.Path(__file__).parent))
import check
E=pathlib.Path('evidence/recovery/2026-11-05/rolling200-02/rack-network15')
PACK=pathlib.Path('temp/recovery-work/rolling200-02/next-implementation15/prepared-rack-network15/packets')
BASE='uc-library/tests/recovery/rack_network_tasks/'
PYTHON='uc-library/.venv/bin/python'
def digest(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def write(p,d):
 (ROOT/p).parent.mkdir(parents=True,exist_ok=True);(ROOT/p).write_text(json.dumps(d,indent=2)+'\n')
def artifact(kind,p):return {'kind':kind,'path':str(p),'sha256':digest(p)}
def command(argv):
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();before=time.monotonic()
 p=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True);return p,{'argv':argv,'start_utc':start,'seconds':time.monotonic()-before,'returncode':p.returncode}
records=[]
for mode in ['format','compile','symbols','native','replay','regressions']:
 print(mode,flush=True);p,record=command([PYTHON,BASE+'check.py',mode]);path=E/(mode+'-final.log');(ROOT/path).write_text(p.stdout+p.stderr);record['log']=str(path);record['log_sha256']=digest(path);records.append(record)
 if p.returncode:raise SystemExit(p.stdout+p.stderr)
ids=[1,2,3,4,6,13];originals={};requests={}
for i in ids:
 packet=PACK/f'rolling200_02_rack_network15_{i:02}';r=json.loads((ROOT/packet/'request.json').read_text());requests[i]=r;o=r['originals'][0]['original'];originals[i]={'elf_sha256':o['elf'],'firmware':o['firmware'],'role':o['role'],'mangled':o['mangled'],'demangled':o['demangled'],'address':o['address'],'size':o['size'],'section':int(o['section_json'])}
fixture=json.loads((ROOT/BASE/'fixtures.json').read_text());casecounts={str(i):sum(c['input']['target']==i for c in fixture['cases']) for i in ids}
limits=[
 'Portable Linux source port only: original ordinary return spelling, class inheritance, fields, vtables, ownership declarations, ARM32 layout/calling convention and binary interoperability remain unresolved.',
 'Core binary instructions never execute. Clock, signed division, allocation, vector and virtual provider boundaries are explicit native models; production uses actual pinned CCL Core and the existing packetClockRawTicks gateway. No legacy Core implementation is reconstructed.',
 'Native detachLEDs is a modeled existing application helper boundary. Fresh 108-case existing helper differential regression separately checks actual canonical helper effects; no claim of executing its ARM body in this oracle.',
 'Native idleTasks does not delete tasks. The scheduling vector borrows pointers; external task and parameter lifetimes must remain valid. Independent notificationStorage retains Rack-created tasks until Rack destruction, including completed tasks; this explicit memory-management adaptation is not original ownership evidence.',
 'Successful allocation/container growth is the differential domain. The source port uses RAII and throws on failed queue additions; original add-failure/exception behavior, arbitrary callback deletion/reordering of initial tasks, concurrent mutation and device/network changes are not validated.',
 'Network tree and timestamp are explicit borrowed bindings; application wiring to the full original mixer tree is outside this bounded port. The existing permissionStartupMilliseconds binding is shared by both reset checks.',
 'No hardware operations, original network provider implementation, network interface changes, or hardware interoperability were exercised. Global integration, installed-role/compile-once checks and SQLite admission remain Root-owned.'
]
domain='476 original ARM executions vs executable C++: base zero return; strict signed64 wrapped deadline compare and signed nanosecond division; nullable task parameter; all network/component/tag-presence masks; 0/1/2/3/6/7/8 control counts; reset flags/time thresholds/negative elapsed/wrap; callback mutation causing dynamic then static assignment; actual CCL controller edits; initial-count sweep, duplicate tasks, deferred pointer removals and callback append. Existing 108 helper behavior cases, 100 prior Rack-method native cases, eight Rack lifecycle native cases, and owner regression with 147 allocation failure paths rerun from current source.'
notes=[]
for i in ids:
 notes.append({'date':'2026-11-05','original':originals[i],'unique_work_item':requests[i]['work_binding']['work_item_id'],'status':'bounded_port_validated_original_declaration_pending','observations':limits,'proof':str(E/'LOCAL_PROOF.json'),'resolution_or_retry_condition':'Resolve original declaration/ARM ABI only with independent evidence. Additional allocation-failure/callback-lifetime or real network/hardware coverage requires separate bounded validation; Root global integration and guarded admission remain required.'})
write(E/'REMARKS.json',{'version':1,'worker':'/root/rolling200_02_rack_network15','remarks':notes,'failed_approaches':['First oracle synthetic PARAM region overlapped task-vtable memory; corrected to disjoint region before fixture production. No expected result copied from C++.','First regression archive link ordering then duplicate historical Control object failed; replaced archive app providers with current canonical source builds. Preserved attempt logs; final runs pass.']})
# Bind all compiled source, test producer, actual provider interfaces/implementations,
# immutable original packets and regression fixtures/producers used by final checks.
paths={}
def bind(kind,p):paths[str(p)]=artifact(kind,pathlib.Path(p))
for p in check.FILES:bind('test' if p.endswith('Replay.cpp') else 'source',p)
for p in check.SOURCES:
 if p not in paths:bind('dependency',p)
for p in ['check.py','native.py','seal.py']:bind('replay' if p=='check.py' else 'producer',BASE+p)
bind('fixture',BASE+'fixtures.json')
for p in ['core/portable/coreparams.h','core/portable/coreparams.cpp','core/portable/corecomponent.h','core/portable/corecomponent.cpp','core/public/corevector.h','core/system/coretime.h','core/platform/shared/posix/coretime.posix.h']:bind('provider',pathlib.Path('third_party/ccl-framework')/p)
for p in [check.LIB+'libcorelib.a',check.LIB+'libpresonus_core_allocator.a','uc-library/include/presonus/dice/packet_services.hpp','uc-library/include/presonus/panel/PanelComponent.hpp','uc-library/include/presonus/panel/control.hpp','uc-library/include/presonus/mixer/MixerComponentBase.hpp','uc-library/src/Presonus/Panel/LEDControlLifecycle.cpp','uc-library/src/surface_panel/LEDState.cpp','uc-library/src/surface_panel/ControlGroup.cpp','uc-library/src/Presonus/Panel/FrontPanelLifecycle.cpp','uc-library/src/Presonus/Mixer/MixerComponentBase.cpp','uc-library/src/Presonus/Mixer/PermissionsComponent.cpp','uc-library/tests/graph_trial07_rackpanel_tests.cpp','uc-library/tests/recovery/trial07/rackpanel/replay.py','uc-library/tests/recovery/trial07/rackpanel/fixtures.json','uc-library/tests/recovery/RackPanelLifecycleReplay.cpp','uc-library/tests/recovery/PanelOwnerRegression.cpp','uc-library/candidates/rolling200_02_rack_lifecycle/check.py','uc-library/candidates/rolling200_02_rack_lifecycle/native.py','uc-library/candidates/rolling200_02_rack_lifecycle/fixtures.json','uc-library/candidates/rolling200_02_rack_panel/check.py','uc-library/candidates/rolling200_02_rack_panel/replay.cpp','uc-library/candidates/rolling200_02_rack_panel/native.py','uc-library/candidates/rolling200_02_rack_panel/native.json','uc-library/candidates/rolling200_02_rack_panel/status-provider.json']:
 bind('dependency',p)
for i in ids:
 for f in ['context.json','request.json','native-context.json','ELF_CONTEXT.md']:
  bind('packet',PACK/f'rolling200_02_rack_network15_{i:02}'/f)
(ROOT/E/'native-pc-audit-replay.json').write_bytes((ROOT/'temp/recovery-work/rolling200-02/rack-network15/native-pc-audit-replay.json').read_bytes())
for p in [E/'REMARKS.json',E/'native-pc-audit.json',E/'native-pc-audit-replay.json']:bind('evidence',p)
for r in records:bind('log',r['log'])
version=subprocess.check_output([str(ROOT/'uc-library/.venv/bin/clang-format'),'--version'],text=True).strip()
proof={'version':1,'worker_agent':'/root/rolling200_02_rack_network15','worker_session_id':'coordinator-owned; not exposed to worker','sealed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checkout_baseline':'f9ffa8e39a0706d5a35b173aa947d5de813a75de','originals':list(originals.values()),'original_ranges':fixture['ranges'],'formatter_version':version,'provider_commit':subprocess.check_output(['git','-C',str(ROOT/'third_party/ccl-framework'),'rev-parse','HEAD'],text=True).strip(),'provider_root_commit_verified':subprocess.check_output(['git','-C',str(ROOT/'third_party/ccl-framework'),'rev-list','--parents','-n','1','e8cbdea4a4a20e15111f5a690798a259c0374b31'],text=True).strip(),'executions':{'original_arm':len(fixture['cases']),'portable_cpp':len(fixture['cases']),'per_target':casecounts,'native_and_portable_separate':True},'checks':records,'source_and_producer_bindings':list(paths.values()),'validation_domain':domain,'limitations':limits,'native_pc_policy':'Fail closed before every instruction; only per-target sealed application closure or intercepted entry. No Core body executed.','ready':False,'readiness_admitted':False}
write(E/'LOCAL_PROOF.json',proof);bind('proof',E/'LOCAL_PROOF.json')
integration={'production_partition':'PRESONUS_rm_SOURCES only (original assigned symbols are RM/server); Root reviews ownership before integration','existing_source':'src/Presonus/Panel/RackPanelComponent.cpp already RM partition; do not add again','new_sources':['src/Presonus/Panel/PanelTask.cpp','src/Presonus/Panel/LEDNotifyTask.cpp'],'public_headers':['presonus/panel/PanelTask.hpp','presonus/panel/LEDNotifyTask.hpp'],'test_target':'RackNetworkTasksReplay from tests/recovery/RackNetworkTasksReplay.cpp; link presonus::rm_components with real Core and allocator, -fno-rtti, -UNDEBUG, --wrap=_ZN8presonus4dice19packetClockRawTicksEv','ctest_argv':[PYTHON,BASE+'check.py','replay','<canonical-built-RackNetworkTasksReplay>',BASE+'fixtures.json'],'fixture_sha256':digest(BASE+'fixtures.json'),'other_required_replays':'Existing graph_trial07_rackpanel, RackPanelLifecycleReplay + PanelOwnerRegression, and rolling200_02_rack_panel; global full Linux, installed-role, compile-once and guarded SQLite admission remain Root-owned','no_shared_build_or_ledger_edits':True}
for i in ids:
 task=requests[i]['task_id'];checks=[{'kind':m,'argv':[PYTHON,BASE+'check.py',m],'timeout_seconds':120} for m in ['format','compile','symbols','replay']]
 if i==13:checks += [{'kind':'native','argv':[PYTHON,BASE+'check.py','native'],'timeout_seconds':120},{'kind':'regressions','argv':[PYTHON,BASE+'check.py','regressions'],'timeout_seconds':240}]
 h={'version':1,'task_id':task,'namespace':requests[i]['namespace'],'packet_manifest':str(PACK/task/'context.json'),'originals':[originals[i]],'artifacts':list(paths.values()),'checks':checks,'validation_domain':domain+' Exact target cases: '+casecounts[str(i)].__str__(),'limitations':limits,'build_integration':integration}
 write(pathlib.Path('uc-library/candidates')/task/'HANDOFF.json',h)
print('Sealed six HANDOFF v1 files',casecounts,flush=True)
