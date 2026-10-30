"""Guarded SPI application; AVB shares existing production code unchanged."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

p=argparse.ArgumentParser(description=__doc__);p.add_argument("--apply",action="store_true");a=p.parse_args()
repo=Path('/home/rs/projects/opencs/ai-line-analysis');lib=repo/"uc-library"
phase=repo/"evidence/recovery/2026-10-27/spi-avb-helpers-root"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
baseline=read(repo/"temp/recovery-work/checkpoints/2026-10-27-led-server-control.json")
for name,digest in baseline["inputs"].items():assert sha(lib/name.removeprefix("uc-library/"))==digest,name
for name,digest in read(lib/"validation/integration.json")["files"].items():assert sha(lib/name)==digest,name
own=lib/"candidates/noaa-spi-service-core";controlfile=own/"CONTROLLED-APPLY.json"
assert sha(controlfile)=="781508c28abb8b9cda91a1b53ce6aaa9fb5049ac443f4d8d3dc945d1b6e0ad15"
control=read(controlfile)
for name,digest in control["frozen_proofs"].items():assert sha(own/name)==digest,name
for name,digest in control["unchanged_dependencies"].items():assert sha(lib/name)==digest,name
assert sha(own/"verify.py")==control["active_reseal_sha256"]
products={}
for name,row in control["copies"].items():
    assert sha(own/name)==row["sha256"],name
    target=lib/row["target"]
    assert not target.exists() if row["active_sha256"] is None else sha(target)==row["active_sha256"]
    products[row["target"]]=(own/name).read_bytes()
for name,target in control["fixture_copies"].items():
    assert not(lib/target).exists();products[target]=(own/name).read_bytes()
header="include/presonus/noaa/spi_packets.hpp"
ready=read(lib/"validation/ready-functions.json")["functions"]
pending=read(lib/"validation/compiled-functions.json")["functions"]
affected={kind:[r for r in rows if any(n in r["sources"] for n in (header,"CMakeLists.txt","cmake/ProductionSourceGroups.cmake"))] for kind,rows in (("ready",ready),("pending",pending))}
assert (len(affected["ready"]),len(affected["pending"]))==(1,4)
assert (len(ready),len(pending))==(603,320)
groups=(lib/"cmake/ProductionSourceGroups.cmake").read_text()
assert "src/Presonus/NOAA/TCardSPIService.cpp" not in groups
groups=groups.replace("set(PRESONUS_rm_SOURCES\n","set(PRESONUS_rm_SOURCES\n  src/Presonus/NOAA/TCardSPIService.cpp\n",1)
groups=groups.replace("set(PRESONUS_PUBLIC_HEADERS\n","set(PRESONUS_PUBLIC_HEADERS\n  presonus/noaa/spi_service.hpp\n",1)
cmake=(lib/"CMakeLists.txt").read_text()
assert "noaa_spi_service_operations" not in cmake
cmake=cmake.replace("  list(APPEND PRESONUS_UC_PUBLIC_HEADERS\n","  list(APPEND PRESONUS_UC_PUBLIC_HEADERS\n    presonus/noaa/spi_service.hpp\n",1)
block="  # spi-avb-helpers-root: real RM SPI application closure.\n"
for test in control["tests"]:
    name=test["name"]
    block+=f"  add_executable({name} {' '.join(test['sources'])})\n"
    block+=f"  target_link_libraries({name} PRIVATE presonus::rm_components)\n"
    block+=f"  target_compile_options({name} PRIVATE {' '.join(test['compile_options'])})\n"
    block+=f"  target_link_options({name} PRIVATE {' '.join(test['link_options'])})\n"
    if "driver" in test:
        block+=f"  add_test(NAME {name} COMMAND ${{Python3_EXECUTABLE}} ${{CMAKE_CURRENT_SOURCE_DIR}}/{test['driver']} $<TARGET_FILE:{name}> ${{CMAKE_CURRENT_SOURCE_DIR}}/{test['driver_arguments'][1]})\n"
    else:
        block+=f"  add_test(NAME {name} COMMAND {name} ${{CMAKE_CURRENT_SOURCE_DIR}}/{test['arguments'][0]})\n"
marker="  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)"
assert cmake.count(marker)==1;cmake=cmake.replace(marker,block+marker,1)
products["CMakeLists.txt"]=cmake.encode();products["cmake/ProductionSourceGroups.cmake"]=groups.encode()
print(json.dumps(dict(apply=a.apply,products=len(products),affected_ready=1,affected_pending=4,expected_cpp=96,groups=dict(common=64,cs18=25,rm=7),expected_headers=81,expected_suites=116,new_ready_spi=5,new_pending_spi=6,avb_separate_current_source_proof_required=True)))
if not a.apply:raise SystemExit(0)
phase.mkdir(parents=True,exist_ok=False)
before={}
for name in [*products,"validation/ready-functions.json","validation/compiled-functions.json","validation/integration.json","validation/integration-linux.json","validation/formatting.json","SYMBOLS.md"]:
    source=lib/name
    if source.exists():
        destination=phase/"before"/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination);before[name]=sha(source)
(phase/"affected-source-closure.json").write_text(json.dumps(affected,indent=2)+"\n")
journal={}
for name,data in products.items():
    target=lib/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    journal[name]=dict(previous_sha256=before.get(name),sha256=sha(target))
(phase/"application.json").write_text(json.dumps(dict(products=journal,controlled_apply_sha256=sha(controlfile),ledgers_unchanged=True),indent=2)+"\n")
cpp=[n for n in products if Path(n).suffix in (".cpp",".hpp",".h")]
(lib/"validation/format-spi-avb-helpers-paths.json").write_text(json.dumps(cpp,indent=2)+"\n")
(lib/"validation/integration-spi-avb-helpers-additions.json").write_text(json.dumps(sorted(products),indent=2)+"\n")
manifest=dict(phase="spi-avb-helpers-application",transfers=[dict(direction="push",area="library",paths=sorted(products)+["validation/format-spi-avb-helpers-paths.json","validation/integration-spi-avb-helpers-additions.json"]),dict(direction="push",area="evidence",paths=["2026-10-27/spi-avb-helpers-root"]),dict(direction="push",area="operators",paths=["apply_spi_avb_helpers.py"])])
(repo/"temp/recovery-work/sync-spi-avb-helpers-application.json").write_text(json.dumps(manifest,indent=2)+"\n")
