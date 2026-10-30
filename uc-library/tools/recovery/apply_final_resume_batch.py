"""Guarded application of the three frozen Linux-resume candidate packets."""
import argparse,hashlib,json,re,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args()
repo=Path.cwd().resolve();lib=repo/'uc-library';out=repo/'evidence/recovery/2026-10-28/final-resume-batch'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
names={'dice-next-services':'5feb0a6a9078f2b8576f2f960deeb97c8877f017cfcdcf2efbb8ecee4cb7fd81','uc-network-manager-next-services':'05bfe23ecea8e6ae6fd3584a56ed8a00666496be03b6a4fd135c2ddcca39f24f','dsp-biquad-methods':'d5b202e7b03b4d975bcdd32527a0a2bdf8b890977adbd39b731e6fe980e7bb08'}
maps={};products={};old={};origins={}
for name,h in names.items():
 f=lib/'candidates'/name/'CONTROLLED-APPLY.json';assert sha(f)==h;maps[name]=read(f)
def add(source,target,h,pre=None):
 source=source.resolve();dest=lib/target
 assert source.is_relative_to(lib) and sha(source)==h
 assert not Path(target).is_absolute() and '..' not in Path(target).parts and target not in products and not dest.is_symlink()
 assert not dest.exists() if pre is None else sha(dest)==pre
 products[target]=source.read_bytes();old[target]=pre;origins[target]=str(source.relative_to(lib))
for name,m in maps.items():
 for row in m['products']:
  source=lib/row['source'] if row['source'].startswith('candidates/') else lib/'candidates'/name/row['source']
  add(source,row.get('target',row.get('destination')),row['sha256'],row.get('previous_sha256',row.get('required_destination_sha256')))
d=maps['dice-next-services'];n=maps['uc-network-manager-next-services'];b=maps['dsp-biquad-methods']
for key in ('fixture','stdin'):
 r=d[key];add(lib/r['source'],r['target'],r['sha256'])
for key,target in [('stdin','fixtures.stdin'),('expected','expected.txt')]:
 r=n['fixture'];add(lib/'candidates/uc-network-manager-next-services'/r[key],'validation/uc-network-manager-next-services/'+target,r[key+'_sha256'])
