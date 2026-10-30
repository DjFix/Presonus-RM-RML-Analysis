"""Prepare one source-bound SPI refresh after VM path migration."""
import ast,hashlib,json,subprocess,sys
from pathlib import Path
repo=Path.cwd().resolve();lib=repo/"uc-library"
old=lib/"candidates/noaa-spi-service-refresh-final-resume"
own=lib/"candidates/noaa-spi-service-refresh-continuation";own.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
allowed={"CMakeLists.txt","cmake/ProductionSourceGroups.cmake"}
snapshot={};union={}
for kind,name,count in (("ready","ready-functions.json",6),("pending","compiled-functions.json",10)):
 p=lib/"validation"/name
 rows=[r for r in read(p)["functions"] if allowed.intersection(r["sources"])]
 assert len(rows)==count
 for r in rows:
  assert sha(lib/r["validation"])==r["validation_sha256"]
  for n,h in r["sources"].items():
   assert n not in union or union[n]==h
   if n not in allowed:assert sha(lib/n)==h,n
   union[n]=h
 snapshot[kind]=rows;snapshot[kind+"_ledger_sha256"]=sha(p)
snapshot.update(source_union=union,c_make_bindings={n:union[n] for n in sorted(allowed)})
(own/"BASELINE.json").write_text(json.dumps(snapshot,indent=2)+"\n")
digest=sha(own/"BASELINE.json");changes={}
for name in ("prepare.py","refresh.py"):
 source=old/name
 text=source.read_text().replace("noaa-spi-service-refresh-final-resume","noaa-spi-service-refresh-continuation").replace("noaa-spi-service-final-resume","noaa-spi-service-continuation").replace("final-resume-root","continuation-root").replace("9451864e6bdbd2a89c425bb158fb484713aecc84beddc609d360b36f66fbcde3",digest)
 ast.parse(text);target=own/name;target.write_text(text)
 changes[name]=dict(source=str(source.relative_to(lib)),source_sha256=sha(source),derivative_sha256=sha(target))
subprocess.run([sys.executable,str(own/"prepare.py"),str(repo)],check=True)
(own/"DERIVATION.json").write_text(json.dumps(dict(baseline_sha256=digest,allowed_rebindings=sorted(allowed),derivatives=changes,reason="Frozen three-candidate application; exact two-CMake source closure refresh"),indent=2)+"\n")
print(json.dumps(dict(ready=6,pending=10,source_bindings=len(union),baseline_sha256=digest)))
