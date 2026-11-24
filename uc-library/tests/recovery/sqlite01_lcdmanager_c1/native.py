"""Observe the exact ARM LCDManager constructor independently of the source port."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP


def digest(data):
    return hashlib.sha256(data).hexdigest()


def observe(original, firmware_root):
    data = (firmware_root / original["elf_path"]).read_bytes()
    assert digest(data) == original["elf"]
    elf = ELFFile(io.BytesIO(data))
    assert elf["e_machine"] == "EM_ARM" and elf.little_endian
    symbols = elf.get_section_by_name(".symtab")

    def symbol(name):
        matches = symbols.get_symbol_by_name(name)
        assert len(matches) == 1, name
        return matches[0]

    entry = symbol(original["mangled"])
    section = elf.get_section(entry["st_shndx"])
    address = entry["st_value"]
    size = entry["st_size"]
    offset = section["sh_offset"] + address - section["sh_addr"]
    assert address >= section["sh_addr"]
    assert address + size <= section["sh_addr"] + section["sh_size"]
    assert (address, size, entry["st_shndx"], section.name, offset) == (
        original["address"], original["size"], original["section"],
        original["section_name"], original["file_offset"],
    )
    native_bytes = data[offset:offset + size]
    assert native_bytes.hex() == original["range_hex"]
    assert digest(native_bytes) == original["range_sha256"]

    table = symbol("_ZTVN8Presonus5Panel10LCDManagerE")
    assert table["st_size"] == 16
    address_point = table["st_value"] + 8
    receiver = 0x800004
    stack = 0x901000
    stop = 0xA00000
    seeds = (0x11223344, 0xFEDCBA98)
    cases = []
    for seed in seeds:
        cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        cpu.mem_map(0, 0xB00000)
        for segment in elf.iter_segments():
            if segment["p_type"] == "PT_LOAD":
                cpu.mem_write(segment["p_vaddr"], segment.data())
        before = (0x13579BDF, 0x2468ACE0, seed, 0xC0FFEE44)
        cpu.mem_write(receiver - 4, struct.pack("<4I", *before))
        for register, value in (
            (UC_ARM_REG_R0, receiver), (UC_ARM_REG_SP, stack), (UC_ARM_REG_LR, stop)
        ):
            cpu.reg_write(register, value)

        executed = []
        written = []
        cpu.hook_add(UC_HOOK_CODE, lambda cpu, pc, width, _: executed.append(pc))
        cpu.hook_add(
            UC_HOOK_MEM_WRITE,
            lambda cpu, access, addr, width, value, _: written.append(
                (addr, width, value & 0xFFFFFFFF)
            ),
        )
        cpu.emu_start(address, stop, count=32)
        assert cpu.reg_read(UC_ARM_REG_PC) == stop
        assert cpu.reg_read(UC_ARM_REG_SP) == stack
        assert executed and all(address <= pc < address + size - 4 for pc in executed)
        after = struct.unpack("<4I", cpu.mem_read(receiver - 4, 16))
        receiver_writes = [w for w in written if not stack - 32 <= w[0] < stack]
        assert receiver_writes == [(receiver, 4, address_point), (receiver + 4, 4, 0)]
        assert after == (before[0], address_point, 0, before[3])
        cases.append({
            "seeded_receiver_and_canaries": before,
            "final_receiver_and_canaries": after,
            "writes_relative_to_receiver": [(a - receiver, n, v) for a, n, v in receiver_writes],
            "executed_addresses": executed,
            "portable_initial_binding_present": bool(after[2]),
        })
    return {**original, "native_vtable_symbol_address": table["st_value"], "cases": cases}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("context", type=Path)
    parser.add_argument("fixtures", type=Path)
    parser.add_argument("--firmware-root", type=Path, default=Path.cwd())
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    packet = json.loads(args.context.read_text())
    observations = [observe(item["original"], args.firmware_root) for item in packet["originals"]]
    result = json.dumps({"observations": observations}, indent=2) + "\n"
    if args.verify:
        assert args.fixtures.read_text() == result, "native fixture changed"
    else:
        args.fixtures.write_text(result)
    print(f"Verified {len(observations)} ranges and {sum(len(x['cases']) for x in observations)} native executions")


if __name__ == "__main__":
    main()
