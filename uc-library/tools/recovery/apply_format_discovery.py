"""Guarded combined application of frozen common formatter/discovery sources."""
from pathlib import Path
import argparse,hashlib,json,re,shutil
p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args()
repo=Path.cwd().resolve();lib=repo/'uc-library';out=repo/'evidence/recovery/2026-10-28/formatter-discovery-batch'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
formatter=lib/'candidates/dsp-value-formatters';discovery=lib/'candidates/uc-network-discovery-services'
assert sha(formatter/'CONTROLLED-APPLY.json')=='fb4aff6b54c8ed47711fb3e5e4deeaa672c305f1e0db3e74bc47d90804b9e27f'
assert sha(discovery/'CONTROLLED-APPLY.json')=='6ddb56d7c82f73b810e95629d80c030d98a6e98f0750db17967b2d96c7374547'
f=read(formatter/'CONTROLLED-APPLY.json');d=read(discovery/'CONTROLLED-APPLY.json')
assert read(out/'candidate-preflight-01/validation.json')['passed']
products={};old={};origins={}
def add(source,target,digest):
    source=source.resolve();dest=(lib/target).resolve()
    assert source.is_relative_to(lib) and dest.is_relative_to(lib) and not dest.exists() and not dest.is_symlink() and target not in products
    assert sha(source)==digest
    products[target]=source.read_bytes();old[target]=None;origins[target]=str(source.relative_to(lib))
for row in f['products']+[f['fixture']]:add(lib/row['source'],row['target'],row['sha256'])
for row in d['products']:
    assert row['require_absent'] and row['required_destination_sha256'] is None
    add(discovery/row['source'],row['destination'],row['sha256'])
def once(text,needle,replacement):
    assert text.count(needle)==1,needle
    return text.replace(needle,replacement,1)
groups=(lib/'cmake/ProductionSourceGroups.cmake').read_text()
counts=lambda t:[len(re.search(r'set\(PRESONUS_'+g+r'_SOURCES\n(.*?)\n\)',t,re.S).group(1).split()) for g in ('common','cs18','rm')]
assert counts(groups)==[86,37,11]
cpp=f['production_common_cpp']+d['production_cpp'];headers=[n.removeprefix('include/') for n in f['public_headers']+d['public_headers']]
groups=once(groups,'set(PRESONUS_common_SOURCES\n','set(PRESONUS_common_SOURCES\n'+''.join('  '+n+'\n' for n in cpp))
groups=once(groups,'set(PRESONUS_PUBLIC_HEADERS\n','set(PRESONUS_PUBLIC_HEADERS\n'+''.join('  '+n+'\n' for n in headers))
cmake=(lib/'CMakeLists.txt').read_text()
cmake=once(cmake,'set(PRESONUS_UC_PUBLIC_HEADERS\n','set(PRESONUS_UC_PUBLIC_HEADERS\n'+''.join('  '+n+'\n' for n in headers))
properties=[]
for name in cpp:
    flags=(f['strict_compile_options']+(['-fno-rtti'] if name in f['no_rtti_sources'] else [])) if name in f['production_common_cpp'] else ['-fno-lto']
    properties.append('set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/'+name+'" APPEND PROPERTY COMPILE_OPTIONS '+' '.join(flags)+')')
cmake=once(cmake,'presonus_build_common_objects()','presonus_build_common_objects()\n'+'\n'.join(properties))
block=discovery/d['cmake_test_block'];assert sha(block)==d['cmake_test_block_sha256']
testblock='''  add_executable(dsp_formatters_tests tests/dsp_formatters_tests.cpp)
  target_link_libraries(dsp_formatters_tests PRIVATE presonus_uc)
  target_compile_options(dsp_formatters_tests PRIVATE '''+' '.join(f['strict_compile_options'])+''')
  add_test(NAME dsp_formatters_retained COMMAND dsp_formatters_tests
    ${CMAKE_CURRENT_SOURCE_DIR}/validation/dsp-formatters/fixtures.txt)
'''+block.read_text()
cmake=once(cmake,'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)',testblock+'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)')
for name,text in [('CMakeLists.txt',cmake),('cmake/ProductionSourceGroups.cmake',groups)]:
    assert (out/'before'/name).read_bytes()==(lib/name).read_bytes()
    products[name]=text.encode();old[name]=sha(lib/name);origins[name]='Root-reviewed combined common source recipe; both header/install lists'
affected={kind:[r for r in read(lib/'validation'/name)['functions'] if {'CMakeLists.txt','cmake/ProductionSourceGroups.cmake'}.intersection(r['sources'])] for kind,name in [('ready','ready-functions.json'),('pending','compiled-functions.json')]}
assert (len(affected['ready']),len(affected['pending']))==(6,10)
print(json.dumps(dict(apply=a.apply,products=len(products),groups=counts(groups),suites=158,headers=98,affected_ready=6,affected_pending=10)))
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
paths=read(lib/'validation/format-format-discovery-candidates.json')+[n for n in products if Path(n).suffix in ('.cpp','.hpp','.h')]
(lib/'validation/format-format-discovery-paths.json').write_text(json.dumps(sorted(set(paths)),indent=2)+'\n')
(lib/'validation/integration-format-discovery-additions.json').write_text(json.dumps(sorted(products),indent=2)+'\n')
