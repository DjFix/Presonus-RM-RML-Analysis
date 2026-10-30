"""Guarded registrar service and three-slot listener application."""
from pathlib import Path
import argparse,hashlib,json,re,shutil
p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args()
repo=Path.cwd().resolve();lib=repo/'uc-library';out=repo/'evidence/recovery/2026-10-28/registrar-batch';own=lib/'candidates/uc-network-registrar-services'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(own/'CONTROLLED-APPLY.json')=='f582f36753b0c3e03a6de73afa9f0752de8b0b3ed5784619336d6c65c43a820c'
m=read(own/'CONTROLLED-APPLY.json');products={};old={};origins={}
def add(source,target,digest,pre=None):
    source=source.resolve();dest=lib/target
    assert source.is_relative_to(lib) and dest.resolve().is_relative_to(lib) and not dest.is_symlink() and target not in products
    assert sha(source)==digest
    assert not dest.exists() if pre is None else sha(dest)==pre
    products[target]=source.read_bytes();old[target]=pre;origins[target]=str(source.relative_to(lib))
for row in m['products']:add(own/row['source'],row['destination'],row['sha256'],row['required_destination_sha256'])
for key,target in [('stdin','fixtures.stdin'),('expected','expected.txt')]:add(own/m['fixture'][key],'validation/uc-network-registrar-services/'+target,m['fixture'][key+'_sha256'])
def once(text,needle,replacement):
    assert text.count(needle)==1,needle
    return text.replace(needle,replacement,1)
groups=(lib/'cmake/ProductionSourceGroups.cmake').read_text()
counts=lambda text:[len(re.search(r'set\(PRESONUS_'+g+r'_SOURCES\n(.*?)\n\)',text,re.S).group(1).split()) for g in ('common','cs18','rm')]
assert counts(groups)==[81,31,10]
groups=once(groups,'set(PRESONUS_common_SOURCES\n','set(PRESONUS_common_SOURCES\n  src/Presonus/UC/ServerRegistrarServices.cpp\n')
cmake=(lib/'CMakeLists.txt').read_text()
block='''  add_executable(uc_network_registrar_services_bridge tests/network_registrar_services/registrar_services_bridge.cpp)
  target_link_libraries(uc_network_registrar_services_bridge PRIVATE presonus::uc)
  target_compile_options(uc_network_registrar_services_bridge PRIVATE -fno-lto)
  add_test(NAME uc_network_registrar_services COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py
    --executable $<TARGET_FILE:uc_network_registrar_services_bridge>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-registrar-services/fixtures.stdin
    --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-registrar-services/expected.txt --cases 3058)
'''
cmake=once(cmake,'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)',block+'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)')
for name,text in [('CMakeLists.txt',cmake),('cmake/ProductionSourceGroups.cmake',groups)]:
    assert (out/'before'/name).read_bytes()==(lib/name).read_bytes()
    products[name]=text.encode();old[name]=sha(lib/name);origins[name]='Root-reviewed frozen registrar recipe'
changed={name for name,digest in old.items() if digest is not None}
affected={kind:[r for r in read(lib/'validation'/name)['functions'] if changed.intersection(r['sources'])] for kind,name in [('ready','ready-functions.json'),('pending','compiled-functions.json')]}
assert (len(affected['ready']),len(affected['pending']))==(6,60)
print(json.dumps(dict(apply=a.apply,products=len(products),groups=counts(groups),suites=146,headers=91,affected_ready=len(affected['ready']),affected_pending=len(affected['pending']))))
if not a.apply:raise SystemExit(0)
assert not (out/'application.json').exists()
for name in products:
    if (lib/name).exists():
        backup=out/'before'/name;backup.parent.mkdir(parents=True,exist_ok=True)
        if backup.exists():assert backup.read_bytes()==(lib/name).read_bytes()
        else:shutil.copyfile(lib/name,backup)
for name,data in products.items():
    dest=lib/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
(out/'affected-source-closure.json').write_text(json.dumps(affected,indent=2)+'\n')
(out/'application.json').write_text(json.dumps({'products':{n:dict(previous_sha256=old[n],applied_sha256=sha(lib/n),source=origins[n]) for n in products}},indent=2)+'\n')
cpp=[name for name in products if Path(name).suffix in ('.cpp','.hpp','.h')]
(lib/'validation/format-registrar-paths.json').write_text(json.dumps(sorted(set(cpp+[origins[name] for name in cpp])),indent=2)+'\n')
(lib/'validation/integration-registrar-additions.json').write_text(json.dumps(sorted(products),indent=2)+'\n')
