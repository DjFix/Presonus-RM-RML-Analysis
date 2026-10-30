"""Apply the frozen common Network adapter packet with explicit guards."""
from pathlib import Path
import argparse, hashlib, json, re, shutil
p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args()
repo=Path.cwd().resolve();lib=repo/'uc-library';own=lib/'candidates/uc-network-adapter-services';out=repo/'evidence/recovery/2026-10-28/adapter-batch'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
assert sha(own/'CONTROLLED-APPLY.json')=='f0a6c3d8ee23d2d9e1b70f71436646c9e9527f9042878d7edb80194e171f4cd2'
m=read(own/'CONTROLLED-APPLY.json');products={};old={};origins={}
for row in m['products']:
    source=(own/row['source']).resolve();dest=(lib/row['destination']).resolve()
    assert source.is_relative_to(own) and dest.is_relative_to(lib) and not dest.exists() and not dest.is_symlink()
    assert row['require_absent'] and row['required_destination_sha256'] is None and sha(source)==row['sha256']
    products[row['destination']]=source.read_bytes();old[row['destination']]=None;origins[row['destination']]=str(source.relative_to(lib))
def once(text,needle,replacement):
    assert text.count(needle)==1,needle
    return text.replace(needle,replacement,1)
groups=(lib/'cmake/ProductionSourceGroups.cmake').read_text()
counts=lambda t:[len(re.search(r'set\(PRESONUS_'+g+r'_SOURCES\n(.*?)\n\)',t,re.S).group(1).split()) for g in ('common','cs18','rm')]
assert counts(groups)==[85,37,11] and m['production_partition']=='common'
groups=once(groups,'set(PRESONUS_common_SOURCES\n','set(PRESONUS_common_SOURCES\n'+''.join('  '+n+'\n' for n in m['production_cpp']))
headers=[n.removeprefix('include/') for n in m['public_headers']]
groups=once(groups,'set(PRESONUS_PUBLIC_HEADERS\n','set(PRESONUS_PUBLIC_HEADERS\n'+''.join('  '+n+'\n' for n in headers))
cmake=(lib/'CMakeLists.txt').read_text()
cmake=once(cmake,'set(PRESONUS_UC_PUBLIC_HEADERS\n','set(PRESONUS_UC_PUBLIC_HEADERS\n'+''.join('  '+n+'\n' for n in headers))
properties='\n'.join('set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/'+n+'" APPEND PROPERTY COMPILE_OPTIONS -fno-lto)' for n in m['production_cpp'])
cmake=once(cmake,'presonus_build_common_objects()','presonus_build_common_objects()\n'+properties)
block=own/m['cmake_test_block'];assert sha(block)==m['cmake_test_block_sha256']
cmake=once(cmake,'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)',block.read_text()+'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)')
for name,text in [('CMakeLists.txt',cmake),('cmake/ProductionSourceGroups.cmake',groups)]:
    assert (out/'before'/name).read_bytes()==(lib/name).read_bytes()
    products[name]=text.encode();old[name]=sha(lib/name);origins[name]='Root-reviewed common adapter recipe; both explicit public-header lists'
affected={kind:[r for r in read(lib/'validation'/name)['functions'] if {'CMakeLists.txt','cmake/ProductionSourceGroups.cmake'}.intersection(r['sources'])] for kind,name in [('ready','ready-functions.json'),('pending','compiled-functions.json')]}
assert (len(affected['ready']),len(affected['pending']))==(6,10)
print(json.dumps(dict(apply=a.apply,products=len(products),groups=counts(groups),suites=156,headers=96,affected_ready=6,affected_pending=10)))
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
paths=read(own/'validation/seal-01/format-paths.json')+[n for n in products if Path(n).suffix in ('.cpp','.hpp','.h')]
(lib/'validation/format-adapter-paths.json').write_text(json.dumps(sorted(set(paths)),indent=2)+'\n')
(lib/'validation/integration-adapter-additions.json').write_text(json.dumps(sorted(products),indent=2)+'\n')
