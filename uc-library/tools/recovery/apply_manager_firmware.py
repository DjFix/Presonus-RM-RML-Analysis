"""Guarded manager firmware source application; no physical operations."""
from pathlib import Path
import argparse, hashlib, json, re, shutil
p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args()
repo=Path.cwd().resolve();lib=repo/'uc-library';out=repo/'evidence/recovery/2026-10-28/manager-adapter-batch';own=lib/'candidates/dice-manager-firmware'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
assert sha(own/'CONTROLLED-APPLY.json')=='83d57b3a770e7cc4549ac65ca5acb4d3f8c29ff1a7761cfd6348c1e00d5eb9ff'
m=read(own/'CONTROLLED-APPLY.json');products={};old={};origins={}
for row in m['products']+m['fixtures']:
    source=(lib/row['source']).resolve();dest=(lib/row['target']).resolve();pre=row['previous_sha256']
    assert source.is_relative_to(lib) and dest.is_relative_to(lib) and not dest.is_symlink() and row['target'] not in products
    assert sha(source)==row['sha256']
    assert not dest.exists() if pre is None else sha(dest)==pre
    products[row['target']]=source.read_bytes();old[row['target']]=pre;origins[row['target']]=row['source']
def once(text,needle,replacement):
    assert text.count(needle)==1,needle
    return text.replace(needle,replacement,1)
groups=(lib/'cmake/ProductionSourceGroups.cmake').read_text()
counts=lambda text:[len(re.search(r'set\(PRESONUS_'+g+r'_SOURCES\n(.*?)\n\)',text,re.S).group(1).split()) for g in ('common','cs18','rm')]
assert counts(groups)==[85,35,11]
assert set(m['production_cpp_partition'].values())=={'cs18'}
groups=once(groups,'set(PRESONUS_cs18_SOURCES\n','set(PRESONUS_cs18_SOURCES\n'+''.join('  '+n+'\n' for n in m['production_cpp_partition']))
headers=[name.removeprefix('include/') for name in m['new_public_headers']]
groups=once(groups,'set(PRESONUS_PUBLIC_HEADERS\n','set(PRESONUS_PUBLIC_HEADERS\n'+''.join('  '+n+'\n' for n in headers))
cmake=(lib/'CMakeLists.txt').read_text()
cmake=once(cmake,'set(PRESONUS_UC_PUBLIC_HEADERS\n','set(PRESONUS_UC_PUBLIC_HEADERS\n'+''.join('  '+n+'\n' for n in headers))
properties='\n'.join('set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/'+name+'" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)' for name in m['production_cpp_partition'])
cmake=once(cmake,'presonus_build_common_objects()','presonus_build_common_objects()\n'+properties)
block='''  add_executable(dice_manager_firmware_bridge tests/dice_manager_firmware_bridge.cpp)
  target_link_libraries(dice_manager_firmware_bridge PRIVATE presonus::cs18_components)
  target_compile_options(dice_manager_firmware_bridge PRIVATE -fno-lto)
  target_link_options(dice_manager_firmware_bridge PRIVATE
'''+''.join('    '+option+'\n' for option in m['test_link_options'])+'''  )
  add_test(NAME dice_manager_firmware_retained COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/dice_manager_firmware_replay.py
    --binary $<TARGET_FILE:dice_manager_firmware_bridge>
    --stdin ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-manager-firmware/stdin.txt
    --fixture ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-manager-firmware/fixtures.jsonl)
  add_test(NAME dice_manager_firmware_exceptions COMMAND dice_manager_firmware_bridge --exception-smoke)
  add_executable(dice_manager_firmware_provider tests/dice_manager_firmware_provider.cpp)
  target_link_libraries(dice_manager_firmware_provider PRIVATE presonus::cs18_components)
  target_compile_options(dice_manager_firmware_provider PRIVATE -fno-lto)
  target_link_options(dice_manager_firmware_provider PRIVATE
'''+''.join('    '+option+'\n' for option in m['provider_link_options'])+'''  )
  add_test(NAME dice_manager_firmware_provider COMMAND dice_manager_firmware_provider)
'''
cmake=once(cmake,'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)',block+'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)')
for name,text in [('CMakeLists.txt',cmake),('cmake/ProductionSourceGroups.cmake',groups)]:
    assert (out/'before'/name).read_bytes()==(lib/name).read_bytes()
    products[name]=text.encode();old[name]=sha(lib/name);origins[name]='Root-reviewed manager firmware recipe, both public-header lists'
changed={name for name,digest in old.items() if digest is not None and hashlib.sha256(products[name]).hexdigest()!=digest}
affected={kind:[r for r in read(lib/'validation'/name)['functions'] if changed.intersection(r['sources'])] for kind,name in [('ready','ready-functions.json'),('pending','compiled-functions.json')]}
assert (len(affected['ready']),len(affected['pending']))==(6,101)
print(json.dumps(dict(apply=a.apply,products=len(products),groups=counts(groups),suites=155,headers=95,affected_ready=6,affected_pending=101)))
if not a.apply:raise SystemExit(0)
assert not (out/'application-manager.json').exists()
for name,data in products.items():
    dest=lib/name
    if dest.exists():
        backup=out/'before'/name;backup.parent.mkdir(parents=True,exist_ok=True)
        if backup.exists():assert backup.read_bytes()==dest.read_bytes()
        else:shutil.copyfile(dest,backup)
    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
(out/'affected-source-closure.json').write_text(json.dumps(affected,indent=2)+'\n')
(out/'application-manager.json').write_text(json.dumps(dict(products={n:dict(previous_sha256=old[n],applied_sha256=sha(lib/n),source=origins[n]) for n in products}),indent=2)+'\n')
(lib/'validation/format-manager-adapter-paths.json').write_text(json.dumps(m['all_cpp'],indent=2)+'\n')
(lib/'validation/integration-manager-adapter-additions.json').write_text(json.dumps(sorted(products),indent=2)+'\n')
