"""Validate the Linux default meter hook against its ARM observations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from native import IDENTITY, RANGE_SHA256

HERE = Path(__file__).parent
FORMAT = [
    "uc-library/.venv/bin/clang-format", "--style=file", "--fallback-style=LLVM",
    "--dry-run", "--Werror",
    "uc-library/include/presonus/panel/FrontPanelComponent.hpp",
    "uc-library/src/Presonus/Panel/FrontPanelComponent.cpp",
    str(HERE / "Replay.cpp"),
]
SOURCES = (
    "include/presonus/panel/FrontPanelComponent.hpp",
    "include/presonus/mixer/ChannelComponent.hpp",
    "src/Presonus/Panel/FrontPanelComponent.cpp",
    "src/Presonus/Panel/FrontPanelLifecycle.cpp",
)
CORE = (
    "third_party/ccl-framework/core/portable/corecomponent.h",
    "third_party/ccl-framework/core/portable/coreattributes.h",
    "third_party/ccl-framework/core/public/corevector.h",
    "third_party/ccl-framework/core/public/corestringbuffer.h",
    "third_party/ccl-framework/core/system/coredebug.h",
)
DOMAIN = (
    "Two isolated ARM executions of the exact 16-byte RM/RML default hook, "
    "with distinct receiver/channel memory patterns and frame/stack values. "
    "Both restore receiver, argument, frame and stack registers, make no calls, "
    "and write only four frame words. Two Linux cases call the default hook on "
    "real pinned-CCL-backed panel/channel objects with idle and active source-port "
    "state, require unchanged object/state bytes and reject every app service call."
)
UNCERTAINTIES = [
    "The ARM body preserves r0; that observation does not determine the original return declaration. The portable hook uses void.",
    "The vtable entry supports virtual membership. Original access, slot/layout, firmware dispatch and hardware behavior remain unverified.",
    "Original construction is outside the checked domain. ARM objects are sentinel memory, and Linux uses existing source-port constructors.",
]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--object", required=True)
    parser.add_argument("--exe")
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--integration", default="none")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--symbols-only", action="store_true")
    args = parser.parse_args()
    names = subprocess.check_output(["nm", "--defined-only", args.object], text=True)
    matches = [line for line in names.splitlines() if line.split()[-1:] == [IDENTITY["mangled"]]]
    assert len(matches) == 1, matches
    print(matches[0])
    if args.symbols_only:
        return

    fixture = json.loads(args.fixtures.read_text())
    assert all(fixture["original"][key] == value for key, value in IDENTITY.items())
    assert fixture["original"]["range_sha256"] == RANGE_SHA256
    assert [case["name"] for case in fixture["cases"]] == ["idle", "active"]
    for case in fixture["cases"]:
        assert not case["external_calls"] and len(case["writes"]) == 4
        assert all(case["stack"] - 16 <= write[0] < case["stack"] for write in case["writes"])
        expected = "unchanged" if case["objects_unchanged"] else "changed"
        result = subprocess.run(
            [str(Path(args.exe).resolve()), case["name"]],
            check=True, text=True, capture_output=True,
        )
        assert result.stdout.splitlines() == [expected] and not result.stderr, result

    subprocess.run(FORMAT, check=True)
    sources = {source: digest(Path("uc-library") / source) for source in SOURCES}
    core = {path: digest(path) for path in CORE}
    row = {
        "original_elf_sha256": IDENTITY["elf_sha256"],
        "mangled": IDENTITY["mangled"],
        "original_address": IDENTITY["address"],
        "cpp_compiled": True,
        "mangling_namespace_checked": True,
        "portable_ready": False,
        "domain": DOMAIN,
        "sources": sources,
        "repository_sources": core,
        "declaration_uncertainties": UNCERTAINTIES,
    }
    count = len(fixture["cases"])
    proof = {
        "cpp_differential_passed": True,
        "compiled_mangled_names_matched": True,
        "portable_ready": False,
        "domain": DOMAIN,
        "functions": [row],
        "mangled_names": [IDENTITY["mangled"]],
        "verified_symbols": matches,
        "original": fixture["original"],
        "native_fixture": {
            "sha256": digest(args.fixtures),
            "unicorn_version": fixture["unicorn_version"],
            "pyelftools_version": fixture["pyelftools_version"],
            "case_count": count,
        },
        "case_count": count,
        "checker_sha256": digest(__file__),
        "native_producer_sha256": digest(HERE / "native.py"),
        "replay_source_sha256": digest(HERE / "Replay.cpp"),
        "object_sha256": digest(args.object),
        "executable_sha256": digest(args.exe),
        "integration_sha256": digest(args.integration) if args.integration != "none" else None,
        "format_argv": FORMAT,
        "format_version": subprocess.check_output([FORMAT[0], "--version"], text=True).strip(),
        "proposed_readiness": {"ready": [], "pending": [row]},
    }
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(f"{count} Linux cases matched the ARM fixture")


if __name__ == "__main__":
    main()
