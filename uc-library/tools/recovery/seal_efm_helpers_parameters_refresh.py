"""Seal active EFM source/namespace/fixture bindings from the canonical build."""
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess

ROOT = Path('/home/rs/projects/opencs/ai-line-analysis')
LIB = ROOT / "uc-library"
BUILD = ROOT / "temp/core-upstream/root-integration-01"
OUT = ROOT / "evidence/recovery/2026-10-27/efm-parameters-input-pin-root/active-helpers-refresh-01"
OUT.mkdir(parents=True, exist_ok=False)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
integration = json.loads((LIB / "validation/integration.json").read_text())
formatting = json.loads((LIB / "validation/formatting.json").read_text())
assert integration["platform"] == "linux" and integration["ctest_passed"]
assert all(sha(LIB / n) == h for n, h in integration["files"].items())
assert sha(ROOT / integration["test_log"]) == integration["test_log_sha256"]
assert formatting["format_check_passed"]
application = json.loads((ROOT / "evidence/recovery/2026-10-27/efm-helpers-root/application.json").read_text())
products = application["products"]
assert all(sha(LIB / n) == row["applied_sha256"] for n, row in products.items())
assert all(formatting["files"][n] == sha(LIB/n) for n in products if Path(n).suffix in (".cpp", ".hpp"))
assert all(integration["files"][n] == sha(LIB/n) for n in products)

commands, cases = [], {}


def run(label, argv, data=None):
    result = subprocess.run(list(map(str, argv)), cwd=ROOT, input=data, capture_output=True)
    (OUT / (label + ".stdout")).write_bytes(result.stdout)
    (OUT / (label + ".stderr")).write_bytes(result.stderr)
    commands.append({"label": label, "argv": list(map(str, argv)), "returncode": result.returncode})
    (OUT / "commands.json").write_text(json.dumps(commands, indent=2)+"\n")
    assert result.returncode == 0, label
    return result.stdout


proofs = [
    (LIB/"candidates/efm-fader-app/validation/checks/native-01/validation.json", "327360c5349c92108a773b18435611218f75d2f5da2bb13c252324e1fa06b586"),
    (LIB/"candidates/efm-fader-app/validation/version/native-01/validation.json", "94e74590116f5d00554f6fc2bc8e4002d1384c90cb6d595d9363ee5c240d25af"),
    (ROOT/"evidence/recovery/2026-10-27/efm-reconstruction/cross-layer/composition-01/validation.json", "bfa51d3e15e5e26989a6611582a3b3bbda75c7372aa3aece1094bc54fb9d1947"),
]
for path, expected in proofs:
    assert sha(path) == expected

executables = {}
for tag, count in [("checks", 5642), ("version", 8199), ("composition", 768)]:
    fixtures = LIB / ("validation/embedded-efm/"+tag+"/fixtures.txt")
    expected = LIB / ("validation/embedded-efm/"+tag+"/arm-output.txt")
    assert len(fixtures.read_bytes().splitlines()) == count
    binary = BUILD / ("efm_"+tag+"_driver")
    assert run(tag, [binary], fixtures.read_bytes()) == expected.read_bytes()
    cases[tag] = count
    executables[str(binary.relative_to(ROOT))] = sha(binary)

compilation = json.loads((BUILD/"compile_commands.json").read_text())
objects = {}
for name in ["src/embedded_efm/efm_packet_checks.cpp", "src/embedded_efm/efm_version_packet.cpp"]:
    rows = [row for row in compilation if Path(row["file"]).resolve() == (LIB/name).resolve()]
    assert len(rows) == 1
    row = rows[0]
    argv = row.get("arguments") or shlex.split(row["command"])
    assert "presonus_cs18_objects.dir" in " ".join(argv)
    path = Path(row.get("output") or argv[argv.index("-o")+1])
    if not path.is_absolute():
        path = Path(row["directory"])/path
    assert path.resolve().is_relative_to(BUILD)
    objects[name] = {"compile_command": row, "object": str(path.relative_to(ROOT)), "object_sha256": sha(path)}
    names = run(Path(name).stem+"-nm", ["nm", "-g", "--defined-only", path]).decode()
    decoded = run(Path(name).stem+"-demangle", ["c++filt"], names.encode()).decode()
    required = ["appendPacketChecks", "validatePacketChecks"] if "packet_checks" in name else ["applyVersionPacket"]
    for method in required:
        assert "presonus::analysis::efm_fader_app::"+method+"(" in decoded

sources = {n: sha(LIB/n) for n in products}
sources.update({n: sha(LIB/n) for n in ["CMakeLists.txt", "cmake/ProductionSourceGroups.cmake", "tools/embedded_efm_replay.py"]})
for name in sources:
    dest = OUT/"sources"/name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(LIB/name, dest)
proof = {
    "passed": True,
    "scope": "Independent raw MCU C++ source ports; no original C++ declarations/mangles, ARM ABI or hardware verification",
    "namespace": "presonus::analysis::efm_fader_app",
    "host_ready_delta": 0,
    "image_sha256": "b87a39cea8ff234c0cca785a7c5433e4ff729d365b56fca05b3023caa3aa53b6",
    "cases": cases,
    "original_comparison_cases": 14592,
    "portable_guard_cases": 17,
    "sources": sources,
    "original_proofs": {str(p.relative_to(ROOT)): h for p, h in proofs},
    "executable_hashes": executables,
    "objects": objects,
    "integration_sha256": sha(LIB/"validation/integration.json"),
    "formatting_sha256": sha(LIB/"validation/formatting.json"),
    "canonical_test_log": integration["test_log"],
    "canonical_test_log_sha256": integration["test_log_sha256"],
    "formatter": formatting["formatter"],
    "firmware_reexecuted_in_this_seal": False,
    "hardware_accessed": False,
    "artifacts": {p.name: sha(p) for p in OUT.iterdir() if p.is_file()},
    "tool_sha256": sha(Path(__file__)),
}
(OUT/"validation.json").write_text(json.dumps(proof, indent=2)+"\n")
print(json.dumps({"passed": True, "cases": cases, "original_comparison_cases": 14592, "portable_guard_cases": 17, "proof_sha256": sha(OUT/"validation.json")}))
