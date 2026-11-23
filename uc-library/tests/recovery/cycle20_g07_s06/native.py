"""Fresh offline replay of original Page selection and Element activation."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP


def sha(data):
    return hashlib.sha256(data).hexdigest()


def probe(page_code, activation_code, table_address, table, old, new):
    receiver, stack, stop = 0x50000000, 0x60000000, 0x70000000
    elements = [0, 0x51000000, 0x52000000]
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    mapped = set()
    for address, data in (*[page_code, activation_code, (table_address, table)],
                          (receiver + 0xd0, struct.pack("<I", elements[old])),
                          *[(item, struct.pack("<I", table_address)) for item in elements[1:]],
                          *[(item + 0x74, struct.pack("<II", 15, 1)) for item in elements[1:]],
                          (stack, b"\0"), (stop, b"\0")):
        for page in range(address & ~4095, ((address + len(data) - 1) & ~4095) + 1, 4096):
            if page not in mapped:
                uc.mem_map(page, 4096)
                mapped.add(page)
        uc.mem_write(address, data)

    def state():
        return elements.index(struct.unpack("<I", uc.mem_read(receiver + 0xd0, 4))[0])

    trace = []

    def observe(emu, address, _, __):
        if address == activation_code[0]:
            trace.append([elements.index(emu.reg_read(UC_ARM_REG_R0)), emu.reg_read(UC_ARM_REG_R1), state()])

    uc.hook_add(UC_HOOK_CODE, observe)
    for reg, value in [(UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, elements[new]),
                       (UC_ARM_REG_LR, stop), (UC_ARM_REG_SP, stack + 4080)]:
        uc.reg_write(reg, value)
    uc.emu_start(page_code[0], stop, count=150)
    assert uc.reg_read(UC_ARM_REG_PC) == stop and uc.reg_read(UC_ARM_REG_SP) == stack + 4080
    states = [list(struct.unpack("<II", uc.mem_read(element + 0x74, 8))) for element in elements[1:]]
    return {"final_active": state(), "ordered_element_activation_with_observed_page_state": trace,
            "element_after": states, "input": [old, new]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    source = args.snapshot / ("temp/recovery-work/control10x20-after-4fed70d11/"
                              "selection/panel-foundation/ELEMENT_ACTIVATION_NATIVE_OBSERVATIONS.json")
    data = source.read_bytes()
    assert sha(data) == "1602c9c2850aa6782deab69bd488e5c5a382411cf5281b244ff257f0b3980f3a"
    originals = []
    for digest, item in json.loads(data)["observations"].items():
        data = (args.snapshot / item["source"]).read_bytes()
        assert sha(data) == digest
        elf = ELFFile(io.BytesIO(data))
        assert elf.elfclass == 32 and elf.little_endian and elf["e_machine"] == "EM_ARM"
        symbols = elf.get_section_by_name(".symtab")
        records = {}
        for key, row in item["members"].items():
            mangled = row["original_mangled"]
            sym, = symbols.get_symbol_by_name(mangled)
            address, size = row["original_address"], row["original_size"]
            assert (sym["st_value"], sym["st_size"], sym["st_shndx"]) == (address, size, 12)
            sec = elf.get_section(12)
            delta = address - sec["sh_addr"]
            assert sec.name == ".text" and 0 <= delta <= delta + size <= sec["sh_size"]
            offset = sec["sh_offset"] + delta
            code = data[offset:offset + size]
            assert sha(code) == row["content_sha256"]
            records[key] = ({"mangled": mangled, "address": address, "size": size,
                             "section": 12, "file_offset": offset, "range_sha256": sha(code)}, (address, code))
        table = item["element_vtable"]
        vtable, = symbols.get_symbol_by_name("_ZTVN8Presonus5Panel7ElementE")
        section = elf.get_section(vtable["st_shndx"])
        assert table["address"] == vtable["st_value"] + 8
        offset = section["sh_offset"] + table["address"] - section["sh_addr"]
        assert offset == table["file_offset"]
        table_data = data[offset:offset + 48]
        activation = records["element_activate"]
        assert struct.unpack("<I", table_data[44:48])[0] == activation[1][0]
        target = records["page_active_element"]
        previous = item["cases"]["page_active_element"]
        cases = [probe(target[1], activation[1], table["address"], table_data, *case["input"]) for case in previous]
        assert cases == previous, cases
        role = item["role"]
        originals.append(target[0] | {"elf_sha256": digest, "role": role,
            "firmware": "CS18AI surface 13840" if role == "client" else "RM/RML mixer 13731",
            "cases": cases, "activation_provider": activation[0], "activation_table": table})
    assert len(originals) == 2
    args.out.write_text(json.dumps({"originals": originals}, indent=2) + "\n")


if __name__ == "__main__":
    main()
