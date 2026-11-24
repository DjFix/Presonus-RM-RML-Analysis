"""Compare compiled Linux behavior with each sealed ARM observation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
LIBRARY = ROOT / "uc-library"
SOURCES = (
    "include/presonus/mixer_state/MixerState.hpp",
    "src/mixer_state/MixerState.cpp",
)
PROVIDERS = (
    "third_party/ccl-framework/core/portable/corecomponent.h",
    "third_party/ccl-framework/core/public/corestringbuffer.h",
    "third_party/ccl-framework/core/public/corevector.h",
)
SYMBOL = "_ZNK8Presonus14IPresetHandler20getEmptyPresetStringEv"
DOMAIN = (
    "Three offline ARM calls per exact ELF range with two synthetic receiver addresses "
    "and repeated pointer identity, mapped read-only NUL and preserved receiver bytes. "
    "Linux concrete const receivers return a non-null NUL pointer with repeated identity, "
    "preserved receiver bytes and survival across receiver destruction."
)
UNCERTAINTIES = [
    "Original return declaration and pointee const qualification are unresolved.",
    "Original virtual declaration, object layout, ARM ABI and hardware behavior are unverified.",
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("fixtures", "object", "exe", "integration", "out"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    fixture = json.loads(args.fixtures.read_text())
    observations = fixture["observations"]
    assert len(observations) == len({row["elf_sha256"] for row in observations}) == 2
    nm_argv = ["nm", "--defined-only", str(args.object)]
    symbol_lines = [
        line for line in subprocess.check_output(nm_argv, text=True).splitlines()
        if line.split()[-1:] == [SYMBOL]
    ]
    assert len(symbol_lines) == 1 and symbol_lines[0].split()[-2] in ("T", "W")
    portable = subprocess.check_output([str(args.exe.resolve())], text=True).strip()
    sources = {name: digest(LIBRARY / name) for name in SOURCES}
    providers = {name: digest(ROOT / name) for name in PROVIDERS}
    pending = []
    for row in observations:
        assert row["mangled"] == SYMBOL and row["receiver_preserved"]
        assert row["receiver_cases"] == 3 and len(set(row["return_words"])) == 1
        assert row["return_words"][0] and row["literal_hex"] == portable == "00"
        pending.append(dict(
            original_elf_sha256=row["elf_sha256"], mangled=SYMBOL,
            original_address=row["address"], cpp_compiled=True,
            mangling_namespace_checked=True, portable_ready=False,
            domain=DOMAIN, sources=sources, repository_sources=providers,
            declaration_uncertainties=UNCERTAINTIES,
        ))
    integration = None
    if args.integration != Path("none"):
        assert json.loads(args.integration.read_text())["ctest_passed"]
        integration = {"path": str(args.integration), "sha256": digest(args.integration)}
    format_argv = ["uc-library/.venv/bin/clang-format", "--version"]
    proof = dict(
        cpp_differential_passed=True, portable_ready=False,
        cpp_compiled=True, mangling_namespace_checked=True,
        observations=observations, native_cases=6, portable_executions=1,
        native_versions={key: fixture[key] for key in ("unicorn", "pyelftools")},
        native_producer_sha256=digest(Path(__file__).with_name("native.py")),
        replay_producer_sha256=digest(Path(__file__)),
        replay_source_sha256=digest(Path(__file__).with_name("Replay.cpp")),
        clang_format=subprocess.check_output(format_argv, text=True).strip(),
        fixtures_sha256=digest(args.fixtures), object_sha256=digest(args.object),
        executable_sha256=digest(args.exe), compiled_symbol=symbol_lines[0],
        symbol_argv=nm_argv, portable_argv=[str(args.exe.resolve())],
        domain=DOMAIN, declaration_uncertainties=UNCERTAINTIES,
        integration=integration,
        proposed_readiness={"ready": [], "pending": pending},
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print("Linux receiver matches the NUL text from both native ELF identities.")


if __name__ == "__main__":
    main()
