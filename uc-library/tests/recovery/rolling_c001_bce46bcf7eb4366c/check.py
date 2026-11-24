import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from native import observe

TASK = "rolling_c001_bce46bcf7eb4366c"
TEST = Path("uc-library/tests/recovery") / TASK
SOURCE = Path("uc-library/src/Presonus/Surface/CascadeHandler.cpp")
HEADER = Path("uc-library/include/presonus/surface/CascadeHandler.hpp")
FORMATTER = "uc-library/.venv/bin/clang-format"
LIMITATIONS = [
    "Original return declaration and exact virtual/member interface remain unresolved.",
    "The portable declaration is a nonvirtual void method. Original inheritance, layout, ARM ABI and hardware remain unverified.",
    "Native execution uses synthetic mapped memory and excludes vtable dispatch and thunk behavior.",
]
DOMAIN = (
    "Three original ARM executions with distinct mapped receiver locations and sentinel state "
    "verify return PC, restored SP/FP, unchanged receiver and argument registers, and only "
    "four stack-frame writes. Three separately constructed portable receivers retain their "
    "root reference and empty pinned Core vector across the call."
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check():
    parser = argparse.ArgumentParser()
    for flag in ("exe", "object", "integration", "out", "elf", "fixtures"):
        parser.add_argument("--" + flag, required=True)
    args = parser.parse_args()
    began = datetime.now(timezone.utc).isoformat()
    original = observe(Path(args.elf))
    assert original == json.loads(Path(args.fixtures).read_text())
    symbols_argv = ["nm", "--defined-only", args.object]
    symbols = subprocess.check_output(symbols_argv, text=True).splitlines()
    assert sum(line.split()[-1] == original["mangled"] for line in symbols if line.split()) == 1

    exe_argv = [str(Path(args.exe).resolve())]
    output = subprocess.check_output(exe_argv, text=True).splitlines()
    assert output == [case["portable_observation"] for case in original["cases"]]
    formatted = [HEADER, SOURCE, TEST / "Replay.cpp"]
    format_argv = [FORMATTER, "--style=file", "--fallback-style=LLVM", "--dry-run",
                   "--Werror", *map(str, formatted)]
    subprocess.run(format_argv, check=True)
    dependencies = subprocess.check_output(
        ["c++", "-std=c++17", "-Iuc-library/include", "-Ithird_party/ccl-framework",
         "-MM", str(SOURCE), str(TEST / "Replay.cpp")], text=True
    ).replace("\\\n", "").split()
    core = {path: digest(path) for path in dependencies if path.startswith("third_party/ccl-framework/core/")}
    sources = [*formatted, TEST / "native.py", TEST / "check.py", Path(args.fixtures)]
    row = {
        "original_elf_sha256": original["elf_sha256"], "mangled": original["mangled"],
        "original_address": original["address"], "cpp_compiled": True,
        "mangling_namespace_checked": True, "portable_ready": False,
        "original_function_verified": False, "hardware_verified": False,
        "validation_domain": DOMAIN, "domain": DOMAIN,
        "declaration_uncertainties": LIMITATIONS,
        "sources": {str(p.relative_to("uc-library")): digest(p) for p in sources},
        "repository_sources": core,
    }
    proof = {
        "passed": True, "proposed_readiness": {"ready": [], "pending": [row]},
        "native": original, "native_elf": args.elf, "portable_case_count": len(output),
        "native_case_count": len(original["cases"]), "object_sha256": digest(args.object),
        "executable_sha256": digest(args.exe), "integration": args.integration,
        "integration_sha256": None if args.integration == "local" else digest(args.integration),
        "format_argv": format_argv, "format_configuration_sha256": digest(".clang-format"),
        "formatter_version": subprocess.check_output([FORMATTER, "--version"], text=True).strip(),
        "symbols_argv": symbols_argv, "portable_argv": exe_argv,
        "observed_symbol": original["mangled"], "replay_argv": __import__("sys").argv,
        "began_utc": began, "ended_utc": datetime.now(timezone.utc).isoformat(),
    }
    Path(args.out).write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{len(output)} original and portable cases matched")


if __name__ == "__main__":
    check()
