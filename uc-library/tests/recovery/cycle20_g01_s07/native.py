"""Capture exact CS18 DAWMixerHandler lifecycle application boundaries offline."""

import argparse
import hashlib
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import (
    UC_ARCH_ARM, UC_ERR_READ_UNMAPPED, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM,
    Uc, UcError,
)
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP


PREFIX = "_ZN8Presonus7Surface15DAWMixerHandler"
RECEIVER, STACK, STOP = (0x3000000, 0x4000000, 0x5000000)
RECEIVER_REGION_SIZE = 0x10000
BOUNDARIES = {
    0x11F430: "ParamList constructor",
    0x11F77C: "ParamList destructor",
    0xAD5C: "unsized imported delete",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def capture(inventory, firmware, variant):
    exact = json.loads(inventory.read_text())
    with firmware.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == exact["elf"]["sha256"]
        stream.seek(0)
        elf = ELFFile(stream)
        segments = [(s["p_vaddr"], s["p_memsz"], s.data())
                    for s in elf.iter_segments() if s["p_type"] == "PT_LOAD"]
        targets = {}
        for name in ("C1", "C2", variant):
            symbol = PREFIX + name + "Ev"
            record = exact["implementations"][symbol]
            row = record["target"]
            section_number = int(row["section_index"])
            section = elf.get_section(section_number)
            start, size = row["original_address"], row["original_size"]
            relative = start - section["sh_addr"]
            offset = section["sh_offset"] + relative
            assert section.name == ".text"
            assert 0 <= relative and relative + size <= section["sh_size"]
            assert offset == record["file_offset"]
            sym = [s for s in elf.get_section_by_name(".symtab").get_symbol_by_name(symbol)
                   if (s["st_value"], s["st_size"], s["st_shndx"]) == (start, size, section_number)]
            assert len(sym) == 1
            stream.seek(offset)
            body = stream.read(size)
            assert len(body) == size and digest(body) == record["range_sha256"]
            targets[name] = (row, offset, body)

    first = min(addr for addr, _, _ in segments) & ~4095
    last = max(addr + size for addr, size, _ in segments)
    receipts = {}
    for name, (row, offset, body) in targets.items():
        start = row["original_address"]
        cases = []
        for fill in (0x39, 0xC7):
            uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
            uc.mem_map(first, (last - first + 4095) & ~4095)
            for address, _, data in segments:
                uc.mem_write(address, data)
            for address in (RECEIVER, STACK, STOP):
                uc.mem_map(address, RECEIVER_REGION_SIZE)
            uc.mem_write(RECEIVER, bytes([fill]) * 256)
            initialized_guard = None
            if name.startswith("C"):
                # Both constructor entries load their static guard at +0x18
                # from a PC-relative literal. Observe the initialized path.
                instruction, = struct.unpack_from("<I", body, 0x18)
                assert instruction & 0xFFFFF000 == 0xE59F0000
                literal = start + 0x18 + 8 + (instruction & 0xFFF)
                initialized_guard, = struct.unpack("<I", uc.mem_read(literal, 4))
                uc.mem_write(initialized_guard, struct.pack("<I", 1))
            assert bytes(uc.mem_read(start, len(body))) == body
            uc.reg_write(UC_ARM_REG_R0, RECEIVER)
            uc.reg_write(UC_ARM_REG_SP, STACK + 0x8000)
            uc.reg_write(UC_ARM_REG_LR, STOP)
            calls, writes, release = [], [], {}

            def code(emulator, pc, size, _):
                if start <= pc < start + len(body):
                    return
                arg = emulator.reg_read(UC_ARM_REG_R0)
                lr = emulator.reg_read(UC_ARM_REG_LR)
                calls.append(dict(boundary=BOUNDARIES[pc], target=pc, site=lr - 4,
                                  receiver_relative=arg - RECEIVER))
                if name.startswith("C"):
                    emulator.emu_stop()
                    return
                if pc == 0xAD5C:
                    assert name == "D0" and arg == RECEIVER and not release
                    assert calls[-2]["boundary"] == "ParamList destructor"
                    assert bytes(emulator.mem_read(arg + 0x48, 32)) == bytes([fill]) * 32
                    emulator.mem_unmap(arg, RECEIVER_REGION_SIZE)
                    release.update(receiver_relative=arg - RECEIVER,
                                   bytes_unmapped=RECEIVER_REGION_SIZE, site=lr - 4)
                emulator.reg_write(UC_ARM_REG_PC, lr)

            def write(emulator, access, addr, size, value, _):
                if RECEIVER <= addr < RECEIVER + 256:
                    writes.append([addr - RECEIVER, size, value])

            uc.hook_add(UC_HOOK_CODE, code)
            uc.hook_add(UC_HOOK_MEM_WRITE, write)
            uc.emu_start(start, STOP, count=1500)
            pc = uc.reg_read(UC_ARM_REG_PC)
            if name.startswith("C"):
                assert pc == 0x11F430
                expected = [("ParamList constructor", 0x48)]
            else:
                assert pc == STOP and uc.reg_read(UC_ARM_REG_R0) == RECEIVER
                expected = [("ParamList destructor", 0x48)]
                if name == "D0":
                    expected.append(("unsized imported delete", 0))
                assert [event[0] for event in writes] == [0xC, 0x10, 0, 0]
                if name == "D0":
                    assert release and release["site"] == calls[-1]["site"]
                    try:
                        uc.mem_read(RECEIVER, 1)
                    except UcError as error:
                        assert error.errno == UC_ERR_READ_UNMAPPED
                        release["post_return_read"] = "UC_ERR_READ_UNMAPPED"
                    else:
                        raise AssertionError("D0 receiver storage remains readable")
                else:
                    assert not release
                    assert bytes(uc.mem_read(RECEIVER + 0x48, 32)) == bytes([fill]) * 32
            assert [(call["boundary"], call["receiver_relative"]) for call in calls] == expected
            cases.append(dict(fill=fill, calls=calls, receiver_writes=writes,
                              preinitialized_guard=initialized_guard,
                              allocator_shim_release=release or None))
        receipts[name] = dict(target=row, offset=offset, section=".text",
                              raw_range_sha256=digest(body), cases=cases)
    return dict(elf=exact["elf"], variant=variant, observations=receipts,
                inventory_sha256=digest(inventory.read_bytes()))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("inventory", type=Path)
    p.add_argument("elf", type=Path)
    p.add_argument("variant", choices=("D1", "D2", "D0"))
    args = p.parse_args()
    print(json.dumps(capture(args.inventory, args.elf, args.variant), indent=2))
