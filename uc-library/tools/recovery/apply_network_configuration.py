"""Guarded Network configuration application in the follow-on batch."""
from pathlib import Path
import argparse,hashlib,json,re,shutil
p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args()
repo=Path.cwd().resolve();lib=repo/'uc-library';out=repo/'evidence/recovery/2026-10-28/followon-batch';own=lib/'candidates/uc-network-configuration'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
assert sha(own/'CONTROLLED-APPLY.json')=='1e2c1a9611ee96010524877c7ebb1e4bfec6edc9ed0fbe5c397077bb76f3a230'
m=read(own/'CONTROLLED-APPLY.json');products={};old={};origins={}
def add(source,target,digest,pre=None):
    source=source.resolve();dest=lib/target
    assert source.is_relative_to(lib) and dest.resolve().is_relative_to(lib) and not dest.is_symlink() and target not in products
    assert sha(source)==digest
    assert not dest.exists() if pre is None else sha(dest)==pre
    products[target]=source.read_bytes();old[target]=pre;origins[target]=str(source.relative_to(lib))
for row in m['products']:add(own/row['source'],row['destination'],row['sha256'],row['required_destination_sha256'])
for key,target in [('stdin','fixtures.stdin'),('expected','expected.txt')]:add(own/m['fixture'][key],'validation/uc-network-configuration/'+target,m['fixture'][key+'_sha256'])
def once(text,needle,replacement):
    assert text.count(needle)==1,needle
    return text.replace(needle,replacement,1)
groups=(lib/'cmake/ProductionSourceGroups.cmake').read_text()
counts=lambda text:[len(re.search(r'set\(PRESONUS_'+g+r'_SOURCES\n(.*?)\n\)',text,re.S).group(1).split()) for g in ('common','cs18','rm')]
assert counts(groups)==[79,28,10]
groups=once(groups,'set(PRESONUS_common_SOURCES\n','set(PRESONUS_common_SOURCES\n  src/Presonus/UC/NetworkManagerConfiguration.cpp\n')
cmake=(lib/'CMakeLists.txt').read_text()
block='''  add_executable(uc_network_configuration_bridge tests/network_configuration/configuration_bridge.cpp)
  target_link_libraries(uc_network_configuration_bridge PRIVATE presonus::uc)
  target_compile_options(uc_network_configuration_bridge PRIVATE -fno-lto)
  target_link_options(uc_network_configuration_bridge PRIVATE -fno-lto
    -Wl,--wrap=_ZN4Core8Platform9PosixLock4lockEv
    -Wl,--wrap=_ZN4Core8Platform9PosixLock6unlockEv
    -Wl,--wrap=_ZN4Core8Platform11PosixThread11setPriorityEi)
  add_test(NAME uc_network_configuration COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py
    --executable $<TARGET_FILE:uc_network_configuration_bridge>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-configuration/fixtures.stdin
    --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-configuration/expected.txt --cases 3992)
'''
cmake=once(cmake,'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)',block+'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)')
for name,text in [('CMakeLists.txt',cmake),('cmake/ProductionSourceGroups.cmake',groups)]:
    assert (out/'before'/name).read_bytes()==(lib/name).read_bytes()
    products[name]=text.encode();old[name]=sha(lib/name);origins[name]='Root-reviewed frozen candidate recipe'
changed={n for n,h in old.items() if h is not None}
affected={kind:[r for r in read(lib/'validation'/name)['functions'] if changed.intersection(r['sources'])] for kind,name in [('ready','ready-functions.json'),('pending','compiled-functions.json')]}
assert (len(affected['ready']),len(affected['pending']))==(6,40)
print(json.dumps(dict(apply=a.apply,products=len(products),groups=counts(groups),suites=140,headers=89,affected_ready=6,affected_pending=40)))
if not a.apply:raise SystemExit(0)
assert not (out/'application.json').exists()
for name in products:
    path=lib/name
    if path.exists():
        backup=out/'before'/name;backup.parent.mkdir(parents=True,exist_ok=True)
        if backup.exists():assert backup.read_bytes()==path.read_bytes()
        else:shutil.copyfile(path,backup)
for name,data in products.items():
    dest=lib/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
(out/'affected-source-closure.json').write_text(json.dumps(affected,indent=2)+'\n')
(out/'application.json').write_text(json.dumps({'products':{n:dict(previous_sha256=old[n],applied_sha256=sha(lib/n),source=origins[n]) for n in products}},indent=2)+'\n')
cpp=[n for n in products if Path(n).suffix in ('.cpp','.hpp','.h')]
(lib/'validation/format-followon-paths.json').write_text(json.dumps(sorted(set(cpp+[origins[n] for n in cpp])),indent=2)+'\n')
(lib/'validation/integration-followon-additions.json').write_text(json.dumps(sorted(products),indent=2)+'\n')
