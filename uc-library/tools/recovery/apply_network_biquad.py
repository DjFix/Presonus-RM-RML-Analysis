"""Guarded disjoint NetworkManager services and Biquad constructor application."""
import argparse,hashlib,json,re,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args()
repo=Path('/home/rs/projects/opencs/ai-line-analysis');lib=repo/'uc-library';phase=repo/'evidence/recovery/2026-10-27/network-biquad-root'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
baseline=read(repo/'temp/recovery-work/checkpoints/2026-10-27-single-pole-closed.json')
for n,h in baseline['inputs'].items():assert sha(lib/n.removeprefix('uc-library/'))==h,n
for n,h in read(lib/'validation/integration.json')['files'].items():assert sha(lib/n)==h,n
net=lib/'candidates/uc-network-manager-services';ctor=lib/'candidates/dsp-biquad-calc'
nm=net/'CONTROLLED-APPLY.json';cm=ctor/'CONSTRUCTOR-CONTROLLED-APPLY.json';handoff=net/'HANDOFF.json'
assert sha(nm)=='91657e249ad363cb355dbf3c6b81c2a06f139c204d0e4875497021350643e21f'
assert sha(cm)=='16038b14c0e1b80d430076c2d5adbe6f3bf49d40988cf7279ac8b415bbf78a10'
assert sha(handoff)=='b745e7c982d2c6272c868cd34f6aa96e7f759f70cfb8d5836c401707bbb0b3ce'
nmap=read(nm);cmap=read(cm);h=read(handoff);products={};origins={};oldhashes={}
def add(source,target,digest):
    source=source.resolve();dest=lib/target
    assert source.is_relative_to(lib) and sha(source)==digest
    assert not Path(target).is_absolute() and '..' not in Path(target).parts and target not in products
    assert not dest.exists() and not dest.is_symlink()
    products[target]=source.read_bytes();origins[target]=str(source.relative_to(lib));oldhashes[target]=None
for row in nmap['products']:add(net/row['source'],row['destination'],row['sha256'])
for row in cmap['products']:add(lib/row['source'],row['target'],row['sha256'])
fixture=cmap['fixture'];add(lib/fixture['source'],fixture['target'],fixture['sha256'])
for test in h['tests']:
    if test['mode']=='stdin':
        for label,row in test['fixtures']['files'].items():
            source=lib/row['path'];assert len(source.read_bytes().splitlines())==test['cases']
            add(source,'validation/uc-network-manager-services/'+test['name']+'/'+label,row['sha256'])
groups=(lib/'cmake/ProductionSourceGroups.cmake').read_text();cmake=(lib/'CMakeLists.txt').read_text()
def once(t,old,new):assert t.count(old)==1,old;return t.replace(old,new,1)
counts=lambda text:[len(re.search(r'set\(PRESONUS_'+g+r'_SOURCES\n(.*?)\n\)',text,re.S).group(1).split()) for g in ('common','cs18','rm')]
assert counts(groups)==[72,25,9]
groups=once(groups,'set(PRESONUS_common_SOURCES\n','set(PRESONUS_common_SOURCES\n  src/Presonus/UC/NetworkManagerServices.cpp\n')
groups=once(groups,'set(PRESONUS_rm_SOURCES\n','set(PRESONUS_rm_SOURCES\n  src/DSP/BiquadCalcConstructor.cpp\n')
groups=once(groups,'set(PRESONUS_PUBLIC_HEADERS\n','set(PRESONUS_PUBLIC_HEADERS\n  presonus/uc/network_manager_services.hpp\n  presonus/dsp/biquad_calc.hpp\n')
cmake=once(cmake,'    presonus/dsp/single_pole.hpp','    presonus/uc/network_manager_services.hpp\n    presonus/dsp/biquad_calc.hpp\n    presonus/dsp/single_pole.hpp')
block=''
for test in h['tests']:
    target=test['name'];block+=f"  add_executable({target} {test['source']})\n  target_link_libraries({target} PRIVATE presonus::uc)\n"
    if test['wraps']:block+=f"  target_link_options({target} PRIVATE "+' '.join('-Wl,--wrap='+name for name in test['wraps'])+")\n"
    if test['mode']=='direct':block+=f"  add_test(NAME {target} COMMAND {target})\n"
    else:block+=f"  add_test(NAME {target} COMMAND ${{Python3_EXECUTABLE}} ${{CMAKE_CURRENT_SOURCE_DIR}}/tools/source_port_replay.py --executable $<TARGET_FILE:{target}> --fixtures ${{CMAKE_CURRENT_SOURCE_DIR}}/validation/uc-network-manager-services/{target}/stdin.txt --expected ${{CMAKE_CURRENT_SOURCE_DIR}}/validation/uc-network-manager-services/{target}/expected.txt --cases {test['cases']})\n"
