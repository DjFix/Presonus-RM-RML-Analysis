"""Check the compiled symbol and replay the native output-buffer observations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from native import ADDRESS, ELF_SHA256, MANGLED, OFFSET, RANGE_SHA256, SECTION, SIZE

ROOT = Path(__file__).resolve().parents[4]
SOURCES = ("include/presonus/surface/PresetsPageComponent.hpp",
           "src/Presonus/Surface/PresetsPageComponent.cpp")
CORE = tuple(f"third_party/ccl-framework/core/{path}" for path in (
    "portable/corecomponent.h", "portable/corecomponent.cpp",
    "public/corestringbuffer.h", "public/corevector.h",
))
DOMAIN = (
    "Three native ARM executions with separately mapped receiver, 256-byte output "
    "buffer and stack. Empty, short with nonzero trailing bytes, and 255-character "
    "terminated buffers preserve all bytes. The receiver sentinel stays unchanged "
    "and only the normal stack frame is written. The native frame and preserved "
    "registers are restored and no external calls occur. A constructed and destroyed "
    "portable receiver using the canonical constructor and real pinned CCL invokes "
    "the public member and preserves buffer bytes and the selection sentinel. "
    "Unexpected application dependency calls abort the portable replay."
)
LIMITATION = (
    "The portable declaration is a direct non-static, nonvirtual void member. "
    "Native vtable address matches suggest virtual membership but do not establish "
    "the original dispatch contract. Native r0 is unchanged, which does not identify "
    "a declared return type. Native object lifecycle, layout, ABI and hardware "
    "behavior remain unresolved."
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_symbol(obj):
    lines = subprocess.check_output(["nm", "--defined-only", str(obj)], text=True).splitlines()
    assert any(line.split()[-2:] == ["T", MANGLED] for line in lines), MANGLED


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("fixture", "exe", "object", "integration", "out"):
        parser.add_argument(f"--{option}", type=Path, required=option == "object")
    args = parser.parse_args()
    check_symbol(args.object)
    if args.exe is None:
        return
    fixture = json.loads(args.fixture.read_text())
    assert tuple(fixture[key] for key in (
        "elf_sha256", "mangled", "address", "size", "section", "offset", "range_sha256"
    )) == (ELF_SHA256, MANGLED, ADDRESS, SIZE, SECTION, OFFSET, RANGE_SHA256)
    assert len(fixture["cases"]) == 3
    for case in fixture["cases"]:
        buffer = bytes.fromhex(case["initial_buffer"])
        selected = case["portable_selected_sentinel"]
        output = subprocess.run([str(args.exe.resolve())], check=True, capture_output=True,
                                text=True, input=" ".join(map(str, [selected, *buffer])))
        assert list(map(int, output.stdout.split())) == [
            selected, *bytes.fromhex(case["observed_buffer"]),
        ]
    pending = {
        "original_elf_sha256": ELF_SHA256, "mangled": MANGLED,
        "cpp_compiled": True, "mangling_namespace_checked": True,
        "cpp_differential_passed": True, "portable_ready": False,
        "declaration_uncertainties": [LIMITATION], "validation_domain": DOMAIN,
        "sources": {name: sha(ROOT / "uc-library" / name) for name in SOURCES},
        "repository_sources": {name: sha(ROOT / name) for name in CORE},
    }
    result = {
        "success": True, "validation_domain": DOMAIN, "cases": len(fixture["cases"]),
        "original_range": {key: fixture[key] for key in (
            "elf_sha256", "mangled", "address", "size", "section", "section_name",
            "offset", "range_sha256", "unicorn")},
        "fixture_sha256": sha(args.fixture), "object_sha256": sha(args.object),
        "executable_sha256": sha(args.exe), "observed_symbol": MANGLED,
        "integration_sha256": sha(args.integration) if args.integration != Path("-") else None,
        "proposed_readiness": {"ready": [], "pending": [pending]},
    }
    if args.out != Path("-"):
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
