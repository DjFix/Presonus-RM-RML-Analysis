"""Snapshot current six/ten SPI identities and derive the next phase-only replay."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

repo=Path('/home/rs/projects/opencs/ai-line-analysis');lib=repo/"uc-library"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
old=lib/"candidates/noaa-spi-service-refresh-receiver-transfer"
own=lib/"candidates/noaa-spi-service-refresh-dispatch-transfers";own.mkdir(exist_ok=False)
snapshot={};union={};cmake={"CMakeLists.txt","cmake/ProductionSourceGroups.cmake"}
for kind,name,expected in (("ready","ready-functions.json",6),("pending","compiled-functions.json",10)):
    path=lib/"validation"/name;rows=[r for r in read(path)["functions"] if cmake.intersection(r["sources"])]
    assert len(rows)==expected
    for row in rows:
        assert sha(lib/row["validation"])==row["validation_sha256"]
        for n,h in row["sources"].items():
            assert n not in union or union[n]==h
            assert sha(lib/n)==h,n
            union[n]=h
    snapshot[kind]=rows;snapshot[kind+"_ledger_sha256"]=sha(path)
snapshot.update(source_union=union,c_make_bindings={n:sha(lib/n) for n in sorted(cmake)})
(own/"BASELINE.json").write_text(json.dumps(snapshot,indent=2)+"\n")
baseline_sha=sha(own/"BASELINE.json");changes={}
for name in ("prepare.py","refresh.py"):
    source=old/name;text=source.read_text().replace("noaa-spi-service-refresh-receiver-transfer","noaa-spi-service-refresh-dispatch-transfers").replace("receiver-transfer-root","dispatch-transfers-root").replace("773c97f053853f502f96f37f83fca0f01d08d33ff2acb2dd1fdbe24816a7f731",baseline_sha)
    ast.parse(text);target=own/name;target.write_text(text)
    changes[name]=dict(source=str(source.relative_to(lib)),source_sha256=sha(source),derivative_sha256=sha(target),changes="Phase paths and exact new current SPI baseline only; all gates retained")
subprocess.run([sys.executable,str(own/"prepare.py"),str(repo)],check=True)
(own/"PHASE-DERIVATIVES.json").write_text(json.dumps(dict(phase="dispatch-transfers-root",baseline_sha256=baseline_sha,derivatives=changes,executed=False),indent=2)+"\n")
print(json.dumps(dict(spi_ready=6,spi_pending=10,source_bindings=len(union),baseline_sha256=baseline_sha)))
