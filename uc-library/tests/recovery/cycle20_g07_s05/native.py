"""Replay both exact Book active Page lookups with role-specific CCL storage."""
import argparse
import hashlib
import importlib
import io
import json
from pathlib import Path
import struct
import sys

from elftools.elf.elffile import ELFFile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    base = args.snapshot / "temp/recovery-work/control10x20-after-4fed70d11/selection/panel-foundation"
    blob = (base / "ACTIVE_PAGE_NATIVE_OBSERVATIONS.json").read_bytes()
    assert sha(blob) == "d273a299035d8dff571a028c0dd4a8d2d468cca6075e1983c7de72dc4aacecd1"
    assert sha((base / "observe_lifecycle_groups.py").read_bytes()) == "3b47f7ee161b9a43af9b9ec28c521ff8c35191a341cf762fc5f69312e1d735ff"
    assert sha((base / "observe_active_page.py").read_bytes()) == "ebc7f8b0abf1dc2f9098d2e5d20636bff3b3a6d7f8c1960224d015f69beb16a3"
    sys.path.insert(0, str(base))
    oracle = importlib.import_module("observe_active_page")
    evidence = json.loads(blob)
    ccl = evidence["pinned_ccl"]
    assert sha((args.snapshot / ccl["path"]).read_bytes()) == ccl["sha256"]
    originals = []
    for row in evidence["occurrences"]:
        data = (args.snapshot / row["path"]).read_bytes()
        assert sha(data) == row["elf_sha256"]
        stream = io.BytesIO(data)
        elf = ELFFile(stream)
        assert elf.elfclass == 32 and elf.little_endian and elf["e_machine"] == "EM_ARM"
        symbols = elf.get_section_by_name(".symtab")
        name = row["original_mangled"]
        symbol, = symbols.get_symbol_by_name(name)
        address, size = row["address"], symbol["st_size"]
        assert symbol["st_value"] == address and size == 64 and symbol["st_shndx"] == 12
        offset, code = oracle.original_range(elf, stream, address, size, 12)
        assert sha(code) == row["range_sha256"]
        error, = symbols.get_symbol_by_name(oracle.ERROR)
        errsec = elf.get_section(error["st_shndx"])
        assert errsec["sh_type"] == "SHT_NOBITS" and errsec["sh_flags"] & 2
        error_address, = struct.unpack("<I", code[-4:])
        assert error_address == row["error"]["address"] == error["st_value"] and error["st_size"] == 4
        cases = [oracle.probe(address, code, error_address, case["index"], case["slots"], case["error_value"])
                 for case in row["cases"]]
        assert len(cases) == 48 and cases == row["cases"]
        originals.append(row | {"mangled": name, "file_offset": offset, "section": 12, "size": size,
            "firmware": "CS18AI surface 13840" if row["role"] == "client" else "RM/RML mixer 13731", "cases": cases})
    assert len(originals) == 2
    args.out.write_text(json.dumps({"originals": originals, "pinned_ccl": ccl}, indent=2) + "\n")


if __name__ == "__main__":
    main()
