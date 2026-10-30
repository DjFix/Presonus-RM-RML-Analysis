"""Guarded FileTransfer plus dependency-ordered panel source application."""
import gzip
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path('/home/rs/projects/opencs/ai-line-analysis')
LIB = ROOT/"uc-library"
PHASE = ROOT/"evidence/recovery/2026-10-27/file-transfer-panel-root"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
baseline = json.loads((ROOT/"temp/recovery-work/checkpoints/2026-10-27-efm-parameters-input-pin.json").read_text())
for name, digest in baseline["inputs"].items():
    assert sha(LIB/name.removeprefix("uc-library/")) == digest, name
own = LIB/"candidates/uc-file-transfer-state"
control = json.loads((own/"CONTROLLED-APPLY.json").read_text())
assert (control["ready_proposal"], control["pending_proposal"]) == (8,2)
assert sha(own/"validation/preflight-01/validation.json") == control["candidate_merger_preflight_sha256"] == "7415a501bf65c30fddbf510abd56e49a7a790763cabb2dc98f29bf587379e8f5"
assert sha(own/"validation/mirror-audit.json") == control["mirror_audit_sha256"]
for name, expected in [("lifecycle-ready-validation.json", "c8d5d53956aa16e82c4f9fc0861fd9634ccb9ba4da7f22084f47fa1e793b6309"), ("ordinary-pending-validation.json", "57b5298a6319d4897ddd3ffb06d7d45e29fcf35e4a89c08b05f20403e9e4af88")]:
    path = own/"validation/native-01"/name
    assert sha(path) == expected
    proof = json.loads(path.read_text())
    for name,digest in proof["sources"].items(): assert sha(LIB/name) == digest, name
    for name,digest in proof["repository_sources"].items(): assert sha(ROOT/name) == digest, name

panel = LIB/"candidates/efm-panel-updater"
loop = LIB/"candidates/efm-panel-update-loop"
assert sha(panel/"HANDOFF.json") == "f3795a624bca25851a9cd3e8668c257024064e365518a599378fee72f3e18ee1"
assert sha(loop/"HANDOFF.json") == "d389c2352521618aa9c8e0737c0882ba98d21e9ffac2e6ab1115813b4293f90b"
for directory,key in [(panel,"source_files"),(loop,"sources")]:
    for name,digest in json.loads((directory/"HANDOFF.json").read_text())[key].items(): assert sha(LIB/name) == digest,name
for name,digest in json.loads((loop/"HANDOFF.json").read_text())["frozen_helper_sources"].items(): assert sha(LIB/name) == digest,name

products = [(own/row["source"],row["destination"]) for row in control["products"]]
for row in control["products"]:
    assert row["required_destination"] == "absent" and sha(own/row["source"]) == row["sha256"]
products += [
    (panel/"PanelProtocol.cpp", "src/embedded_panel/PanelProtocol.cpp"),
    (panel/"include/presonus/mcu/panel_protocol.hpp", "include/presonus/mcu/panel_protocol.hpp"),
    (panel/"bridge.cpp", "tests/panel_protocol_port_bridge.cpp"),
    (loop/"UpdateLoop.cpp", "src/embedded_panel/UpdateLoop.cpp"),
    (loop/"include/presonus/mcu/update_loop.hpp", "include/presonus/mcu/update_loop.hpp"),
    (loop/"bridge.cpp", "tests/panel_update_loop_bridge.cpp"),
    (own/"validation/native-01/fixtures.stdin", "validation/uc-file-transfer-state/fixtures.stdin"),
    (own/"validation/native-01/arm-output.txt", "validation/uc-file-transfer-state/arm-output.txt"),
    (ROOT/"evidence/recovery/2026-10-27/efm32-faders/panel_surface_code.bin", "validation/embedded-panel/panel_surface_code.bin"),
]
assert sha(products[-1][0]) == "afa9c18621f8fb7327c343e5b8ffd7bc727b335831434bc9b671e0d3172524b7"
for source,target in products: assert source.is_file() and not (LIB/target).exists(),target
assert len((own/"validation/native-01/fixtures.stdin").read_bytes().splitlines()) == 11052
exports = []
for tag,rel,count,expected in [
    ("protocol", "behavioral-07-thumb", 10933, "37f96ad2221873c0850c54310767ad0725a7ba55e558361cc6aed31333267bff"),
    ("loop", "update-loop-01-thumb", 120, "2ecbc87c97e1802d8deb9b0c55f9b871c43fbce94c67499401c459141c78cd26"),
]:
    directory = ROOT/"evidence/recovery/2026-10-27/efm-reconstruction/panel"/rel
    assert sha(directory/"validation.json") == expected
    rows = [json.loads(line) for line in (directory/"cases.jsonl").read_text().splitlines()]
    assert len(rows) == count and all(row["passed"] and row["actual"] == row["expected"] for row in rows)
    exports.append((tag, directory, rows))

