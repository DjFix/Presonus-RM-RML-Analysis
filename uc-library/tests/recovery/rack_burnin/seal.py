"""Run fresh local gates, bind hashes and emit seven stock HANDOFF v1 files.
This is a worker-local proof producer, not readiness or canonical admission.
"""
import datetime,hashlib,importlib.util,json,pathlib,platform,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[4]
HERE=pathlib.Path(__file__).parent
EVIDENCE=ROOT/'evidence/recovery/2026-11-06/rolling200-02/rack-burnin135'
PACKETS=ROOT/'temp/recovery-work/rolling200-02/next-implementation135/prepared135/packets'
PYTHON='uc-library/.venv/bin/python';CHECK='uc-library/tests/recovery/rack_burnin/check.py'
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def rel(p):return str(pathlib.Path(p).relative_to(ROOT)) if pathlib.Path(p).is_absolute() else str(p)
def dump(p,data):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,indent=2)+'\n')
def main():
 EVIDENCE.mkdir(parents=True,exist_ok=True)
 records=[]
 for mode in ['format','compile','symbols','native','replay','regressions']:
  argv=[PYTHON,CHECK,mode];start=datetime.datetime.now(datetime.timezone.utc).isoformat();before=time.monotonic()
  log=EVIDENCE/(mode+'.log')
  with log.open('w') as f:result=subprocess.run(argv,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
  records.append(dict(kind=mode,argv=argv,returncode=result.returncode,start_utc=start,seconds=time.monotonic()-before,log=rel(log),log_sha256=sha(rel(log))))
  dump(EVIDENCE/'commands.json',records)
  if result.returncode:raise SystemExit('Gate failed: '+mode+'; '+str(log))
 fixture=json.loads((HERE/'fixtures.json').read_text())
 sources=['uc-library/include/presonus/panel/RackPanelComponent.hpp','uc-library/include/presonus/panel/PanelRegistrar.hpp','uc-library/include/presonus/surface_panel/ControlHelpers.hpp','uc-library/src/Presonus/Panel/RackPanelBurnIn.cpp','uc-library/src/Presonus/Panel/ControlRegistrarCommands.cpp','uc-library/src/Presonus/Panel/PanelRegistrarDualMessage.cpp']
 tests=['uc-library/tests/recovery/RackPanelBurnInReplay.cpp']
 producers=[CHECK,rel(HERE/'native.py'),rel(HERE/'seal.py')]
 providers=['uc-library/src/Presonus/Panel/RackPanelComponent.cpp','uc-library/src/Presonus/Panel/PanelRegistrar.cpp','uc-library/src/Presonus/Panel/protocol_comm.cpp','uc-library/src/Presonus/Panel/uart_protocol.cpp','uc-library/src/Presonus/Panel/PanelTask.cpp','uc-library/src/Presonus/Panel/LEDNotifyTask.cpp','uc-library/src/Presonus/Panel/PanelComponentLifecycle.cpp','uc-library/src/Presonus/Panel/control.cpp','uc-library/src/Presonus/Panel/param_edit_handler.cpp','uc-library/src/Presonus/DelayTimer.cpp','uc-library/src/Presonus/DICE/PacketClockGateway.cpp','third_party/ccl-framework/core/system/coretime.h','third_party/ccl-framework/core/platform/shared/posix/coretime.posix.h','third_party/ccl-framework/core/system/coredebug.cpp','third_party/ccl-framework/core/portable/coreparams.cpp','third_party/ccl-framework/core/public/corevector.h','uc-library/tests/recovery/rack_network_tasks/check.py','uc-library/tests/recovery/rack_network_tasks/fixtures.json','uc-library/candidates/rolling200_02_rack_lifecycle/check.py','uc-library/candidates/rolling200_02_rack_lifecycle/native.py','uc-library/candidates/rolling200_02_rack_lifecycle/fixtures.json']+[str(p.relative_to(ROOT)) for p in (ROOT/'temp/recovery-work/rolling200-03/provider-supplements189/uart189').glob('*') if p.is_file()]
 libraries=['temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a','temp/core-upstream/root-integration-01/libpresonus_uc.a']
 domain='Seven portable methods / eleven original ELF identities. Exact four-byte LED, meter and scan messages; both bools; virtual base/derived dispatch; null primary; disabled/enabled secondary; primary mutation of message and enabled state before secondary. Burn-in signed nanosecond division and strict >500ms deadline, final resampling, held-count 4 and >6 consecutive polls, process-shared latch/counter/timestamp across two receivers, active clearing and immediate relatch/double-send; onIdle exact burn-in/permissions/network/task call order. 814 independent ARM frames and actual C++/CCL/protocol wire replay; explicit binding failures, source-port exception timing, actual permission gating, task lifetime/removal and existing provider regressions.'
 limitations='Portable source port only. All seven ordinary original return declarations, original inheritance/fields/layout and ARM32 calling convention remain unresolved; no original ABI or hardware interoperability claim. Abstract native getPort is implemented only as an independent explicit borrowed-port binding for existing standalone consumers; PanelRegistrar uses its existing actual getPort provider. Original clock/debug/division/getPort/port boundaries and existing permissions/network/idleTasks are intercepted in the ARM oracle; actual pinned CCL/application/protocol providers and existing regressions execute separately. Synthetic native memory is not an original class layout declaration. Single-threaded caller domain; counter wrap expressed explicitly but >2^31 consecutive-poll exhaustion not replayed. Native invalid enabled/null-secondary dereference and exceptions are outside native equivalence; portable failures are explicit, tested adaptations. No hardware, device opening, network, serial, ioctl, flashing or native syscall passthrough.'
 integration={'production_partitions':{'common':['uc-library/src/Presonus/Panel/ControlRegistrarCommands.cpp'],'rm':['uc-library/src/Presonus/Panel/RackPanelBurnIn.cpp','uc-library/src/Presonus/Panel/PanelRegistrarDualMessage.cpp']},'public_headers':sources[:3],'test_target':'rack_panel_burnin_replay','test_sources':tests,'instrumented_test_translation_units':sources[3:]+providers[:2],'compile_options':['-finstrument-functions (only instrumented test TUs)','-fno-rtti','-ffunction-sections','-fdata-sections'],'link_dependencies':['canonical application archive','pinned CCL corelib and allocator','pthread','dl','z'],'link_options':['--gc-sections','--wrap=clock_gettime','--wrap=_ZN4Core11DebugPrintfEPKcz'],'ctest_replay_argv':[PYTHON,CHECK,'replay','<canonical-built-rack_panel_burnin_replay>','uc-library/tests/recovery/rack_burnin/fixtures.json'],'notes':'Root adds exactly one production OBJECT partition per new CPP. The test-only instrumented current canonical TUs override matching archive members; do not instrument the replay TU itself. Canonical full Linux CTest/installed-role/compile-once/active-source/admission remain Root-owned. onIdle overrides the real upstream Component virtual and retains the actual permission-reset provider in standalone regression links; group application and CCL archives as in check.py.'}
 proof={'version':1,'producer':{'path':rel(HERE/'seal.py'),'sha256':sha(rel(HERE/'seal.py'))},'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'host':platform.platform(),'checkout_base':'3a5d52a2677966b0b6e2e6a662bc0e3b5588965b','original_ranges':fixture['ranges'],'source_sha256':{p:sha(p) for p in sources},'provider_sha256':{p:sha(p) for p in providers+libraries},'producer_sha256':{p:sha(p) for p in producers},'fixture_sha256':sha(rel(HERE/'fixtures.json')),'native_frames':sum(len(c['frames']) for c in fixture['cases']),'native_scenarios':len(fixture['cases']),'checks':records,'validation_domain':domain,'limitations':limitations,'declaration_verified':False,'arm_abi_verified':False,'hardware_validated':False,'readiness_admitted':False,'core_provider_commit':subprocess.check_output(['git','-C','third_party/ccl-framework','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'formatter_version':subprocess.check_output(['uc-library/.venv/bin/clang-format','--version'],cwd=ROOT,text=True).strip(),'versions':subprocess.check_output([PYTHON,'-c','import unicorn,elftools; print("unicorn",unicorn.__version__,"pyelftools",elftools.__version__)'],cwd=ROOT,text=True).strip(),'build_integration':integration}
 remarks=[]
 for packet in sorted(PACKETS.glob('*rack*')):
  request=json.loads((packet/'request.json').read_text())
  work=request.get('work_binding',{})
  for record in request['originals']:
   original=record['original']
   remarks.append({'date':'2026-11-06','elf_sha256':original['elf'],'mangled':original['mangled'],'work_binding':work,'status':'compiled_declaration_pending','note':domain,'unresolved':limitations,'evidence':rel(EVIDENCE/'proof.json'),'retry_condition':'Independent original declaration/layout evidence for declaration/ABI promotion; new bounded native observations for expanded semantic domains. Preserve the present notes and append resolutions.'})
 dump(EVIDENCE/'remarks.json',remarks)
 proof['remarks_path']=rel(EVIDENCE/'remarks.json');proof['remarks_sha256']=sha(rel(EVIDENCE/'remarks.json'))
 dump(EVIDENCE/'proof.json',proof)
 artifacts=[]
 def add(kind,p):
  p=rel(p)
  if p not in [a['path'] for a in artifacts]:artifacts.append(dict(kind=kind,path=p,sha256=sha(p)))
 for p in sources:add('source',p)
 for p in tests:add('test',p)
 add('fixture',HERE/'fixtures.json');add('replay',CHECK)
 for p in producers+providers+libraries:add('dependency',p)
 for p in [EVIDENCE/'proof.json',EVIDENCE/'commands.json',EVIDENCE/'native-audit.json',EVIDENCE/'remarks.json']:add('proof',p)
 for r in records:add('log',r['log'])
 for packet in sorted(PACKETS.glob('*rack*')):
  current=list(artifacts)
  manifest=packet/'context.json';native=packet/'native-context.json';request=packet/'request.json'
  for path in [manifest,native,request]:current.append(dict(kind='packet',path=rel(path),sha256=sha(rel(path))))
  ctx=json.loads(manifest.read_text());originals=[]
  for item in ctx['originals']:
   o=item['original'];originals.append(dict(elf_sha256=o['elf'],firmware=o['firmware'],role=o['role'],mangled=o['mangled'],address=o['address'],size=o['size'],section=o['section_json']))
  checks=[dict(kind=mode,argv=[PYTHON,CHECK,mode],timeout_seconds=300 if mode=='regressions' else 180) for mode in ['format','compile','symbols','native','replay','regressions']]
  handoff=dict(version=1,task_id=ctx['task_id'],namespace='Presonus::Panel',packet_manifest=rel(manifest),originals=originals,artifacts=current,checks=checks,validation_domain=domain,limitations=limitations,build_integration=integration)
  dump(ROOT/'uc-library/candidates'/ctx['task_id']/'HANDOFF.json',handoff)
 spec=importlib.util.spec_from_file_location('accept_worker',ROOT/'uc-library/tools/recovery/accept_worker.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 for packet in sorted(PACKETS.glob('*rack*')):
  path=ROOT/'uc-library/candidates'/packet.name/'HANDOFF.json';module.validate(json.loads(path.read_text()));print('Stock validate PASS',rel(path))
if __name__=='__main__':main()
