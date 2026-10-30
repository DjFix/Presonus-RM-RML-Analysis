"""Guarded DICE receiver and Network listener application; no classification."""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--apply', action='store_true')
args=parser.parse_args()
repo=Path.cwd().resolve();lib=repo/'uc-library'
out=repo/'evidence/recovery/2026-10-28/continuation-batch'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
maps={}
for name,digest in {'dice-continuation':'29a249d041bc0f4ed75b539a3c8ea85ac14d27f6a0ecb835138bd73460ddf056','uc-network-continuation':'f11098bc487103df5e4e55629bb0df175e3d0555bfa56b31f48ae450bc05dbb2'}.items():
    path=lib/'candidates'/name/'CONTROLLED-APPLY.json'
    assert sha(path)==digest
    maps[name]=read(path)
products={};previous={};origins={}
def add(source,target,digest,old=None):
    source=source.resolve();dest=lib/target
    assert source.is_relative_to(lib) and sha(source)==digest
    assert not Path(target).is_absolute() and '..' not in Path(target).parts and target not in products
    assert dest.resolve().is_relative_to(lib) and not dest.is_symlink()
    assert not dest.exists() if old is None else sha(dest)==old
    products[target]=source.read_bytes();previous[target]=old;origins[target]=str(source.relative_to(lib))
for name,manifest in maps.items():
    for row in manifest['products']+manifest.get('fixtures',[]):
        source=lib/row['source'] if row['source'].startswith('candidates/') else lib/'candidates'/name/row['source']
        add(source,row.get('target',row.get('destination')),row['sha256'],row.get('previous_sha256',row.get('required_destination_sha256')))
network=maps['uc-network-continuation']
for key,target in [('stdin','fixtures.stdin'),('expected','expected.txt')]:
    fixture=network['fixture']
    add(lib/'candidates/uc-network-continuation'/fixture[key],'validation/uc-network-listener-services/'+target,fixture[key+'_sha256'])
def once(text,needle,replacement):
    assert text.count(needle)==1,needle
    return text.replace(needle,replacement,1)
groups=(lib/'cmake/ProductionSourceGroups.cmake').read_text()
counts=lambda text:[len(re.search(r'set\(PRESONUS_'+g+r'_SOURCES\n(.*?)\n\)',text,re.S).group(1).split()) for g in ('common','cs18','rm')]
assert counts(groups)==[75,27,10]
groups=once(groups,'set(PRESONUS_common_SOURCES\n','set(PRESONUS_common_SOURCES\n'+''.join('  '+p+'\n' for p in network['production_cpp']))
groups=once(groups,'set(PRESONUS_cs18_SOURCES\n','set(PRESONUS_cs18_SOURCES\n  src/Presonus/DICE/SysexReceiverLifecycle.cpp\n')
groups=once(groups,'set(PRESONUS_PUBLIC_HEADERS\n','set(PRESONUS_PUBLIC_HEADERS\n  presonus/uc/server_registrar.hpp\n')
cmake=(lib/'CMakeLists.txt').read_text()
cmake=once(cmake,'    presonus/dice/manager_services.hpp','    presonus/uc/server_registrar.hpp\n    presonus/dice/manager_services.hpp')
block='''  add_executable(dice_receiver_lifecycle_bridge tests/dice_receiver_lifecycle_bridge.cpp)
  target_link_libraries(dice_receiver_lifecycle_bridge PRIVATE presonus::cs18_components)
  target_link_options(dice_receiver_lifecycle_bridge PRIVATE
    -Wl,--wrap=_ZN8Presonus4DICE9Dice3Uart4postERNS0_11SysexPacketE
    -Wl,--wrap=_ZN4Core8Portable9Deletable11addInstanceEPS1_)
  add_test(NAME dice_receiver_lifecycle_retained COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/dice_receiver_lifecycle_replay.py
    --binary $<TARGET_FILE:dice_receiver_lifecycle_bridge>
    --fixture ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-receiver-lifecycle/fixtures.jsonl
    --stdin ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-receiver-lifecycle/stdin.txt)
  add_executable(uc_network_listener_bridge tests/network_listener_services/listener_bridge.cpp)
  target_link_libraries(uc_network_listener_bridge PRIVATE presonus::uc)
  target_compile_options(uc_network_listener_bridge PRIVATE -fno-lto)
  target_link_options(uc_network_listener_bridge PRIVATE -fno-lto
    -Wl,--wrap=_ZN4Core8Platform9PosixLock4lockEv
    -Wl,--wrap=_ZN4Core8Platform9PosixLock6unlockEv)
  add_test(NAME uc_network_listeners COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py
    --executable $<TARGET_FILE:uc_network_listener_bridge>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-listener-services/fixtures.stdin
    --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-listener-services/expected.txt --cases 2640)
'''
cmake=once(cmake,'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)',block+'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)')
baseline=read(out/'baseline-hashes.json')
for name,text in [('CMakeLists.txt',cmake),('cmake/ProductionSourceGroups.cmake',groups)]:
    assert sha(lib/name)==baseline[name]
    products[name]=text.encode();previous[name]=sha(lib/name);origins[name]='Root-reviewed candidate test/group recipes'
changed={n for n,h in previous.items() if h is not None}
affected={kind:[r for r in read(lib/'validation'/filename)['functions'] if changed.intersection(r['sources'])] for kind,filename in [('ready','ready-functions.json'),('pending','compiled-functions.json')]}
assert (len(affected['ready']),len(affected['pending']))==(30,57)
print(json.dumps(dict(apply=args.apply,products=len(products),groups=counts(groups),suites=138,headers=89,affected_ready=30,affected_pending=57)))
if not args.apply:raise SystemExit(0)
assert not (out/'application.json').exists()
for name in products:
    path=lib/name
    if path.exists():
        backup=out/'before'/name;backup.parent.mkdir(parents=True,exist_ok=True)
        if backup.exists():assert backup.read_bytes()==path.read_bytes()
        else:shutil.copyfile(path,backup)
(out/'affected-source-closure.json').write_text(json.dumps(affected,indent=2)+'\n')
for name,data in products.items():
    dest=lib/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
(out/'application.json').write_text(json.dumps({'products':{n:dict(previous_sha256=previous[n],applied_sha256=sha(lib/n),source=origins[n]) for n in products},'classification_not_yet_applied':True},indent=2)+'\n')
cpp=[n for n in products if Path(n).suffix in ('.cpp','.hpp','.h')]
cpp += [origins[n] for n in cpp]
(lib/'validation/format-continuation-paths.json').write_text(json.dumps(sorted(set(cpp)),indent=2)+'\n')
(lib/'validation/integration-continuation-additions.json').write_text(json.dumps(sorted(products),indent=2)+'\n')
