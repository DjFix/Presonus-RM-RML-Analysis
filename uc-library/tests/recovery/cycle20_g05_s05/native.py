"""Execute the exact RM callback through each observed native primary slot."""
import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn.arm_const import (
    UC_ARM_REG_FP, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_SP,
)

ELF_SHA256 = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
SYMBOL = "_ZN8Presonus5Panel19FrontPanelComponent12presetStoredERKNS0_15PresetComponentEi"
RANGE_SHA256 = "60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad"
SLOTS = {"FrontPanelComponent": 0x3267BC, "Fat24FrontPanelComponent": 0x32AF44,
         "StormFrontPanelComponent": 0x32B51C}
INDICES = (-2147483648, -1, 0, 7, 2147483647)


def observe(path):
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == ELF_SHA256
    elf = ELFFile(io.BytesIO(data))
    symbol, = elf.get_section_by_name(".symtab").get_symbol_by_name(SYMBOL)
    section = elf.get_section(symbol["st_shndx"])
    entry, size = symbol["st_value"], symbol["st_size"]
    offset = section["sh_offset"] + entry - section["sh_addr"]
    code = data[offset:offset + size]
    assert (entry, size, offset, section.name, symbol["st_shndx"]) == (
        0x69CFC, 16, 0x61CFC, ".text", 12)
    assert hashlib.sha256(code).hexdigest() == RANGE_SHA256
    cases = []
    for owner, address in SLOTS.items():
        vtable, = elf.get_section_by_name(".symtab").get_symbol_by_name(
            f"_ZTVN8Presonus5Panel{len(owner)}{owner}E")
        table_section = elf.get_section(vtable["st_shndx"])
        assert address - vtable["st_value"] == 76 < vtable["st_size"]
        target, = struct.unpack_from("<I", table_section.data(),
                                     address - table_section["sh_addr"])
        assert target == entry
        for index in INDICES:
            cases.append(execute(owner, target, size, code, index))
    return {"elf_sha256": ELF_SHA256, "mangled": SYMBOL, "address": entry,
            "size": size, "section": section.name, "section_index": 12,
            "file_offset": offset, "range_sha256": RANGE_SHA256, "cases": cases}


def execute(owner, target, size, code, index):
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    code_page = target & ~4095
    stack, panel, preset, stop = 0x100000, 0x110000, 0x120000, 0x130000
    for page in (code_page, stack, panel, preset, stop):
        machine.mem_map(page, 4096)
    machine.mem_write(target, code)
    machine.mem_write(panel, b"\x39" * 4096)
    machine.mem_write(preset, b"\xc7" * 4096)
    initial_sp, initial_fp = stack + 2048, stack + 3072
    for register, value in ((UC_ARM_REG_SP, initial_sp), (UC_ARM_REG_FP, initial_fp),
                            (UC_ARM_REG_LR, stop), (UC_ARM_REG_R0, panel),
                            (UC_ARM_REG_R1, preset), (UC_ARM_REG_R2, index & 0xffffffff)):
        machine.reg_write(register, value)
    executed, writes = [], []
    machine.hook_add(UC_HOOK_CODE, lambda uc, address, _, user: executed.append(address))
    machine.hook_add(UC_HOOK_MEM_WRITE,
                     lambda uc, access, address, size, value, user: writes.append((address, size)))
    machine.emu_start(target, stop, count=16)
    assert machine.reg_read(UC_ARM_REG_PC) == stop
    assert machine.reg_read(UC_ARM_REG_SP) == initial_sp
    assert machine.reg_read(UC_ARM_REG_FP) == initial_fp
    assert executed == list(range(target, target + size, 4))
    assert all(initial_sp - 16 <= address < address + size <= initial_sp
               for address, size in writes)
    assert machine.mem_read(panel, 4096) == b"\x39" * 4096
    assert machine.mem_read(preset, 4096) == b"\xc7" * 4096
    return {"owner": owner, "index": index, "panel_changed": False,
            "preset_changed": False, "external_calls": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, required=True)
    output = parser.add_mutually_exclusive_group(required=True)
    output.add_argument("--generate", type=Path)
    output.add_argument("--check", type=Path)
    args = parser.parse_args()
    observed = observe(args.elf)
    if args.generate:
        args.generate.write_text(json.dumps(observed, indent=2) + "\n")
    elif json.loads(args.check.read_text()) != observed:
        raise SystemExit("Original ARM observations diverged from sealed fixtures")
    print(f"Executed {len(observed['cases'])} exact RM ARM callback cases")


if __name__ == "__main__":
    main()
