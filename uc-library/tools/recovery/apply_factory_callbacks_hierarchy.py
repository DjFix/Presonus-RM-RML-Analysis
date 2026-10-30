"""Fixed three-packet application; guarded plan/apply, never admits readiness."""
import argparse
import hashlib
import json
from pathlib import Path
from apply_queue_gate_geq import once, counts

r=Path.cwd();lib=r/'uc-library';phase=r/'evidence/recovery/2026-10-29/factory-callbacks-hierarchy-batch'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
inputs={
'candidates/uc-event-factory-owned-data/CONTROLLED-APPLY-925.json':'2cf12597c2d39d823c6fc9c902bcea00aa47cba4ebed5d13049420e9b5ff9685',
'candidates/uc-event-factory-owned-data/CMAKE-RECIPE-925.json':'f7e4c44c42163e248310abaa04fc9291aa09327d4ac99c793e54dbe663b11a02',
'candidates/uc-event-factory-owned-data/CMAKE-TEST-INSERTIONS-925.cmake':'2abf95dadcb37c4c56556994a35994a0f0f822b86c6d0bb6125b0ebaf408f23b',
'candidates/uc-network-manager-callbacks-report-multicast/CONTROLLED-APPLY.json':'9e3e2caea9580d625776075124dd389b87499e1c8bd4279420fe1edec1f6c045',
'candidates/uc-outgoing-socket-identity/CONTROLLED-APPLY.json':'f8f1b8cec9d1bf72ae384002a44f1d320d1f489e4aedba5ddac4978b0557e9f1',
'candidates/uc-outgoing-socket-identity/CMAKE-RECIPE.json':'75d5b35d44d92aa1bd79f1308d8ac588df2bfd70a0fa8f285b4d31ce00ac0782',
'candidates/uc-factory-callbacks-hierarchy-native-profile/CMAKE-CALLBACK-RECIPE.json':'cc268d45993c8c6a96f1315c9c011f20a55dc6f8acfdeddc213829e0cc1eabf3'}
p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args()
for n,h in inputs.items():assert sha(lib/n)==h,n
maps=[read(lib/n) for n in inputs if 'CONTROLLED-APPLY' in n];products={};previous={};origins={}
for m in maps:
 for row in m['products']:
  n=row['target'];s=lib/row['source'];t=lib/n;assert n not in products and not t.is_symlink();assert s.resolve().is_relative_to(lib.resolve()) and t.resolve().is_relative_to(lib.resolve());assert sha(s)==row['sha256'];old=row['previous_sha256'];assert (not t.exists()) if old is None else sha(t)==old
  products[n]=s.read_bytes();previous[n]=old;origins[n]=row['source']
assert len(products)==36
groups=(lib/'cmake/ProductionSourceGroups.cmake').read_text();cmake=(lib/'CMakeLists.txt').read_text();assert counts(groups)==[117,46,63]
newcpp=sorted(n for n in products if n.startswith('src/') and n.endswith('.cpp') and previous[n] is None);headers=sorted(n.removeprefix('include/') for n in products if n.startswith('include/') and previous[n] is None);assert len(newcpp)==6 and len(headers)==4
for n in newcpp:
 assert n not in groups;groups=once(groups,'set(PRESONUS_common_SOURCES\n','set(PRESONUS_common_SOURCES\n  '+n+'\n')
assert counts(groups)==[123,46,63]
for h in headers:
 assert h not in groups and h not in cmake;groups=once(groups,'set(PRESONUS_PUBLIC_HEADERS\n','set(PRESONUS_PUBLIC_HEADERS\n  '+h+'\n');cmake=once(cmake,'set(PRESONUS_UC_PUBLIC_HEADERS\n','set(PRESONUS_UC_PUBLIC_HEADERS\n  '+h+'\n')
# Append after all broad resets; actual Connection reset now owns its real RTTI.
flags=newcpp+['src/Presonus/UC/connection.cpp','src/Presonus/UC/external_connection.cpp','src/Presonus/UC/EventQueueLifetime.cpp']
properties='\n'.join('set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/'+n+'" APPEND PROPERTY COMPILE_OPTIONS -frtti -fno-lto)' for n in flags)
cmake=once(cmake,'include(CTest)',properties+'\ninclude(CTest)')
factory=read(lib/'candidates/uc-event-factory-owned-data/CMAKE-RECIPE-925.json');hier=read(lib/'candidates/uc-outgoing-socket-identity/CMAKE-RECIPE.json');callbacks=read(lib/'candidates/uc-factory-callbacks-hierarchy-native-profile/CMAKE-CALLBACK-RECIPE.json')
lines=(lib/'candidates/uc-event-factory-owned-data/CMAKE-TEST-INSERTIONS-925.cmake').read_text().splitlines();suites=[t['target'] for t in factory['tests']]
for t in callbacks['new_test_targets']:
 n=t['target'];assert 'add_executable('+n not in cmake;lines.extend([f"add_executable({n} {t['source']})",f'target_link_libraries({n} PRIVATE stdc++ presonus::uc)',f"target_compile_options({n} PRIVATE {' '.join(t['compile_options'])})",f"target_link_options({n} PRIVATE {' '.join(t['link_options'])})",f"add_test(NAME {t['ctest']['name']} COMMAND {' '.join(t['ctest']['command'])})"]);suites.append(t['ctest']['name'])
