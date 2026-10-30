"""Guarded common multicast and disjoint formatter bool-lifecycle application."""
from pathlib import Path
import argparse,hashlib,json,re,shutil
p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args()
repo=Path.cwd().resolve();lib=repo/'uc-library';out=repo/'evidence/recovery/2026-10-28/multicast-lifecycle-batch'
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
own=lib/'candidates/uc-network-multicast-sockets';fp=lib/'candidates/dsp-formatter-option-lifecycle/CONTROLLED-APPLY.json'
assert sha(own/'CONTROLLED-APPLY.json')=='a38e509ba84fbc408776535f78e3fea4b7d236f7ca90946f88a10fd20133ee81'
assert sha(fp)=='fd89b817fb5d7acac38a504fa9265d0089b1209fd2e9aee2aed53241897c0127'
m=read(own/'CONTROLLED-APPLY.json');f=read(fp);assert read(out/'candidate-preflight-01/validation.json')['passed']
products={};old={};origins={}
def add(source,target,digest,pre):
    source=source.resolve();dest=(lib/target).resolve()
    assert source.is_relative_to(lib) and dest.is_relative_to(lib) and not dest.is_symlink() and target not in products
    assert sha(source)==digest
    assert not dest.exists() if pre is None else sha(dest)==pre
    products[target]=source.read_bytes();old[target]=pre;origins[target]=str(source.relative_to(lib))
for row in m['products']:
    assert row['require_absent'] and row['required_destination_sha256'] is None
    add(own/row['source'],row['destination'],row['sha256'],None)
for row in f['products']:add(lib/row['source'],row['target'],row['sha256'],row['previous_sha256'])
assert sha(lib/f['retained_fixture']['target'])==f['retained_fixture']['sha256']
def once(text,needle,replacement):
    assert text.count(needle)==1,needle
    return text.replace(needle,replacement,1)
groups=(lib/'cmake/ProductionSourceGroups.cmake').read_text()
counts=lambda t:[len(re.search(r'set\(PRESONUS_'+g+r'_SOURCES\n(.*?)\n\)',t,re.S).group(1).split()) for g in ('common','cs18','rm')]
assert counts(groups)==[90,42,11]
groups=once(groups,'set(PRESONUS_common_SOURCES\n','set(PRESONUS_common_SOURCES\n'+''.join('  '+n+'\n' for n in m['production_cpp']))
headers=[n.removeprefix('include/') for n in m['public_headers']]
groups=once(groups,'set(PRESONUS_PUBLIC_HEADERS\n','set(PRESONUS_PUBLIC_HEADERS\n'+''.join('  '+n+'\n' for n in headers))
cmake=(lib/'CMakeLists.txt').read_text()
cmake=once(cmake,'set(PRESONUS_UC_PUBLIC_HEADERS\n','set(PRESONUS_UC_PUBLIC_HEADERS\n'+''.join('  '+n+'\n' for n in headers))
props='\n'.join('set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/'+n+'" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)' for n in m['production_cpp'])
cmake=once(cmake,'presonus_build_common_objects()','presonus_build_common_objects()\n'+props)
block=own/m['cmake_test_block'];assert sha(block)==m['cmake_test_block_sha256']
testblock=block.read_text()+'''  add_executable(dsp_formatter_option_lifecycle_tests tests/dsp_formatter_option_lifecycle_tests.cpp)
  target_link_libraries(dsp_formatter_option_lifecycle_tests PRIVATE presonus_uc)
  target_compile_options(dsp_formatter_option_lifecycle_tests PRIVATE '''+' '.join(f['test_compile_options'])+''')
  target_link_options(dsp_formatter_option_lifecycle_tests PRIVATE '''+' '.join(f['test_link_options'])+''')
  add_test(NAME dsp_formatter_option_lifecycle_tests COMMAND dsp_formatter_option_lifecycle_tests)
'''
cmake=once(cmake,'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)',testblock+'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)')
for name,text in [('CMakeLists.txt',cmake),('cmake/ProductionSourceGroups.cmake',groups)]:
    assert (out/'before'/name).read_bytes()==(lib/name).read_bytes()
    products[name]=text.encode();old[name]=sha(lib/name);origins[name]='Root-reviewed common multicast/lifecycle recipe; both header lists'
changed={n for n,h in old.items() if h is not None and hashlib.sha256(products[n]).hexdigest()!=h}
affected={kind:[r for r in read(lib/'validation'/name)['functions'] if changed.intersection(r['sources'])] for kind,name in [('ready','ready-functions.json'),('pending','compiled-functions.json')]}
assert (len(affected['ready']),len(affected['pending']))==(22,30),(len(affected['ready']),len(affected['pending']))
print(json.dumps(dict(apply=a.apply,products=len(products),groups=counts(groups),suites=165,headers=103,affected_ready=22,affected_pending=30)))
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
paths=read(lib/'validation/format-multicast-lifecycle-candidates.json')+[n for n in products if Path(n).suffix in ('.cpp','.hpp','.h')]
(lib/'validation/format-multicast-lifecycle-paths.json').write_text(json.dumps(sorted(set(paths)),indent=2)+'\n')
(lib/'validation/integration-multicast-lifecycle-additions.json').write_text(json.dumps(sorted(products),indent=2)+'\n')
