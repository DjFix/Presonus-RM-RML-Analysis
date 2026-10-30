"""Guarded SinglePole sources and reviewed packaging postimages; no admission."""
import argparse,hashlib,json,re,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--packaging-map',type=Path,required=True);p.add_argument('--packaging-sha256',required=True);p.add_argument('--apply',action='store_true');a=p.parse_args()
repo=Path('/home/rs/projects/opencs/ai-line-analysis');lib=repo/'uc-library';phase=repo/'evidence/recovery/2026-10-27/single-pole-root'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
baseline=read(repo/'temp/recovery-work/checkpoints/2026-10-27-pot-fader.json')
for n,h in baseline['inputs'].items():assert sha(lib/n.removeprefix('uc-library/'))==h,n
for n,h in read(lib/'validation/integration.json')['files'].items():assert sha(lib/n)==h,n
own=lib/'candidates/dsp-single-pole';mapping=own/'CONTROLLED-APPLY.json'
assert sha(mapping)=='29efe6c504656ea697ca7a3b38c5bb2732d0f694aa7f5418eaca85257f200174'
mapdata=read(mapping);products={};origins={};previous={}
def add(source,target,digest,old=None):
    source=source.resolve();dest=lib/target
    assert source.is_relative_to(lib) and sha(source)==digest
    assert not Path(target).is_absolute() and '..' not in Path(target).parts and target not in products
    assert not dest.is_symlink()
    assert not dest.exists() if old is None else sha(dest)==old
    products[target]=source.read_bytes();origins[target]=str(source.relative_to(lib));previous[target]=old
for source,row in mapdata['copies'].items():add(own/source,row['target'],row['sha256'],row['preimage_sha256'])
fixture=mapdata['fixture'];add(own/fixture['source'],fixture['target'],fixture['sha256'])
package=a.packaging_map.resolve();assert package.is_relative_to(lib) and sha(package)==a.packaging_sha256
rows=read(package)['products']
assert {r['target'] for r in rows}=={'CMakeLists.txt','cmake/ProductionSourceGroups.cmake','cmake/presonus_ucConfig.cmake.in'}
for row in rows:
    old=row.get('required_preimage_sha256',row.get('previous_sha256'))
    assert old is not None
    add(lib/row['source'],row['target'],row['sha256'],old)
groups=products['cmake/ProductionSourceGroups.cmake'].decode()
counts=[len(re.search(r'set\(PRESONUS_'+g+r'_SOURCES\n(.*?)\n\)',groups,re.S).group(1).split()) for g in ('common','cs18','rm')]
assert counts==[72,25,9] and groups.count('src/DSP/SinglePole.cpp')==1
changed={n for n,h in previous.items() if h is not None}
affected={kind:[r for r in read(lib/'validation'/name)['functions'] if changed.intersection(r['sources'])] for kind,name in [('ready','ready-functions.json'),('pending','compiled-functions.json')]}
assert (len(affected['ready']),len(affected['pending']))==(6,10)
print(json.dumps(dict(apply=a.apply,products=len(products),affected_ready=6,affected_pending=10,expected_ready=638,expected_names=342,expected_pending=393,suites=127,groups=counts,headers=85)))
if not a.apply:raise SystemExit(0)
assert not (phase/'application.json').exists();phase.mkdir(exist_ok=True)
for n in [*products,'validation/ready-functions.json','validation/compiled-functions.json','validation/integration.json','validation/integration-linux.json','validation/formatting.json','SYMBOLS.md']:
    if (lib/n).exists():
        dest=phase/'before'/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(lib/n,dest)
(phase/'affected-source-closure.json').write_text(json.dumps(affected,indent=2)+'\n')
for n,data in products.items():
    dest=lib/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
(phase/'application.json').write_text(json.dumps(dict(products={n:dict(previous_sha256=previous[n],applied_sha256=sha(lib/n),source=origins[n]) for n in products},global_ledgers_unchanged=True,packaging_map=str(package.relative_to(lib)),packaging_sha256=sha(package)),indent=2)+'\n')
(lib/'validation/format-single-pole-paths.json').write_text(json.dumps([n for n in products if Path(n).suffix in ('.cpp','.hpp','.h')],indent=2)+'\n')
(lib/'validation/integration-single-pole-additions.json').write_text(json.dumps(sorted(products),indent=2)+'\n')
manifest=dict(phase='single-pole-application',transfers=[dict(direction='push',area='library',paths=sorted(products)+['validation/format-single-pole-paths.json','validation/integration-single-pole-additions.json','candidates/noaa-spi-service-refresh-single-pole']),dict(direction='push',area='evidence',paths=['2026-10-27/single-pole-root']),dict(direction='push',area='operators',paths=['apply_single_pole.py','prepare_single_pole_spi.py','prepare_single_pole_spi_snapshot.py'])])
(repo/'temp/recovery-work/sync-single-pole-application.json').write_text(json.dumps(manifest,indent=2)+'\n')