r=b['fixture'];add(lib/r['source'],r['target'],r['sha256'])
groups=(lib/'cmake/ProductionSourceGroups.cmake').read_text();cmake=(lib/'CMakeLists.txt').read_text()
def once(t,needle,replacement):assert t.count(needle)==1,needle;return t.replace(needle,replacement,1)
count=lambda t:[len(re.search(r'set\(PRESONUS_'+g+r'_SOURCES\n(.*?)\n\)',t,re.S).group(1).split()) for g in ('common','cs18','rm')]
assert count(groups)==[73,25,10]
groups=once(groups,'set(PRESONUS_common_SOURCES\n','set(PRESONUS_common_SOURCES\n  src/Presonus/UC/NetworkManagerNextServices.cpp\n  src/DSP/BiquadMethods.cpp\n')
groups=once(groups,'set(PRESONUS_cs18_SOURCES\n','set(PRESONUS_cs18_SOURCES\n'+''.join('  '+x+'\n' for x in d['production_cpp']))
groups=once(groups,'set(PRESONUS_PUBLIC_HEADERS\n','set(PRESONUS_PUBLIC_HEADERS\n  presonus/dice/manager_services.hpp\n')
cmake=once(cmake,'    presonus/dsp/single_pole.hpp','    presonus/dice/manager_services.hpp\n    presonus/dsp/single_pole.hpp')
flags='''
set_source_files_properties(src/Presonus/DICE/Dice3ManagerServices.cpp src/portable/dice/CclManagerServices.cpp PROPERTIES COMPILE_OPTIONS "-fno-rtti;-fno-lto")
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/DSP/BiquadMethods.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin)
'''
cmake=once(cmake,'presonus_build_common_objects()','presonus_build_common_objects()'+flags)
block='''  add_executable(dice_manager_services_bridge tests/dice_manager_services_bridge.cpp)
  target_compile_features(dice_manager_services_bridge PRIVATE cxx_std_17)
  target_compile_options(dice_manager_services_bridge PRIVATE -fno-rtti -fno-lto)
  target_link_libraries(dice_manager_services_bridge PRIVATE presonus::cs18_components)
  target_link_options(dice_manager_services_bridge PRIVATE -fno-lto
'''+''.join('    -Wl,--wrap='+x+'\n' for x in d['wraps'])+'''  )
  add_test(NAME dice_manager_services_retained COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tools/dice_manager_services_replay.py --binary $<TARGET_FILE:dice_manager_services_bridge> --stdin ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-manager-services/stdin.txt --fixture ${CMAKE_CURRENT_SOURCE_DIR}/validation/dice-manager-services/fixtures.jsonl)
  add_test(NAME dice_manager_services_provider COMMAND dice_manager_services_bridge --provider-smoke)
  add_executable(uc_network_next_services_bridge tests/network_next_services/next_services_bridge.cpp tests/network_next_services/next_services_virtual_entry.cpp)
  target_link_libraries(uc_network_next_services_bridge PRIVATE presonus::uc)
  target_compile_options(uc_network_next_services_bridge PRIVATE -fno-lto)
  target_link_options(uc_network_next_services_bridge PRIVATE -fno-lto
'''+''.join('    -Wl,--wrap='+x+'\n' for x in n['wraps'])+'''  )
  add_test(NAME uc_network_next_services COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py --executable $<TARGET_FILE:uc_network_next_services_bridge> --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-manager-next-services/fixtures.stdin --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-network-manager-next-services/expected.txt --cases 3572)
  add_executable(dsp_biquad_methods_tests tests/dsp_biquad_methods_tests.cpp)
  target_compile_features(dsp_biquad_methods_tests PRIVATE cxx_std_17)
  target_link_libraries(dsp_biquad_methods_tests PRIVATE presonus::uc)
  add_test(NAME dsp_biquad_methods COMMAND dsp_biquad_methods_tests "${CMAKE_CURRENT_SOURCE_DIR}/validation/dsp-biquad-methods/fixtures.txt" "${CMAKE_CURRENT_BINARY_DIR}/dsp-biquad-methods-differences.txt")
'''
cmake=once(cmake,'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)',block+'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)')
for name,text in [('CMakeLists.txt',cmake),('cmake/ProductionSourceGroups.cmake',groups)]:products[name]=text.encode();old[name]=sha(lib/name);origins[name]='Root-reviewed frozen candidate CMake recipes'
changed={x for x,h in old.items() if h is not None}
affected={kind:[r for r in read(lib/'validation'/filename)['functions'] if changed.intersection(r['sources'])] for kind,filename in [('ready','ready-functions.json'),('pending','compiled-functions.json')]}
assert (len(affected['ready']),len(affected['pending']))==(9,20)
print(json.dumps(dict(apply=a.apply,products=len(products),source_groups=count(groups),suites=136,headers=88,affected_ready=9,affected_pending=20,expected_ready=637,expected_names=341,expected_pending=422)))
if not a.apply:raise SystemExit(0)
assert not (out/'application.json').exists();out.mkdir(exist_ok=True)
for name in [*products,'validation/ready-functions.json','validation/compiled-functions.json','validation/integration.json','validation/integration-linux.json','validation/formatting.json','SYMBOLS.md']:
 if (lib/name).exists():dest=out/'before'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(lib/name,dest)
(out/'affected-source-closure.json').write_text(json.dumps(affected,indent=2)+'\n')
for name,data in products.items():dest=lib/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
(out/'application.json').write_text(json.dumps(dict(products={x:dict(previous_sha256=old[x],applied_sha256=sha(lib/x),source=origins[x]) for x in products},classification_not_yet_applied=True),indent=2)+'\n')
(lib/'validation/format-final-resume-paths.json').write_text(json.dumps([x for x in products if Path(x).suffix in ('.cpp','.hpp','.h')],indent=2)+'\n')
(lib/'validation/integration-final-resume-additions.json').write_text(json.dumps(sorted(products),indent=2)+'\n')
