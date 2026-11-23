"""Replay Page or Book active parameter with the genuine ARM vtable targets."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP


def sha(data):
    return hashlib.sha256(data).hexdigest()


def word(value):
    return struct.pack("<I", value)


def probe(row, code, tables, case):
    book, page, element = 0x40000000, 0x41000000, 0x42000000
    stack, stop = 0x60000000, 0x70000000
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    mapped = set()

    def put(address, data):
        for mapped_page in range(address & ~4095, ((address + len(data) - 1) & ~4095) + 1, 4096):
            if mapped_page not in mapped:
                uc.mem_map(mapped_page, 4096)
                mapped.add(mapped_page)
        uc.mem_write(address, data)

    for address, data in (*code.values(), *tables.values()):
        put(address, data)
    selection = case["active_element"]
    if selection:
        put(element, word(row["tables"][selection]["address"]))
    put(page + 0xd0, word(element if selection else 0))
    put(book + 4, struct.pack("<II", book + 0x200, len(case["slots"])))
    put(book + 0x90, struct.pack("<i", case["selected"]))
    for index, present in enumerate(case["slots"]):
        put(book + 0x200 + index * 4, word(page if present else 0))
    put(row["encoder"]["address"], word(13303488 if case["parameter_present"] else 0))
    put(row["error"]["address"], word(page if case["error_has_page"] else 0))
    put(stack, b"\0")
    put(stop, b"\0")
    trace, writes = [], []
    labels = {address: name for name, (address, _) in code.items()}

    def visit(_emu, address, _size, _user):
        if address in labels:
            trace.append(labels[address])

    uc.hook_add(UC_HOOK_CODE, visit)
    uc.hook_add(UC_HOOK_MEM_WRITE, lambda _u, _op, a, n, _value, _user: writes.append((a, n)))
    uc.reg_write(UC_ARM_REG_R0, page if case["entry"] == "Page" else book)
    uc.reg_write(UC_ARM_REG_LR, stop)
    uc.reg_write(UC_ARM_REG_SP, stack + 4080)
    uc.emu_start(code[case["entry"]][0], stop, count=150)
    assert uc.reg_read(UC_ARM_REG_PC) == stop and uc.reg_read(UC_ARM_REG_SP) == stack + 4080
    assert all(stack <= address < address + size <= stack + 4096 for address, size in writes)
    return case | {"result": uc.reg_read(UC_ARM_REG_R0), "trace": trace}


def original_range(elf, data, index, address, size, offset, digest):
    section = elf.get_section(index)
    delta = address - section["sh_addr"]
    assert 0 <= delta <= delta + size <= section["sh_size"]
    assert offset == section["sh_offset"] + delta
    result = data[offset:offset + size]
    assert sha(result) == digest
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--target", choices=("Page", "Book"), required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    path = args.snapshot / ("temp/recovery-work/control10x20-after-4fed70d11/"
                            "selection/panel-foundation/ACTIVE_PARAM_NATIVE_OBSERVATIONS.json")
    data = path.read_bytes()
    assert sha(data) == "77235d770387192ce12502e8167be4a12d34a9af0f773ecd0b3873defb3d53ed"
    doc = json.loads(data)
    ccl = doc["ccl"]
    assert sha((args.snapshot / ccl["path"]).read_bytes()) == ccl["sha256"]
    originals = []
    for row in doc["observations"]:
        data = (args.snapshot / row["path"]).read_bytes()
        assert sha(data) == row["elf_sha256"]
        elf = ELFFile(io.BytesIO(data))
        assert elf.elfclass == 32 and elf.little_endian and elf["e_machine"] == "EM_ARM"
        symbols = elf.get_section_by_name(".symtab")
        code = {}
        for name, item in row["functions"].items():
            sym, = symbols.get_symbol_by_name(item["mangled"])
            entry = item["address"]
            assert sym["st_value"] == entry and sym["st_size"] == item["size"]
            assert sym["st_shndx"] == item["section"] and elf.get_section(item["section"]).name == ".text"
            code[name] = (entry, original_range(elf, data, item["section"], entry, item["size"],
                                                item["file_offset"], item["range_sha256"]))
        tables = {}
        for name, table in row["tables"].items():
            sym, = symbols.get_symbol_by_name(table["mangled"])
            start = sym["st_value"]
            assert start + 8 == table["address"] and sym["st_shndx"] == table["section"]
            assert sym["st_size"] == table["size"]
            body = original_range(elf, data, table["section"], start, table["size"],
                                  table["file_offset"], table["range_sha256"])
            assert struct.unpack_from("<I", body, 8 + table["slot"])[0] == code[name][0] == table["slot_target"]
            tables[name] = (start, body)
        for cell in (row["encoder"], row["error"]):
            sym, = symbols.get_symbol_by_name(cell["mangled"])
            assert sym["st_shndx"] == cell["section"] and sym["st_size"] == cell["size"]
            assert sym["st_value"] == cell["address"] and elf.get_section(cell["section"])["sh_type"] == "SHT_NOBITS"
        assert struct.unpack("<I", code["Book"][1][-4:])[0] == row["error"]["address"]
        assert struct.unpack("<I", code["TextEntryElement"][1][-4:])[0] == row["encoder"]["address"]
        expected = [case for case in row["cases"] if case["entry"] == args.target]
        cases = [probe(row, code, tables, case) for case in expected]
        assert cases == expected and len(cases) == (6 if args.target == "Page" else 48)
        role = row["role"]
        originals.append(row["functions"][args.target] | {"elf_sha256": row["elf_sha256"], "role": role,
            "firmware": "CS18AI surface 13840" if role == "client" else "RM/RML mixer 13731",
            "cases": cases, "providers": row["functions"], "vtable_bindings": row["tables"],
            "data_bindings": {"encoder": row["encoder"], "error": row["error"]}})
    assert len(originals) == 2
    args.out.write_text(json.dumps({"originals": originals, "ccl": ccl}, indent=2) + "\n")


if __name__ == "__main__":
    main()
