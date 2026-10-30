"""Guarded offline programmer packet addition to the follow-on batch."""
import argparse,hashlib,json,re,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args()
repo=Path.cwd().resolve();lib=repo/'uc-library';out=repo/'evidence/recovery/2026-10-28/device-eq-batch'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
mapfile=lib/'candidates/dice-programmer-open-close/CONTROLLED-APPLY.json'
assert sha(mapfile)=='5f7fa0632c546728ecd841f62297827e49d6e1813ed68748730164e93674e8dd'
m=read(mapfile);products={};old={};origins={}
for row in m['products']+m['fixtures']:
    source=(lib/row['source']).resolve();target=(lib/row['target']).resolve();pre=row['previous_sha256']
    assert source.is_relative_to(lib) and target.is_relative_to(lib) and not target.is_symlink()
    assert sha(source)==row['sha256'] and row['target'] not in products
    assert not target.exists() if pre is None else sha(target)==pre
    products[row['target']]=source.read_bytes();old[row['target']]=pre;origins[row['target']]=row['source']
def once(text,needle,replacement):
    assert text.count(needle)==1,needle
    return text.replace(needle,replacement,1)
groups=(lib/'cmake/ProductionSourceGroups.cmake').read_text()
counts=lambda text:[len(re.search(r'set\(PRESONUS_'+g+r'_SOURCES\n(.*?)\n\)',text,re.S).group(1).split()) for g in ('common','cs18','rm')]
assert counts(groups)==[82,31,10]
groups=once(groups,'set(PRESONUS_cs18_SOURCES\n','set(PRESONUS_cs18_SOURCES\n'+''.join('  '+n+'\n' for n in m['production_cpp_partition']))
groups=once(groups,'set(PRESONUS_PUBLIC_HEADERS\n','set(PRESONUS_PUBLIC_HEADERS\n  presonus/dice/programmer_device_services.hpp\n')
cmake=(lib/'CMakeLists.txt').read_text()
cmake=once(cmake,'    presonus/dice/manager_services.hpp','    presonus/dice/programmer_device_services.hpp\n    presonus/dice/manager_services.hpp')
block='''  add_executable(dice_programmer_device_bridge tests/dice_programmer_device_bridge.cpp)
  target_link_libraries(dice_programmer_device_bridge PRIVATE presonus::cs18_components)
  target_compile_options(dice_programmer_device_bridge PRIVATE -fno-lto)
  target_link_options(dice_programmer_device_bridge PRIVATE
    -Wl,--wrap=open -Wl,--wrap=__open_2 -Wl,--wrap=close -Wl,--wrap=ioctl)
  add_test(NAME dice_programmer_device_retained COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/dice_programmer_device_replay.py
    --binary $<TARGET_FILE:dice_programmer_device_bridge>
    --stdin ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-programmer-device/stdin.txt
    --fixture ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-programmer-device/fixtures.jsonl)
  add_test(NAME dice_programmer_device_provider COMMAND dice_programmer_device_bridge --provider-smoke)
'''
cmake=once(cmake,'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)',block+'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)')
for name,text in [('CMakeLists.txt',cmake),('cmake/ProductionSourceGroups.cmake',groups)]:
    products[name]=text.encode();old[name]=sha(lib/name);origins[name]='Root-reviewed frozen programmer recipe'
affected={kind:[r for r in read(lib/'validation'/name)['functions'] if 'include/presonus/dice/programmer.hpp' in r['sources']] for kind,name in [('ready','ready-functions.json'),('pending','compiled-functions.json')]}
assert (len(affected['ready']),len(affected['pending']))==(4,9)
print(json.dumps(dict(apply=a.apply,products=len(products),groups=counts(groups),suites=148,headers=92,programmer_refresh_ready=4,programmer_refresh_pending=9)))
if not a.apply:raise SystemExit(0)
assert not (out/'application-device.json').exists()
for name in [*products,'validation/integration.json','validation/integration-linux.json','validation/formatting.json']:
    if (lib/name).exists():
        backup=out/'before-device'/name;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(lib/name,backup)
(out/'affected-device-source-closure.json').write_text(json.dumps(affected,indent=2)+'\n')
for name,data in products.items():
    dest=lib/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
(out/'application-device.json').write_text(json.dumps({'products':{n:dict(previous_sha256=old[n],applied_sha256=sha(lib/n),source=origins[n]) for n in products}},indent=2)+'\n')
paths=read(lib/'validation/format-device-eq-paths.json') if (lib/'validation/format-device-eq-paths.json').exists() else [];cpp=[n for n in products if Path(n).suffix in ('.cpp','.hpp','.h')]
(lib/'validation/format-device-eq-paths.json').write_text(json.dumps(sorted(set(paths+cpp+[origins[n] for n in cpp])),indent=2)+'\n')
paths=read(lib/'validation/integration-device-eq-additions.json') if (lib/'validation/integration-device-eq-additions.json').exists() else []
(lib/'validation/integration-device-eq-additions.json').write_text(json.dumps(sorted(set(paths)|set(products)),indent=2)+'\n')
