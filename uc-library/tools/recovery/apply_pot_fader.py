"""Guarded fixed Pot/Fader application; root owns shared build files."""
import argparse, hashlib, json, re, shutil
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');a=p.parse_args()
repo=Path('/home/rs/projects/opencs/ai-line-analysis');lib=repo/'uc-library'
phase=repo/'evidence/recovery/2026-10-27/pot-fader-root'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
baseline=read(repo/'temp/recovery-work/checkpoints/2026-10-27-dispatch-transfers.json')
for n,h in baseline['inputs'].items():assert sha(lib/n.removeprefix('uc-library/'))==h,n
for n,h in read(lib/'validation/integration.json')['files'].items():assert sha(lib/n)==h,n
mapping=lib/'candidates/panel-fader-control/validation/seal-01/CONTROLLED-APPLY.json'
assert sha(mapping)=='540feb6ea3f66232afa490af113cc805e52ea90332bfea261de08e9c0c7ab709'
m=read(mapping);assert sha(lib/m['proof'])==m['proof_sha256']
products={};origins={}
def add(source,target,digest):
    assert sha(source)==digest and not (lib/target).exists() and target not in products
    assert '..' not in Path(target).parts
    products[target]=source.read_bytes();origins[target]=str(source.relative_to(lib))
for row in m['products']:add(lib/row['source'],row['target'],row['sha256'])
fixture=lib/m['fixture'];add(fixture,'validation/panel-pot-fader/fixtures.jsonl',m['fixture_sha256'])
meta=read(fixture.parent/'validation.json')
assert meta['passed'] and meta['cases']==28960
add(fixture.parent/'validation.json','validation/panel-pot-fader/validation.json',sha(fixture.parent/'validation.json'))
cmake=(lib/'CMakeLists.txt').read_text();groups=(lib/'cmake/ProductionSourceGroups.cmake').read_text()
def once(t,old,new):assert t.count(old)==1,old;return t.replace(old,new,1)
counts=lambda text:[len(re.search(r'set\(PRESONUS_'+g+r'_SOURCES\n(.*?)\n\)',text,re.S).group(1).split()) for g in ('common','cs18','rm')]
assert counts(groups)==[70,25,8]
groups=once(groups,'set(PRESONUS_common_SOURCES\n','set(PRESONUS_common_SOURCES\n'+''.join('  '+n+'\n' for n in m['common_cpp']))
groups=once(groups,'set(PRESONUS_PUBLIC_HEADERS\n','set(PRESONUS_PUBLIC_HEADERS\n  presonus/panel/pot_fader_control.hpp\n')
cmake=once(cmake,'    presonus/panel/switch_control.hpp','    presonus/panel/pot_fader_control.hpp\n    presonus/panel/switch_control.hpp')
block='''  add_executable(panel_pot_fader_bridge tests/panel_pot_fader_bridge.cpp tests/panel_pot_fader_virtual_entry.cpp)
  target_link_libraries(panel_pot_fader_bridge PRIVATE presonus::uc)
  target_compile_options(panel_pot_fader_bridge PRIVATE -fno-lto)
  target_link_options(panel_pot_fader_bridge PRIVATE -fno-lto
'''+''.join('    -Wl,--wrap='+n+'\n' for n in m['wraps'])+'''  )
  add_test(NAME panel_pot_fader_retained COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/panel_pot_fader_replay.py --binary $<TARGET_FILE:panel_pot_fader_bridge>
    --fixture ${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-pot-fader/fixtures.jsonl
    --out-root ${PRESONUS_REPOSITORY_ROOT}/temp/recovery-work/pot-fader-ctest)
  add_test(NAME panel_pot_fader_provider COMMAND panel_pot_fader_bridge --smoke)
'''
cmake=once(cmake,'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)',block+'  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)')
for n,t in [('CMakeLists.txt',cmake),('cmake/ProductionSourceGroups.cmake',groups)]:products[n]=t.encode();origins[n]='Root fixed CMake additions'
changed={'CMakeLists.txt','cmake/ProductionSourceGroups.cmake'}
affected={kind:[r for r in read(lib/'validation'/name)['functions'] if changed.intersection(r['sources'])] for kind,name in [('ready','ready-functions.json'),('pending','compiled-functions.json')]}
assert (len(affected['ready']),len(affected['pending']))==(6,10)
print(json.dumps(dict(apply=a.apply,products=len(products),affected_ready=6,affected_pending=10,expected_ready=638,expected_names=342,expected_pending=392,suites=126,groups=counts(groups),public_headers=84)))
if not a.apply:raise SystemExit(0)
assert not (phase/'application.json').exists();phase.mkdir(parents=True,exist_ok=True)
for n in [*products,'validation/ready-functions.json','validation/compiled-functions.json','validation/integration.json','validation/integration-linux.json','validation/formatting.json','SYMBOLS.md']:
    if (lib/n).exists():
        dest=phase/'before'/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(lib/n,dest)
(phase/'affected-source-closure.json').write_text(json.dumps(affected,indent=2)+'\n')
rows={}
for n,data in products.items():
    dest=lib/n;old=sha(dest) if dest.exists() else None;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    rows[n]=dict(previous_sha256=old,applied_sha256=sha(dest),source=origins[n])
(phase/'application.json').write_text(json.dumps(dict(products=rows,global_ledgers_unchanged=True),indent=2)+'\n')
paths=[n for n in products if Path(n).suffix in ('.cpp','.hpp','.h')]
(lib/'validation/format-pot-fader-paths.json').write_text(json.dumps(paths,indent=2)+'\n')
(lib/'validation/integration-pot-fader-additions.json').write_text(json.dumps(sorted(products),indent=2)+'\n')
manifest=dict(phase='pot-fader-application',transfers=[dict(direction='push',area='library',paths=sorted(products)+['validation/format-pot-fader-paths.json','validation/integration-pot-fader-additions.json','candidates/noaa-spi-service-refresh-pot-fader']),dict(direction='push',area='evidence',paths=['2026-10-27/pot-fader-root']),dict(direction='push',area='operators',paths=['apply_pot_fader.py','prepare_pot_fader_spi.py'])])
(repo/'temp/recovery-work/sync-pot-fader-application.json').write_text(json.dumps(manifest,indent=2)+'\n')
