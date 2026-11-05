"""Seal worker-local proof and HANDOFF v1. No global build/registry writes."""
from pathlib import Path
import hashlib,json,subprocess,datetime,time,sys
R=Path.cwd();A=Path(__file__).resolve().parent;T=R/'uc-library/tests/recovery/rolling200-02/eq-constructors'
E=R/'evidence/recovery/2026-11-05/rolling200-02/eq-constructors/local-final01'
E.mkdir(parents=True,exist_ok=False)
rel=lambda p:str(p.relative_to(R));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,value):p.write_text(json.dumps(value,indent=2)+'\n')
checks=[]
for mode in ['format','compile','symbols','native','replay','adapter','regression','sanitizer']:
 argv=['uc-library/.venv/bin/python',rel(T/'check.py'),mode];start=time.monotonic();stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
 p=subprocess.run(argv,cwd=R,text=True,capture_output=True)
 (E/(mode+'.stdout')).write_text(p.stdout);(E/(mode+'.stderr')).write_text(p.stderr)
 checks.append({'kind':mode,'argv':argv,'returncode':p.returncode,'started_utc':stamp,'elapsed_seconds':time.monotonic()-start})
 write(E/'CHECKS.json',checks)
 if p.returncode:raise SystemExit(f'{mode} failed; preserved logs {E}')
versions={}
for name,argv in [('formatter',['uc-library/.venv/bin/clang-format','--version']),('compiler',['/usr/bin/c++','--version']),('unicorn',['uc-library/.venv/bin/python','-c','import unicorn;print(unicorn.__version__)']),('ccl_git_root',['git','-C','third_party/ccl-framework','show','--no-patch','--format=%H %P','e8cbdea4a4a20e15111f5a690798a259c0374b31'])]:
 versions[name]={'argv':argv,'output':subprocess.check_output(argv,cwd=R,text=True).strip()}
