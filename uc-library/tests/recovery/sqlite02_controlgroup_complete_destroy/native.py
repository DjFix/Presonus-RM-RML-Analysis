"""Run hash-bound Group and Control ARM instructions in disposable guest pages."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0
from unicorn.arm_const import UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP

GROUP = "_ZN8Presonus5Panel12ControlGroup"
CONTROL = "_ZN8Presonus5Panel7Control"
GROUP_CTORS = {"D2": "C2Eii", "D1": "C1Eii", "D0": "C1Eii"}
PAGE = 0x1000
RECEIVER = 0x1000000
STACK = 0x1100000
STOP = 0x1200000
CASES = [[], [0], [1], [1, 0, 2]]


def digest(data):
    return sha256(data).hexdigest()


def observe(original, firmware_root):
    path = firmware_root / original["elf_path"]
    raw = path.read_bytes()
    assert digest(raw) == original["elf"]
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        symbols = elf.get_section_by_name(".symtab")

        def body(name):
            symbol, = symbols.get_symbol_by_name(name)
            index = symbol["st_shndx"]
            section = elf.get_section(index)
            address, size = symbol["st_value"], symbol["st_size"]
            offset = section["sh_offset"] + address - section["sh_addr"]
            data = raw[offset:offset + size]
            return {"mangled": name, "address": address, "size": size,
                    "section": index, "section_name": section.name,
                    "file_offset": offset, "range_sha256": digest(data),
                    "range_hex": data.hex()}

        target = body(original["mangled"])
        for key in target:
            assert target[key] == original[key], (key, target, original)

        variant = target["mangled"][-4:-2]
        group_ctor = body(GROUP + GROUP_CTORS[variant])
        add = body(GROUP + "3addEPNS0_7ControlE")
        control_ctor = body(CONTROL + "C1Ei")
        control_d0 = body(CONTROL + "D0Ev")
        vtable = body("_ZTVN8Presonus5Panel7ControlE")
        assert struct.unpack_from("<I", raw, vtable["file_offset"] + 8 + 12)[0] == control_d0["address"]
        relocations = elf.get_section_by_name(".rel.plt")
        dynsym = elf.get_section(relocations["sh_link"])
        plt = elf.get_section_by_name(".plt")
        delete, = [plt["sh_addr"] + 20 + 12 * index
                   for index, relocation in enumerate(relocations.iter_relocations())
                   if dynsym.get_symbol(relocation["r_info_sym"]).name == "_ZdlPv"]
        segments = [(segment["p_vaddr"], segment.data(), segment["p_memsz"])
                    for segment in elf.iter_segments() if segment["p_type"] == "PT_LOAD"]

    rows = []
    for entries in CASES:
        uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        image_end = max(addr + size for addr, _, size in segments)
        uc.mem_map(0, (image_end + PAGE - 1) & -PAGE)
        for addr, data, _ in segments:
            uc.mem_write(addr, data)
        uc.mem_map(STACK, PAGE)
        uc.mem_map(STOP, PAGE)
        uc.mem_map(RECEIVER, PAGE)
        names = {RECEIVER: "group"}
        for entry in filter(None, entries):
            address = RECEIVER + entry * PAGE
            uc.mem_map(address, PAGE)
            names[address] = str(entry)

        def invoke(function, receiver, one=0, two=0):
            uc.reg_write(UC_ARM_REG_SP, STACK + PAGE - 16)
            uc.reg_write(UC_ARM_REG_LR, STOP)
            uc.reg_write(UC_ARM_REG_R0, receiver)
            uc.reg_write(UC_ARM_REG_R1, one)
            uc.reg_write(UC_ARM_REG_R2, two)
            uc.emu_start(function["address"], STOP, count=10000)
            assert uc.reg_read(UC_ARM_REG_PC) == STOP

        invoke(group_ctor, RECEIVER, 42, 0)
        for entry in entries:
            address = RECEIVER + entry * PAGE if entry else 0
            if address:
                invoke(control_ctor, address, entry)
                address_point, = struct.unpack("<I", uc.mem_read(address, 4))
                assert address_point == vtable["address"] + 8
            invoke(add, RECEIVER, address)

        calls, freed, writes = [], [], []
        live = set(names)

        def on_code(machine, address, size, _):
            receiver = machine.reg_read(UC_ARM_REG_R0)
            if address == delete:
                assert receiver in live
                assert receiver != RECEIVER or variant == "D0"
                live.remove(receiver)
                freed.append(names[receiver])
                machine.mem_unmap(receiver, PAGE)
                machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))
                return
            assert any(item["address"] <= address < item["address"] + item["size"]
                       for item in (target, control_d0)), hex(address)
            if address == control_d0["address"]:
                assert receiver in live and receiver != RECEIVER
                calls.append(names[receiver])

        def on_write(_, unused_type, address, size, value, unused_data):
            if STACK <= address and address + size <= STACK + PAGE:
                return
            page = address & -PAGE
            assert page in live and address + size <= page + PAGE
            writes.append([names[page], address - page, size, value])

        uc.hook_add(UC_HOOK_CODE, on_code)
        uc.hook_add(UC_HOOK_MEM_WRITE, on_write)
        invoke(target, RECEIVER)
        assert uc.reg_read(UC_ARM_REG_R0) == RECEIVER
        assert calls == [str(entry) for entry in entries if entry]
        assert freed == calls + (["group"] if variant == "D0" else [])
        mapped = {region[0] for region in uc.mem_regions()}
        assert {page for page in names if page in mapped} == live
        rows.append({"entries": entries, "control_d0_order": calls, "free_order": freed,
                     "receiver_mapped": RECEIVER in mapped, "native_writes": writes,
                     "native_r0_preserves_receiver": True})
    return {"elf_sha256": original["elf"], "elf_path": original["elf_path"],
            "firmware": original["firmware"], "role": original["role"],
            "target": target, "support_ranges": [group_ctor, add, control_ctor, control_d0, vtable],
            "operator_delete_plt": delete, "cases": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("context", type=Path)
    parser.add_argument("firmware_root", type=Path)
    args = parser.parse_args()
    observations = [
        observe(item["original"], args.firmware_root)
        for item in json.loads(args.context.read_text())["originals"]
    ]
    print(json.dumps(observations, indent=2) + "\n", end="")


if __name__ == "__main__":
    main()
