"""Rerun exact Page and Element destructor bodies against frozen role ELFs."""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    base = args.snapshot / "temp/recovery-work/control10x20-after-4fed70d11/selection/panel-foundation"
    producer = base / "observe_lifecycle_groups.py"
    assert sha(producer.read_bytes()) == "3b47f7ee161b9a43af9b9ec28c521ff8c35191a341cf762fc5f69312e1d735ff"
    spec = importlib.util.spec_from_file_location("lifecycle_oracle", producer)
    oracle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(oracle)
    bindings = (base / "PAGE_LIFECYCLE_VIRTUAL_BINDINGS.json").read_bytes()
    assert sha(bindings) == "9b4f080fae1d32e46e912b18aefc1cd26aa95600bbb237b8a8eadeeb0fdf31cc"
    initializer = (base / "PAGE_AVAILABILITY_INITIALIZER.json").read_bytes()
    pending = json.loads(initializer)["originals"]
    result = {"originals": [], "constructor_initializer": []}
    for digest, classes in json.loads(bindings)["roles"].items():
        role = classes["Page"]["0"]["role"]
        path = {"client": "rootfs/CS18_v13840/home/root/surface",
                "server": "rootfs/RML16AI_Rack_13731/home/root/mixer"}[role]
        data = (args.snapshot / path).read_bytes()
        assert digest == sha(data)
        stream = io.BytesIO(data)
        elf = ELFFile(stream)
        assert elf.elfclass == 32 and elf.little_endian and elf["e_machine"] == "EM_ARM"
        symbols = elf.get_section_by_name(".symtab")
        functions = {}
        for owner, variants in classes.items():
            for number, row in variants.items():
                entry = row["entry"]
                symbol, = symbols.get_symbol_by_name(row["mangled"])
                assert symbol["st_value"] == entry and symbol["st_shndx"] == 12
                size = symbol["st_size"]
                offset, code = oracle.original_range(elf, stream, entry, size, 12)
                assert sha(code) == row["range_sha256"]
                vptr = row["vtable_address_point"]
                assert struct.unpack_from("<I", code, len(code) - 4)[0] == vptr
                slots = oracle.file_bytes_at(elf, stream, vptr, 8)
                assert struct.unpack("<II", slots) == (variants["1"]["entry"], variants["0"]["entry"])
                runtime = row["direct_runtime_calls"]
                if runtime:
                    site, name, meta = runtime[0]
                    target = json.loads(meta)["target_address"]
                    branch, = struct.unpack("<i", code[site-entry:site-entry+4])
                    displacement = (branch << 8) & 0xffffffff
                    if displacement & 0x80000000:
                        displacement -= 1 << 32
                    assert (branch >> 24) & 255 == 0xeb
                    assert site + 8 + (displacement >> 6) == target
                    assert name.split("@")[0] == "operator delete(void*)"
                else:
                    target = None
                functions[owner, int(number)] = {
                    "address": entry, "code": code.hex(), "vptr": vptr,
                    "vtable_slots": slots.hex(), "unsized_delete": target,
                    "mangled": row["mangled"], "file_offset": offset, "size": size,
                    "range_sha256": sha(code), "section": 12,
                }
        for row in pending:
            if row["elf_sha256"] != digest:
                continue
            symbol, = symbols.get_symbol_by_name(row["mangled"])
            address = symbol["st_value"]
            offset, code = oracle.original_range(elf, stream, address, symbol["st_size"], 12)
            assert sha(code) == row["range"]
            for key in ("set_instruction", "write_instruction"):
                instruction = row[key]
                delta = instruction["address"] - address
                assert code[delta:delta + 4].hex() == instruction["bytes"]
            result["constructor_initializer"].append(row | {"file_offset": offset})
        for variant in (0, 1, 2):
            cases = []
            for layout in ([], [None], [[]], [None, [], None, []], [[], [], None, []]):
                cases.append(oracle.replay(functions, "Page", variant, layout))
            target = functions["Page", variant].copy()
            del target["code"]
            result["originals"].append(target | {"elf_sha256": digest, "role": role,
                "firmware": classes["Page"][str(variant)]["firmware"], "variant": variant,
                "child_deleting_target": functions["Element", 0]["address"], "cases": cases})
    args.out.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
