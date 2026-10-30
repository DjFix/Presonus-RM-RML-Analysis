"""Seal dependency-ordered active raw parameter sources from canonical Linux archives."""
import gzip
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess

ROOT = Path('/home/rs/projects/opencs/ai-line-analysis')
LIB = ROOT/"uc-library"
BUILD = ROOT/"temp/core-upstream/root-integration-01"
OUT = ROOT/"evidence/recovery/2026-10-27/efm-parameters-input-pin-root/active-parameters-01"
OUT.mkdir(parents=True, exist_ok=False)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
integration = json.loads((LIB/"validation/integration.json").read_text())
formatting = json.loads((LIB/"validation/formatting.json").read_text())
assert integration["ctest_passed"] and integration["platform"] == "linux"
assert integration["test_suites"] == 105
assert all(sha(LIB/n) == h for n,h in integration["files"].items())
assert sha(ROOT/integration["test_log"]) == integration["test_log_sha256"]
image = ROOT/"evidence/recovery/2026-10-27/efm32-faders/fader-efm32-application-0x1000.bin"
assert sha(image) == "b87a39cea8ff234c0cca785a7c5433e4ff729d365b56fca05b3023caa3aa53b6"
application = json.loads((ROOT/"evidence/recovery/2026-10-27/efm-parameters-input-pin-root/application.json").read_text())
names = [n for n in application["products"] if "embedded-efm" in n or "embedded_efm" in n or n in ("tests/efm_fields_driver.cpp", "tests/efm_packed_driver.cpp")]
for name in names:
    assert sha(LIB/name) == application["products"][name]["applied_sha256"]
    assert integration["files"][name] == sha(LIB/name)
    if Path(name).suffix in (".cpp", ".hpp"):
        assert formatting["files"][name] == sha(LIB/name)
names += ["CMakeLists.txt", "cmake/ProductionSourceGroups.cmake", "tools/embedded_efm_replay.py"]
commands, executables, counts, proof_bindings = [], {}, {}, {}


def run(label, argv, data=None):
    result = subprocess.run(list(map(str, argv)), cwd=ROOT, input=data, capture_output=True)
    with gzip.open(OUT/(label+".stdout.gz"), "wb") as stream:
        stream.write(result.stdout)
    (OUT/(label+".stderr")).write_bytes(result.stderr)
    commands.append({"label": label, "argv": list(map(str, argv)), "returncode": result.returncode})
    (OUT/"commands.json").write_text(json.dumps(commands, indent=2)+"\n")
    assert result.returncode == 0, label
    return result.stdout


for tag, candidate, count, proof_hash in [
    ("fields", "efm-fader-parameters", 35306, "5e4fa5e8d827e2eaf5da25cbece678e120ef929df2931b92ff3818cd8e38a061"),
    ("packed", "efm-fader-packed-parameters", 20179, "46ed56594471de6908d568103b8ddf1375c4b25528a915896bca56d0d3bb2936"),
]:
    own = LIB/"candidates"/candidate
    proof_path = own/"validation/native-01/validation.json"
    assert sha(proof_path) == proof_hash
    proof_bindings[str(proof_path.relative_to(ROOT))] = proof_hash
    proof = json.loads(proof_path.read_text())
    fixtures_name = "fixtures.bin.gz" if tag == "packed" else "fixtures.stdin.gz"
    expected_name = "arm-output.bin.gz" if tag == "packed" else "arm-output.txt.gz"
    fixtures = LIB/"validation/embedded-efm"/tag/fixtures_name
    expected = LIB/"validation/embedded-efm"/tag/expected_name
    assert sha(fixtures) == proof["artifacts"][fixtures_name]
    assert sha(expected) == proof["artifacts"][expected_name]
    stdin, witness = gzip.decompress(fixtures.read_bytes()), gzip.decompress(expected.read_bytes())
    if tag == "packed":
        assert len(stdin) == count*4100 and len(witness) == count*4097
    else:
        assert len(stdin.splitlines()) == len(witness.splitlines()) == count
    binary = BUILD/("efm_"+tag+"_driver")
    assert run(tag, [binary], stdin) == witness
    executables[str(binary.relative_to(ROOT))] = sha(binary)
    counts[tag] = count
    if tag == "packed":
        correction = own/"validation/range-kinds.json"
        assert sha(correction) == "cc99ce41569a532f55fcf291ba0e3520cf4c713b66d062bbef3053216713e1ae"
        proof_bindings[str(correction.relative_to(ROOT))] = sha(correction)

compilation = json.loads((BUILD/"compile_commands.json").read_text())
objects = {}
for name, namespace, methods in [
    ("src/embedded_efm/efm_parameter_fields.cpp", "presonus::analysis::efm_fader_parameters::", ["transferStrided", "applyParameterPacket"]),
    ("src/embedded_efm/efm_packed_parameters.cpp", "presonus::analysis::efm_fader_packed_parameters::", ["applyPackedParameterPacket"]),
]:
    rows = [r for r in compilation if Path(r["file"]).resolve() == (LIB/name).resolve()]
    assert len(rows) == 1
    row = rows[0]
    argv = row.get("arguments") or shlex.split(row["command"])
    assert "presonus_cs18_objects.dir" in " ".join(argv)
    path = Path(row.get("output") or argv[argv.index("-o")+1])
    if not path.is_absolute():
        path = Path(row["directory"])/path
    objects[name] = {"compile_command": row, "object": str(path.relative_to(ROOT)), "object_sha256": sha(path)}
    output = run(Path(name).stem+"-nm", ["nm", "-g", "--defined-only", path])
    decoded = run(Path(name).stem+"-demangle", ["c++filt"], output).decode()
    assert all(namespace+method+"(" in decoded for method in methods)
sources = {n: sha(LIB/n) for n in names}
for name in sources:
    dest = OUT/"sources"/name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(LIB/name, dest)
result = {
    "passed": True, "cases": counts, "original_comparison_cases": 55448,
    "portable_guard_cases": 37, "host_ready_delta": 0,
    "scope": "Independent raw-image source ports; original C++ declarations/mangles and ARM ABI unavailable; no peripheral or hardware verification",
    "image_sha256": sha(image), "original_proofs": proof_bindings,
    "sources": sources, "objects": objects, "executable_hashes": executables,
    "integration_sha256": sha(LIB/"validation/integration.json"),
    "formatting_sha256": sha(LIB/"validation/formatting.json"),
    "formatter": formatting["formatter"], "canonical_test_log": integration["test_log"],
    "canonical_test_log_sha256": integration["test_log_sha256"],
    "original_helpers_recovered_once": True,
    "firmware_reexecuted_in_this_seal": False, "hardware_accessed": False,
    "artifacts": {p.name: sha(p) for p in OUT.iterdir() if p.is_file()},
    "tool_sha256": sha(Path(__file__)),
}
(OUT/"validation.json").write_text(json.dumps(result, indent=2)+"\n")
print(json.dumps({"passed": True, "cases": counts, "proof_sha256": sha(OUT/"validation.json")}))
