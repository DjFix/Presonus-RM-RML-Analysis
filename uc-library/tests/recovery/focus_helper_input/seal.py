"""Seal four exact task deliveries after all shared source changes finish."""
import datetime,hashlib,json,os,subprocess,time
from pathlib import Path
R=Path(__file__).resolve().parents[4];T=Path('uc-library/tests/recovery/focus_helper_input')
E=Path('evidence/recovery/2026-11-06/rolling200-03-focus01-routing')
PREVIOUS=Path('evidence/recovery/2026-11-06/rolling200-03-focus01')
PACKETS=Path('temp/recovery-work/rolling200-03/focus01/prepared01/packets')
PY='uc-library/.venv/bin/python';FMT='uc-library/.venv/bin/clang-format'
OWN=['uc-library/include/presonus/FocusHelperButton.hpp','uc-library/src/Presonus/FocusHelperButton.cpp','uc-library/tests/recovery/FocusHelperInputReplay.cpp']
def sha(p):return hashlib.sha256((R/p).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
checks=[{'kind':m,'argv':[PY,str(T/'check.py'),m],'timeout_seconds':120} for m in ['format','compile','symbols','native','replay']]
(R/E).mkdir(parents=True,exist_ok=True)
logs=[]
for check in checks:
 start=now();tick=time.monotonic();p=subprocess.run(check['argv'],cwd=R,text=True,capture_output=True,timeout=120)
 path=E/(check['kind']+'.log');(R/path).write_text(p.stdout+p.stderr)
 logs.append({**check,'started':start,'finished':now(),'seconds':time.monotonic()-tick,'returncode':p.returncode,'log':str(path),'sha256':sha(path)})
 print(check['kind'],p.returncode,flush=True)
 assert p.returncode==0,p.stdout+p.stderr
versions={}
for key,argv in [('format',[FMT,'--version']),('compile',['/usr/bin/c++','--version']),('symbols',['/usr/bin/nm','--version']),('python',[PY,'--version']),('unicorn',[PY,'-c','import unicorn;print(unicorn.__version__)']),('pyelftools',[PY,'-c','import elftools;print(elftools.__version__)']),('ccl-history',['git','-C','third_party/ccl-framework','log','--reverse','--format=%H %P'])]:versions[key]=subprocess.check_output(argv,cwd=R,text=True).strip()
assert versions['ccl-history'].splitlines()[0].strip()=='e8cbdea4a4a20e15111f5a690798a259c0374b31'
fixture=json.loads((R/T/'fixtures.json').read_text())
reqs=[json.loads((R/PACKETS/f'rolling200_03_focus01_{i:02d}'/'request.json').read_text()) for i in range(1,5)]
domain='499 exact original ARM execution scenarios: paramChanged messages0/1/2/3/4/6; 19 float bit patterns including signed zeros/subnormals, positive/negative fractions, signed limits/overflow, positive/negative infinity and quiet/signaling NaN; nine radio target integers and initially clear/set active flags. Four draw on/enabled branches. restoreFocus/onIdle absent, invalid-cast, empty native View/modern noncontainer adaptation and real ContainerView parents, empty/multiple/repeated-name ordered children, detached/attached actual root, initially clear/set flags. Per-boundary native trace and app flag-write/PC audits. Actual pinned CCL constructor/attributes borrowed pointer, parameter observer notifications and enable changes; real expired edit ends before restoration; actual RootView focus transitions with children virtually reporting a distinct root that receives no focus requests, native button receiver assertion, and child onFocus order, clearing before callbacks; actual Button/ThemePainter/Graphics drawing counts.'
limitations=[
 'REA MCP tools are absent in this session; installed rea6.8.0 doctor records missing Codex registration and unavailable native engines. No configuration or engine installation performed. Evidence is ordinary pyelftools/Unicorn and real CCL source/provider output, not REA Evidence.',
 'Portable source port on actual pinned CCL5.0.0. Original app ordinary return declarations, class/vtable/field layouts, inheritance details, ARM ABI and hardware interoperability remain unresolved/unverified. Exact symbols establish encoded identity only. All four targets are compiled-declaration-pending; no ready promotion.',
 'Native oracle executes only the four hash/range-verified app bodies and expanded original __aeabi_f2iz runtime. Core, strcmp and virtual providers are intercepted before execution in private memory; no Core binary reconstruction, host syscall or device passthrough. C++ separately executes actual CCL providers with matching bounded inputs. Not full original binary integration.',
 'Original View cast precedes native child field access. Modern CCL children belong to ContainerView: real castTo(View) then asContainer/getChildren is an intentional source adaptation; invalid/noncontainer parents return safely. Plain modern View cannot claim original layout equivalence. No null child, dangling borrowed name, malformed vectors, concurrent hierarchy mutation, or callback child destruction/mutation is supported by this proof.',
 'Borrowed viewName_ storage must outlive use. Tests preserve actual Attributes storage and check pointer identity; no ownership extension is inferred. Child-count snapshot mirrors native loop. Root is requested from the button for each name match, including repeated names; traversal does not stop after first match.',
 'Explicit conversion handles observed runtime NaN-to-zero and signed saturation without undefined host casts. Bit-pattern cases include positive signaling NaN and both signed quiet NaNs; this is bounded value/flag behavior, not exhaustive 2^32 float or floating exception/fenv equivalence. Upstream RadioButton::isOn uses its own actual provider conversion; draw tests restrict parameters to finite0/1.',
 'Draw replay covers untextured untitled default-style Button background and extra four-edge focus frame with actual ThemePainter and a test Graphics implementation. Bitmap/icon/text/focused-button double-frame branches remain outside this added bounded draw domain; provider behavior is not reconstructed here.'
]
notes={'version':1,'created':now(),'status':'implemented-compiled-declaration-pending','previous_proof':str(PREVIOUS/'proof.json'),'original_notes':[],'development_remarks':[{'observation':'Root review requested receiver verification because task prose could imply child root. Native0x64d30 preserves this in r7;0x64d90 loads vtable[r7];0x64d94 passes r7 in r0;0x64d9c calls slot0x14. Child is r6 and only enters r1 at0x64da4 for root setFocusView slot0x70 at0x64db4.','status':'resolved','resolution':'Production already correct. Native hook now asserts receiver is exact button. Every portable replay child overrides getRootView to return a different real RootView; that root must receive no focus requests and remain unfocused. Original proofs preserved, new proof generation records regression.'},{'observation':'Initial provider notification assertion failed because actual RadioButton::setAttributes resets radioValue to default0. Replay now explicitly restores radio target1 before testing notifications; production method unchanged. Initial Attributes default construction failed: replaced test instances with actual DefaultAllocatedAttributes.','status':'resolved','resolution':'Current fresh compile and executable replay pass with real provider APIs; no oracle or gate weakened.'}]}
for req in reqs:
 o=req['originals'][0]['original']
 notes['original_notes'].append({'elf_sha256':o['elf'],'mangled':o['mangled'],'work_item_id':req['work_binding']['work_item_id'],'status':'compiled-declaration-pending','remarks':limitations,'evidence':str(E/'proof.json'),'resolution_or_retry_condition':'Root local acceptance, canonical Linux/role/install/compile-once/source checks and guarded pending admission; readiness promotion requires independent original return declaration evidence. Preserve bounded Core adaptation/behavior notes.'})
(R/E/'NOTES.json').write_text(json.dumps(notes,indent=2)+'\n')
files=set(OWN)|{str(p.relative_to(R)) for p in (R/T).glob('*') if p.is_file()}
files.update(str(p.relative_to(R)) for p in (R/E).rglob('*') if p.is_file() and p.name!='proof.json')
for req in reqs:
 p=R/PACKETS/req['task_id'];files.update(str(x.relative_to(R)) for x in p.iterdir() if x.is_file())
files.add(str(PREVIOUS/'proof.json'))
files.update(str(x.relative_to(R)) for x in (R/PREVIOUS/'expansion').glob('*') if x.is_file())
files.add(str(PREVIOUS/'rea-doctor.json'))
files.update(['AGENTS.md','docs/worker-handoff.md','docs/core-framework-lineage.md'])
# Capture real direct and transitive project/provider headers from compiler.
deps=subprocess.check_output(['/usr/bin/c++','-std=c++17','-Wno-multichar','-Iuc-library/include','-Ithird_party/ccl-framework','-MM',*OWN[1:]],cwd=R,text=True)
for token in deps.replace('\\\n',' ').split():
 if not token.endswith(':') and (R/token).is_file() and not Path(token).is_absolute():files.add(token)
for p in ['core/portable/coreattributes.cpp','core/portable/coreparams.cpp','core/portable/gui/corecontrols.cpp','core/portable/gui/coreview.cpp','core/portable/gui/coreviewshared.cpp','core/portable/gui/coregraphics.cpp','core/portable/gui/corebitmap.cpp','core/platform/shared/coreplatformtime.cpp']:files.add('third_party/ccl-framework/'+p)
files.update(['temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a','temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a','temp/core-upstream/root-integration-01/private-glibc29-provider/libpresonus_private_glibc29.a'])
proof={'version':1,'created':now(),'cwd':str(R),'base_commit':'e6599660fb8c7a9a2d36e69be798875a74dbea06','worker_thread_id':os.environ.get('CODEX_THREAD_ID'),'parent_session_id':os.environ.get('CODEX_SESSION_ID'),'scope':'Worker-local portable implementation; no canonical integration/admission','versions':versions,'originals':[q['originals'][0]['original'] for q in reqs],'native_input_elf_sha256':fixture['elf_sha256'],'native_ranges':fixture['ranges'],'native_scenarios':len(fixture['cases']),'source_sha256':{p:sha(p) for p in sorted(files)},'commands':logs,'validation_domain':domain,'limitations':limitations,'formatting_verified':True,'compiled':True,'mangling_verified':True,'namespace_signature_verified':True,'namespace_signature_scope':'Exact original namespace/class and encoded parameter/const-reference symbols; ordinary returns unresolved','native_behavior_verified':True,'native_behavior_scope':'Bounded exact app/runtime instructions and intercepted providers; separately actual pinned CCL portable provider behavior','original_declaration_verified':False,'original_arm_abi_verified':False,'hardware_verified':False}
(R/E/'proof.json').write_text(json.dumps(proof,indent=2)+'\n');files.add(str(E/'proof.json'))
def kind(p):
 if p==str(E/'proof.json'):return 'proof'
 if p.endswith('/context.json'):return 'packet'
 if p==str(T/'fixtures.json'):return 'fixture'
 if p==str(T/'check.py'):return 'replay'
 if p in OWN:return 'test' if '/tests/' in p else 'source'
 return 'dependency'
for req in reqs:
 o=req['originals'][0]['original'];p=PACKETS/req['task_id'];c=R/'uc-library/candidates'/req['task_id'];c.mkdir(parents=True,exist_ok=True)
 h={'version':1,'task_id':req['task_id'],'namespace':req['namespace'],'packet_manifest':str(p/'context.json'),'originals':[{'elf_sha256':o['elf'],'firmware':o['firmware'],'role':o['role'],'mangled':o['mangled'],'address':o['address'],'size':o['size'],'section':'.text'}],'artifacts':[{'kind':kind(f),'path':f,'sha256':sha(f)} for f in sorted(files)],'checks':checks,'validation_domain':domain,'limitations':limitations,'build_integration':{'production_partition':'Existing canonical src/Presonus/FocusHelperButton.cpp partition; no new production CPP','public_headers':['include/presonus/FocusHelperButton.hpp'],'test_targets':['FocusHelperInputReplay'],'test_sources':['tests/recovery/FocusHelperInputReplay.cpp'],'link_dependencies':['corelib','presonus_core_allocator','presonus_private_glibc29','png','zlib','pthread','dl','m'],'ctest_argv':[PY,str(T/'check.py'),'replay','<canonical-built-FocusHelperInputReplay>',str(T/'fixtures.json')],'fixture_sha256':sha(T/'fixtures.json'),'notes':'Root owns shared build/public lists, canonical Linux integration, role/install/compile-once, current source proof binding, guarded SQLite pending admission, tracker/mirror. No shared files modified. Four HANDOFFs share final source/proof hashes and each retains exactly its sealed original identity.'}}
 (c/'HANDOFF.json').write_text(json.dumps(h,indent=2)+'\n')
 print('sealed',req['task_id'])
