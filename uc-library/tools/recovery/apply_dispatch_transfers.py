"""Guarded two-candidate application; retains source identities and build partitions."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

p=argparse.ArgumentParser(description=__doc__);p.add_argument("--apply",action="store_true");a=p.parse_args()
repo=Path('/home/rs/projects/opencs/ai-line-analysis');lib=repo/"uc-library"
phase=repo/"evidence/recovery/2026-10-27/dispatch-transfers-root"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
baseline=read(repo/"temp/recovery-work/checkpoints/2026-10-27-receiver-transfer.json")
for n,h in baseline["inputs"].items():assert sha(lib/n.removeprefix("uc-library/"))==h,n
for n,h in read(lib/"validation/integration.json")["files"].items():assert sha(lib/n)==h,n
switch=lib/"candidates/panel-switch-dispatch";manager=lib/"candidates/uc-transfer-manager-transfers"
sfile=switch/"validation/seal-01/CONTROLLED-APPLY.json";mfile=manager/"CONTROLLED-APPLY.json"
assert sha(sfile)=="c69434680fadd6ca2ce7725862c4f30dfc3670334d58e82824df22e672d375c9"
assert sha(mfile)=="0c4bbb8de966dab0d85f509b3701723158d6d58c76de5662a6df2749bb258d77"
smap=read(sfile);mmap=read(mfile);handoff=read(manager/"HANDOFF.json")
assert sha(manager/"HANDOFF.json")=="840fb5d893041489602c721c53c616715ff905df8606e7263e56a37a86cb93ef"
assert sha(switch/"validation/seal-01/validation.json")=="da58b0ac8493702d2f3ad79e80d13c8a417829f7d5ca62e1b1d1133aac998670"
products={};oldhashes={};origins={}
def add(source,target,digest,old=None):
    source=source.resolve();dest=lib/target
    assert source.is_relative_to(lib) and sha(source)==digest
    assert target not in products and not dest.is_symlink() and ".." not in Path(target).parts
    assert not dest.exists() if old is None else sha(dest)==old
    products[target]=source.read_bytes();oldhashes[target]=old;origins[target]=str(source.relative_to(lib))
for row in smap["products"]:add(lib/row["source"],row["target"],row["sha256"],row["previous_sha256"])
for row in mmap["products"]:add(manager/row["source"],row["destination"],row["sha256"],row.get("required_destination_sha256"))
fixture=lib/smap["fixture"];add(fixture,"validation/panel-switch-dispatch/fixtures.jsonl",smap["fixture_sha256"])
meta=read(fixture.parent/"validation.json");assert meta["passed"] and meta["cases"]==44512 and meta["fixture_sha256"]==sha(fixture)
add(fixture.parent/"validation.json","validation/panel-switch-dispatch/validation.json",sha(fixture.parent/"validation.json"))
for test in handoff["tests"]:
    for field,label in (("stdin","stdin.txt"),("expected","expected.txt")):
        source=manager/test[field];assert len(source.read_bytes().splitlines())==test["cases"]
        add(source,"validation/uc-transfer-manager-transfers/"+test["target"]+"/"+label,sha(source))
changed={n for n,h in oldhashes.items() if h is not None}|{"CMakeLists.txt","cmake/ProductionSourceGroups.cmake"}
affected={kind:[r for r in read(lib/"validation"/name)["functions"] if changed.intersection(r["sources"])] for kind,name in (("ready","ready-functions.json"),("pending","compiled-functions.json"))}
assert (len(affected["ready"]),len(affected["pending"]))==(16,40)
groups=(lib/"cmake/ProductionSourceGroups.cmake").read_text();cmake=(lib/"CMakeLists.txt").read_text()
def once(text,old,new):assert text.count(old)==1,old;return text.replace(old,new,1)
counts=lambda text:[len(re.search(r"set\(PRESONUS_"+g+r"_SOURCES\n(.*?)\n\)",text,re.S).group(1).split()) for g in ("common","cs18","rm")]
assert counts(groups)==[67,25,8]
units=smap["common_cpp"]+["src/Presonus/UC/FileTransferManagerTransfers.cpp"]
groups=once(groups,"set(PRESONUS_common_SOURCES\n","set(PRESONUS_common_SOURCES\n"+"".join("  "+n+"\n" for n in units))
assert counts(groups)==[70,25,8]
block='''  # dispatch-transfers-root: same original methods, explicit per-image rate profile.
  add_executable(panel_switch_dispatch_bridge tests/panel_switch_dispatch_bridge.cpp)
  target_link_libraries(panel_switch_dispatch_bridge PRIVATE presonus::uc)
  target_compile_options(panel_switch_dispatch_bridge PRIVATE -fno-lto)
  target_link_options(panel_switch_dispatch_bridge PRIVATE -fno-lto
'''+''.join('    -Wl,--wrap='+n+'\n' for n in smap['wraps'])+'''  )
  add_test(NAME panel_switch_dispatch_retained COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/panel_switch_dispatch_replay.py --binary $<TARGET_FILE:panel_switch_dispatch_bridge>
    --fixture ${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-switch-dispatch/fixtures.jsonl
    --out-root ${PRESONUS_REPOSITORY_ROOT}/temp/recovery-work/switch-dispatch-ctest)
'''
for test in handoff["tests"]:
    target=test["target"]
    block+=f"  add_executable({target} tests/{test['source']})\n  target_link_libraries({target} PRIVATE {test['link']})\n"
    block+=f"  target_link_options({target} PRIVATE "+" ".join("-Wl,--wrap="+n for n in test["wraps"])+")\n"
    block+=f"  add_test(NAME {target} COMMAND ${{Python3_EXECUTABLE}} ${{CMAKE_CURRENT_SOURCE_DIR}}/tools/source_port_replay.py --executable $<TARGET_FILE:{target}> --fixtures ${{CMAKE_CURRENT_SOURCE_DIR}}/validation/uc-transfer-manager-transfers/{target}/stdin.txt --expected ${{CMAKE_CURRENT_SOURCE_DIR}}/validation/uc-transfer-manager-transfers/{target}/expected.txt --cases {test['cases']})\n"
marker="  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)";cmake=once(cmake,marker,block+marker)
for name,data in (("CMakeLists.txt",cmake),("cmake/ProductionSourceGroups.cmake",groups)):
    products[name]=data.encode();oldhashes[name]=sha(lib/name);origins[name]="Fixed phase build additions, prior lists preserved"
print(json.dumps(dict(apply=a.apply,products=len(products),cpp_paths=sum(Path(n).suffix in (".cpp",".hpp",".h") for n in products),affected_ready=16,affected_pending=40,ready_expected=622,names_expected=334,pending_expected=378,suites=124,production_cpp=103,groups=counts(groups),headers=83)))
if not a.apply:raise SystemExit(0)
assert not (phase/"application.json").exists() and not (phase/"before").exists();phase.mkdir(parents=True,exist_ok=True)
for name in [*products,"validation/ready-functions.json","validation/compiled-functions.json","validation/integration.json","validation/integration-linux.json","validation/formatting.json","SYMBOLS.md"]:
    if(lib/name).exists():
        target=phase/"before"/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(lib/name,target)
(phase/"affected-source-closure.json").write_text(json.dumps(affected,indent=2)+"\n")
for name,data in products.items():target=lib/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
(phase/"application.json").write_text(json.dumps(dict(products={n:dict(previous_sha256=oldhashes[n],applied_sha256=sha(lib/n),source=origins[n]) for n in products},global_ledgers_unchanged=True),indent=2)+"\n")
(lib/"validation/format-dispatch-transfers-paths.json").write_text(json.dumps([n for n in products if Path(n).suffix in (".cpp",".hpp",".h")],indent=2)+"\n")
(lib/"validation/integration-dispatch-transfers-additions.json").write_text(json.dumps(sorted(products),indent=2)+"\n")
manifest=dict(phase="dispatch-transfers-application",transfers=[dict(direction="push",area="library",paths=sorted(products)+["validation/format-dispatch-transfers-paths.json","validation/integration-dispatch-transfers-additions.json","candidates/noaa-spi-service-refresh-dispatch-transfers"]),dict(direction="push",area="evidence",paths=["2026-10-27/dispatch-transfers-root"]),dict(direction="push",area="operators",paths=["apply_dispatch_transfers.py","prepare_dispatch_transfers_spi.py"])])
(repo/"temp/recovery-work/sync-dispatch-transfers-application.json").write_text(json.dumps(manifest,indent=2)+"\n")
