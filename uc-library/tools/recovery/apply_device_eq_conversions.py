"""Guarded final four-method EQ addition to the device integration batch."""
from pathlib import Path
import argparse,hashlib,json,re,shutil
p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args()
repo=Path.cwd().resolve();lib=repo/'uc-library';out=repo/'evidence/recovery/2026-10-28/device-eq-batch'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
mapfile=lib/'candidates/dsp-eq-type-conversions/CONTROLLED-APPLY.json';assert sha(mapfile)=='1b167d72759b3ed1b5f62b2fe08acb104c77949825e2465ec2f5c4d86f4f94a2'
m=read(mapfile);products={};old={};origins={}
for row in m['products']+[m['fixture']]:
    source=(lib/row['source']).resolve();dest=(lib/row['target']).resolve();pre=row.get('previous_sha256')
    assert source.is_relative_to(lib) and dest.is_relative_to(lib) and not dest.is_symlink() and row['target'] not in products
    assert sha(source)==row['sha256']
    assert not dest.exists() if pre is None else sha(dest)==pre
    products[row['target']]=source.read_bytes();old[row['target']]=pre;origins[row['target']]=row['source']
def once(text,needle,replacement):
    assert text.count(needle)==1,needle
    return text.replace(needle,replacement,1)
groups=(lib/'cmake/ProductionSourceGroups.cmake').read_text()
counts=lambda text:[len(re.search(r'set\(PRESONUS_'+g+r'_SOURCES\n(.*?)\n\)',text,re.S).group(1).split()) for g in ('common','cs18','rm')]
assert counts(groups)==[82,33,10]
groups=once(groups,'set(PRESONUS_rm_SOURCES\n','set(PRESONUS_rm_SOURCES\n  src/mixer_dsp/EQTypeConversions.cpp\n')
cmake=(lib/'CMakeLists.txt').read_text()
cmake=once(cmake,'presonus_build_common_objects()','presonus_build_common_objects()\nset_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/mixer_dsp/EQTypeConversions.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)')
block='''  add_executable(dsp_eq_type_conversions_tests tests/dsp_eq_type_conversions_tests.cpp)
  target_compile_features(dsp_eq_type_conversions_tests PRIVATE cxx_std_17)
  target_link_libraries(dsp_eq_type_conversions_tests PRIVATE presonus_rm_components)
  add_test(NAME dsp_eq_type_conversions COMMAND dsp_eq_type_conversions_tests
    "${CMAKE_CURRENT_SOURCE_DIR}/validation/dsp-eq-type-conversions/fixtures.txt"
    "${CMAKE_CURRENT_SOURCE_DIR}/../temp/test-work/dsp-eq-type-conversions-differences.txt")
'''
cmake=once(cmake,'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)',block+'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)')
for name,text in [('CMakeLists.txt',cmake),('cmake/ProductionSourceGroups.cmake',groups)]:products[name]=text.encode();old[name]=sha(lib/name);origins[name]='Root-reviewed final EQ recipe'
affected={kind:[r for r in read(lib/'validation'/name)['functions'] if 'include/presonus/mixer_dsp/Dsp.hpp' in r['sources']] for kind,name in [('ready','ready-functions.json'),('pending','compiled-functions.json')]}
assert (len(affected['ready']),len(affected['pending']))==(5,5)
print(json.dumps(dict(apply=a.apply,products=len(products),groups=counts(groups),suites=149,headers=92,eq_refresh_ready=5,eq_refresh_pending=5,new_eq_pending=4)))
if not a.apply:raise SystemExit(0)
assert not (out/'application-eq.json').exists()
for name in [*products,'validation/integration.json','validation/integration-linux.json','validation/formatting.json']:
    if (lib/name).exists():
        backup=out/'before-eq'/name;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(lib/name,backup)
(out/'affected-eq-source-closure.json').write_text(json.dumps(affected,indent=2)+'\n')
for name,data in products.items():
    dest=lib/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
(out/'application-eq.json').write_text(json.dumps({'products':{name:dict(previous_sha256=old[name],applied_sha256=sha(lib/name),source=origins[name]) for name in products}},indent=2)+'\n')
cpp=[name for name in products if Path(name).suffix in ('.cpp','.hpp','.h')];paths=read(lib/'validation/format-device-eq-paths.json')
(lib/'validation/format-device-eq-paths.json').write_text(json.dumps(sorted(set(paths+cpp+[origins[name] for name in cpp])),indent=2)+'\n')
paths=read(lib/'validation/integration-device-eq-additions.json')
(lib/'validation/integration-device-eq-additions.json').write_text(json.dumps(sorted(set(paths)|set(products)),indent=2)+'\n')