PHASE.mkdir(parents=True,exist_ok=False)
preimages = ["CMakeLists.txt","cmake/ProductionSourceGroups.cmake","validation/ready-functions.json","validation/compiled-functions.json","validation/integration.json","validation/integration-linux.json","validation/formatting.json","SYMBOLS.md"]
for name in preimages:
    target = PHASE/"before"/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(LIB/name,target)
old = LIB/"candidates/noaa-spi-refresh-params"
new = LIB/"candidates/noaa-spi-refresh-file-transfer-panel"
(new/"tools").mkdir(parents=True,exist_ok=False)
derivatives = {}
for name in ["inspect_closure.py","replay_existing.py"]:
    source = old/"tools"/name;target = new/"tools"/name
    target.write_text(source.read_text().replace("noaa-spi-refresh-params","noaa-spi-refresh-file-transfer-panel").replace("efm-parameters-input-pin-root","file-transfer-panel-root"))
    derivatives[str(target.relative_to(LIB))] = {"source":str(source.relative_to(LIB)),"source_sha256":sha(source),"derivative_sha256":sha(target),"changes":"Phase paths only; validation guards retained"}
copied = {}
for source,name in products:
    target = LIB/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    copied[name] = {"source":str(source.relative_to(ROOT)),"source_sha256":sha(source),"applied_sha256":sha(target)}
for tag,directory,rows in exports:
    for field,filename in [("command","fixtures.stdin.gz"),("expected","arm-output.txt.gz")]:
        name = "validation/embedded-panel/"+tag+"/"+filename
        target = LIB/name;assert not target.exists();target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(gzip.compress("".join(row[field]+"\n" for row in rows).encode(),mtime=0))
        copied[name] = {"source":str((directory/"cases.jsonl").relative_to(ROOT)),"source_sha256":sha(directory/"cases.jsonl"),"applied_sha256":sha(target),"adaptation":"Exact retained commands/expected lines, gzip only; no oracle replay"}
for name,data in [("validation/uc-file-transfer-state/provider.stdin",b"s\n"),("validation/uc-file-transfer-state/provider-output.txt",b"s 1 1\n")]:
    target = LIB/name;assert not target.exists();target.write_bytes(data);copied[name] = {"source":"Reviewed existing source-provider smoke contract","applied_sha256":sha(target)}

