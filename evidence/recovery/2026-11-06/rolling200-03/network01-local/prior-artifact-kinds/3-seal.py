"""Seal bounded local observations; global integration/admission remains Root-owned."""
import pathlib,json,hashlib,subprocess,datetime,time,os
ROOT=pathlib.Path(__file__).resolve().parents[4]
BASE=pathlib.Path('uc-library/tests/recovery/network_list_input')
EVIDENCE=pathlib.Path('evidence/recovery/2026-11-06/rolling200-03/network01-local')
PACKETS=pathlib.Path('temp/recovery-work/rolling200-03/network01/prepared01/packets')
PY='uc-library/.venv/bin/python'
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
checks=[{'kind':x,'argv':[PY,str(BASE/'check.py'),x],'timeout_seconds':180} for x in ['format','compile','symbols','replay','native']]
(ROOT/EVIDENCE).mkdir(parents=True,exist_ok=True)
logs=[]
for check in checks:
 tick=time.monotonic();start=now();r=subprocess.run(check['argv'],cwd=ROOT,text=True,capture_output=True,timeout=180)
 log=EVIDENCE/(check['kind']+'.log');(ROOT/log).write_text(r.stdout+r.stderr)
 logs.append({**check,'started':start,'finished':now(),'seconds':time.monotonic()-tick,'returncode':r.returncode,'log':str(log),'sha256':sha(log)})
 print(check['kind'],r.returncode,flush=True);assert r.returncode==0,r.stdout+r.stderr
versions={k:subprocess.check_output(v,cwd=ROOT,text=True).strip() for k,v in [('formatter',['uc-library/.venv/bin/clang-format','--version']),('compiler',['/usr/bin/c++','--version']),('symbols',['/usr/bin/nm','--version']),('unicorn',[PY,'-c','import unicorn;print(unicorn.__version__)']),('pyelftools',[PY,'-c','import elftools;print(elftools.__version__)']),('ccl-history',['git','-C','third_party/ccl-framework','log','--reverse','--format=%H %P'])]}
assert versions['ccl-history'].splitlines()[0].strip()=='e8cbdea4a4a20e15111f5a690798a259c0374b31'
fixture=json.loads((ROOT/BASE/'fixtures.json').read_text())
domain='380 original app ARM executions: 60 wheel cases with zero through five views, INT_MIN/-1/0/1/INT_MAX delta, both axes and alternating observed callback returns; 320 selection combinations covering INT_MIN/-1/0/1/INT_MAX index, selection false/true, target 0/1/2/9, null/non-null userData, null row and three non-null-row trigger values (including INT_MAX). Actual CCL models, ListView attach/detach, list item storage, View inherited wheel return, Parameter/Component lookup and real owner selection implementation execute. Every forwarded event is the same object; no early stop. Invalidation follows captured owner calls. A target-lookup probe mutates row userData after the original read and confirms the selected identity was captured once before lookup.'
limitations=[
 'Portable source port only. Original fields, inheritance/layout, ordinary return declarations, ARM ABI and hardware behavior remain unverified. Wheel uses provisional void app member, not a fake CCL override. Selection void matches pinned provider override, not independently recovered original return.',
 'Original native application instructions alone execute; getTargetType/selectMixer/selectDAW/View invalidate and wheel callbacks are observed boundary entries. No historical Core instructions execute. Host real CCL providers and existing owner select implementations execute; offline application dependency adapter returns null components and excludes device/network actions.',
 'Real existing owner getTargetType normalizes tag30 finite int-representable parameter values to 0/1. Other target returns 2/9 use a clearly explicit host test boundary; they do not claim actual owner reachability. Production logic preserves other-type no-selection path.',
 'Stable attached views/items and live owner, live finite tag30 parameter and non-null caller view on valid row paths are required. Reentrant attachment/detachment, source container mutation, concurrent access, exceptions, stale pointers and exceeding actual CCL five-view capacity are excluded. Native captures initial count and reloads current storage/count each loop; source uses actual provider indexing under this stable domain.',
 'Pinned ListView inherits View::onWheelInput returning false; historical original vtable slot corresponds to ListView wheel behavior. This intentional provider difference is retained, not reconstructed from Core firmware. Actual Content wheel implementation is not substituted for ListView dispatch.',
 'drawItem remains separately unresolved: original nested ListViewModel::DrawInfo differs from pinned ListViewModelBase::DrawInfo. No fake compatibility type, readiness credit or symbol replacement is provided.',
 'No ready/pending fragment is submitted; Root retains global Linux/full CTest, installed-role/compile-once, source freshness, tracker and guarded SQLite admission. Local success is not readiness admission.'
]
files=set(['uc-library/include/presonus/surface/NetworkSetupComponent.hpp','uc-library/src/Presonus/Surface/NetworkListSelection.cpp','uc-library/tests/recovery/NetworkListInputReplay.cpp']+[str(BASE/x) for x in ['native.py','check.py','seal.py','fixtures.json']])
# Bind actual compiled providers and app implementations, plus original inputs.
import check
for f in check.SOURCES:files.add(f)
for f in check.COMPILE:
 if (ROOT/f).is_file() and not f.startswith('-') and not f.startswith('/'):files.add(f)
