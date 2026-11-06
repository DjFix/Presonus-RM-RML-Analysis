"""Bind final source, independent native fixture and actual local command receipts."""
import datetime,hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
BASE='evidence/recovery/2026-11-06/rolling200-03/daw-maps183-fix01'
DIR='uc-library/tests/recovery/daw_map_construction'
PACKETS='temp/recovery-work/rolling200-03/daw_maps183/prepared183/packets'
def digest(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def write(p,x):
 q=ROOT/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(x,indent=2)+'\n')
def main():
 stamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
 fixture=json.loads((ROOT/DIR/'fixtures.json').read_text())
 deps=set()
 for name in ['production.d','maps.d']:
  text=(ROOT/'temp/recovery-work/daw_maps183-local'/name).read_text().replace('\\\n',' ')
  deps.update(s for s in text.split() if s.startswith(('third_party/','uc-library/')))
 for path in sorted(deps):
  if path.startswith('third_party/ccl-framework/'):
   relative=path.removeprefix('third_party/ccl-framework/')
   original=subprocess.check_output(['git','-C',str(ROOT/'third_party/ccl-framework'),'show','e8cbdea4a4a20e15111f5a690798a259c0374b31:'+relative])
   assert hashlib.sha256(original).hexdigest()==digest(path),path
 commit=subprocess.check_output(['git','-C',str(ROOT/'third_party/ccl-framework'),'show','-s','--format=%H %P','HEAD'],text=True).strip()
 assert commit=='e8cbdea4a4a20e15111f5a690798a259c0374b31',commit
 sources=['uc-library/include/presonus/DAWTimeInfo.hpp','uc-library/src/Presonus/DAWTimeMapsConstruction.cpp','uc-library/src/Presonus/DAWTimeMaps.cpp']
 tests=['uc-library/tests/recovery/DAWTimeMapsConstructionReplay.cpp']
 producers=[DIR+'/'+s for s in ['native.py','check.py','seal.py']]
 logs=sorted(str(p.relative_to(ROOT)) for p in (ROOT/BASE).glob('*.json') if p.name not in ['PROOF.json','OBSERVATIONS.json'])
 for log in logs:
  data=json.loads((ROOT/log).read_text())
  if 'returncode' in data:assert data['returncode']==0,log
 regression=['uc-library/tests/recovery/ranked09/maps/'+s for s in ['driver.cpp','replay.py','fixtures.json']]
 regression+=['uc-library/tests/recovery/reconstruction-200-01/large01_w05/'+s for s in ['driver.cpp','replay.py','fixtures.json']]
 regression+=['uc-library/tests/graph_trial08_timeinfo_tests.cpp','uc-library/tests/recovery/trial08/timeinfo/replay.py','uc-library/tests/recovery/trial08/timeinfo/native-fixtures.json']
 libraries=['temp/core-upstream/root-integration-01/'+s for s in ['libpresonus_uc.a','libpresonus_cs18_components.a','upstream-core/sdk/lib/libcorelib.a','upstream-core/sdk/lib/libpresonus_core_allocator.a','private-glibc29-provider/libpresonus_private_glibc29.a']]
 originals=[]
 for packet in sorted((ROOT/PACKETS).iterdir()):
  r=json.loads((packet/'request.json').read_text());o=r['originals'][0]['original'];originals.append(dict(elf_sha256=o['elf'],firmware=o['firmware'],role=o['role'],mangled=o['mangled'],address=o['address'],size=o['size'],section='.text'))
 domain='4 independently range-checked C1/C2 originals; 48 ARM application executions at four memory patterns and true/false/exception-stop resize boundaries. Actual pinned CCL initial capacities/deltas 16/64, zero logical count, growth/clear/destructor and allocation failures. 382 owned-map/provider cases at 0,1,15,16,17,63,64,65,129 sorted items; existing map searches, bar lookup, seconds conversion, immutable copies/rvalues/assignments, transactional replacement and cleanup. Existing 378 borrowed-map, 557 map/event/getter and 20 narrow timeinfo ARM regressions pass.'
 limits=['Portable source port, not ARM32 ABI/layout or original map inheritance recovery. Typed Item fields and owned immutable storage/record encodings are intentional source-port declarations; unencoded original map return declarations remain unresolved.','Native Core resize is intercepted before any Core instruction; true/false are controlled boundary returns, not actual native provider allocation. Exception case stops at boundary; native unwind/cleanup is not executed or claimed. Pinned CCL provider real array failure/cleanup is separately executed.','Default original constructor allocation sizes are observed r1 requests 16/64; actual source-provider capacities/deltas are preferred policy. Source provider uses throwing host new; no claim of native allocator failure equivalence.','Borrowed APIs retain caller lifetime/readability requirements. Sorted finite item lists required for replacement and existing search assumptions; malformed pointers, unsorted records, concurrent mutation and extreme allocations are excluded.','No original map destructor target, hardware, native Core implementation, actual device I/O, system-call passthrough or the eight retained DAW lifecycle/format/factory targets are delivered. Global full Linux/integration/installed-role/compile-once/registry admission remains Root-owned.']
 observations=dict(date=stamp,status='implemented-local-checks-passed-awaiting-root-acceptance',entries=[])
 for o,packet in zip(originals,sorted((ROOT/PACKETS).iterdir())):
  r=json.loads((packet/'request.json').read_text())
  observations['entries'].append(dict(original=o,unique_work_item=r['work_binding']['work_item_id'],remarks=limits,resolution='owned source and local bounded checks delivered; original ABI/native unwind remain unresolved',retry_condition='new exact original declaration/layout/unwind evidence or Root canonical integration result',evidence=[BASE+'/PROOF.json',DIR+'/fixtures.json']))
 observations['integration_resolution']=dict(cause='Canonical DAWTimeMaps.cpp object retained old borrowed-only layout (records +0/count +8); new constructor/driver use records +16/count +24. This is a stale header-dependent object, not allocation instrumentation or an O3 source failure.',proof='DIAGNOSIS.json; immutable snapshot fails intermittently, replacing only maps object with fresh same-argv compile passes 12/12. Root must rebuild every header-dependent TU and replay canonical gates.',prior_proof='evidence/recovery/2026-11-06/rolling200-03/daw-maps183/PROOF.json')
 observations['historical_local_failure']=dict(observation='First regression link attempted -lpng; host has libpng16.so.16 but no libpng.so linker name. Corrected argv to actual absolute runtime; all three regressions then passed.',tool_chunk='a51e1d',captured_output='/usr/bin/ld: cannot find -lpng: No such file or directory; collect2: error: ld returned 1 exit status',resolution='explicit /usr/lib/x86_64-linux-gnu/libpng16.so.16 and libz.so.1 in check.py; not a source behavior failure')
 write(BASE+'/OBSERVATIONS.json',observations)
 bound=sorted(set(sources+tests+producers+list(deps)+regression+libraries+[DIR+'/fixtures.json','AGENTS.md','docs/worker-handoff.md','docs/core-framework-lineage.md']))
 receipts={Path(p).stem:json.loads((ROOT/p).read_text()) for p in logs}
 proof=dict(version=1,date=stamp,checkout=str(ROOT),compiler_version=subprocess.check_output(['/usr/bin/c++','--version'],text=True),python_version=subprocess.check_output([str(ROOT/'uc-library/.venv/bin/python'),'--version'],text=True),originals=originals,native_ranges=fixture['ranges'],oracle_producer=dict(path=DIR+'/native.py',sha256=digest(DIR+'/native.py'),unicorn=subprocess.check_output([str(ROOT/'uc-library/.venv/bin/python'),'-c','import unicorn;print(unicorn.__version__)'],text=True).strip()),provider=dict(commit=commit,policy='unchanged actual pinned source, no Core firmware execution',source_hashes={p:digest(p) for p in sorted(deps) if p.startswith('third_party/')}),source_hashes={p:digest(p) for p in sources},input_hashes={p:digest(p) for p in bound},commands=receipts,validation_domain=domain,limitations=limits,compiled_aliasing='Linux C1/C2 pair symbols share compiler-selected entry addresses; originals are four distinct ranges independently hashed and executed. Matching symbol names do not prove ABI/layout.',ready=False)
 write(BASE+'/PROOF.json',proof)
 for o,packet in zip(originals,sorted((ROOT/PACKETS).iterdir())):
  task=packet.name;manifest=str(packet.relative_to(ROOT)/'context.json')
  kinds={p:'dependency' for p in bound+logs+[BASE+'/OBSERVATIONS.json']}
  kinds.update({p:'source' for p in sources});kinds.update({p:'test' for p in tests});kinds[DIR+'/fixtures.json']='fixture';kinds[DIR+'/check.py']='replay';kinds[DIR+'/native.py']='oracle';kinds[DIR+'/seal.py']='producer';kinds[BASE+'/PROOF.json']='proof';kinds[manifest]='packet'
  checks=[dict(kind=k if k in ['format','compile','symbols','replay'] else 'replay',argv=['uc-library/.venv/bin/python',DIR+'/check.py',k],timeout_seconds=120) for k in ['format','compile','symbols','oracle','replay','regression']]
  write('uc-library/candidates/'+task+'/HANDOFF.json',dict(version=1,task_id=task,namespace='Presonus',packet_manifest=manifest,originals=[o],artifacts=[dict(kind=k,path=p,sha256=digest(p)) for p,k in sorted(kinds.items())],checks=checks,validation_domain=domain,limitations=limits,build_integration=dict(production_partition='cs18',production_sources=['src/Presonus/DAWTimeMapsConstruction.cpp'],existing_sources=['src/Presonus/DAWTimeMaps.cpp'],public_headers=['presonus/DAWTimeInfo.hpp'],target='recovery_daw_map_construction',test_source=tests[0],link_dependencies=['presonus::cs18_components','actual pinned Core::Vector template headers'],ctest_argv=['uc-library/.venv/bin/python',DIR+'/check.py','replay','--executable','$<TARGET_FILE:recovery_daw_map_construction>'],fixture_bindings=[DIR+'/fixtures.json'],notes='Root adds production CPP exactly once to cs18 OBJECT partition; no shared CMake edited. Immutable copies preserve views; borrowed APIs/search algorithms retained. Root supplies canonical archive link and full gates.')))
 print('Sealed 4 exact packet HANDOFF v1 files with final shared source hashes')
if __name__=='__main__':main()