search=['rg','-n','LogInterpolator','third_party/ccl-framework/core'];p=subprocess.run(search,cwd=R,text=True,capture_output=True);assert p.returncode==1
write(E/'PROVIDER_SEARCH.json',{'argv':search,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr,'scope':'Complete actual pinned Core source tree; not a claim about other releases or vendor-private providers.'})
source=[R/'uc-library/include/presonus/mixer_dsp/EQControl.hpp',R/'uc-library/src/Presonus/EQControl.cpp']
packets=R/'temp/recovery-work/rolling200-02/implementation-plan01/packets-eq-constructors02/packets'
requests=[json.loads((packet/'request.json').read_text()) for packet in sorted(packets.glob('rolling200_02_eq_constructors_*'))]
identity=lambda q:{'elf_sha256':q['targets'][0]['original_elf_sha256'],'firmware':'CS18AI surface 13840','role':'client','mangled':q['targets'][0]['mangled'],'address':q['targets'][0]['address'],'size':q['targets'][0]['size'],'section':12}
fixtures=json.loads((T/'fixtures.json').read_text())
limitations=[
'Portable source port only. Original inheritance/layout/vtable/exception ABI/ARM calling convention/binary interoperability are not recovered. Host C1/C2 alias at one entry is distinct from original two different 584-byte ranges; every original range is separately section/hash checked and executed.',
'No native Core body executes. Native oracle records exact successful original application instructions/stores and named provider entry arguments; pinned actual CCL providers replay separately. Exception landing pads are range-verified bytes but not executed; allocation failure/unwinding is excluded.',
'Pinned CCL 5.0.0 has no Core::LogInterpolator. Root corrected the erroneous planning assertion after complete source-tree search. Independent presonus::dsp::EQControlFrequencyInterpolator uses actual CCL Interpolator bootstrap state(0,1,mid1), not a fabricated Core class; all conversion calls reject bootstrap until an existing supported positive EqLogSourceInterpolator domain is configured. Invalid transition disables conversion while leaving previous visible range values. Explicit bootstrap reset disables conversion. No original Core conversion equivalence is claimed.',
'Existing EqLogSourceInterpolator supports eight finite positive domains and midpoint0; preserved unchanged. 2056 delegated forward/inverse samples plus bootstrap/reset/invalid-transition checks establish only this independent source adaptation behavior.',
'CCL ParamList/NumericParam behavior takes precedence over original missing Core provider behavior. Standalone pinned factory has linear/linrev/zoom, so hpfQ skew is unresolved/null until application bootstrap; source table preserves original skew and gain labels exactly, without implicit global registration. Host and independent provider replay observe the same pinned behavior; no claim that missing native Core skew/gain bodies were executed.',
'Static exact-range getCurve prologue reads original offsets0x88/0x8c, separate from frequency-provider range(0,1). Constructor observed stores prove portable curve limits0/0; initial suspicion that these model provider min/max was rejected by native evidence. No sealed contract was edited.',
'Three original null borrowed slots are represented as explicit untyped independent borrowed boundaries; their original declarations, types, ownership and future binding interfaces remain unresolved. No device/hardware/network/guest syscall passthrough occurs.',
'Actual source supporting RAII and150 real parameter destruction notifications (plus sanitizer replay) prove bounded host lifetime only; original destructor variants receive no readiness credit.',
'No ready/pending fragments or readiness admission supplied. Root owns shared CMake/full Linux/installed-role/compile-once/active-source/guarded SQLite/tracker/mirror gates.'
]
proof={'version':1,'passed':True,'date':datetime.datetime.now(datetime.timezone.utc).isoformat(),'worker_session':'/root/rolling200_02_eq_constructors','checkout':str(R),'baseline':'d548724a88fbb82e34f7a43b1c56081c6afda7c9','originals':[identity(q) for q in requests],'versions':versions,'source_sha256':{rel(p):sha(p) for p in source},'checks':checks,'native_execution':{'elf_sha256':fixtures['elf_sha256'],'ranges':fixtures['ranges'],'cases':len(fixtures['cases']),'provider_boundary_trace_and_native_writes':rel(T/'fixtures.json'),'fixture_sha256':sha(T/'fixtures.json'),'executed_Core_instructions':0,'policy':fixtures['policy']},'portable_replay':{'explicit_C1_cases':25,'explicit_C2_cases':25,'provider_table_replays':50,'adapter_samples':2056,'actual_parameter_destructions':150,'sanitizer_replays':50,'compiled_executable_sha256':sha(R/'temp/recovery-work/rolling200-02/eq-constructors/replay')},'curve_range_mapping':fixtures['curve_range_mapping'],'regression':{'legacy_eq_methods':1038,'setter_size_idle':17,'curve_cases':len(json.loads((T.parent/'eq-curves/curve-fixtures.json').read_text())['cases']),'scope':'Unchanged prior fixtures replayed freshly against final owned source; no old native execution relabelled as new.'},'limitations':limitations,'structure':{'existing_source_partition':'CS18 EQControl.cpp, no new production CPP','public_headers':[rel(source[0])],'new_namespace':'presonus::dsp independent adapter only','unintegrated_eq_band_helpers_used':False,'shared_build_registry_files_modified':False}}
write(E/'LOCAL_PROOF.json',proof)
notes=[]
for q in requests:
 notes.append({'date':proof['date'],'original_elf_sha256':q['targets'][0]['original_elf_sha256'],'mangled':q['targets'][0]['mangled'],'work_item_id':q['work_binding']['work_item_id'],'status':'compiled_locally_validated_source_port_pending_Root_integration','remarks':limitations,'failed_approaches':['Historical Root plan named nonexistent pinned Core::LogInterpolator; initial compile rejected it and independent adapter correction was explicitly approved.','Replay initially sent paramChanged(nullptr,kChanged) when actual Control parameter is null, violating provider precondition. ASAN identified actual Control dereference; test corrected to pass real hpfQ parameter, with production behavior unchanged.','Sanitizer global metadata retains otherwise unused formatter vtables; fresh provider source plus supporting historical application archive definitions required for sanitizer link only. Ordinary compile and regression rebuild existing provider source directly.'],'retry_or_resolution_condition':'Root reviews bounded source adaptation and corrections, integrates source/test targets, replays all global gates and performs guarded admission; original Core log conversion, GUI/ARM ABI and destructor evidence remain separate unresolved work.','proof':rel(E/'LOCAL_PROOF.json'),'proof_sha256':sha(E/'LOCAL_PROOF.json')})
