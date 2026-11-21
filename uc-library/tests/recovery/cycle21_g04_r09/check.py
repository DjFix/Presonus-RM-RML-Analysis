"""Fresh GEQ D0 replay against the actual canonical executable and object."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from native import ADDRESS, ELF_SHA, MANGLED, SIZE, observe

ROOT = Path(__file__).resolve().parents[4]
DOMAIN = ("Exact RM13731 ARM D0 normal null/present branches, optional release "
          "before cleanup, verified Dsp D2 and operator delete PLT targets, "
          "and guest receiver deletion via actual unmap. Modeled unwind landing "
          "pad only. Host real CCL property release and Dsp child cleanup, "
          "same live GEQ receiver freed with unsized delete, plus legacy "
          "tagged construction and flatten.")
LIMITS = ("Original construction, layout and overall ABI remain unresolved. "
          "The new independent tagged source-port ownership assumes a "
          "distinct handler and ordinary nonthrowing cleanup. Unwind "
          "landing-pad target verified under an injected continuation.")
SOURCE = ("include/presonus/mixer/GEQComponent.hpp", "src/Presonus/Mixer/GEQComponent.cpp")
DSP = ("include/presonus/DspComponent.hpp", "src/Presonus/DspComponent.cpp",
       "include/presonus/dsp/IController.hpp")
PROVIDERS = ("third_party/ccl-framework/core/public/coreproperty.h",
             "third_party/ccl-framework/core/portable/corecomponent.cpp",
             "third_party/ccl-framework/core/portable/corecomponent.h",
             "third_party/ccl-framework/core/portable/coreparams.h")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def symbol_and_delete_relocation(obj):
    symbols = subprocess.check_output(["nm", "--defined-only", obj], text=True)
    lines = [line for line in symbols.splitlines() if line.split()[-1:] == [MANGLED]]
    assert len(lines) == 1, lines
    scoped = subprocess.check_output(["objdump", "-dr", "--disassemble=" + MANGLED, obj], text=True)
    symbol_start = scoped.index("<" + MANGLED + ">:")
    body = scoped[symbol_start:].split("\n\n", 1)[0]
    # Decode relocations at addresses within D0. Objdump can print relocations
    # for prior functions in a shared .text section, interleaved before the
    # second D0 instruction. Discard addresses below the D0 symbol.
    low = int(lines[0].split()[0], 16)
    relocations = [(int(offset, 16), name)
                   for offset, name in re.findall(r"^\s*([0-9a-f]+):\s+R_\S+\s+(\S+)", body, re.M)]
    relocations = [name for address, name in relocations if address >= low]
    assert sum(bool(re.match(r"^_ZdlPv(?:[-+]|$)", name)) for name in relocations) == 1, body
    assert not any(name.startswith(("_ZdlPvm", "_ZdlPvj")) for name in relocations), body
    return lines, relocations


def compare(exe, fixtures):
    fresh = observe(exe)
    assert fresh == fixtures, "Fresh original/real-provider observations differ from fixture"
    for row in fresh["cases"]:
        if row["mode"] == "modeled-unwind":
            assert row["calls"][-1][0] == "end_cleanup" and not row["deallocated"]
            continue
        assert row["calls"][-1] == ["unsized_delete_unmapped", row["guest_receiver"]]
        expected = row["provider_events"] + [4]
        actual = subprocess.check_output([exe, row["mode"]], text=True)
        assert list(map(int, actual.split())) == expected, (row, actual)
    assert subprocess.check_output([exe, "legacy"], text=True).strip() == "legacy-ok"
    return fresh


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("exe", "object", "fixtures", "out", "integration"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    exe, obj = args.exe.resolve(), args.object.resolve()
    symbols, relocations = symbol_and_delete_relocation(obj)
    actual = compare(exe, json.loads(args.fixtures.read_text()))
    integration = json.loads(args.integration.read_text())
    assert isinstance(integration, dict) and integration
    row = {"original_elf_sha256": ELF_SHA, "mangled": MANGLED,
           "address": ADDRESS, "size": SIZE, "section": 12,
           "firmware": "RM/RML mixer 13731", "role": "server",
           "domain": DOMAIN, "sources": {p: digest(ROOT / "uc-library" / p) for p in SOURCE + DSP},
           "repository_sources": {p: digest(ROOT / p) for p in PROVIDERS},
           "cpp_compiled": True, "mangling_namespace_checked": True,
           "portable_ready": False, "declaration_uncertainties": [LIMITS]}
    proof = {"behavior_passed": True, "domain": DOMAIN,
             "compiled_mangled_names_matched": True, "compiled_symbols": symbols,
             "deleting_destructor_relocations": relocations, "case_count": 3,
             "source_contracts": [LIMITS], "native": actual,
             "proposed_readiness": {"ready": [], "pending": [row]},
             "fixture_sha256": digest(args.fixtures), "executable_sha256": digest(exe),
             "object_sha256": digest(obj), "integration_sha256": digest(args.integration),
             "producer_sha256": digest(__file__), "native_producer_sha256": digest(Path(__file__).with_name("native.py")),
             "replay_source_sha256": digest(Path(__file__).with_name("Replay.cpp"))}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps({"behavior_passed": True, "host_cases": 3, "native_cases": len(actual["cases"])}))


if __name__ == "__main__":
    main()
