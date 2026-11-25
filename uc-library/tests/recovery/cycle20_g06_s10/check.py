"""Verify one original panel method's portable state and exact symbol surface."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys

TASK = "cycle20_g06_s10"
MODE = "lookup"
CLASS = "LCDManager"
DOMAIN = 'Eight observations per role over null, repeated and switched typed delegates, clear, hit in each of the actual front/mixer/nested CCL trees, and delegated miss. ARM exact slot forwards the unchanged query pointer and opaque result; Linux typed adapter forwards to canonical MixerLCD with actual CCL roots.'
LIMITS = 'Original ARM layout, class ancestry and lifecycle remain unresolved. Replay uses stable borrowed lifetimes and excludes concurrent binding mutations. The original delegate call crosses a controlled slot-0 shim; other slots, CS18 concrete delegate, RM hardware services and actual hardware are excluded.'
DECLARATION = 'Portable CCL Parameter pointer is provisional; original return declaration is unresolved.'
TEST = Path("uc-library/tests/recovery") / TASK
SOURCES = [f"include/presonus/panel/{CLASS}.hpp", f"src/Presonus/Panel/{CLASS}.cpp"]
CORE = "third_party/ccl-framework/core/"
CORE_DEPENDENCIES = [CORE + f"portable/{path}" for path in
                     ("corecomponent.h", "corecomponent.cpp", "coreparams.h", "coreparams.cpp")]
APP_DEPENDENCIES = ["uc-library/include/presonus/panel/MixerLCD.hpp"] if CLASS == "LCDManager" else []
if CLASS == "LCDManager":
    CORE_DEPENDENCIES += [CORE + "public/corestringbuffer.h",
                          CORE + "portable/corecontrollershared.h"]
    APP_DEPENDENCIES += [
        "uc-library/src/Presonus/Panel/MixerLCD.cpp",
        "uc-library/include/presonus/panel/FrontPanelComponent.hpp",
        "uc-library/include/presonus/panel/PanelComponent.hpp",
        "uc-library/include/presonus/mixer/MixerComponentBase.hpp",
    ]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(argv, **kwargs):
    return subprocess.run(argv, text=True, capture_output=True, check=True, **kwargs).stdout


def replay(exe, fixture):
    first = fixture["originals"][0]["cases"]
    inputs, expected = [], []
    for rows in (original["cases"] for original in fixture["originals"]):
        current_in, current_out = adapters(rows)
        if not expected:
            inputs, expected = current_in, current_out
        assert inputs == current_in and expected == current_out
    observed = run([exe.resolve()], input="".join(inputs)).splitlines()
    assert observed == expected, {"expected": expected, "observed": observed}
    assert len(observed) == len(first)
    return observed


def adapters(rows):
    inputs, expected = [], []
    tags = (0, 6101, 6201, 6202)
    for row in rows:
        if MODE in ("get", "set"):
            inputs.append(f"{row['input']}\n")
            expected.append(str(row["after"]))
        elif MODE == "previous":
            inputs.append(f"{row['cursor']} {row['dirty']}\n")
            expected.append(f"{row['returns']} {row['out_cursor']} {row['out_dirty']}")
        else:
            inputs.append(f"{row['binding']} {row['query']}\n")
            called = (row["calls"] or [0])[0]
            expected.append(f"{called} {tags[row['opaque_provider_case']]}")
    return inputs, expected


def symbols(value, required):
    public = {}
    for line in run(["nm", "--defined-only", "--format=posix", value]).splitlines():
        cols = line.split()
        if cols[1].isupper():
            public[cols[0]] = cols[1:]
    assert required in public and public[required][0] == "T"
    if CLASS == "LCDManager":
        expected = {
            "_ZN8Presonus5Panel10LCDManager11setDelegateEPNS0_12ILCDDelegateE",
            "_ZN8Presonus5Panel10LCDManagerC1Ev",
            "_ZN8Presonus5Panel10LCDManagerC2Ev",
            "_ZNK8Presonus5Panel10LCDManager22lookupElementParameterEPKc",
        }
        default_book = "_ZNK8Presonus5Panel10LCDManager14getDefaultBookEv"
        if default_book in public:
            expected.add(default_book)
            disassembly = run(["objdump", "-dr", f"--disassemble={default_book}", value])
            assert default_book in disassembly
            assert not re.search(r"\bR_[A-Z0-9_]+\b", disassembly)
        expected.update({
            "_ZN8Presonus5Panel10LCDManager6doIdleEv",
            "_ZN8Presonus5Panel10LCDManagerD0Ev",
            "_ZN8Presonus5Panel10LCDManagerD1Ev",
            "_ZN8Presonus5Panel10LCDManagerD2Ev",
        })
        # The restored virtual lifetime uses the actual pinned Core singleton
        # and Deletable metadata. These exact host exports do not assert ARM ABI.
        data = {
            "_ZN4Core8Portable9SingletonIN8Presonus5Panel10LCDManagerEE11theInstanceE": "B",
            "_ZTIN4Core8Portable9DeletableE": "V",
            "_ZTIN4Core8Portable9SingletonIN8Presonus5Panel10LCDManagerEEE": "V",
            "_ZTIN8Presonus5Panel10LCDManagerE": "V",
            "_ZTSN4Core8Portable9DeletableE": "V",
            "_ZTSN4Core8Portable9SingletonIN8Presonus5Panel10LCDManagerEEE": "V",
            "_ZTSN8Presonus5Panel10LCDManagerE": "V",
            "_ZTVN8Presonus5Panel10LCDManagerE": "V",
        }
        assert {name: fields[0] for name, fields in public.items()} == {
            **dict.fromkeys(expected, "T"), **data
        }
        undefined = run(["nm", "--undefined-only", value]).splitlines()
        assert {line.split()[-1] for line in undefined} == {
            "_ZTVN10__cxxabiv117__class_type_infoE",
            "_ZTVN10__cxxabiv120__si_class_type_infoE",
            "_ZdlPvm",
        }
    else:
        assert len(public) == 3
        assert all(symbol.startswith(("_ZN8Presonus5Panel", "_ZNK8Presonus5Panel"))
                   and CLASS in symbol and fields[0] == "T"
                   for symbol, fields in public.items())
        assert not run(["nm", "--undefined-only", value]).strip()
    return public


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("native", "symbols", "replay"))
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--fixture-sha256", required=True)
    parser.add_argument("--object", type=Path)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    assert digest(args.fixtures) == args.fixture_sha256
    fixture = json.loads(args.fixtures.read_text())
    assert fixture["task_id"] == TASK
    if args.mode == "native":
        assert json.loads(run([sys.executable, "-B", TEST / "native.py"])) == fixture
        print(f"{TASK}: exact original cases independently reproduced")
        return
    surface = symbols(args.object, fixture["originals"][0]["mangled"])
    disassembly = None
    if MODE == "set":
        disassembly = run(["objdump", "-dr", args.object]).split(
            " <" + fixture["originals"][0]["mangled"] + ">:\n", 1)[1].split("\n\n", 1)[0]
        # The canonical Linux x86_64 object branches across the pointer store
        # when the argument equals the loaded binding.
        assert ("\tcmp " in disassembly and "\tje " in disassembly
                and disassembly.index("\tcmp ") < disassembly.index("\tje ")
                < disassembly.index("\tmov ") < disassembly.index("\tret"))
    if args.mode == "symbols":
        print(json.dumps(surface, sort_keys=True))
        return
    results = replay(args.exe, fixture)
    formatting_tools = ["uc-library/.venv/bin/clang-format", "--style=file", "--fallback-style=LLVM"]
    run([*formatting_tools, "--dry-run", "--Werror",
         *[f"uc-library/{name}" for name in SOURCES], TEST / "Replay.cpp"])
    version = run([formatting_tools[0], "--version"]).strip()
    proof_reference = json.loads(args.integration.read_text())
    assert proof_reference["platform"] == "linux" and proof_reference["ctest_passed"] is True

    rows = []
    for original in fixture["originals"]:
        row = {key: original[key] for key in ("original_elf_sha256", "mangled", "firmware", "role")}
        row.update(original_address=original["address"], cpp_compiled=True, portable_ready=False,
                   mangling_namespace_checked=True, domain=DOMAIN,
                   declaration_uncertainties=[DECLARATION],
                   sources={path: digest(Path("uc-library") / path) for path in SOURCES},
                   repository_sources={path: digest(path) for path in CORE_DEPENDENCIES})
        rows.append(row)
    proof = {
        "task_id": TASK, "cpp_differential_passed": True,
        "compiled_mangled_names_matched": True, "portable_ready": False,
        "functions": rows, "proposed_readiness": {"ready": [], "pending": rows},
        "compiled_symbol_surface": surface, "domain": DOMAIN, "limitations": LIMITS,
        "originals": fixture["originals"], "native_scope": fixture["scope"],
        "native_case_count": sum(len(orig["cases"]) for orig in fixture["originals"]),
        "portable_case_count": len(results), "portable_stdout": results, "formatter_version": version,
        "format_check_passed": True, "fixtures_sha256": digest(args.fixtures),
        "object_sha256": digest(args.object), "exe_sha256": digest(args.exe),
        "app_provider_sha256": {path: digest(path) for path in APP_DEPENDENCIES},
        "integration_reference": str(args.integration), "integration_sha256": digest(args.integration),
        "producers": {str(path): digest(path) for path in
                      (TEST / "check.py", TEST / "native.py", TEST / "Replay.cpp")},
        "commands": {"checker_argv": sys.argv, "x86_64_setter_disassembly": disassembly},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n")
    print(f"{TASK}: {proof['native_case_count']} original cases; {len(results)} linked portable cases passed")


if __name__ == "__main__":
    main()
