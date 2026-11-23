"""Rerun both exact Page name getters with the sealed ARM leaf oracle."""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    base = args.snapshot / "temp/recovery-work/control10x20-after-4fed70d11/selection/panel-foundation"
    producer = base / "observe_leaf_groups.py"
    assert sha(producer.read_bytes()) == "e738587c455de6ff8557c69b07dee02d892c6c942f23cfe1322c1821aa585e6d"
    spec = importlib.util.spec_from_file_location("getter_oracle", producer)
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    observed = (base / "LEAF_NATIVE_OBSERVATIONS.json").read_bytes()
    assert sha(observed) == "2ba2a99c50721e37b3911c294ef9d02b52ed76ae9e0c435110e314ba2ef9b458"
    result = {"originals": []}
    for group in json.loads(observed)["groups"].values():
        for row in group["occurrences"]:
            if row["original_mangled"] != "_ZNK8Presonus5Panel4Page7getNameEv":
                continue
            data = (args.snapshot / row["source_elf"]).read_bytes()
            assert sha(data) == row["elf_sha256"]
            elf = ELFFile(io.BytesIO(data))
            symbol, = elf.get_section_by_name(".symtab").get_symbol_by_name(row["original_mangled"])
            address, size = row["address"], row["size"]
            assert (symbol["st_value"], symbol["st_size"], symbol["st_shndx"]) == (address, size, 12)
            section = elf.get_section(12)
            assert section.name == ".text" and section["sh_flags"] & 4
            displacement = address - section["sh_addr"]
            assert 0 <= displacement <= displacement + size <= section["sh_size"]
            offset = section["sh_offset"] + displacement
            code = data[offset:offset + size]
            assert offset == row["file_offset"] and sha(code) == row["range_sha256"]
            cases = []
            for case in row["cases"]:
                value = bytes.fromhex(case["input"])
                assert value[-1] == 0 and b"\0" not in value[:-1]
                cases.append(oracle.replay(address, code, "pointer", case["receiver"], value[:-1]))
            assert cases == row["cases"]
            result["originals"].append(row | {"mangled": row["original_mangled"], "section": 12, "cases": cases})
    assert len(result["originals"]) == 2
    args.out.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
