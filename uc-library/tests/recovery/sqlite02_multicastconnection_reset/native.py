"""Execute the packet's ARM reset ranges with traced application socket boundaries."""

import argparse
import hashlib
import io
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP

PREFIX = "_ZN8Presonus2UC19MulticastConnection"
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
    boundaries = {
        symbol(PREFIX + "18makeUnicastSocketsEb")["st_value"]: ("unicast", 0xAC),
        symbol(PREFIX + "20makeMulticastSocketsEb")["st_value"]: ("multicast", 0xE0),
    }
    receiver, stack, stop = 0x800000, 0x901000, 0xA00000
    cases = []
    for unicast, multicast in ((0, 0), (1, 0), (0, 1), (1, 1), (7, 129)):
        cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        cpu.mem_map(0, 0xB00000)
        for segment in elf.iter_segments():
            if segment["p_type"] == "PT_LOAD":
                cpu.mem_write(segment["p_vaddr"], segment.data())
        cpu.mem_write(receiver + 0xAC, bytes([unicast]))
        cpu.mem_write(receiver + 0xE0, bytes([multicast]))
        cpu.mem_write(receiver + 0xF7, bytes([0xAB, 0x36, 0xCF]))
        for register, value in ((UC_ARM_REG_R0, receiver), (UC_ARM_REG_SP, stack),
                                (UC_ARM_REG_LR, stop)):
            cpu.reg_write(register, value)
        calls, writes = [], []

        def code(cpu, pc, width, _):
            if pc not in boundaries:
                assert address <= pc < address + size, hex(pc)
                return
            name, field = boundaries[pc]
            assert cpu.reg_read(UC_ARM_REG_R0) == receiver
            enabled = cpu.reg_read(UC_ARM_REG_R1)
            assert enabled in (0, 1)
            calls.append([name, enabled, cpu.mem_read(receiver + 0xF8, 1)[0]])
            # This is the named provider boundary, with its enable-byte effect.
            cpu.mem_write(receiver + field, bytes([enabled]))
            cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))

        def write(cpu, access, address, width, value, _):
            if not stack - 32 <= address < stack:
                writes.append([address - receiver, width, value])

        cpu.hook_add(UC_HOOK_CODE, code)
        cpu.hook_add(UC_HOOK_MEM_WRITE, write)
        cpu.emu_start(address, stop, count=96)
        assert cpu.reg_read(UC_ARM_REG_PC) == stop
        assert cpu.reg_read(UC_ARM_REG_SP) == stack
        assert writes == [[0xF8, 1, 1]]
        assert list(cpu.mem_read(receiver + 0xF7, 3)) == [0xAB, 1, 0xCF]
        cases.append({
            "initial_flags": [unicast, multicast],
            "writes": writes,
            "calls": calls,
            "final_flags": [cpu.mem_read(receiver + x, 1)[0] for x in (0xAC, 0xE0)],
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