runner = LIB/"tools/source_port_replay.py"
assert not runner.exists()
runner.write_text('''"""Replay retained source-port lines against an active root executable."""
import argparse
import gzip
from pathlib import Path
import subprocess
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--executable',type=Path,required=True)
p.add_argument('--fixtures',type=Path,required=True)
p.add_argument('--expected',type=Path,required=True)
p.add_argument('--cases',type=int,required=True)
p.add_argument('--argument',action='append',default=[])
a=p.parse_args()
def read(path):
    raw=path.read_bytes()
    return gzip.decompress(raw) if path.suffix=='.gz' else raw
stdin,expected=read(a.fixtures),read(a.expected)
assert len(stdin.splitlines())==len(expected.splitlines())==a.cases
r=subprocess.run([str(a.executable),*a.argument],input=stdin,capture_output=True)
assert r.returncode==0,r.stderr.decode(errors='replace')
assert r.stdout==expected,'Active source-port output differs from retained witness'
print(f'PASS {a.cases} retained source-port cases')
''')
copied[str(runner.relative_to(LIB))] = {"source":"Scoped retained fixture runner","applied_sha256":sha(runner)}
groups = LIB/"cmake/ProductionSourceGroups.cmake";text = groups.read_text()
text = text.replace("set(PRESONUS_common_SOURCES\n","set(PRESONUS_common_SOURCES\n  src/Presonus/UC/FileTransfer.cpp\n",1)
text = text.replace("set(PRESONUS_cs18_SOURCES\n","set(PRESONUS_cs18_SOURCES\n  src/embedded_panel/PanelProtocol.cpp\n  src/embedded_panel/UpdateLoop.cpp\n",1)
headers = "  presonus/uc/file_transfer.hpp\n  presonus/mcu/panel_protocol.hpp\n  presonus/mcu/update_loop.hpp\n"
text = text.replace("set(PRESONUS_PUBLIC_HEADERS\n","set(PRESONUS_PUBLIC_HEADERS\n"+headers,1);groups.write_text(text)
cmake = LIB/"CMakeLists.txt";text = cmake.read_text();marker="  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)";assert text.count(marker)==1
block='''  add_executable(uc_file_transfer_state_bridge tests/uc_file_transfer_state_bridge.cpp)
  target_link_libraries(uc_file_transfer_state_bridge PRIVATE presonus::uc)
  target_link_options(uc_file_transfer_state_bridge PRIVATE -Wl,--wrap=_Znwm -Wl,--wrap=_ZdlPv -Wl,--wrap=_ZdlPvm)
  add_test(NAME uc_file_transfer_state COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py --executable $<TARGET_FILE:uc_file_transfer_state_bridge>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-file-transfer-state/fixtures.stdin
    --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-file-transfer-state/arm-output.txt --cases 11052)
  add_test(NAME uc_file_transfer_state_provider COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py --executable $<TARGET_FILE:uc_file_transfer_state_bridge>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-file-transfer-state/provider.stdin
    --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/uc-file-transfer-state/provider-output.txt --cases 1)
  add_executable(panel_protocol_port_bridge tests/panel_protocol_port_bridge.cpp)
  target_link_libraries(panel_protocol_port_bridge PRIVATE presonus::cs18_components)
  add_test(NAME embedded_panel_protocol COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py --executable $<TARGET_FILE:panel_protocol_port_bridge>
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/embedded-panel/protocol/fixtures.stdin.gz
    --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/embedded-panel/protocol/arm-output.txt.gz --cases 10933)
  add_executable(panel_update_loop_bridge tests/panel_update_loop_bridge.cpp)
  target_link_libraries(panel_update_loop_bridge PRIVATE presonus::cs18_components)
  add_test(NAME embedded_panel_update_loop COMMAND ${Python3_EXECUTABLE}
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/source_port_replay.py --executable $<TARGET_FILE:panel_update_loop_bridge>
    --argument ${CMAKE_CURRENT_SOURCE_DIR}/validation/embedded-panel/panel_surface_code.bin
    --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/embedded-panel/loop/fixtures.stdin.gz
    --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/embedded-panel/loop/arm-output.txt.gz --cases 120)
'''
text = text.replace(marker,block+marker).replace("set(PRESONUS_UC_PUBLIC_HEADERS\n","set(PRESONUS_UC_PUBLIC_HEADERS\n"+headers,1);cmake.write_text(text)
cpp = [n for n in copied if Path(n).suffix in (".cpp",".hpp",".h")]
(LIB/"validation/format-file-transfer-panel-paths.json").write_text(json.dumps(cpp,indent=2)+"\n")
extra = sorted(set(copied)|{"CMakeLists.txt","cmake/ProductionSourceGroups.cmake"})
(LIB/"validation/integration-file-transfer-panel-additions.json").write_text(json.dumps(extra,indent=2)+"\n")
application = {"products":copied,"derivatives":derivatives,"expected_suites":109,"expected_headers":78,"expected_partitions":{"common":62,"cs18":24,"rm":6},"proposed_host_delta":{"ready":8,"pending":2,"mangles":4},"admission_performed":False,"tool_sha256":sha(Path(__file__)),"preimage_hashes":{n:sha(PHASE/"before"/n) for n in preimages}}
(PHASE/"application.json").write_text(json.dumps(application,indent=2)+"\n")
print(json.dumps({"products":len(copied),"cpp_paths":len(cpp),"expected_suites":109,"expected_ready":595,"expected_pending":298,"global_ledgers_changed":False}))
