"""Guarded common formatter/client internal-helper application."""
from pathlib import Path
import argparse,hashlib,json,re,shutil
p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args()
repo=Path.cwd().resolve();lib=repo/'uc-library';out=repo/'evidence/recovery/2026-10-28/additional-strings-batch'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
fp=lib/'candidates/dsp-additional-formatters/CONTROLLED-APPLY.json';sp=lib/'candidates/string-utils/CONTROLLED-APPLY.json'
assert sha(fp)=='4b97eb7eedea555b408915cbbbb73827041ad739ec956f2208907c5a5db7f600'
assert sha(sp)=='e114650a4b8c554bc731d2fccdeaf9cdb80a0d85d24eef8c3449857e2a684e0b'
f=read(fp);s=read(sp);assert read(out/'candidate-preflight-01/validation.json')['passed']
products={};old={};origins={}
for row in f['products']+[f['fixture']]+s['products']:
    source=(lib/row['source']).resolve();dest=(lib/row['target']).resolve()
    assert source.is_relative_to(lib) and dest.is_relative_to(lib) and not dest.exists() and not dest.is_symlink() and row['target'] not in products
    assert sha(source)==row['sha256']
    products[row['target']]=source.read_bytes();old[row['target']]=None;origins[row['target']]=row['source']
def once(text,needle,replacement):
    assert text.count(needle)==1,needle
    return text.replace(needle,replacement,1)
groups=(lib/'cmake/ProductionSourceGroups.cmake').read_text()
counts=lambda t:[len(re.search(r'set\(PRESONUS_'+g+r'_SOURCES\n(.*?)\n\)',t,re.S).group(1).split()) for g in ('common','cs18','rm')]
assert counts(groups)==[89,37,11] and s['production_partition']=='cs18'
for group,names in [('common',f['production_common_cpp']),('cs18',s['production_cpp'])]:
    groups=once(groups,'set(PRESONUS_'+group+'_SOURCES\n','set(PRESONUS_'+group+'_SOURCES\n'+''.join('  '+n+'\n' for n in names))
headers=[n.removeprefix('include/') for n in f['public_headers']+s['public_headers']]
groups=once(groups,'set(PRESONUS_PUBLIC_HEADERS\n','set(PRESONUS_PUBLIC_HEADERS\n'+''.join('  '+n+'\n' for n in headers))
cmake=(lib/'CMakeLists.txt').read_text()
cmake=once(cmake,'set(PRESONUS_UC_PUBLIC_HEADERS\n','set(PRESONUS_UC_PUBLIC_HEADERS\n'+''.join('  '+n+'\n' for n in headers))
properties=[]
for name in f['production_common_cpp']+s['production_cpp']:
    flags=(f['strict_compile_options']+(['-fno-rtti'] if name in f['no_rtti_sources'] else [])) if name in f['production_common_cpp'] else ['-fno-lto']
    properties.append('set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/'+name+'" APPEND PROPERTY COMPILE_OPTIONS '+' '.join(flags)+')')
cmake=once(cmake,'presonus_build_common_objects()','presonus_build_common_objects()\n'+'\n'.join(properties))
block='''  add_executable(dsp_additional_formatters_tests tests/dsp_additional_formatters_tests.cpp)
  target_link_libraries(dsp_additional_formatters_tests PRIVATE presonus_uc)
  target_compile_options(dsp_additional_formatters_tests PRIVATE '''+' '.join(f['strict_compile_options'])+''')
  add_test(NAME dsp_additional_formatters_retained COMMAND dsp_additional_formatters_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/dsp-additional-formatters/fixtures.txt)
  add_executable(string_utils_bridge tests/string_utils_bridge.cpp)
  target_link_libraries(string_utils_bridge PRIVATE presonus::cs18_components)
  target_compile_options(string_utils_bridge PRIVATE -fno-lto)
  add_test(NAME string_utils_retained COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py
    --executable $<TARGET_FILE:string_utils_bridge>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/string-utils/fixtures.stdin
    --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/string-utils/expected.txt --cases 588)
'''
cmake=once(cmake,'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)',block+'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)')
for name,text in [('CMakeLists.txt',cmake),('cmake/ProductionSourceGroups.cmake',groups)]:
    assert (out/'before'/name).read_bytes()==(lib/name).read_bytes()
    products[name]=text.encode();old[name]=sha(lib/name);origins[name]='Root-reviewed common/client partition and both public-header lists'
affected={kind:[r for r in read(lib/'validation'/name)['functions'] if {'CMakeLists.txt','cmake/ProductionSourceGroups.cmake'}.intersection(r['sources'])] for kind,name in [('ready','ready-functions.json'),('pending','compiled-functions.json')]}
assert (len(affected['ready']),len(affected['pending']))==(6,10)
print(json.dumps(dict(apply=a.apply,products=len(products),groups=counts(groups),suites=160,headers=100,affected_ready=6,affected_pending=10)))
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
paths=read(lib/'validation/format-additional-strings-candidates.json')+[n for n in products if Path(n).suffix in ('.cpp','.hpp','.h')]
(lib/'validation/format-additional-strings-paths.json').write_text(json.dumps(sorted(set(paths)),indent=2)+'\n')
(lib/'validation/integration-additional-strings-additions.json').write_text(json.dumps(sorted(products),indent=2)+'\n')
