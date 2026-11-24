from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

ROOT = next(base for base in (Path.cwd(), *Path.cwd().parents)
            if (base / "temp/core-upstream/root-integration-01/upstream-core/sdk").is_dir())
SDK = ROOT / "temp/core-upstream/root-integration-01/upstream-core/sdk"
SCRATCH = Path("temp/recovery-work/sqlite01_messenger_set_handler")
SOURCE = Path("uc-library/src/Presonus/Link/Messenger.cpp")
TEST = Path(__file__).parent / "Replay.cpp"
OBJECT = SCRATCH / "Messenger.o"
BINARY = SCRATCH / "replay"
SYMBOL = "_ZN8Presonus4Link9Messenger13setMsgHandlerEPN4Core16IPropertyHandlerE"


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def symbol(path):
    output = subprocess.check_output(["nm", "--defined-only", path], text=True)
    matches = [line for line in output.splitlines() if line.split()[-1:] == [SYMBOL]]
    if len(matches) != 1 or matches[0].split()[-2] != "T":
        raise SystemExit("Expected one global definition")
    return matches[0]


def replay(binary, fixture):
    output = subprocess.check_output([binary], text=True).splitlines()
    observed = [line for line in output if line.startswith("handler ")]
    cases = json.loads(Path(fixture).read_text())["cases"]
    expected = [f"handler {case['handler']}" for case in cases]
    if observed != expected:
        raise SystemExit(f"Portable observations differ: {observed!r} != {expected!r}")
    print(f"Portable handler observations and lifetime checks: {len(cases)}")


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "compile":
        SCRATCH.mkdir(parents=True, exist_ok=True)
        compiler = ["/usr/bin/c++", "-Wall", "-Wextra", "-Wpedantic", "-pthread",
                    "-Ulinux", "-Iuc-library/include", "-isystem",
                    SDK / "include/presonus-core-5"]
        subprocess.run([*compiler, "-c", SOURCE, "-o", OBJECT], check=True)
        subprocess.run([*compiler, TEST, OBJECT, SDK / "lib/libcorelib.a",
                        SDK / "lib/libpresonus_core_allocator.a", "-ldl", "-o",
                        BINARY], check=True)
    elif mode == "symbols":
        print(symbol(OBJECT))
    elif mode == "replay":
        replay(*sys.argv[2:])
    elif mode == "proof":
        binary, obj, fixture, integration, out = sys.argv[2:]
        replay(binary, fixture)
        names = {path: symbol(path) for path in (binary, obj)}
        integration_binding = {}
        if integration != "-":
            if json.loads(Path(integration).read_text()).get("ctest_passed") is not True:
                raise SystemExit("Canonical integration must record passing CTest")
            integration_binding = {"path": integration, "sha256": digest(integration)}
        header = Path("uc-library/include/presonus/link/Messenger.hpp")
        formatter = "uc-library/.venv/bin/clang-format"
        format_argv = [formatter, "--style=file", "--fallback-style=LLVM", "--dry-run",
                       "--Werror", str(SOURCE), str(header), str(TEST)]
        subprocess.run(format_argv, check=True)
        sources = {str(path.relative_to("uc-library")): digest(path)
                   for path in (SOURCE, header)}
        provider = "third_party/ccl-framework/core/public/coreproperty.h"
        evidence = json.loads(Path(fixture).read_text())
        domain = ("Five sequential native and portable stores covering non-null bind, "
                  "replacement, repeated binding, null unbind and live binding at "
                  "portable receiver teardown. No writes outside the handler slot in "
                  "the seeded ARM receiver. No CCL handler callbacks or ownership transfer.")
        row = dict(original_elf_sha256=evidence["elf_sha256"], mangled=SYMBOL,
                   cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
                   domain=domain, sources=sources, repository_sources={provider: digest(provider)},
                   declaration_uncertainties=["Original ordinary return type unresolved."])
        proof = dict(cpp_differential_passed=True, compiled_mangled_names_matched=True,
                     domain=domain, functions=[row], integration=integration_binding,
                     proposed_readiness={"ready": [], "pending": [row]}, native_evidence=evidence,
                     portable_case_count=len(evidence["cases"]), symbols=names,
                     formatted_sources=sources, format_argv=format_argv,
                     formatter=subprocess.check_output([formatter, "--version"], text=True).strip(),
                     fixture_sha256=digest(fixture), oracle_sha256=digest(TEST.with_name("native.py")),
                     checker_sha256=digest(__file__), test_sha256=digest(TEST),
                     executable_sha256=digest(binary), object_sha256=digest(obj))
        if out != "-":
            Path(out).write_text(json.dumps(proof, indent=2) + "\n")
    else:
        raise SystemExit(f"Unknown check: {mode}")
