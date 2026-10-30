"""Guarded EFM helper integration, preserving frozen candidate proofs."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path('/home/rs/projects/opencs/ai-line-analysis')
LIB = ROOT / "uc-library"
PHASE = ROOT / "evidence/recovery/2026-10-27/efm-helpers-root"
PHASE.mkdir(parents=True, exist_ok=False)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
baseline = json.loads((ROOT / "temp/recovery-work/checkpoints/2026-10-27-control-file-services.json").read_text())
for name, digest in baseline["inputs"].items():
    assert sha(LIB / name.removeprefix("uc-library/")) == digest, name
build_files = ["CMakeLists.txt", "cmake/ProductionSourceGroups.cmake"]
for name in build_files + ["validation/ready-functions.json", "validation/compiled-functions.json", "validation/integration.json", "validation/integration-linux.json", "validation/formatting.json", "SYMBOLS.md"]:
    dest = PHASE / "before" / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(LIB / name, dest)
affected = {}
for label, name in [("ready", "ready-functions.json"), ("pending", "compiled-functions.json")]:
    rows = json.loads((LIB / "validation" / name).read_text())["functions"]
    affected[label] = [r for r in rows if set(build_files).intersection(r["sources"])]
assert (len(affected["ready"]), len(affected["pending"])) == (1, 4)
(PHASE / "dependency-review.json").write_text(json.dumps({"affected": affected, "build_file_preimages": {n: sha(LIB/n) for n in build_files}}, indent=2) + "\n")

old = LIB / "candidates/noaa-spi-refresh"
new = LIB / "candidates/noaa-spi-refresh-efm"
assert not new.exists()
(new / "tools").mkdir(parents=True)
derivatives = {}
for name in ["inspect_closure.py", "replay_existing.py"]:
    source = old / "tools" / name
    text = source.read_text()
    assert "noaa-spi-refresh" in text
    text = text.replace("noaa-spi-refresh", "noaa-spi-refresh-efm").replace("control-file-services-root", "efm-helpers-root")
    dest = new / "tools" / name
    dest.write_text(text)
    derivatives[str(dest.relative_to(LIB))] = {"source": str(source.relative_to(LIB)), "source_sha256": sha(source), "derivative_sha256": sha(dest), "changes": "Only phase-specific output/candidate paths and description; existing validation guards retained"}

candidate = LIB / "candidates/efm-fader-app"
copies = {}
for name, expected in [("validation/checks/native-01/validation.json", "327360c5349c92108a773b18435611218f75d2f5da2bb13c252324e1fa06b586"), ("validation/version/native-01/validation.json", "94e74590116f5d00554f6fc2bc8e4002d1384c90cb6d595d9363ee5c240d25af")]:
    assert sha(candidate/name) == expected
    for rel, digest in json.loads((candidate/name).read_text())["source_hashes"].items():
        assert sha(LIB/rel.removeprefix("uc-library/")) == digest, rel

def copy(source, target, rewrite=False):
    dest = LIB / target
    assert not dest.exists(), target
    dest.parent.mkdir(parents=True, exist_ok=True)
    if rewrite:
        text = source.read_text()
        for header in ["efm_packet_checks.hpp", "efm_version_packet.hpp"]:
            text = text.replace('"'+header+'"', '"presonus/embedded_efm/'+header+'"')
        dest.write_text(text)
    else:
        shutil.copyfile(source, dest)
    copies[target] = {"source": str(source.relative_to(ROOT)), "source_sha256": sha(source), "applied_sha256": sha(dest), "adaptation": "Public include path only" if rewrite else "Byte-identical copy"}

for stem in ["efm_packet_checks", "efm_version_packet"]:
    copy(candidate / "include" / (stem+".hpp"), "include/presonus/embedded_efm/"+stem+".hpp")
    copy(candidate / "src" / (stem+".cpp"), "src/embedded_efm/"+stem+".cpp", True)
for tag in ["checks", "version"]:
    copy(candidate / "tests" / (tag+"_driver.cpp"), "tests/efm_"+tag+"_driver.cpp", True)
    for src, dest in [("fixtures.stdin", "fixtures.txt"), ("arm-output.txt", "arm-output.txt")]:
        copy(candidate / "validation" / tag / "native-01" / src, "validation/embedded-efm/"+tag+"/"+dest)
copy(ROOT / "uc-library/tools/recovery/efm-composition/driver.cpp", "tests/efm_composition_driver.cpp", True)
for src, dest in [("fixtures.stdin", "fixtures.txt"), ("arm-output.txt", "arm-output.txt")]:
    copy(ROOT / "evidence/recovery/2026-10-27/efm-reconstruction/cross-layer/composition-01" / src, "validation/embedded-efm/composition/"+dest)

groups = LIB / build_files[1]
text = groups.read_text()
marker = "set(PRESONUS_cs18_SOURCES\n"
assert text.count(marker) == 1
text = text.replace(marker, marker+"  src/embedded_efm/efm_packet_checks.cpp\n  src/embedded_efm/efm_version_packet.cpp\n")
marker = "set(PRESONUS_PUBLIC_HEADERS\n"
assert text.count(marker) == 1
text = text.replace(marker, marker+"  presonus/embedded_efm/efm_packet_checks.hpp\n  presonus/embedded_efm/efm_version_packet.hpp\n")
groups.write_text(text)
cmake = LIB / build_files[0]
text = cmake.read_text()
marker = "  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)"
assert text.count(marker) == 1
block = '''  foreach(efm_suite checks version composition)
    add_executable(efm_${efm_suite}_driver tests/efm_${efm_suite}_driver.cpp)
    target_link_libraries(efm_${efm_suite}_driver PRIVATE presonus::cs18_components)
    add_test(NAME embedded_efm_${efm_suite} COMMAND ${Python3_EXECUTABLE}
      ${CMAKE_CURRENT_SOURCE_DIR}/tools/dice_uart_assembly_replay.py
      --executable $<TARGET_FILE:efm_${efm_suite}_driver>
      --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/embedded-efm/${efm_suite}/fixtures.txt
      --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/embedded-efm/${efm_suite}/arm-output.txt)
  endforeach()
'''
text = text.replace(marker, block+marker)
marker = "set(PRESONUS_UC_PUBLIC_HEADERS\n"
assert text.count(marker) == 1
text = text.replace(marker, marker+"  presonus/embedded_efm/efm_packet_checks.hpp\n  presonus/embedded_efm/efm_version_packet.hpp\n")
cmake.write_text(text)
cpp = [name for name in copies if Path(name).suffix in (".cpp", ".hpp")]
(LIB / "validation/format-efm-helpers-paths.json").write_text(json.dumps(cpp, indent=2)+"\n")
(LIB / "validation/integration-efm-helpers-additions.json").write_text(json.dumps(sorted(set(copies) | set(build_files)), indent=2)+"\n")
application = {"applied_at": datetime.now(timezone.utc).isoformat(), "products": copies, "derivatives": derivatives, "role": "CS18 only: selected parent/nested MCU bytes come from surface ELF; no RM identity established", "namespace": "presonus::analysis::efm_fader_app", "original_mangles_available": False, "host_ready_delta": 0, "expected_suites": 101, "expected_headers": 73, "expected_cpp_partitions": {"common": 60, "cs18": 20, "rm": 6}, "ledger_admission_performed": False}
(PHASE / "application.json").write_text(json.dumps(application, indent=2)+"\n")
print(json.dumps({"applied_products": len(copies), "cpp_paths": len(cpp), "expected_suites": 101, "host_ready_delta": 0, "old_proofs_requiring_refresh": 5}))
