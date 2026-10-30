"""Apply two dependency-ordered raw candidates and an independent InputPin closure."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path('/home/rs/projects/opencs/ai-line-analysis')
LIB = ROOT / "uc-library"
PHASE = ROOT / "evidence/recovery/2026-10-27/efm-parameters-input-pin-root"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
baseline = json.loads((ROOT / "temp/recovery-work/checkpoints/2026-10-27-efm-helpers.json").read_text())
for name, digest in baseline["inputs"].items():
    assert sha(LIB / name.removeprefix("uc-library/")) == digest, name
pin = LIB / "candidates/noaa-spi-service"
control_path = pin / "CONTROLLED-INPUT-PIN.json"
assert sha(control_path) == "bdce38ed8ad7b1ae97131336a5af21a618be9e0c4fa9c9f9595619604898d6b2"
control = json.loads(control_path.read_text())
for name, digest in control["frozen_proofs"].items():
    assert sha(pin/name) == digest, name
assert sha(pin/"seal_input_pin.py") == "5b96e6860244510f5ef7ebb54fed5760363d2131a8763bb89f1fffae3786de4c"
assert sha(LIB/"src/surface_panel/InputPin.cpp") == control["unchanged_implementation_sha256"]
for name, row in control["copies"].items():
    assert sha(pin/name) == row["sha256"]
    target = LIB / row["target"]
    assert sha(target) == row["active_sha256"] if row["active_sha256"] else not target.exists()

raw = []
for tag, expected in [
    ("efm-fader-parameters", "98dd42c8e8a0f905ec341a6388e6ae6795622ba6d6bb14a7d849b0c211cdd46e"),
    ("efm-fader-packed-parameters", "f2b1ab0f7d231961c683ab3e6889bd46ee89b9d192c8bd9d78528dc43a68fdae"),
]:
    own = LIB / "candidates" / tag
    assert sha(own/"HANDOFF.json") == expected
    handoff = json.loads((own/"HANDOFF.json").read_text())
    for field in ["proof", "mirror_audit", "range_kinds"]:
        if field in handoff:
            assert sha(own/handoff[field]["path"]) == handoff[field]["sha256"]
    for name, digest in {**handoff["products"], **handoff.get("frozen_dependencies", {})}.items():
        assert sha(LIB/name.removeprefix("uc-library/")) == digest, name
    proof = json.loads((own/handoff["proof"]["path"]).read_text())
    fixture_names = ["fixtures.bin.gz", "arm-output.bin.gz"] if tag.endswith("packed-parameters") else ["fixtures.stdin.gz", "arm-output.txt.gz"]
    for filename in fixture_names:
        assert sha(own/"validation/native-01"/filename) == proof["artifacts"][filename]
    raw.append((own, handoff))

resuming_staged_copies = PHASE.exists()
PHASE.mkdir(parents=True, exist_ok=True)
preimages = ["CMakeLists.txt", "cmake/ProductionSourceGroups.cmake", "include/presonus/surface_panel/InputPin.hpp", "tools/embedded_efm_replay.py", "validation/ready-functions.json", "validation/compiled-functions.json", "validation/integration.json", "validation/integration-linux.json", "validation/formatting.json", "SYMBOLS.md"]
for name in preimages:
    dest = PHASE/"before"/name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if resuming_staged_copies:
        assert sha(LIB/name) == sha(dest), "Cannot resume after an original input changed: "+name
    else:
        shutil.copyfile(LIB/name, dest)

old = LIB/"candidates/noaa-spi-refresh-efm"
new = LIB/"candidates/noaa-spi-refresh-params"
(new/"tools").mkdir(parents=True, exist_ok=resuming_staged_copies)
derivatives = {}
for name in ["inspect_closure.py", "replay_existing.py"]:
    source = old/"tools"/name
    dest = new/"tools"/name
    text = source.read_text().replace("noaa-spi-refresh-efm", "noaa-spi-refresh-params").replace("efm-helpers-root", "efm-parameters-input-pin-root")
    if dest.exists():
        assert resuming_staged_copies and dest.read_text() == text
    else:
        dest.write_text(text)
    derivatives[str(dest.relative_to(LIB))] = {"source": str(source.relative_to(LIB)), "source_sha256": sha(source), "derivative_sha256": sha(dest), "changes": "Phase/candidate/output paths only; validation guards retained"}

copies = {}


def copy(source, target, rewrite=False):
    dest = LIB/target
    dest.parent.mkdir(parents=True, exist_ok=True)
    if rewrite:
        text = source.read_text()
        for header in ["efm_parameter_fields.hpp", "efm_packed_parameters.hpp"]:
            text = text.replace('"'+header+'"', '"presonus/embedded_efm/'+header+'"')
        data = text.encode()
    else:
        data = source.read_bytes()
    if dest.exists() and target != "include/presonus/surface_panel/InputPin.hpp":
        assert resuming_staged_copies and dest.read_bytes() == data, target
    else:
        dest.write_bytes(data)
    copies[target] = {"source": str(source.relative_to(ROOT)), "source_sha256": sha(source), "applied_sha256": sha(dest), "adaptation": "Public include path only" if rewrite else "Byte-identical copy"}


for own, handoff in raw:
    packed = own.name.endswith("packed-parameters")
    stem = "efm_packed_parameters" if packed else "efm_parameter_fields"
    tag = "packed" if packed else "fields"
    copy(own/"include"/(stem+".hpp"), "include/presonus/embedded_efm/"+stem+".hpp")
    copy(own/"src"/(stem+".cpp"), "src/embedded_efm/"+stem+".cpp", True)
    copy(own/"tests"/(tag+"_driver.cpp"), "tests/efm_"+tag+"_driver.cpp", True)
    for filename in (["fixtures.bin.gz", "arm-output.bin.gz"] if packed else ["fixtures.stdin.gz", "arm-output.txt.gz"]):
        source = own/"validation/native-01"/filename
        proof = json.loads((own/handoff["proof"]["path"]).read_text())
        assert sha(source) == proof["artifacts"][filename]
        copy(source, "validation/embedded-efm/"+tag+"/"+filename)
for name, row in control["copies"].items():
    copy(pin/name, row["target"])
for name, target in control["fixture_copies"].items():
    assert sha(pin/name) == control["fixture_sha256"]
    copy(pin/name, target)

groups = LIB/"cmake/ProductionSourceGroups.cmake"
text = groups.read_text()
text = text.replace("set(PRESONUS_common_SOURCES\n", "set(PRESONUS_common_SOURCES\n  src/Presonus/Panel/input_pin_lifetime.cpp\n", 1)
text = text.replace("set(PRESONUS_cs18_SOURCES\n", "set(PRESONUS_cs18_SOURCES\n  src/embedded_efm/efm_parameter_fields.cpp\n  src/embedded_efm/efm_packed_parameters.cpp\n", 1)
headers = "  presonus/embedded_efm/efm_parameter_fields.hpp\n  presonus/embedded_efm/efm_packed_parameters.hpp\n"
text = text.replace("set(PRESONUS_PUBLIC_HEADERS\n", "set(PRESONUS_PUBLIC_HEADERS\n"+headers, 1)
groups.write_text(text)

cmake = LIB/"CMakeLists.txt"
text = cmake.read_text()
marker = "  add_library(uc_symbol_catalog_check OBJECT tests/symbol_catalog.cpp)"
assert text.count(marker) == 1
block = '''  set(efm_fields_cases 35306)
  set(efm_packed_cases 20179)
  set(efm_fields_fixture fixtures.stdin.gz)
  set(efm_fields_expected arm-output.txt.gz)
  set(efm_packed_fixture fixtures.bin.gz)
  set(efm_packed_expected arm-output.bin.gz)
  foreach(efm_suite fields packed)
    set(efm_replay_extra)
    if(efm_suite STREQUAL "packed")
      set(efm_replay_extra --binary-records)
    endif()
    add_executable(efm_${efm_suite}_driver tests/efm_${efm_suite}_driver.cpp)
    target_link_libraries(efm_${efm_suite}_driver PRIVATE presonus::cs18_components)
    add_test(NAME embedded_efm_${efm_suite} COMMAND ${Python3_EXECUTABLE}
      ${CMAKE_CURRENT_SOURCE_DIR}/tools/embedded_efm_replay.py
      --executable $<TARGET_FILE:efm_${efm_suite}_driver>
      --fixtures ${CMAKE_CURRENT_SOURCE_DIR}/validation/embedded-efm/${efm_suite}/${efm_${efm_suite}_fixture}
      --expected ${CMAKE_CURRENT_SOURCE_DIR}/validation/embedded-efm/${efm_suite}/${efm_${efm_suite}_expected}
      --cases ${efm_${efm_suite}_cases} ${efm_replay_extra})
  endforeach()
'''
for test in control["tests"]:
    target = test["name"]
    block += "  add_executable("+target+" "+" ".join(test["sources"])+")\n"
    block += "  target_link_libraries("+target+" PRIVATE presonus::uc)\n"
    block += "  target_compile_options("+target+" PRIVATE "+" ".join(test["compile_options"])+")\n"
    block += "  target_link_options("+target+" PRIVATE -fno-lto "+" ".join(test["link_options"])+")\n"
    args = " ".join("${CMAKE_CURRENT_SOURCE_DIR}/"+arg for arg in test["arguments"])
    block += "  add_test(NAME "+target+" COMMAND "+target+(" "+args if args else "")+")\n"
text = text.replace(marker, block+marker)
text = text.replace("set(PRESONUS_UC_PUBLIC_HEADERS\n", "set(PRESONUS_UC_PUBLIC_HEADERS\n"+headers, 1)
cmake.write_text(text)
runner = LIB/"tools/embedded_efm_replay.py"
text = runner.read_text()
assert "fixtures = args.fixtures.read_bytes()\nexpected = args.expected.read_bytes()" in text
text = text.replace("import argparse\n", "import argparse\nimport gzip\n")
text = text.replace('args = parser.parse_args()', 'parser.add_argument("--binary-records", action="store_true")\nargs = parser.parse_args()')
text = text.replace("fixtures = args.fixtures.read_bytes()\nexpected = args.expected.read_bytes()", "def read_fixture(path):\n    data = path.read_bytes()\n    return gzip.decompress(data) if path.suffix == '.gz' else data\n\n\nfixtures = read_fixture(args.fixtures)\nexpected = read_fixture(args.expected)")
text = text.replace('assert len(fixtures.splitlines()) == args.cases\nassert len(expected.splitlines()) == args.cases', 'if args.binary_records:\n    assert len(fixtures) == args.cases * 4100\n    assert len(expected) == args.cases * 4097\nelse:\n    assert len(fixtures.splitlines()) == args.cases\n    assert len(expected.splitlines()) == args.cases')
runner.write_text(text)
cpp = [name for name in copies if Path(name).suffix in (".cpp", ".hpp")]
(LIB/"validation/format-efm-parameters-input-pin-paths.json").write_text(json.dumps(cpp, indent=2)+"\n")
additional = sorted(set(copies) | {"CMakeLists.txt", "cmake/ProductionSourceGroups.cmake", "tools/embedded_efm_replay.py"})
(LIB/"validation/integration-efm-parameters-input-pin-additions.json").write_text(json.dumps(additional, indent=2)+"\n")
application = {"applied_at": datetime.now(timezone.utc).isoformat(), "products": copies, "derivatives": derivatives, "preimage_hashes": {n: sha(PHASE/"before"/n) for n in preimages}, "expected_suites": 105, "expected_headers": 75, "expected_partitions": {"common": 61, "cs18": 22, "rm": 6}, "proposed_host_delta": {"ready": 10, "mangles": 5, "pending": 0}, "admission_performed": False, "dependency_order": ["efm-fader-parameters", "efm-fader-packed-parameters"], "independent_candidate": "noaa-spi-service InputPin closure"}
(PHASE/"application.json").write_text(json.dumps(application, indent=2)+"\n")
print(json.dumps({"products": len(copies), "cpp_paths": len(cpp), "expected_suites": 105, "proposed_ready": 587, "pending": 296, "global_ledgers_changed": False}))
