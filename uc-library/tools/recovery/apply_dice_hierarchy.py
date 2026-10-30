"""Guarded DICE hierarchy and disjoint formatter lifecycle application."""
from pathlib import Path
import argparse,hashlib,json,re,shutil
p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args()
repo=Path.cwd().resolve();lib=repo/'uc-library';out=repo/'evidence/recovery/2026-10-28/dice-hierarchy-batch'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
dp=lib/'candidates/dice-control-inspection/CONTROLLED-APPLY.json';fp=lib/'candidates/dsp-formatter-lifecycle/CONTROLLED-APPLY.json'
assert sha(dp)=='212c0fb2e635cfc9a035d78552f8c031d88df3c4863211b04e18d11569e525ea'
assert sha(fp)=='c5687f4f6e5b1737edd7a9fb5f6b696e608448edf3a034088b39ff8ed9e16e4a'
d=read(dp);f=read(fp);products={};old={};origins={}
for proof in d['component_proofs']:assert sha(dp.parent/proof['path'])==proof['sha256']
for row in d['products']+d['fixtures']+f['products']:
    source=(lib/row['source']).resolve();dest=(lib/row['target']).resolve();pre=row['previous_sha256']
    assert source.is_relative_to(lib) and dest.is_relative_to(lib) and not dest.is_symlink() and row['target'] not in products
    assert sha(source)==row['sha256']
    assert not dest.exists() if pre is None else sha(dest)==pre
    products[row['target']]=source.read_bytes();old[row['target']]=pre;origins[row['target']]=row['source']
assert sha(lib/f['retained_fixture']['target'])==f['retained_fixture']['sha256']
def once(text,needle,replacement):
    assert text.count(needle)==1,needle
    return text.replace(needle,replacement,1)
groups=(lib/'cmake/ProductionSourceGroups.cmake').read_text()
counts=lambda t:[len(re.search(r'set\(PRESONUS_'+g+r'_SOURCES\n(.*?)\n\)',t,re.S).group(1).split()) for g in ('common','cs18','rm')]
assert counts(groups)==[90,38,11] and set(d['production_cpp_partition'].values())=={'cs18'}
groups=once(groups,'set(PRESONUS_cs18_SOURCES\n','set(PRESONUS_cs18_SOURCES\n'+''.join('  '+n+'\n' for n in d['production_cpp_partition']))
headers=[n.removeprefix('include/') for n in d['new_public_headers']]
groups=once(groups,'set(PRESONUS_PUBLIC_HEADERS\n','set(PRESONUS_PUBLIC_HEADERS\n'+''.join('  '+n+'\n' for n in headers))
cmake=(lib/'CMakeLists.txt').read_text()
cmake=once(cmake,'set(PRESONUS_UC_PUBLIC_HEADERS\n','set(PRESONUS_UC_PUBLIC_HEADERS\n'+''.join('  '+n+'\n' for n in headers))
properties='\n'.join('set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/'+n+'" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)' for n in d['production_cpp_partition'])
cmake=once(cmake,'presonus_build_common_objects()','presonus_build_common_objects()\n'+properties)
block='''  add_executable(dice_subsystem_control_bridge tests/dice_subsystem_control_bridge.cpp)
  target_link_libraries(dice_subsystem_control_bridge PRIVATE presonus::cs18_components)
  target_compile_options(dice_subsystem_control_bridge PRIVATE '''+' '.join(d['test_compile_options'])+''')
  target_link_options(dice_subsystem_control_bridge PRIVATE
'''+''.join('    '+o+'\n' for o in d['test_link_options'])+'''  )
  add_test(NAME dice_subsystem_control_retained COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/dice_subsystem_control_replay.py
    --binary $<TARGET_FILE:dice_subsystem_control_bridge>
    --stdin ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-subsystem-control/stdin.txt
    --fixture ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-subsystem-control/fixtures.jsonl)
  add_executable(dice_subsystem_runtime_provider tests/dice_subsystem_runtime_provider.cpp)
  target_link_libraries(dice_subsystem_runtime_provider PRIVATE presonus::cs18_components)
  target_compile_options(dice_subsystem_runtime_provider PRIVATE '''+' '.join(d['test_compile_options'])+''')
  target_link_options(dice_subsystem_runtime_provider PRIVATE
'''+''.join('    '+o+'\n' for o in d['provider_link_options'])+'''  )
  add_test(NAME dice_subsystem_runtime_provider COMMAND dice_subsystem_runtime_provider)
  add_executable(dsp_formatter_lifecycle_tests tests/dsp_formatter_lifecycle_tests.cpp)
  target_link_libraries(dsp_formatter_lifecycle_tests PRIVATE presonus_uc)
  target_compile_options(dsp_formatter_lifecycle_tests PRIVATE '''+' '.join(f['test_compile_options'])+''')
  target_link_options(dsp_formatter_lifecycle_tests PRIVATE '''+' '.join(f['test_link_options'])+''')
  add_test(NAME dsp_formatter_lifecycle_tests COMMAND dsp_formatter_lifecycle_tests)
'''
cmake=once(cmake,'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)',block+'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)')
for name,text in [('CMakeLists.txt',cmake),('cmake/ProductionSourceGroups.cmake',groups)]:
    assert (out/'before'/name).read_bytes()==(lib/name).read_bytes()
    products[name]=text.encode();old[name]=sha(lib/name);origins[name]='Root-reviewed combined hierarchy/lifecycle recipe; both public-header lists'
changed={n for n,h in old.items() if h is not None and hashlib.sha256(products[n]).hexdigest()!=h}
affected={kind:[r for r in read(lib/'validation'/name)['functions'] if changed.intersection(r['sources'])] for kind,name in [('ready','ready-functions.json'),('pending','compiled-functions.json')]}
assert (len(affected['ready']),len(affected['pending']))==(32,176),(len(affected['ready']),len(affected['pending']))
print(json.dumps(dict(apply=a.apply,products=len(products),groups=counts(groups),suites=163,headers=102,affected_ready=32,affected_pending=176)))
if not a.apply:raise SystemExit(0)
assert not (out/'application.json').exists()
for name,data in products.items():
    dest=lib/name
    if dest.exists():
        backup=out/'before'/name;backup.parent.mkdir(parents=True,exist_ok=True)
        if backup.exists():assert backup.read_bytes()==dest.read_bytes()
        else:shutil.copyfile(dest,backup)
    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
(out/'application.json').write_text(json.dumps(dict(products={n:dict(previous_sha256=old[n],applied_sha256=sha(lib/n),source=origins[n]) for n in products}),indent=2)+'\n')
(out/'affected-source-closure.json').write_text(json.dumps(affected,indent=2)+'\n')
paths=d['all_cpp']+[n for n in products if Path(n).suffix in ('.cpp','.hpp','.h')]+[r['source'] for r in f['products']]
for name in ('candidates/uc-network-registrar-services/validation/dice-manager-firmware-seal-01/format-paths.json','candidates/uc-network-server-metadata/validation/dice-manager-firmware-seal-01/format-paths.json','candidates/uc-network-adapter-services/validation/active-seal-01/format-paths.json','candidates/uc-network-discovery-services/validation/active-seal-01/format-paths.json'):
    paths+=read(lib/name)
(lib/'validation/format-dice-hierarchy-paths.json').write_text(json.dumps(sorted(set(paths)),indent=2)+'\n')
(lib/'validation/integration-dice-hierarchy-additions.json').write_text(json.dumps(sorted(products),indent=2)+'\n')
