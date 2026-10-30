"""Freeze current SPI proofs before the reviewed CMake/group changes."""
from pathlib import Path
import hashlib,json,ast,subprocess,sys
r=Path.cwd();lib=r/'uc-library';out=r/'evidence/recovery/2026-10-29/factory-callbacks-hierarchy-batch';own=lib/'candidates/noaa-spi-service-refresh-factory-callbacks-hierarchy';old=lib/'candidates/noaa-spi-service-refresh-basic-activity';own.mkdir(exist_ok=False);read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();allowed={'CMakeLists.txt','cmake/ProductionSourceGroups.cmake'};snapshot={};union={}
for kind,file,count in [('ready','ready-functions.json',6),('pending','compiled-functions.json',10)]:
 rows=[x for x in read(lib/'validation'/file)['functions'] if allowed.intersection(x['sources'])];assert len(rows)==count
 for x in rows:
  assert sha(lib/x['validation'])==x['validation_sha256']
  for n,h in x['sources'].items():assert sha(lib/n)==h;assert n not in union or union[n]==h;union[n]=h
 snapshot[kind]=rows;snapshot[kind+'_ledger_sha256']=sha(lib/'validation'/file)
snapshot.update(source_union=union,c_make_bindings={n:union[n] for n in sorted(allowed)});(own/'BASELINE.json').write_text(json.dumps(snapshot,indent=2)+'\n');previous=sha(old/'BASELINE.json');digest=sha(own/'BASELINE.json');derivatives={}
for name in ['prepare.py','refresh.py']:
 source=old/name;text=source.read_text().replace('noaa-spi-service-refresh-basic-activity','noaa-spi-service-refresh-factory-callbacks-hierarchy').replace('noaa-spi-service-basic-activity','noaa-spi-service-factory-callbacks-hierarchy').replace('basic-activity-root','factory-callbacks-hierarchy-root').replace(previous,digest);ast.parse(text);p=own/name;p.write_text(text);derivatives[name]=dict(source=str(source.relative_to(lib)),source_sha256=sha(source),derivative_sha256=sha(p))
v=subprocess.run([sys.executable,str(own/'prepare.py'),str(r)],capture_output=True,text=True);(out/'spi-prepare.stdout').write_text(v.stdout);(out/'spi-prepare.stderr').write_text(v.stderr);assert v.returncode==0,v.stderr;(own/'DERIVATION.json').write_text(json.dumps(dict(baseline_sha256=digest,derivatives=derivatives,allowed_rebindings=sorted(allowed)),indent=2)+'\n');print(json.dumps(dict(passed=True,ready=6,pending=10,baseline_sha256=digest)))