files.update(['rootfs/CS18_v13840/home/root/surface','third_party/ccl-framework/core/portable/gui/corelistview.h','third_party/ccl-framework/core/portable/gui/corelistview.cpp','third_party/ccl-framework/core/portable/gui/coreview.h','third_party/ccl-framework/core/portable/gui/coreview.cpp','third_party/ccl-framework/core/portable/gui/coreviewshared.h','third_party/ccl-framework/core/portable/corecomponent.cpp','third_party/ccl-framework/core/portable/coreparams.h','third_party/ccl-framework/core/portable/coreparams.cpp','docs/core-framework-lineage.md','docs/worker-handoff.md'])
files.discard(str(check.EXE))
requests=[]
for n in [1,2]:
 packet=PACKETS/f'rolling200_03_network01_{n:02}';req=json.loads((ROOT/packet/'request.json').read_text());requests.append((packet,req))
 for name in ['context.json','request.json','native-context.json','TASK.md','CONTEXT.md','ELF_CONTEXT.md','SOURCE_SLICES.md']:files.add(str(packet/name))
 for c in [req.get('reconstruction_contract',{}).get('path')]:
  if c:files.add(c)
files.update(x['log'] for x in logs)
proof_path=EVIDENCE/'proof.json'
proof={'version':1,'created':now(),'worker':'rolling200_03_network01','checks':logs,'versions':versions,'fixture_sha256':sha(BASE/'fixtures.json'),'range_bindings':fixture['ranges'],'oracle_audit':fixture['audit'],'validation_domain':domain,'limitations':limitations,'sources_and_dependencies':[{'path':f,'sha256':sha(f)} for f in sorted(files)],'original_declaration_verified':False,'original_arm_abi_verified':False,'hardware_verified':False,'remarks':[{'observation':'Existing owner getTargetType returns booleanized target; other native target types unavailable through actual owner.','resolution':'Actual 0/1 provider paths replayed; additional 2/9 branch tests explicitly intercepted at owner query boundary. Retry original reachability only with new owner evidence.'},{'observation':'Initial test used a temporary borrowed ParamInfo and omitted pointer returns in offline dependencies.','resolution':'Persisted ParamInfo for full NumericParam lifetime and explicit null pointer adapter returns; all final checks rerun.'},{'observation':'drawItem original nested DrawInfo type identity mismatch.','status':'unresolved separate target','retry_condition':'Real provider adaptation contract with original encoded type identity; no fabricated Core class.'}]}
(ROOT/proof_path).write_text(json.dumps(proof,indent=2)+'\n');files.add(str(proof_path))
for packet,req in requests:
 o=req['originals'][0]['original'];dest=ROOT/'uc-library/candidates'/req['task_id'];dest.mkdir(parents=True,exist_ok=True)
 h={'version':1,'task_id':req['task_id'],'namespace':req['namespace'],'packet_manifest':str(packet/'context.json'),'originals':[{'elf_sha256':o['elf'],'firmware':o['firmware'],'role':o['role'],'mangled':o['mangled'],'address':o['address'],'size':o['size'],'section':'.text'}],'artifacts':[{'kind':'proof' if f==str(proof_path) else 'packet' if f==str(packet/'context.json') else 'fixture' if f.endswith('/fixtures.json') else 'replay' if f==str(BASE/'check.py') else 'source' if '/src/' in f or '/include/' in f else 'dependency','path':f,'sha256':sha(f)} for f in sorted(files)],'checks':checks,'validation_domain':domain,'limitations':limitations,'build_integration':{'production_partition':'Existing NetworkListSelection.cpp stays exactly once in its existing CS18 OBJECT partition; no new production CPP. Root verifies original ownership/partition audit.','public_headers':['include/presonus/surface/NetworkSetupComponent.hpp'],'test_targets':['NetworkListInputReplay'],'test_sources':['tests/recovery/NetworkListInputReplay.cpp'],'compile_options':['-fno-rtti','-fno-lto'],'link_dependencies':['presonus_cs18_components','presonus_uc','actual pinned corelib','presonus_core_allocator','presonus_private_glibc29','PNG','zlib','pthread','dl','m'],'link_options':['--wrap='+x for x in check.WRAPS],'ctest_argv':[PY,str(BASE/'check.py'),'replay','<canonical-built-NetworkListInputReplay>'],'fixture_sha256':sha(BASE/'fixtures.json'),'notes':'Exact replay protocol is six integers per line; compares callback traces and invalidation order against independently generated original instructions. No shared integration mutation or readiness fragment.'}}
 (dest/'HANDOFF.json').write_text(json.dumps(h,indent=2)+'\n')
print('Two packet-specific HANDOFF v1 records sealed')