write(E/'REMARKS.json',notes)
diff=subprocess.check_output(['git','diff','d548724a88fbb82e34f7a43b1c56081c6afda7c9','--',*[rel(p) for p in source]],cwd=R,text=True);(A/'OWNED.diff').write_text(diff)
artifacts={}
def add(path,kind):
 p=Path(path);p=p if p.is_absolute() else R/p
 assert p.is_file(),str(p)
 artifacts[rel(p)]={'kind':kind,'path':rel(p),'sha256':sha(p)}
for p in source:add(p,'source')
add(R/'uc-library/tests/recovery/EQConstructorsReplay.cpp','test')
for p in T.iterdir():
 if p.is_file():add(p,'fixture' if p.suffix=='.json' else 'replay')
for p in E.iterdir():
 if p.is_file():add(p,'proof')
for p in [A/'seal.py',A/'OWNED.diff']:add(p,'producer' if p.suffix=='.py' else 'diff')
for p in ['rootfs/CS18_v13840/home/root/surface','uc-library/include/presonus/mixer_dsp/EqSourceProviders.hpp','uc-library/src/Presonus/Dsp/EqSourceProviders.cpp','uc-library/src/mixer_dsp/Logarithm.hpp','uc-library/src/mixer_dsp/Logarithm.cpp','uc-library/src/Presonus/EQControlBandParams.cpp','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a','temp/core-upstream/root-integration-01/libpresonus_uc.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a']:
 add(p,'dependency')
for name in ['core/portable/coreparams.cpp','core/portable/coreparams.h','core/portable/coreparaminfo.h','core/portable/gui/corecontrols.cpp','core/portable/gui/corecontrols.h','core/portable/gui/coreviewshared.h','core/portable/gui/coreview.h','core/public/coreinterpolator.cpp','core/public/coreinterpolator.h','core/public/corevector.h','core/public/gui/corecolor.h']:
 add('third_party/ccl-framework/'+name,'provider_source')
for group in ['eq-control','eq-curves']:
 for p in (T.parent/group).iterdir():
  if p.is_file():add(p,'regression_dependency')
for q in requests:
 current=dict(artifacts);packet=packets/q['task_id']
 for name in ['context.json','request.json','native-context.json','TASK.md','ELF_CONTEXT.md','SOURCE_SLICES.md','CONTEXT.md']:
  p=packet/name;current[rel(p)]={'kind':'packet','path':rel(p),'sha256':sha(p)}
 p=R/q['reconstruction_contract']['path'];current[rel(p)]={'kind':'historical_contract','path':rel(p),'sha256':sha(p)}
 data={'version':1,'task_id':q['task_id'],'namespace':'Presonus::EQControl','packet_manifest':rel(packet/'context.json'),'originals':[identity(q)],'artifacts':list(current.values()),'checks':[{'kind':m if m in ['format','compile','symbols','replay'] else 'replay','argv':['uc-library/.venv/bin/python',rel(T/'check.py'),m],'timeout_seconds':180} for m in ['format','compile','symbols','native','replay','adapter','regression','sanitizer']],'validation_domain':{'scope':'Successful constructor C1/C2,25 rectangles each including shifted/negative/zero/reversed extents and20 seeded arbitrary valid extents; exact native stores, provider call order/receivers/args, all three HPF table records, actual pinned Control/interpolators/ParamList, host flags and150 lifetime notifications; source adaptation transitions tested separately.','original_variant':q['targets'][0]['mangled'],'native_cases_for_this_original':25,'fixture':rel(T/'fixtures.json')},'limitations':limitations,'build_integration':{'production_partition':'Existing CS18 OBJECT partition EQControl.cpp; no new production CPP or global CMake modifications','public_headers':['uc-library/include/presonus/mixer_dsp/EQControl.hpp'],'test_sources':['uc-library/tests/recovery/EQConstructorsReplay.cpp'],'test_targets':['proposed eq_constructors_replay using actual canonical presonus target; Root integrates'],'link_dependencies':['actual pinned CCL corelib + allocator','existing unchanged EqSourceProviders and Logarithm sources/private glibc29 provider','libpng,z,pthread,dl,m'],'ctest_argv':['uc-library/.venv/bin/python',rel(T/'check.py'),'replay','$CANONICAL_BUILT_EXECUTABLE',rel(T/'fixtures.json')],'extra_replays':['native','adapter','regression','sanitizer'],'root_global_gates_required':True}}
 out=A/q['task_id'];out.mkdir(exist_ok=False);write(out/'HANDOFF.json',data)
 print(rel(out/'HANDOFF.json'))
