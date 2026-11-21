"""Check the exact compiled symbol and compare portable replay with ARM state."""
import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE_PATHS = ("include/presonus/DisplayCommandList.hpp", "src/Presonus/DisplayCommandList.cpp")
CORE_PATHS = tuple("third_party/ccl-framework/core/" + name for name in (
    "public/corevector.h",
    "public/gui/corecolor.h",
    "public/gui/corerect.h",
    "portable/gui/corebitmap.h",
    "portable/gui/corebitmap.cpp",
    "portable/gui/coregraphics.h",
))
ELF_SHA256 = "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0"
MANGLED = "_ZN8Presonus18DisplayCommandList10drawBitmapEiiRKN4Core8Portable6BitmapEiiii"
DOMAIN = (
    "13 valid display states: bitmap hits, ordered insertions at beginning/middle/end, "
    "32-entry cap, unsigned ascending identity keys, 16-bit ID wrap, 48/49/50 command "
    "counts, six signed/oversized coordinate values narrowed to 16 bits, and all 1000 "
    "command bytes with untouched padding. Original ARM application ran with real "
    "Linux libc and an explicit bounded comparator callback; the portable replay "
    "runs true pinned CCL Bitmap and ConstVector comparator with actual libc bsearch."
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_symbols(obj):
    symbols = subprocess.check_output(["nm", str(obj)], text=True).splitlines()
    assert any(line.split()[-2:] == ["T", MANGLED] for line in symbols if line.strip())
    assert any(line.split()[-2:] == ["U", "bsearch"] for line in symbols if line.strip())


def replay(exe, fixture):
    for case in fixture["cases"]:
        key = case["key"]
        entries = case["initial_entries"]
        inputs = [case["initial_count"], len(entries), case["initial_id"], *case["args"]]
        for address, ident in entries:
            inputs.extend([address - key, ident])
        result = subprocess.run(
            [str(exe.resolve())], input=" ".join(map(str, inputs)), text=True,
            capture_output=True, check=True,
        ).stdout.splitlines()
        host_key, count, table_count, next_id = map(int, result[0].split())
        delta = host_key - key
        assert [count, table_count, next_id] == [
            case["count"], case["bitmap_count"], case["next_id"],
        ], case
        assert table_count + 2 == len(result)
        expected_table = [[(entry + delta) & 0xFFFFFFFF, ident] for entry, ident in case["table"]]
        assert [list(map(int, line.split())) for line in result[1:-1]] == expected_table, case
        expected_commands = bytearray.fromhex(case["commands"])
        for index in range(case["initial_count"], count):
            offset = 20 * index
            if expected_commands[offset] == 6:
                token, = struct.unpack_from("<I", expected_commands, offset + 8)
                struct.pack_into("<I", expected_commands, offset + 8, (token + delta) & 0xFFFFFFFF)
        assert bytes.fromhex(result[-1]) == expected_commands, case


def readiness():
    return {
        "ready": [],
        "pending": [{
            "original_elf_sha256": ELF_SHA256,
            "mangled": MANGLED,
            "cpp_compiled": True,
            "mangling_namespace_checked": True,
            "cpp_differential_passed": True,
            "portable_ready": False,
            "declaration_uncertainties": [
                "Original return declaration and original vtable base interface are unverified.",
            ],
            "validation_domain": DOMAIN,
            "sources": {name: sha(ROOT / "uc-library" / name) for name in SOURCE_PATHS},
            "repository_sources": {name: sha(ROOT / name) for name in CORE_PATHS},
        }],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--object", type=Path, required=True)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    check_symbols(args.object)
    if args.exe is None:
        return
    fixture = json.loads(args.fixture.read_text())
    assert fixture["elf_sha256"] == ELF_SHA256
    assert len(fixture["cases"]) == 13
    replay(args.exe, fixture)
    receipt = {
        "success": True, "domain": DOMAIN, "validation_domain": DOMAIN,
        "cases": len(fixture["cases"]), "proposed_readiness": readiness(),
        "fixture_sha256": sha(args.fixture), "object_sha256": sha(args.object),
        "executable_sha256": sha(args.exe), "observed_symbol": MANGLED,
        "integration_sha256": sha(args.integration) if args.integration and args.integration != Path("-") else None,
    }
    if args.out and args.out != Path("-"):
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
