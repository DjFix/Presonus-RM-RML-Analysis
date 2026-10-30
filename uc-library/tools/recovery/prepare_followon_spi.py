"""Snapshot the admitted SPI source closure for the next bounded batch."""
import ast,hashlib,json,subprocess,sys
from pathlib import Path

repo=Path.cwd().resolve();lib=repo/'uc-library'
out=repo/'evidence/recovery/2026-10-28/followon-batch';out.mkdir(exist_ok=False)
old=lib/'candidates/noaa-spi-service-refresh-continuation'
own=lib/'candidates/noaa-spi-service-refresh-followon';own.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();read=lambda p:json.loads(p.read_text())
snapshot={};union={};allowed={'CMakeLists.txt','cmake/ProductionSourceGroups.cmake'}
for kind,name,count in [('ready','ready-functions.json',6),('pending','compiled-functions.json',10)]:
    path=lib/'validation'/name
    rows=[r for r in read(path)['functions'] if allowed.intersection(r['sources'])]
    assert len(rows)==count
    for row in rows:
        assert sha(lib/row['validation'])==row['validation_sha256']
        for name,digest in row['sources'].items():
            assert name not in union or union[name]==digest
            assert sha(lib/name)==digest,name
            union[name]=digest
    snapshot[kind]=rows;snapshot[kind+'_ledger_sha256']=sha(path)
snapshot.update(source_union=union,c_make_bindings={n:union[n] for n in sorted(allowed)})
(own/'BASELINE.json').write_text(json.dumps(snapshot,indent=2)+'\n');digest=sha(own/'BASELINE.json')
previous_digest=sha(old/'BASELINE.json');derivatives={}
for name in ['prepare.py','refresh.py']:
    source=old/name
    text=source.read_text().replace('noaa-spi-service-refresh-continuation','noaa-spi-service-refresh-followon').replace('noaa-spi-service-continuation','noaa-spi-service-followon').replace('continuation-root','followon-root').replace(previous_digest,digest)
    ast.parse(text);target=own/name;target.write_text(text)
    derivatives[name]=dict(source=str(source.relative_to(lib)),source_sha256=sha(source),derivative_sha256=sha(target))
subprocess.run([sys.executable,str(own/'prepare.py'),str(repo)],check=True)
(own/'DERIVATION.json').write_text(json.dumps(dict(baseline_sha256=digest,derivatives=derivatives,allowed_rebindings=sorted(allowed)),indent=2)+'\n')
for name in ['CMakeLists.txt','cmake/ProductionSourceGroups.cmake','validation/ready-functions.json','validation/compiled-functions.json','validation/integration.json','validation/integration-linux.json','validation/formatting.json','SYMBOLS.md']:
    backup=out/'before'/name;backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes((lib/name).read_bytes())
print(json.dumps(dict(snapshot_sha256=digest,ready=6,pending=10,source_bindings=len(union))))
