"""Freeze SPI/CMake closure for Fader/typed event values/NOAA routes integration."""
from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json,subprocess,sys
repo=Path.cwd().resolve();lib=repo/'uc-library';out=repo/'evidence/recovery/2026-10-28/basic-activity-batch';out.mkdir(exist_ok=False)
old=lib/'candidates/noaa-spi-service-refresh-mixer-leaves-programmer';own=lib/'candidates/noaa-spi-service-refresh-basic-activity';own.mkdir(exist_ok=False)
read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
snapshot={};union={};allowed={'CMakeLists.txt','cmake/ProductionSourceGroups.cmake'}
for kind,name,count in [('ready','ready-functions.json',6),('pending','compiled-functions.json',10)]:
    path=lib/'validation'/name;rows=[r for r in read(path)['functions'] if allowed.intersection(r['sources'])];assert len(rows)==count
    for row in rows:
        assert sha(lib/row['validation'])==row['validation_sha256']
        for name,digest in row['sources'].items():
            assert name not in union or union[name]==digest
            assert sha(lib/name)==digest,name
            union[name]=digest
    snapshot[kind]=rows;snapshot[kind+'_ledger_sha256']=sha(path)
snapshot.update(source_union=union,c_make_bindings={name:union[name] for name in sorted(allowed)})
(own/'BASELINE.json').write_text(json.dumps(snapshot,indent=2)+'\n');digest=sha(own/'BASELINE.json')
previous=sha(old/'BASELINE.json');derivatives={}
for name in ['prepare.py','refresh.py']:
    source=old/name;text=source.read_text().replace('noaa-spi-service-refresh-mixer-leaves-programmer','noaa-spi-service-refresh-basic-activity').replace('noaa-spi-service-mixer-leaves-programmer','noaa-spi-service-basic-activity').replace('mixer-leaves-programmer-root','basic-activity-root').replace(previous,digest)
    if name=='refresh.py':
        text=text.replace("scratch=repo/'temp/recovery-work/noaa-spi-fader-queue-router-02-tmp'","scratch=repo/'temp/recovery-work'/('noaa-spi-'+phase+'-tmp')")
    ast.parse(text);target=own/name;target.write_text(text)
    derivatives[name]=dict(source=str(source.relative_to(lib)),source_sha256=sha(source),derivative_sha256=sha(target))
subprocess.run([sys.executable,str(own/'prepare.py'),str(repo)],check=True)
(own/'DERIVATION.json').write_text(json.dumps(dict(baseline_sha256=digest,derivatives=derivatives,allowed_rebindings=sorted(allowed)),indent=2)+'\n')
for name in ['CMakeLists.txt','cmake/ProductionSourceGroups.cmake','validation/ready-functions.json','validation/compiled-functions.json','validation/integration.json','validation/integration-linux.json','validation/formatting.json','SYMBOLS.md']:
    target=out/'before'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((lib/name).read_bytes())
event=dict(event='root-review-start',at=datetime.now(timezone.utc).isoformat(),ready=917,ready_names=511,pending=857,candidates=['uc-basic-connection-lifecycle'])
(out/'queue-events.jsonl').write_text(json.dumps(event)+'\n')
print(json.dumps(dict(snapshot_sha256=digest,ready=6,pending=10,source_bindings=len(union))))