n=hier['new_test_target'];assert 'add_executable('+n not in cmake;lines.extend([f"add_executable({n} {hier['new_test_cpp']})",f'target_link_libraries({n} PRIVATE stdc++ presonus::uc)',f"target_compile_options({n} PRIVATE {' '.join(hier['target_compile_options'])})",f"add_test(NAME {n} COMMAND {' '.join(hier['test_command'])})"]);suites.append(n)
assert len(suites)==len(set(suites))==7
migrated=['uc_connection_receive_ccl_tests','uc_ccl_provider_tests','uc_connection_tests','uc_external_connection_tests','uc_network_services_loopback','uc_network_handler_queries_bridge']
for n in migrated:
 assert 'add_executable('+n in cmake
 lines.extend([f'if(TARGET {n})',f'  target_include_directories({n} PRIVATE "${{CMAKE_CURRENT_SOURCE_DIR}}/tests")',f'  target_compile_options({n} PRIVATE -frtti -fno-lto)',f'endif()'])
marker='  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)';cmake=once(cmake,marker,'\n'.join('  '+s for s in lines)+'\n'+marker)
for n,s in [('CMakeLists.txt',cmake),('cmake/ProductionSourceGroups.cmake',groups)]:products[n]=s.encode();previous[n]=sha(lib/n);origins[n]='Pinned three-packet build recipe'
changed={n for n,h in previous.items() if h and hashlib.sha256(products[n]).hexdigest()!=h};impact={k:[x for x in read(lib/'validation'/f)['functions'] if changed.intersection(x['sources'])] for k,f in [('ready','ready-functions.json'),('pending','compiled-functions.json')]}
plan=dict(products=len(products),partitions=counts(groups),expected_cpp=232,expected_headers=158,expected_suites=277,new_suites=suites,affected_ready=len(impact['ready']),affected_pending=len(impact['pending']),previous=previous,result_hashes={n:hashlib.sha256(b).hexdigest() for n,b in products.items()},input_hashes=inputs)
phase.mkdir(parents=True,exist_ok=True)
if not a.apply:
 (phase/'application-plan.json').write_text(json.dumps(plan,indent=2)+'\n');(phase/'planned-full-impact.json').write_text(json.dumps(impact,indent=2)+'\n')
else:
 pre=read(phase/'candidate-preflight-01/validation.json');assert pre['passed'];assert not (phase/'application.json').exists();assert read(phase/'application-plan.json')==plan
 for n,h in pre['guard_after'].items():assert sha(lib/n)==h,n
 for n,h in pre['fragments_sha256'].items():assert sha(lib/n)==h,n
 for n,b in products.items():
  target=lib/n
  if target.exists():
   backup=phase/'before'/n;backup.parent.mkdir(parents=True,exist_ok=True);assert not backup.exists();backup.write_bytes(target.read_bytes())
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
 (phase/'application.json').write_text(json.dumps(plan,indent=2)+'\n');(phase/'affected-source-closure.json').write_text(json.dumps(impact,indent=2)+'\n')
 paths=sorted(n for n in products if Path(n).suffix in ('.cpp','.hpp','.h'));(lib/'validation/format-factory-callbacks-hierarchy-active-paths.json').write_text(json.dumps(paths,indent=2)+'\n')
 additions=set(products)|set(inputs)|{'tools/recovery/apply_factory_callbacks_hierarchy.py','candidates/uc-factory-callbacks-hierarchy-native-profile/tests/replay_production.py','candidates/uc-outgoing-socket-identity/validation/original-01/fixtures.stdin','candidates/uc-outgoing-socket-identity/validation/original-01/expected.txt'}
 (lib/'validation/integration-factory-callbacks-hierarchy-active-additions.json').write_text(json.dumps(sorted(additions),indent=2)+'\n')
print(json.dumps({k:v for k,v in plan.items() if k not in ('previous','result_hashes','input_hashes')}))
