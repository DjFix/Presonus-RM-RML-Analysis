"""Seal only worker-local evidence; no registry, CMake or global proof mutation."""
import datetime,hashlib,importlib.util,json,pathlib,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0,str(pathlib.Path(__file__).parent))
import check
import native
import unicorn
EVID='evidence/recovery/2026-11-05/rolling200-02/fx-lifecycle'
CAND='uc-library/candidates/rolling200_02_fx_lifecycle'
PACKETS='temp/recovery-work/rolling200-02/implementation-plan01/packets-current-fx-lifecycle03/packets'
def sha(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def write(path,obj):
 p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,indent=2)+'\n')
def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def main():
 start=stamp();checks=[]
 for mode in ['format','compile','symbols','replay']:
  argv=['uc-library/.venv/bin/python',check.DIR+'/check.py',mode]
  t=time.monotonic();ts=stamp();r=subprocess.run(argv,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  log=EVID+'/'+mode+'.log';(ROOT/log).write_text(r.stdout)
  checks.append(dict(kind=mode,argv=argv,timeout_seconds=120,start_utc=ts,seconds=time.monotonic()-t,returncode=r.returncode,log=log))
  print(mode,r.returncode,flush=True)
  assert r.returncode==0,r.stdout
 fixture=json.loads((ROOT/(check.DIR+'/fixtures.json')).read_text())
 assert native.generate()==fixture
 for i,record in enumerate(fixture['ranges'],1):
  packet=ROOT/PACKETS/f'rolling200_02_fx_lifecycle_{i:02}'
  request=json.loads((packet/'request.json').read_text());target=request['targets'][0]
  assert target['mangled']==record['mangled'] and target['address']==record['address'] and target['size']==record['size']
  bodies=json.loads((packet/'native-context.json').read_text())['bodies'].values()
  body=next(x for x in bodies if x['address']==record['address'])
  assert body['bytes_sha256']==record['sha256'] and body['file_offset']==record['file_offset'] and body['size']==record['size']
  assert sha(str(packet.relative_to(ROOT))+'/context.json')==['5399ad10a9f17df042908a4edefe7be07b42a036f510597ed05ae5009fc1bf0c','3ff2bb6a24e91d3501dd5ff3040a12ba99d64128e442e5b4ae14feeb232000f3','9072071b2f70009f97fd90012b1840d7ed0e2d782a46a997ae2c48f229692bd2'][i-1]
 limits=[
  'Portable lifecycle source port using explicit composition, not original inheritance/layout/ARM32 binary compatibility. Host D1/D2 alias; all three native full byte ranges are checked independently and their normal paths executed.',
  'Native Core removeObserver/vector and application PresetComponent calls are bounded external providers; no native Core body is executed. Native operator delete is observed at its actual call boundary; original allocator implementation is not executed.',
  'Host runs actual pinned CCL membership/vector destruction and canonical PresetComponent destructor, including actual cache-observer removal and Core Component destruction. PresetApplicationServices and opaque cache delegate token are explicit test boundaries. Base destructor has no separate original readiness admission.',
  'Owned lifecycle registration receiver is the actual owned PresetComponent observer. Parameter notifications, original Fx observer dispatch and original receiver adjustment equivalence are outside this destruction-only source-port domain.',
  'Legacy borrowed-array constructor intentionally has no observer registration, vector storage ownership or base provider. New owning constructor does not own borrowed children/parameter/services. Copying is disabled to preserve single lifecycle ownership.',
  'Exception/unwind landing pads, allocation failure, invalid input, concurrent callbacks, full native base lifecycle, hardware and network behavior remain untested. All cleanup providers must outlive the component; throwing cleanup callbacks are unsupported.',
  'Native vtable writes are recorded and guarded, but host source composition intentionally does not reproduce ARM vtable fields. Host semantic comparison excludes the literal native pointer/vtable values and compares provider order plus actual allocation/membership invariants.',
  'Native count/cache fields are provider boundary inputs, not inferred original declarations. Array free and cache membership are separately checked through actual source providers; these are not claims about original Core binary behavior.'
 ]
 domain='24 independently executed native target cases: each D0/D1/D2 × null/non-null optional parameter × empty/three borrowed nonnull child-pointer vector × absent/present source-port cache registration. Host replay compares V/B/[D] provider order; actual CCL membership before/after; actual vector array and vector object deallocation before actual base cleanup; actual base cache deregistration and object deallocation; actual D0 free versus explicit D1/D2 destruction without object free; duplicate borrowed child survival. Prior getRecallParameter, presetStored/updateFxName, getFxIndex missing-selection, recall(false), and preset-type behaviors are exercised as source-port regressions, not new original method admissions.'
 dependencies=[
  'uc-library/include/presonus/panel/PresetComponent.hpp','uc-library/include/presonus/panel/PresetNameCache.hpp','uc-library/include/presonus/panel/FXPresetRecallComponent.hpp',
  *check.DEPENDENCIES,'uc-library/src/Presonus/Panel/PresetComponentSlotPaths.cpp','uc-library/src/Presonus/Panel/PresetParameterAccess.hpp',
  'third_party/ccl-framework/core/portable/coreparams.h','third_party/ccl-framework/core/portable/coreparams.cpp','third_party/ccl-framework/core/public/corevector.h','third_party/ccl-framework/core/portable/corecomponent.h','third_party/ccl-framework/core/portable/corecomponent.cpp',
  check.SDK+'libcorelib.a',check.SDK+'libpresonus_core_allocator.a','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a','temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so',
  'uc-library/tools/recovery/accept_worker.py']
 dependencies=list(dict.fromkeys(dependencies))
 sources=[check.HEADER,check.SOURCE,check.TEST]
 producers=[check.DIR+'/native.py',check.DIR+'/check.py',check.DIR+'/make_delivery.py']
 paths=sources+dependencies+producers+[check.DIR+'/fixtures.json']
 hashes={p:sha(p) for p in paths}
 proof=dict(version=1,worker='rolling200_02_fx_lifecycle',checkout=str(ROOT),base_commit='d548724a88fbb82e34f7a43b1c56081c6afda7c9',validation_start_utc=start,validation_end_utc=stamp(),identity_ranges=fixture['ranges'],elf=dict(path=fixture['elf_path'],sha256=fixture['elf_sha256']),source_and_provider_hashes=hashes,executable=dict(path=check.EXE,sha256=sha(check.EXE)),checks=checks,compile_argv=check.COMPILE,native_case_count=24,host_case_count=24,validation_domain=domain,limitations=limits,formatter_version=subprocess.check_output([str(ROOT/'uc-library/.venv/bin/clang-format'),'--version'],text=True).strip(),compiler_version=subprocess.check_output(['/usr/bin/c++','--version'],text=True).splitlines()[0],unicorn_version=unicorn.__version__,python_version=sys.version,provider_commit=subprocess.check_output(['git','-C','third_party/ccl-framework','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),provider_root_history=subprocess.check_output(['git','-C','third_party/ccl-framework','rev-list','--parents','--max-count=1','e8cbdea4a4a20e15111f5a690798a259c0374b31'],cwd=ROOT,text=True).strip(),readiness_admitted=False,hardware_validated=False,original_arm_abi_verified=False,source_port_behavior_validated=True)
 write(EVID+'/PROOF.json',proof)
 notes=[]
 for i,record in enumerate(fixture['ranges'],1):
  task=f'rolling200_02_fx_lifecycle_{i:02}';packet=PACKETS+'/'+task;request=json.loads((ROOT/packet/'request.json').read_text());orig=request['originals'][0]['original']
  notes.append(dict(date=stamp(),original_elf_sha256=fixture['elf_sha256'],mangled=record['mangled'],unique_work_item=request['work_binding']['work_item_id'],status='local_source_port_validated_pending_root_integration',owner=task,evidence=[EVID+'/PROOF.json',check.DIR+'/fixtures.json'],remarks=limits,resolution_or_retry_condition='Root reviews source-port lifecycle composition and native/provider boundaries, runs local acceptance and canonical integration/admission gates. Revisit original receiver/layout/unwind questions only when new native evidence or explicit scope warrants. Initial local compile attempted RTTI enabled against RTTI-disabled pinned provider; failed undefined NumericParam typeinfo, corrected to -fno-rtti. That failed pre-seal invocation is not a successful proof.'))
 write(EVID+'/REMARKS.json',notes)
 integration=dict(production_partition='existing PRESONUS_rm_SOURCES only; FxPresetComponent.cpp already listed once',production_cpp=check.SOURCE,public_headers=[check.HEADER],test_target='fx_preset_lifecycle_replay',test_source=check.TEST,link_dependencies=['presonus_uc','presonus_core'],ctest_name='fx_preset_lifecycle_provider_differential',ctest_argv=['uc-library/.venv/bin/python',check.DIR+'/check.py','replay','--executable','$<TARGET_FILE:fx_preset_lifecycle_replay>','--fixtures',check.DIR+'/fixtures.json'],fixture_bindings={check.DIR+'/fixtures.json':sha(check.DIR+'/fixtures.json')},assertions='Test executable must retain assertions (no NDEBUG); private global operator delete/delete[] interposition belongs only to standalone test binary.',worker_scope='No shared CMake, registry, tracker, global proof or readiness edits. No ready/pending fragments produced; Root owns required guarded dry-run/admission.')
 for i in range(1,4):
  task=f'rolling200_02_fx_lifecycle_{i:02}';packet=PACKETS+'/'+task;request=json.loads((ROOT/packet/'request.json').read_text());orig=request['originals'][0]['original']
  artifacts=[]
  def artifact(kind,p):artifacts.append(dict(kind=kind,path=p,sha256=sha(p)))
  for p in [check.HEADER,check.SOURCE]:artifact('source',p)
  artifact('test',check.TEST);artifact('fixture',check.DIR+'/fixtures.json');artifact('replay',check.DIR+'/check.py');artifact('producer',check.DIR+'/native.py');artifact('producer',check.DIR+'/make_delivery.py')
  for p in dependencies:artifact('dependency',p)
  for p in ['context.json','request.json','native-context.json','ELF_CONTEXT.md','TASK.md','SOURCE_SLICES.md','CONTEXT.md']:artifact('packet',packet+'/'+p)
  artifact('contract',request['reconstruction_contract']['path'])
  artifact('proof',EVID+'/PROOF.json');artifact('remarks',EVID+'/REMARKS.json')
  for c in checks:artifact('log',c['log'])
  handoff=dict(version=1,task_id=task,namespace='Presonus::Panel::FxPresetComponent',packet_manifest=packet+'/context.json',originals=[dict(elf_sha256=orig['elf'],firmware=orig['firmware'],role=orig['role'],mangled=orig['mangled'],demangled=orig['demangled'],address=orig['address'],size=orig['size'],section=orig['section_json'])],artifacts=artifacts,checks=[{k:c[k] for k in ['kind','argv','timeout_seconds']} for c in checks],validation_domain=domain,limitations=limits,build_integration=integration)
  dest=CAND+'/'+task+'/HANDOFF.json';write(dest,handoff)
  spec=importlib.util.spec_from_file_location('accept_worker',ROOT/'uc-library/tools/recovery/accept_worker.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  module.validate(json.loads((ROOT/dest).read_text()))
  print('Stock accept_worker.validate passed',dest,flush=True)
if __name__=='__main__':main()
