"""Execute the packet ARM range independently and record its bounded observations."""

import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP


ROOT = Path(__file__).resolve().parents[4]
TASK = Path(__file__).resolve().parent.name


def digest(data):
    return hashlib.sha256(data).hexdigest()


def observe(original, firmware):
    data = (firmware / original["elf_path"]).read_bytes()
    assert digest(data) == original["elf"]
    elf = ELFFile(io.BytesIO(data))
    assert elf["e_machine"] == "EM_ARM" and elf.little_endian
    symbols = elf.get_section_by_name(".symtab")

    def symbol(name):
        entries = symbols.get_symbol_by_name(name)
        assert len(entries) == 1, name
        return entries[0]

    entry = symbol(original["mangled"])
    section = elf.get_section(entry["st_shndx"])
    address, size = entry["st_value"], entry["st_size"]
    offset = section["sh_offset"] + address - section["sh_addr"]
    assert section["sh_addr"] <= address
    assert address + size <= section["sh_addr"] + section["sh_size"]
    assert (address, size, entry["st_shndx"], section.name, offset) == (
        original["address"], original["size"], original["section"],
        original["section_name"], original["file_offset"],
    )
    body = data[offset:offset + size]
    assert body.hex() == original["range_hex"]
    assert digest(body) == original["range_sha256"]
    lock = symbol("_ZN4Core7Threads8CoreLock4lockEv")["st_value"]
    unlock = symbol("_ZN4Core7Threads8CoreLock6unlockEv")["st_value"]
    invalidate = symbol("_ZN8Presonus2UC14AdapterHandler21invalidateAddressListEv")
    boundaries = {lock: "lock", unlock: "unlock", invalidate["st_value"]: "invalidate"}
    receiver, adapter, stack, stop = 0x800000, 0x810000, 0x901000, 0xA00000
    cases = []
    for current, requested, cached in ((0, 0, 1), (1, 1, 1), (0, 255, 1), (1, 0, 1), (1, 128, 0), (7, 1, 1)):
        cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        cpu.mem_map(0, 0xB00000)
        for segment in elf.iter_segments():
            if segment["p_type"] == "PT_LOAD":
                cpu.mem_write(segment["p_vaddr"], segment.data())
        cpu.mem_write(receiver + 0x94, struct.pack("<I", adapter))
        cpu.mem_write(adapter + 0x20, bytes([77, current, 231]))
        cpu.mem_write(adapter + 0x2A3, bytes([15, cached, 19]))
        for register, value in ((UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, requested),
                                (UC_ARM_REG_SP, stack), (UC_ARM_REG_LR, stop)):
            cpu.reg_write(register, value)
        calls, writes = [], []

        def code(cpu, pc, width, _):
            name = boundaries.get(pc)
            if name is None:
                assert address <= pc < address + size or invalidate["st_value"] <= pc < invalidate["st_value"] + invalidate["st_size"], hex(pc)
                return
            expected = adapter if name == "invalidate" else receiver + 0x14
            assert cpu.reg_read(UC_ARM_REG_R0) == expected
            calls.append([name, cpu.mem_read(adapter + 0x21, 1)[0],
                          cpu.mem_read(adapter + 0x2A4, 1)[0]])
            if name != "invalidate":
                cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))

        def write(cpu, access, address, width, value, _):
            if not stack - 96 <= address < stack:
                writes.append([address - adapter, width, value])

        cpu.hook_add(UC_HOOK_CODE, code)
        cpu.hook_add(UC_HOOK_MEM_WRITE, write)
        cpu.emu_start(address, stop, count=96)
        assert cpu.reg_read(UC_ARM_REG_PC) == stop
        assert cpu.reg_read(UC_ARM_REG_SP) == stack
        final = cpu.mem_read(adapter + 0x20, 3)
        cache = cpu.mem_read(adapter + 0x2A3, 3)
        assert final[0] == 77 and final[2] == 231 and cache[0] == 15 and cache[2] == 19
        cases.append({
            "input": [current, requested, cached], "calls": calls, "writes": writes,
            "final": [cpu.reg_read(UC_ARM_REG_R0), final[1], cache[1]],
        })
    return {**original, "boundaries": boundaries, "cases": cases}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    fixture = Path(__file__).with_name("fixtures.json")
    packet = ROOT / "temp/recovery-work/sqlite-issued/packet" / TASK / "CONTEXT.json"
    firmware = next(p for p in (ROOT, *ROOT.parents) if (p / "rootfs").is_dir())
    originals = json.loads(packet.read_text())["originals"]
    observations = [observe(item["original"], firmware) for item in originals]
    result = json.dumps({"observations": observations}, indent=2) + "\n"
    if args.verify:
        assert fixture.read_text() == result
    else:
        fixture.write_text(result)
    print(f"{len(observations)} ELF ranges, {sum(len(item['cases']) for item in observations)} native executions")


if __name__ == "__main__":
    main()