block+='''  add_executable(dsp_biquad_constructor_tests tests/dsp_biquad_constructor_tests.cpp)
  target_compile_features(dsp_biquad_constructor_tests PRIVATE cxx_std_17)
  target_link_libraries(dsp_biquad_constructor_tests PRIVATE presonus::rm_components)
  add_test(NAME dsp_biquad_constructor COMMAND dsp_biquad_constructor_tests
    "${CMAKE_CURRENT_SOURCE_DIR}/validation/dsp-biquad-constructor/fixtures.txt")
'''
cmake=once(cmake,'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)',block+'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)')
for n,t in [('CMakeLists.txt',cmake),('cmake/ProductionSourceGroups.cmake',groups)]:
    products[n]=t.encode();origins[n]='Root fixed disjoint batch additions';oldhashes[n]=sha(lib/n)
changed={n for n,h in oldhashes.items() if h is not None}
affected={kind:[r for r in read(lib/'validation'/name)['functions'] if changed.intersection(r['sources'])] for kind,name in [('ready','ready-functions.json'),('pending','compiled-functions.json')]}
assert (len(affected['ready']),len(affected['pending']))==(6,10)
print(json.dumps(dict(apply=a.apply,products=len(products),affected_ready=6,affected_pending=10,ready=639,names=343,pending=403,suites=132,groups=counts(groups),headers=87)))
if not a.apply:raise SystemExit(0)
assert not (phase/'application.json').exists();phase.mkdir(parents=True,exist_ok=True)
for n in [*products,'validation/ready-functions.json','validation/compiled-functions.json','validation/integration.json','validation/integration-linux.json','validation/formatting.json','SYMBOLS.md']:
    if (lib/n).exists():
        dest=phase/'before'/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(lib/n,dest)
(phase/'affected-source-closure.json').write_text(json.dumps(affected,indent=2)+'\n')
for n,data in products.items():dest=lib/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
(phase/'application.json').write_text(json.dumps(dict(products={n:dict(previous_sha256=oldhashes[n],applied_sha256=sha(lib/n),source=origins[n]) for n in products},global_ledgers_unchanged=True),indent=2)+'\n')
(lib/'validation/format-network-biquad-paths.json').write_text(json.dumps([n for n in products if Path(n).suffix in ('.cpp','.hpp','.h')],indent=2)+'\n')
(lib/'validation/integration-network-biquad-additions.json').write_text(json.dumps(sorted(products),indent=2)+'\n')
manifest=dict(phase='network-biquad-application',transfers=[dict(direction='push',area='library',paths=sorted(products)+['validation/format-network-biquad-paths.json','validation/integration-network-biquad-additions.json','candidates/noaa-spi-service-refresh-network-biquad']),dict(direction='push',area='evidence',paths=['2026-10-27/network-biquad-root']),dict(direction='push',area='operators',paths=['apply_network_biquad.py','prepare_network_biquad_spi.py','prepare_network_biquad_spi_snapshot.py'])])
(repo/'temp/recovery-work/sync-network-biquad-application.json').write_text(json.dumps(manifest,indent=2)+'\n')
