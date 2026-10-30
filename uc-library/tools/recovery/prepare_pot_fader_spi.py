"""Bind the fixed next SPI CMake refresh to the current admitted source closure."""
import ast,hashlib,json,subprocess,sys
from pathlib import Path
repo=Path('/home/rs/projects/opencs/ai-line-analysis');lib=repo/'uc-library'
old=lib/'candidates/noaa-spi-service-refresh-dispatch-transfers-03'
own=lib/'candidates/noaa-spi-service-refresh-pot-fader';own.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
snapshot={};union={};cmake={'CMakeLists.txt','cmake/ProductionSourceGroups.cmake'}
for kind,name,expected in [('ready','ready-functions.json',6),('pending','compiled-functions.json',10)]:
    path=lib/'validation'/name;rows=[r for r in read(path)['functions'] if cmake.intersection(r['sources'])]
    assert len(rows)==expected
    for row in rows:
        assert sha(lib/row['validation'])==row['validation_sha256']
        for n,h in row['sources'].items():
            assert n not in union or union[n]==h
            assert sha(lib/n)==h,n
            union[n]=h
    snapshot[kind]=rows;snapshot[kind+'_ledger_sha256']=sha(path)
snapshot.update(source_union=union,c_make_bindings={n:sha(lib/n) for n in sorted(cmake)})
(own/'BASELINE.json').write_text(json.dumps(snapshot,indent=2)+'\n')
changes={};newsha=sha(own/'BASELINE.json')
for name in ('prepare.py','refresh.py'):
    source=old/name
    text=source.read_text().replace('noaa-spi-service-refresh-dispatch-transfers-03','noaa-spi-service-refresh-pot-fader').replace('noaa-spi-service-dispatch-transfers','noaa-spi-service-pot-fader').replace('dispatch-transfers-root','pot-fader-root').replace('aa6b7fae81f496f7339a49e191dfebbccedf729c6fff06583bd31c73bd15a333',newsha)
    ast.parse(text);target=own/name;target.write_text(text)
    changes[name]=dict(source=str(source.relative_to(lib)),source_sha256=sha(source),derivative_sha256=sha(target),changes='Phase paths and exact current SPI snapshot only; all corrected source/range/native gates retained')
subprocess.run([sys.executable,str(own/'prepare.py'),str(repo)],check=True)
(own/'PHASE-DERIVATIVES.json').write_text(json.dumps(dict(phase='pot-fader-root',baseline_sha256=newsha,derivatives=changes,executed=False),indent=2)+'\n')
print(json.dumps(dict(ready=6,pending=10,source_bindings=len(union),baseline_sha256=newsha)))
