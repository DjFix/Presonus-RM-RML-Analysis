"""Replay portable MixerLCD lookup with exact native receiver/path observations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

TASK = "cycle20_g06_s08"
TEST = Path("uc-library/tests/recovery") / TASK
SOURCE = ("include/presonus/panel/MixerLCD.hpp", "src/Presonus/Panel/MixerLCD.cpp")
APP_PROVIDER = (
    "uc-library/include/presonus/panel/FrontPanelComponent.hpp",
    "uc-library/include/presonus/panel/PanelComponent.hpp",
    "uc-library/include/presonus/mixer/MixerComponentBase.hpp",
    "uc-library/src/Presonus/Panel/FrontPanelLifecycle.cpp",
    "uc-library/src/Presonus/Panel/PanelComponentLifecycle.cpp",
)
CCL_PROVIDER = (
    "third_party/ccl-framework/core/portable/corecomponent.h",
    "third_party/ccl-framework/core/portable/corecomponent.cpp",
    "third_party/ccl-framework/core/portable/corecontrollershared.h",
    "third_party/ccl-framework/core/portable/coreparams.h",
    "third_party/ccl-framework/core/portable/coreparams.cpp",
    "third_party/ccl-framework/core/public/corestringbuffer.h",
    "third_party/ccl-framework/core/public/corestringtraits.h",
)
DOMAIN = ("Twenty-one ASCII name cases, including empty, renamed and full 31-byte front root names, "
          "exact and interior prefix, case mismatch, missing and repeated separators, 127-byte boundary, "
          "and long nonprefix passthrough. Exact original ARM observations compare receiver identity, "
          "selected path, and original input pointer reuse against actual current CCL Linux trees. "
          "Distinct front, mixer and nested mixer parameter pointers and genuine misses are checked.")
LIMITS = ("Original return declaration, original ancestry/ARM ABI, unsupported pointer lifetimes, "
          "non-ASCII or null name inputs and hardware are outside the replay. "
          "The native oracle captures calls at exact CCL and libc targets using declared shims. "
          "The Linux replay invokes linked pinned CCL code and uses a wrapper only to observe its callee "
          "and arguments. The port forwards a view of its bounded buffer for the prefix path.")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(argv, **kwargs):
    return subprocess.run(argv, check=True, text=True, capture_output=True, **kwargs).stdout


def encoded(text):
    return text.encode().hex() or "-"


def expected_tag(role, path):
    if role == "front":
        return 6101 if path in ("fader", "/fader") else 0
    return {"fader": 6201, "other/panel/fader": 6202}.get(path, 0)


def replay(executable, fixture):
    inputs = []
    expected = []
    for case in fixture["cases"]:
        inputs.append(f"{encoded(case['front_name'])} {encoded(case['query'])}\n")
        role, path = case["lookup"]
        original = next(item for item in case["boundaries"]
                        if item["callee"] == "Component::lookupParameter")
        original_pointer = int(original["original_input_pointer"])
        expected.append(f"{role} {encoded(path)} {expected_tag(role, path)} {original_pointer}")
    lines = run([str(executable.resolve())], input="".join(inputs)).splitlines()
    assert lines == expected, [(i, a, b) for i, (a, b) in enumerate(zip(lines, expected))
                               if a != b]
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("symbols", "native", "replay"))
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--fixture-sha256", required=True)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--object", type=Path)
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    assert sha(args.fixtures) == args.fixture_sha256
    native = json.loads(args.fixtures.read_text())
    assert native["task_id"] == TASK
    if args.mode == "native":
        assert json.loads(run([sys.executable, "-B", str(TEST / "native.py")])) == native
        print(f"{TASK}: independently reran {len(native['cases'])} original cases")
        return

    object_symbols = run(["nm", "--defined-only", "--format=posix", args.object])
    compiled, = [line.split() for line in object_symbols.splitlines()
                 if line.split()[:2] == [native["mangled"], "T"]]
    undefined_symbols = run(["nm", "--undefined-only", args.object])
    assert any(line.split()[-1] == "_ZNK4Core8Portable9Component15lookupParameterEPKc"
               for line in undefined_symbols.splitlines())
    if args.mode == "symbols":
        print(" ".join(compiled))
        return

    portable = replay(args.exe, native)
    formatter = "uc-library/.venv/bin/clang-format"
    formatter_version = run([formatter, "--version"]).strip()
    formatted = [*[f"uc-library/{path}" for path in SOURCE], str(TEST / "Replay.cpp")]
    run([formatter, "--style=file", "--fallback-style=LLVM", "--dry-run", "--Werror", *formatted])
    integration = json.loads(args.integration.read_text())
    assert integration["ctest_passed"] is True and integration["platform"] == "linux"
    row = {key: native[key] for key in ("original_elf_sha256", "mangled", "firmware", "role")}
    row.update(original_address=native["address"], portable_ready=False,
               cpp_compiled=True, mangling_namespace_checked=True, domain=DOMAIN,
               declaration_uncertainties=["Core::Portable::Parameter* is the pinned provider spelling. The original MixerLCD return declaration is unresolved."],
               sources={path: sha(Path("uc-library") / path) for path in SOURCE},
               repository_sources={path: sha(path) for path in CCL_PROVIDER})
    result = {
        "task_id": TASK, "cpp_differential_passed": True,
        "compiled_mangled_names_matched": True, "portable_ready": False,
        "functions": [row], "compiled_symbol": compiled, "domain": DOMAIN, "limitations": LIMITS,
        "native": native, "native_case_count": len(native["cases"]),
        "portable_case_count": len(portable), "portable_stdout": portable,
        "app_provider_sha256": {path: sha(path) for path in APP_PROVIDER},
        "formatter_version": formatter_version, "format_check_passed": True,
        "fixture_sha256": sha(args.fixtures), "exe_sha256": sha(args.exe),
        "object_sha256": sha(args.object), "integration_sha256": sha(args.integration),
        "integration_reference": str(args.integration), "replay_argv": sys.argv,
        "producers": {str(path): sha(path) for path in
                      (TEST / "check.py", TEST / "native.py", TEST / "Replay.cpp")},
        "proposed_readiness": {"ready": [], "pending": [row]},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"{TASK}: {len(portable)} original and portable lookup cases agree")


if __name__ == "__main__":
    main()
