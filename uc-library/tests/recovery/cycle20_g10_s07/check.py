"""Check compiled teardown variants and the same-receiver disposal replay."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from native import CLASS, IDENTITIES, PREFIX

ROOT = Path(__file__).resolve().parents[4]
BASE = "OffscreenElement"
SOURCES = (
    f"include/presonus/panel/{CLASS}.hpp",
    f"src/Presonus/Panel/{CLASS}.cpp",
    "include/presonus/panel/Element.hpp", "src/Presonus/Panel/Element.cpp",
) + (("include/presonus/panel/OffscreenElement.hpp",
      "src/Presonus/Panel/OffscreenElement.cpp") if BASE != "Element" else ())
UNCERTAINTIES = [
    "Portable class and typed base composition cover tested teardown only. "
    "Original full class declarations, constructor, receiver layout and ARM ABI remain unresolved.",
]
DOMAIN = (
    f"{CLASS} direct and native vtable D1/D0 in CS18 and RM, two payload seeds each. "
    "Actual original instructions reset the receiver's first word to the Element vtable "
    "address point, preserve the remaining bytes and call the exact unsized allocator "
    "target only for D0. The native boundary unmaps the same receiver and a post-return "
    "read fails. Portable qualified D1 and virtual delete through Element preserve or "
    "unmap the same page respectively, and the linked unsized delete hook verifies disposal."
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(*argv):
    return subprocess.check_output(argv, text=True)


def compiled_variants(obj):
    symbols = {}
    for line in run("nm", "--defined-only", str(obj)).splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[-1] in {PREFIX + v + "Ev" for v in ("D0", "D1", "D2")}:
            symbols[fields[-1]] = fields[0]
    assert len(symbols) == 3
    assert symbols[PREFIX + "D1Ev"] == symbols[PREFIX + "D2Ev"]
    base_prefix = f"_ZN8Presonus5Panel{len(BASE)}{BASE}"
    boundary = "_ZdlPv" if BASE == "Element" else base_prefix + "dlEPv"
    dump = run("objdump", "-dr", "--disassemble=" + PREFIX + "D0Ev", str(obj))
    assert re.search(r"R_X86_64_(?:PLT32|PC32)\s+" + re.escape(boundary) + r"(?:-0x4)?\s*$",
                     dump, re.MULTILINE), dump
    assert base_prefix + "D2Ev" in dump
    assert "_ZdlPvm" not in dump
    return {"symbols": symbols, "D0_compiled_allocator_target": boundary,
            "D0_disassembly": dump, "D2_incidental_host_emission": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path)
    parser.add_argument("--object", type=Path, required=True)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--integration", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    compiled = compiled_variants(args.object)
    if args.exe is None:
        print(json.dumps(compiled))
        return

    fixture = json.loads(args.fixture.read_text())
    assert fixture["class"] == CLASS
    assert [row["role"] for row in fixture["originals"]] == list(IDENTITIES)
    pending, observations = [], []
    for original in fixture["originals"]:
        role, elf = original["role"], original["elf_sha256"]
        assert elf == IDENTITIES[role][0]
        assert len(original["cases"]) == 8 and len(original["ranges"]) == 2
        for row in original["ranges"]:
            assert row["mangled"] == PREFIX + row["variant"] + "Ev"
            pending.append({
                "original_elf_sha256": elf, "mangled": row["mangled"],
                "cpp_compiled": True, "mangling_namespace_checked": True,
                "cpp_differential_passed": True, "portable_ready": False,
                "validation_domain": DOMAIN,
                "declaration_uncertainties": UNCERTAINTIES,
                "sources": {name: sha(ROOT / "uc-library" / name) for name in SOURCES},
            })
        for case in original["cases"]:
            variant, seed = case["variant"], case["seed"]
            count, unmapped = map(int, run(str(args.exe.resolve()), variant, str(seed)).split())
            assert count == len(case["delete_receivers"])
            assert unmapped == case["receiver_unmapped_after_return"]
            observations.append({"role": role, "native_route": case["route"],
                                 "variant": variant, "seed": seed,
                                 "portable_route": "qualified" if variant == "D1" else "virtual delete",
                                 "portable_delete_calls": count, "portable_receiver_unmapped": bool(unmapped)})
    receipt = {
        "success": True, "validation_domain": DOMAIN, "cases": len(observations),
        "native_ranges": [{k: v for k, v in entry.items() if k != "cases"}
                          for entry in fixture["originals"]],
        "portable_observations": observations, "compiled_teardown": compiled,
        "executable_sha256": sha(args.exe), "fixture_sha256": sha(args.fixture),
        "object_sha256": sha(args.object), "replay_sha256": sha(__file__),
        "integration_sha256": (
            sha(args.integration)
            if args.integration and args.integration != Path("-") else None
        ),
        "proposed_readiness": {"ready": [], "pending": pending},
    }
    if args.out and args.out != Path("-"):
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
