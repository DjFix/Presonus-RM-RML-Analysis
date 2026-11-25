"""Compile the real portable MIDI providers and compare against ARM fixtures."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

SOURCE = "uc-library/src/Presonus/UC/MidiEndpoint.cpp"
HEADER = "uc-library/include/presonus/uc/midi_endpoint.hpp"
TEST = Path(__file__).with_name("Replay.cpp").resolve().relative_to(Path.cwd())
SOURCES = (SOURCE, "uc-library/src/Presonus/UC/MidiConnection.cpp")
SOURCE_BINDINGS = (*SOURCES, HEADER, "uc-library/include/presonus/uc/midi_connection.hpp")
CORE_HEADERS = ("public/corevector.h", "public/corestringbuffer.h", "public/corestringtraits.h")
FORMATTER = "uc-library/.venv/bin/clang-format"
FORMAT = [FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror",
          HEADER, SOURCE, str(TEST)]
WRAPS = ("_Znam", "_ZdaPv", "_ZdaPvm", "_ZdlPv", "_ZdlPvm")
DOMAINS = {
    "complete_construct": "Exact C1 per role through original CString32 and vector initialization. Compare a genuine derived placement object with two prefill patterns against native string/ID defaults, empty vector, capacity zero and delta five.",
    "base_construct": "Exact separate C2 per role through original CString32 and vector initialization. Compare genuine derived placement object state from both prefill patterns.",
    "complete_destroy": "Exact D1 per role with empty and populated borrowed rosters. Compare explicit qualified complete destructor entry and actual vector allocation release without receiver deletion.",
    "base_destroy": "Exact D2 per role with empty and populated rosters. Compare real portable base destruction after a concrete derived destructor, actual vector buffer release and borrowed connection survival.",
    "deleting_destroy": "Exact both-role D0. Compare real virtual deletion of a derived receiver through MidiEndpoint, actual vector buffer release followed by receiver release for populated rosters and continued live borrowed connections.",
    "get_info": "Two-role projection with type, independent signed IDs and separate CCL strings including 31 ASCII characters, live storage borrowing and leading caller field preservation.",
    "find_connection_for_handler": "Two-role empty, present, duplicate, absent and null-handler lookup with true typed borrowed connections. Compare first pointer identity and order.",
    "send_from": "Two-role in-process dispatch across empty, all-success, mixed and all-failure rosters. Compare ordered real handler callbacks, exact borrowed event reference and result aggregation without short-circuiting.",
    "add_connection": "Client role empty, spare capacity, full growth and allocation failure. Compare actual CCL append or unchanged roster and abstract callback observes post-attempt contents even after allocation failure.",
    "remove_connection": "Server role empty, missing, present, duplicate and final-entry removal. Compare abstract callback occurring before first-match erasure or attempted erasure, roster ordering and borrowed ownership.",
}
UNCERTAINTIES = {
    "get_info": ["Original unencoded return declaration. The port uses void and independent field names for the observed writes."],
    "find_connection_for_handler": ["Original unencoded pointer return declaration and qualification. The port uses the observed MidiConnection pointer type."],
    "send_from": ["Original unencoded result declaration. The port uses bool for the observed 0/1 aggregate."],
    "add_connection": ["Original unencoded return declaration. The port uses void for the observed callback-oriented operation."],
    "remove_connection": ["Original unencoded return declaration. The port uses void for the observed callback and erase operation."],
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(argv):
    return subprocess.run(argv, check=True, capture_output=True, text=True).stdout


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def compile_replay(output):
    output.mkdir(parents=True, exist_ok=True)
    flags = ["-std=c++17", "-O2", "-fno-lto", "-Ulinux", "-pthread",
             "-Iuc-library/include", "-isystem", "third_party/ccl-framework"]
    objects, commands, artifacts = [], [], {}
    dependencies = set()
    for source in (*SOURCES, str(TEST)):
        obj = output / Path(source).with_suffix(".o").name
        depfile = obj.with_suffix(".d")
        command = ["c++", *flags, "-MD", "-MF", str(depfile), "-c", source, "-o", str(obj)]
        run(command)
        commands.append(command)
        objects.append(str(obj))
        for artifact in (obj, depfile):
            artifacts[str(artifact)] = digest(artifact)
        dependencies.update(depfile.read_text().replace("\\\n", "").split()[1:])
    required = {*SOURCE_BINDINGS, *(f"third_party/ccl-framework/core/{name}" for name in CORE_HEADERS)}
    assert required <= dependencies, required - dependencies
    executable = output / "replay"
    command = ["c++", "-fno-lto", "-pthread", *(f"-Wl,--wrap={name}" for name in WRAPS),
               *objects, "-o", str(executable)]
    run(command)
    commands.append(command)
    dump(output / "build.json", {"compiler": run(["c++", "--version"]).splitlines()[0],
                                 "cwd": str(Path.cwd()), "argv": commands,
                                 "artifacts": artifacts,
                                 "link_inputs": {path: digest(path) for path in objects},
                                 "executable_sha256": digest(executable)})
    print("Built real pinned CCL template and MidiConnection providers with checked depfiles")


def check_symbol(obj, mangled):
    symbols = run(["nm", "--defined-only", str(obj)]).splitlines()
    exact, = [line for line in symbols if line.split()[-1:] == [mangled]]
    assert exact.split()[-2] in ("T", "W")
    if mangled.endswith("D0Ev"):
        disassembly = run(["objdump", "-dr", f"--disassemble={mangled}", str(obj)])
        assert "_ZdlPv" in disassembly
    return exact


def expand(items):
    for item in items:
        if isinstance(item, list):
            yield from expand(item)
        else:
            yield str(item)


def expected(case):
    result = case["result"] if isinstance(case["result"], list) else [case["result"]]
    return [list(expand(call)) for call in case["calls"]] + [["result", *map(str, result)]]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("compile", "symbols", "replay"))
    parser.add_argument("--build-dir", type=Path)
    parser.add_argument("--variant", choices=DOMAINS)
    parser.add_argument("--fixtures", type=Path)
    parser.add_argument("--object", type=Path)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--integration", type=Path)
    args = parser.parse_args()
    if args.operation == "compile":
        compile_replay(args.build_dir)
        return
    rows = json.loads(args.fixtures.read_text())
    mangled, = {row["original"]["mangled"] for row in rows}
    symbol = check_symbol(args.object, mangled)
    if args.operation == "symbols":
        print(symbol)
        return
    start = datetime.now(timezone.utc).isoformat()
    run(FORMAT)
    results = []
    for row in rows:
        observed = []
        for case in row["cases"]:
            argv = [str(args.exe), args.variant, str(case["case"])]
            actual = [shlex.split(line) for line in run(argv).splitlines()]
            want = expected(case)
            assert actual == want, (row["original"]["role"], argv, actual, want)
            observed.append({"argv": argv, "output": actual})
        results.append({"original": row["original"], "portable": observed})

    uncertainty = UNCERTAINTIES.get(args.variant, [])
    sources = {str(Path(p).relative_to("uc-library")): digest(p) for p in SOURCE_BINDINGS}
    core = {str(p): digest(p) for p in
            (Path("third_party/ccl-framework/core") / name for name in CORE_HEADERS)}
    proposals = []
    for origin in (row["original"] for row in rows):
        entry = {"mangled": mangled, "original_elf_sha256": origin["elf"],
                 "original_address": origin["address"], "cpp_compiled": True,
                 "mangling_namespace_checked": True, "portable_ready": not uncertainty,
                 "domain": DOMAINS[args.variant], "sources": sources, "repository_sources": core}
        if uncertainty:
            entry["declaration_uncertainties"] = uncertainty
        proposals.append(entry)
    proof = {"cpp_differential_passed": True, "behavior_validation_passed": True,
             "compiled_mangled_names_matched": True, "mangling_namespace_checked": True,
             "mangled_names": [mangled], "compiled_symbol": symbol, "functions": proposals,
             "proposed_readiness": {"ready": [] if uncertainty else proposals,
                                    "pending": proposals if uncertainty else []},
             "validation_domain": DOMAINS[args.variant], "roles": results,
             "formatter_version": run([FORMATTER, "--version"]).strip(),
             "format_argv": FORMAT, "format_check_passed": True,
             "fixtures": {"path": str(args.fixtures), "sha256": digest(args.fixtures)},
             "exe_sha256": digest(args.exe), "object_sha256": digest(args.object),
             "native_producer_sha256": digest(Path(__file__).with_name("native.py")),
             "checker_sha256": digest(__file__), "replay_start_utc": start,
             "replay_end_utc": datetime.now(timezone.utc).isoformat()}
    if args.integration:
        proof["integration"] = {"path": str(args.integration), "sha256": digest(args.integration)}
        proof["integration_sha256"] = proof["integration"]["sha256"]
    dump(args.out, proof)
    print(f"Matched {sum(len(result['portable']) for result in results)} portable comparisons")


if __name__ == "__main__":
    main()
