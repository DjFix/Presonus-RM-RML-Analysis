"""Guarded offline programmer packet addition to the follow-on batch."""
import argparse,hashlib,json,re,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args()
repo=Path.cwd().resolve();lib=repo/'uc-library';out=repo/'evidence/recovery/2026-10-28/queries-batch'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
mapfile=lib/'candidates/dice-programmer-pages/CONTROLLED-APPLY.json'
assert sha(mapfile)=='49c624710e602ac7f6aedee9a876f0171dcf1765f5cf2f90e1b1a8f09fb6ed54'
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
assert counts(groups)==[81,30,10]
groups=once(groups,'set(PRESONUS_cs18_SOURCES\n','set(PRESONUS_cs18_SOURCES\n'+''.join('  '+n+'\n' for n in m['new_production_cpp']))
cmake=(lib/'CMakeLists.txt').read_text()
block='''  add_executable(dice_programmer_pages_bridge tests/dice_programmer_pages_bridge.cpp)
  target_link_libraries(dice_programmer_pages_bridge PRIVATE presonus::cs18_components)
  target_compile_options(dice_programmer_pages_bridge PRIVATE -fno-lto)
  target_link_options(dice_programmer_pages_bridge PRIVATE -Wl,--wrap=ioctl)
  add_test(NAME dice_programmer_pages_retained COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/dice_programmer_pages_replay.py
    --binary $<TARGET_FILE:dice_programmer_pages_bridge>
    --stdin ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-programmer-pages/stdin.txt
    --fixture ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-programmer-pages/fixtures.jsonl)
  add_test(NAME dice_programmer_pages_provider COMMAND dice_programmer_pages_bridge --provider-smoke)
'''
cmake=once(cmake,'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)',block+'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)')
for name,text in [('CMakeLists.txt',cmake),('cmake/ProductionSourceGroups.cmake',groups)]:
    products[name]=text.encode();old[name]=sha(lib/name);origins[name]='Root-reviewed frozen programmer recipe'
affected={kind:[r for r in read(lib/'validation'/name)['functions'] if 'include/presonus/dice/programmer.hpp' in r['sources']] for kind,name in [('ready','ready-functions.json'),('pending','compiled-functions.json')]}
assert (len(affected['ready']),len(affected['pending']))==(4,6)
print(json.dumps(dict(apply=a.apply,products=len(products),groups=counts(groups),suites=145,headers=91,programmer_refresh_ready=4,programmer_refresh_pending=6)))
if not a.apply:raise SystemExit(0)
assert not (out/'application-pages.json').exists()
for name in [*products,'validation/integration.json','validation/integration-linux.json','validation/formatting.json']:
    if (lib/name).exists():
        backup=out/'before-pages'/name;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(lib/name,backup)
(out/'affected-pages-source-closure.json').write_text(json.dumps(affected,indent=2)+'\n')
for name,data in products.items():
    dest=lib/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
(out/'application-pages.json').write_text(json.dumps({'products':{n:dict(previous_sha256=old[n],applied_sha256=sha(lib/n),source=origins[n]) for n in products}},indent=2)+'\n')
paths=read(lib/'validation/format-queries-paths.json');cpp=[n for n in products if Path(n).suffix in ('.cpp','.hpp','.h')]
(lib/'validation/format-queries-paths.json').write_text(json.dumps(sorted(set(paths+cpp+[origins[n] for n in cpp])),indent=2)+'\n')
paths=read(lib/'validation/integration-queries-additions.json')
(lib/'validation/integration-queries-additions.json').write_text(json.dumps(sorted(set(paths)|set(products)),indent=2)+'\n')
