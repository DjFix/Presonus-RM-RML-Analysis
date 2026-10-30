"""Retain old NOAA source dependencies while binding fresh SPI to root objects."""
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

assert sys.platform.startswith("linux")
repo=Path.cwd().resolve();lib=repo/"uc-library";build=repo/"temp/core-upstream/root-integration-01"
phase=repo/"evidence/recovery/2026-10-27/spi-avb-helpers-root"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
snapshot=read(phase/"affected-source-closure.json")
assert (len(snapshot["ready"]),len(snapshot["pending"]))==(1,4)
allowed={"CMakeLists.txt","cmake/ProductionSourceGroups.cmake","include/presonus/noaa/spi_packets.hpp"}
old={n:h for rows in snapshot.values() for row in rows for n,h in row["sources"].items()}
changed={n:dict(previous=h,current=sha(lib/n)) for n,h in old.items() if sha(lib/n)!=h}
assert set(changed)==allowed
integration=read(lib/"validation/integration.json");assert integration["ctest_passed"] and integration["test_suites"]==116
for n,h in integration["files"].items():assert sha(lib/n)==h,n
source=lib/"validation/noaa-spi-service";out=source/"root-closure-01";out.mkdir(exist_ok=False)
sources={n:sha(lib/n) for n in old}
for proofname in ("validation.json","pending-validation.json"):
    proof=read(source/proofname)
    assert proof["source_mode"]=="active" and proof["cpp_differential_passed"]
    for n,h in proof["sources"].items():assert sha(lib/n)==h,n
    sources.update(proof["sources"])
formatting=read(lib/"validation/formatting.json")
for n,h in sources.items():
    if Path(n).suffix in (".cpp",".hpp",".h"):assert formatting["files"].get(n)==h,n
objects={};native_names=set()
commands=read(build/"compile_commands.json")
for relative in ("src/Presonus/NOAA/TCardSPIService.cpp","src/Presonus/NOAA/TCardSPIPackets.cpp","src/Presonus/NOAA/SysexPacketConstruction.cpp"):
    rows=[r for r in commands if Path(r["file"]).resolve()==lib/relative];assert len(rows)==1
    argv=rows[0].get("arguments") or shlex.split(rows[0]["command"])
    obj=Path(argv[argv.index("-o")+1]);obj=obj if obj.is_absolute() else Path(rows[0]["directory"])/obj
    assert obj.is_file() and obj.is_relative_to(build)
    text=subprocess.check_output(["nm","--defined-only",str(obj)],text=True)
    (out/(obj.name+".nm.log")).write_text(text)
    native_names.update(line.split()[-1] for line in text.splitlines() if line.split())
    objects[relative]=dict(compile_entry=rows[0],object=str(obj.relative_to(repo)),sha256=sha(obj))
archive=build/"libpresonus_rm_components.a"
members=subprocess.check_output(["ar","t",str(archive)],text=True).splitlines()
assert all(members.count(Path(row["object"]).name)==1 for row in objects.values())
archive_names=subprocess.check_output(["nm","--defined-only",str(archive)],text=True)
(out/"rm-archive-nm.log").write_text(archive_names)
archive_names={line.split()[-1] for line in archive_names.splitlines() if line.split()}
for kind,filename in (("ready","validation.json"),("pending","pending-validation.json")):
    proof=read(source/filename)
    assert {r["mangled"] for r in proof["functions"]}<=native_names&archive_names
    proof.update(sources=sources,preserved_previous_source_closure=True,previous_source_count=len(old),explicit_source_rebindings=changed,root_objects=objects,root_rm_archive_sha256=sha(archive),canonical_integration_sha256=sha(lib/"validation/integration.json"),root_producer_sha256=sha(Path(__file__)))
    newproof=out/filename;newproof.write_text(json.dumps(proof,indent=2)+"\n")
    rows=read(source/(kind+"-functions.fragment.json"))["functions"]
    rows=[dict(r,sources=sources,validation=str(newproof.relative_to(lib)),validation_sha256=sha(newproof)) for r in rows]
    (out/(kind+"-functions.fragment.json")).write_text(json.dumps(dict(functions=rows),indent=2)+"\n")
shutil.copytree(out,phase/"spi-root-closure-01")
print(json.dumps(dict(ready=6,pending=10,preserved_previous_source_count=len(old),source_count=len(sources),explicit_rebindings=sorted(changed))))
