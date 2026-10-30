"""Add the frozen Biquad completion packet to the continuation integration."""
from pathlib import Path
import argparse, hashlib, json, re, shutil

p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args()
repo=Path.cwd().resolve();lib=repo/'uc-library';out=repo/'evidence/recovery/2026-10-28/continuation-batch'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
mapfile=lib/'candidates/dsp-biquad-incremental/CONTROLLED-APPLY.json'
assert sha(mapfile)=='8ad842ecac8c90a82b93b5be4b1ad9a950e9c45de894ef7c59340cc7529c680a'
m=read(mapfile);products={};previous={};origins={}
for row in m['products']+[m['fixture']]:
    source=(lib/row['source']).resolve();name=row['target'];dest=lib/name;old=row.get('previous_sha256')
    assert source.is_relative_to(lib) and sha(source)==row['sha256']
    assert dest.resolve().is_relative_to(lib) and not dest.is_symlink() and name not in products
    assert not dest.exists() if old is None else sha(dest)==old
    products[name]=source.read_bytes();previous[name]=old;origins[name]=row['source']
def once(text,needle,replacement):
    assert text.count(needle)==1,needle
    return text.replace(needle,replacement,1)
groups=(lib/'cmake/ProductionSourceGroups.cmake').read_text()
count=lambda text:[len(re.search(r'set\(PRESONUS_'+g+r'_SOURCES\n(.*?)\n\)',text,re.S).group(1).split()) for g in ('common','cs18','rm')]
assert count(groups)==[77,28,10]
groups=once(groups,'set(PRESONUS_common_SOURCES\n','set(PRESONUS_common_SOURCES\n'+''.join('  '+s+'\n' for s in m['production_common_cpp']))
cmake=(lib/'CMakeLists.txt').read_text()
old='set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/src/DSP/BiquadMethods.cpp" APPEND PROPERTY COMPILE_OPTIONS -fno-lto -fno-fast-math -ffp-contract=off -frounding-math -fno-builtin)'
new='set_property(SOURCE '+ ' '.join('"${CMAKE_CURRENT_SOURCE_DIR}/'+s+'"' for s in m['strict_sources'])+' APPEND PROPERTY COMPILE_OPTIONS '+' '.join(m['strict_compile_options'])+')'
cmake=once(cmake,old,new)
block='''  add_executable(dsp_biquad_incremental_tests tests/dsp_biquad_incremental_tests.cpp)
  target_compile_features(dsp_biquad_incremental_tests PRIVATE cxx_std_17)
  target_link_libraries(dsp_biquad_incremental_tests PRIVATE presonus::uc)
  add_test(NAME dsp_biquad_incremental COMMAND dsp_biquad_incremental_tests
    "${CMAKE_CURRENT_SOURCE_DIR}/validation/dsp-biquad-incremental/fixtures.txt"
    "${CMAKE_CURRENT_SOURCE_DIR}/../temp/test-work/dsp-biquad-incremental-differences.txt")
'''
cmake=once(cmake,'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)',block+'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)')
for name,text in [('CMakeLists.txt',cmake),('cmake/ProductionSourceGroups.cmake',groups)]:
    products[name]=text.encode();previous[name]=sha(lib/name);origins[name]='Root-reviewed Biquad recipe'
print(json.dumps(dict(apply=a.apply,products=len(products),groups=count(groups),suites=139,headers=89)))
if not a.apply:raise SystemExit(0)
assert not (out/'application-biquad.json').exists()
for name in [*products,'validation/integration.json','validation/integration-linux.json','validation/formatting.json']:
    if (lib/name).exists():
        backup=out/'before-biquad'/name;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(lib/name,backup)
affected={kind:[r for r in read(lib/'validation'/filename)['functions'] if 'src/DSP/BiquadMethods.cpp' in r['sources']] for kind,filename in [('ready','ready-functions.json'),('pending','compiled-functions.json')]}
assert (len(affected['ready']),len(affected['pending']))==(0,4)
(out/'affected-biquad-source-closure.json').write_text(json.dumps(affected,indent=2)+'\n')
for name,data in products.items():
    dest=lib/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
(out/'application-biquad.json').write_text(json.dumps({'products':{n:dict(previous_sha256=previous[n],applied_sha256=sha(lib/n),source=origins[n]) for n in products}},indent=2)+'\n')
paths=read(lib/'validation/format-continuation-paths.json')
paths += [n for n in products if Path(n).suffix in ('.cpp','.hpp','.h')]
paths += [origins[n] for n in products if Path(n).suffix in ('.cpp','.hpp','.h')]
(lib/'validation/format-continuation-paths.json').write_text(json.dumps(sorted(set(paths)),indent=2)+'\n')
paths=read(lib/'validation/integration-continuation-additions.json')
(lib/'validation/integration-continuation-additions.json').write_text(json.dumps(sorted(set(paths)|set(products)),indent=2)+'\n')
