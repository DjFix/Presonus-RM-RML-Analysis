"""Apply exactly three sealed candidates; root alone owns build and ledgers."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

p=argparse.ArgumentParser(description=__doc__);p.add_argument("--apply",action="store_true");a=p.parse_args()
repo=Path('/home/rs/projects/opencs/ai-line-analysis');lib=repo/"uc-library"
phase=repo/"evidence/recovery/2026-10-27/receiver-transfer-root"
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
baseline=read(repo/"temp/recovery-work/checkpoints/2026-10-27-spi-avb-helpers.json")
for name,h in baseline["inputs"].items():assert sha(lib/name.removeprefix("uc-library/"))==h,name
for name,h in read(lib/"validation/integration.json")["files"].items():assert sha(lib/name)==h,name
def checked(relative,digest):
    path=(lib/relative).resolve();assert path.is_relative_to(lib) and path.is_file() and sha(path)==digest,relative
    return path
receiver=lib/"candidates/noaa-sysex-receiver"
manager=lib/"candidates/uc-transfer-service-bindings"
switch=lib/"candidates/panel-switch-control"
rmap=read(checked("candidates/noaa-sysex-receiver/CONTROLLED-APPLY.json","95a71a50aba19d33015903edbedd64fe0a40e1c51554ef9663f916f8866b51dd"))
mmap=read(checked("candidates/uc-transfer-service-bindings/CONTROLLED-APPLY.json","b3722f0ec41d20cd8d0195dd53513b738dfd1ab2b437e6791f2410c1175ebc3f"))
smap=read(checked("candidates/panel-switch-control/validation/seal-01/CONTROLLED-APPLY.json","edb85e32db01cda9b0439f28e306f08f48fca3b7dd01a0b68d56d7f740850792"))
assert sha(receiver/rmap["candidate_proof"]["path"])==rmap["candidate_proof"]["sha256"]
checked(smap["proof"],smap["proof_sha256"])
checked("candidates/uc-transfer-service-bindings/validation/native-02/manager-pending-validation.json",mmap["manager_proof_sha256"])
for n,h in rmap["spi_required_active_products"].items():checked(n,h)
products={};preimages={};origins={}
def add(source,target,digest,previous=None):
    source=source.resolve();destination=lib/target
    assert source.is_relative_to(lib) and source.is_file() and sha(source)==digest
    assert target not in products and not Path(target).is_absolute() and ".." not in Path(target).parts
    assert not destination.is_symlink()
    assert (not destination.exists()) if previous is None else (destination.is_file() and sha(destination)==previous),target
    products[target]=source.read_bytes();preimages[target]=previous;origins[target]=str(source.relative_to(lib))
for source,row in rmap["copies"].items():add(receiver/source,row["target"],row["sha256"],row["preimage_sha256"])
for source,row in rmap["fixtures"].items():add(receiver/source,row["target"],row["sha256"])
for row in mmap["products"]:add(manager/row["source"],row["destination"],row["sha256"],row.get("required_destination_sha256"))
for row in smap["products"]:add(lib/row["source"],row["target"],row["sha256"],row["previous_sha256"])
for name,target in (("fixtures.stdin","validation/uc-transfer-manager/fixtures.stdin"),("arm-output.txt","validation/uc-transfer-manager/arm-output.txt")):
    source=manager/"validation/native-02"/name
    assert len(source.read_bytes().splitlines())==6016
    add(source,target,sha(source))
add(lib/smap["fixture"],"validation/panel-switch-control/fixtures.jsonl",smap["fixture_sha256"])
changed={n for n,h in preimages.items() if h is not None}|{"CMakeLists.txt","cmake/ProductionSourceGroups.cmake"}
ledgers={kind:read(lib/"validation"/name)["functions"] for kind,name in (("ready","ready-functions.json"),("pending","compiled-functions.json"))}
affected={kind:[r for r in rows if changed.intersection(r["sources"])] for kind,rows in ledgers.items()}
assert (len(ledgers["ready"]),len(ledgers["pending"]),len(affected["ready"]),len(affected["pending"]))==(610,326,31,22)
groups=(lib/"cmake/ProductionSourceGroups.cmake").read_text();cmake=(lib/"CMakeLists.txt").read_text()
def once(text,old,new):assert text.count(old)==1,old;return text.replace(old,new,1)
count=lambda text,group:len(re.search(r"set\(PRESONUS_"+group+r"_SOURCES\n(.*?)\n\)",text,re.S).group(1).split())
assert [count(groups,g) for g in ("common","cs18","rm")]==[64,25,7]
groups=once(groups,"set(PRESONUS_common_SOURCES\n","set(PRESONUS_common_SOURCES\n  src/Presonus/UC/FileTransferManager.cpp\n  src/Presonus/Panel/SwitchControl.cpp\n  src/portable/panel/SwitchParameterGateway.cpp\n")
groups=once(groups,"set(PRESONUS_rm_SOURCES\n","set(PRESONUS_rm_SOURCES\n  src/Presonus/NOAA/SysexReceiver.cpp\n")
headers="  presonus/uc/file_transfer_manager.hpp\n  presonus/panel/switch_control.hpp\n"
groups=once(groups,"set(PRESONUS_PUBLIC_HEADERS\n","set(PRESONUS_PUBLIC_HEADERS\n"+headers)
cmake=once(cmake,"  list(APPEND PRESONUS_UC_PUBLIC_HEADERS\n","  list(APPEND PRESONUS_UC_PUBLIC_HEADERS\n    presonus/uc/file_transfer_manager.hpp\n    presonus/panel/switch_control.hpp\n")
assert [count(groups,g) for g in ("common","cs18","rm")]==[67,25,8]
assert len(re.search(r"set\(PRESONUS_PUBLIC_HEADERS\n(.*?)\n\)",groups,re.S).group(1).split())==83
ctest=rmap["ctest"];target=ctest["target"]
block=f"  # receiver-transfer-root: three source-preserving application candidates.\n  add_executable({target} {' '.join(ctest['sources'])})\n  target_link_libraries({target} PRIVATE {ctest['link_target']})\n  target_compile_options({target} PRIVATE {' '.join(ctest['test_only_compile_options'])})\n  target_link_options({target} PRIVATE {' '.join(ctest['link_options'])})\n  add_test(NAME {target} COMMAND {target} ${{CMAKE_CURRENT_SOURCE_DIR}}/{ctest['arguments'][0]})\n"
block+='''  add_executable(uc_file_transfer_manager_bridge tests/uc_file_transfer_manager_bridge.cpp)
  target_link_libraries(uc_file_transfer_manager_bridge PRIVATE presonus::uc)
  target_link_options(uc_file_transfer_manager_bridge PRIVATE -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME uc_transfer_manager_retained COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py --executable $<TARGET_FILE:uc_file_transfer_manager_bridge>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-transfer-manager/fixtures.stdin
    --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-transfer-manager/arm-output.txt --cases 6016)
  add_test(NAME uc_transfer_manager_provider COMMAND uc_file_transfer_manager_bridge --provider-smoke)
  add_executable(panel_switch_control_bridge tests/panel_switch_control_bridge.cpp tests/panel_switch_control_virtual_entry.cpp)
  target_link_libraries(panel_switch_control_bridge PRIVATE presonus::uc)
  target_compile_options(panel_switch_control_bridge PRIVATE -fno-lto)
  target_link_options(panel_switch_control_bridge PRIVATE -fno-lto
'''+''.join('    -Wl,--wrap='+name+'\n' for name in smap['wraps'])+'''  )
  add_test(NAME panel_switch_control_retained COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/panel_switch_control_replay.py --binary $<TARGET_FILE:panel_switch_control_bridge>
    --fixture ${CMAKE_CURRENT_SOURCE_DIR}/validation/panel-switch-control/fixtures.jsonl
    --out-root ${PRESONUS_REPOSITORY_ROOT}/temp/recovery-work/switch-control-ctest)
  add_test(NAME panel_switch_control_provider COMMAND panel_switch_control_bridge --smoke)
'''
marker="  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)"
cmake=once(cmake,marker,block+marker)
for name,data in (("CMakeLists.txt",cmake),("cmake/ProductionSourceGroups.cmake",groups)):
    products[name]=data.encode();preimages[name]=sha(lib/name);origins[name]="Guarded fixed-phase additions; prior content preserved"
print(json.dumps(dict(apply=a.apply,products=len(products),affected_ready=31,affected_pending=22,expected_ready=622,expected_mangles=334,expected_pending=358,expected_suites=121,cpp=100,groups=dict(common=67,cs18=25,rm=8),headers=83)))
if not a.apply:raise SystemExit(0)
assert not (phase/"application.json").exists() and not (phase/"before").exists()
phase.mkdir(parents=True,exist_ok=True)
for name in [*products,"validation/ready-functions.json","validation/compiled-functions.json","validation/integration.json","validation/integration-linux.json","validation/formatting.json","SYMBOLS.md"]:
    if(lib/name).exists():
        dest=phase/"before"/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(lib/name,dest)
(phase/"affected-source-closure.json").write_text(json.dumps(affected,indent=2)+"\n")
journal={}
for name,data in products.items():
    dest=lib/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    journal[name]=dict(previous_sha256=preimages[name],applied_sha256=sha(dest),source=origins[name])
(phase/"application.json").write_text(json.dumps(dict(products=journal,global_ledgers_unchanged=True),indent=2)+"\n")
cpp=[n for n in products if Path(n).suffix in (".cpp",".hpp",".h")]
(lib/"validation/format-receiver-transfer-paths.json").write_text(json.dumps(cpp,indent=2)+"\n")
(lib/"validation/integration-receiver-transfer-additions.json").write_text(json.dumps(sorted(products),indent=2)+"\n")
manifest=dict(phase="receiver-transfer-application",transfers=[dict(direction="push",area="library",paths=sorted(products)+["validation/format-receiver-transfer-paths.json","validation/integration-receiver-transfer-additions.json"]),dict(direction="push",area="evidence",paths=["2026-10-27/receiver-transfer-root"]),dict(direction="push",area="operators",paths=["apply_receiver_transfer.py"])])
(repo/"temp/recovery-work/sync-receiver-transfer-application.json").write_text(json.dumps(manifest,indent=2)+"\n")
