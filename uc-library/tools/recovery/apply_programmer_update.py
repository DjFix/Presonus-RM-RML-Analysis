"""Guarded offline final programmer orchestration application."""
from pathlib import Path
import argparse,hashlib,json,re,shutil
p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args()
repo=Path.cwd().resolve();lib=repo/'uc-library';out=repo/'evidence/recovery/2026-10-28/update-interp-batch';own=lib/'candidates/dice-programmer-update'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(own/'CONTROLLED-APPLY.json')=='d50fbee283878668528e181632dfdf9ac069c24192f3ec35438616437e259edd'
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
assert counts(groups)==[83,33,11]
groups=once(groups,'set(PRESONUS_cs18_SOURCES\n','set(PRESONUS_cs18_SOURCES\n'+''.join('  '+name+'\n' for name in m['production_cpp_partition']))
cmake=(lib/'CMakeLists.txt').read_text()
properties='\n'.join('set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/'+name+'" APPEND PROPERTY COMPILE_OPTIONS '+' '.join(options)+')' for name,options in m['production_compile_options'].items())
cmake=once(cmake,'presonus_build_common_objects()','presonus_build_common_objects()\n'+properties)
block='''  add_executable(dice_programmer_update_bridge tests/dice_programmer_update_bridge.cpp)
  target_link_libraries(dice_programmer_update_bridge PRIVATE presonus::cs18_components)
  target_compile_options(dice_programmer_update_bridge PRIVATE '''+' '.join(m['test_compile_options'])+''')
  target_link_options(dice_programmer_update_bridge PRIVATE
'''+''.join('    '+option+'\n' for option in m['test_link_options'])+'''  )
  add_test(NAME dice_programmer_update_retained COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/dice_programmer_update_replay.py
    --binary $<TARGET_FILE:dice_programmer_update_bridge>
    --stdin ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-programmer-update/stdin.txt
    --fixture ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-programmer-update/fixtures.jsonl)
'''
cmake=once(cmake,'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)',block+'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)')
for name,text in [('CMakeLists.txt',cmake),('cmake/ProductionSourceGroups.cmake',groups)]:
    assert (out/'before'/name).read_bytes()==(lib/name).read_bytes()
    products[name]=text.encode();old[name]=sha(lib/name);origins[name]='Root-reviewed strict-FP offline update recipe'
changed={name for name,digest in old.items() if digest is not None and hashlib.sha256(products[name]).hexdigest()!=digest}
affected={kind:[row for row in read(lib/'validation'/name)['functions'] if changed.intersection(row['sources'])] for kind,name in [('ready','ready-functions.json'),('pending','compiled-functions.json')]}
assert (len(affected['ready']),len(affected['pending']))==(10,21)
print(json.dumps(dict(apply=a.apply,products=len(products),groups=counts(groups),suites=151,headers=93,affected_ready=10,affected_pending=21)))
if not a.apply:raise SystemExit(0)
assert not (out/'application-update.json').exists()
for name in products:
    if (lib/name).exists():
        backup=out/'before'/name;backup.parent.mkdir(parents=True,exist_ok=True)
        if backup.exists():assert backup.read_bytes()==(lib/name).read_bytes()
        else:shutil.copyfile(lib/name,backup)
for name,data in products.items():
    dest=lib/name;dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists() or dest.read_bytes()!=data:dest.write_bytes(data)
(out/'affected-source-closure.json').write_text(json.dumps(affected,indent=2)+'\n')
(out/'application-update.json').write_text(json.dumps({'products':{name:dict(previous_sha256=old[name],applied_sha256=sha(lib/name),source=origins[name]) for name in products}},indent=2)+'\n')
cpp=[name for name in products if Path(name).suffix in ('.cpp','.hpp','.h')]
(lib/'validation/format-update-interp-paths.json').write_text(json.dumps(sorted(set(cpp+[origins[name] for name in cpp])),indent=2)+'\n')
(lib/'validation/integration-update-interp-additions.json').write_text(json.dumps(sorted(products),indent=2)+'\n')
