"""Replay verified ARM firmware bodies using an isolated stack and receiver."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn import __version__ as unicorn_version
from unicorn.arm_const import (
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
    UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC,
)

STACK = 0x70000000
RECEIVER = 0x71000000
RETURN = 0x72000000
MASK = 0xffffffff


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def execute(o, image_bytes, base, argument, clock, divide):
    cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    page = base & ~0xfff
    cpu.mem_map(page, (base - page + len(image_bytes) + 0xfff) & ~0xfff)
    cpu.mem_write(base, image_bytes)
    for addr in (STACK, RECEIVER, RETURN):
        cpu.mem_map(addr, 0x1000)
    cpu.mem_write(RECEIVER, bytes(range(64)))
    cpu.reg_write(UC_ARM_REG_R0, RECEIVER)
    cpu.reg_write(UC_ARM_REG_R1, argument & MASK)
    cpu.reg_write(UC_ARM_REG_SP, STACK + 0x800)
    cpu.reg_write(UC_ARM_REG_LR, RETURN)
    trace = []
    writes = []

    def hook(uc, address, size, _):
        if address == clock:
            trace.append(["clock", argument])
            uc.reg_write(UC_ARM_REG_R0, argument & MASK)
            uc.reg_write(UC_ARM_REG_R1, (argument >> 32) & MASK)
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
        if address == divide:
            divisor = uc.reg_read(UC_ARM_REG_R2) | (uc.reg_read(UC_ARM_REG_R3) << 32)
            trace.append(["division", divisor])

    cpu.hook_add(UC_HOOK_CODE, hook)
    cpu.hook_add(UC_HOOK_MEM_WRITE, lambda uc, access, addr, size, value, data:
                 writes.append([addr, size, value & ((1 << (size * 8)) - 1)]))
    cpu.emu_start(o["address"], RETURN, count=3000)
    assert cpu.reg_read(UC_ARM_REG_PC) == RETURN
    assert cpu.reg_read(UC_ARM_REG_SP) == STACK + 0x800
    assert cpu.mem_read(RECEIVER, 64) == bytes(range(64))
    assert all(STACK <= addr and addr + size <= STACK + 0x800 for addr, size, _ in writes)
    result = cpu.reg_read(UC_ARM_REG_R0)
    if clock is None:
        assert not trace and result in (0, RECEIVER)
        result = int(result == RECEIVER)
    else:
        result |= cpu.reg_read(UC_ARM_REG_R1) << 32
        if result >> 63:
            result -= 1 << 64
        assert trace == [["clock", argument], ["division", 1000000]]
    return dict(argument=argument, result=result, calls=trace, stack_writes=writes,
                returned=True, stack_restored=True, receiver_unchanged=True)


def run(original):
    image = Path(original["elf_path"])
    assert digest(image) == original["elf"]
    with image.open("rb") as stream:
        elf = ELFFile(stream)
        section = elf.get_section(original["section"])
        base = section["sh_addr"]
        text = section.data()
        offset = original["address"] - base
        assert section.name == original["section_name"] == ".text"
        assert original["file_offset"] == section["sh_offset"] + offset
        names = elf.get_section_by_name(".symtab")
        def addresses(name):
            return {entry["st_value"] for entry in names.get_symbol_by_name(name)}
        symbols = names.get_symbol_by_name(original["mangled"])
        assert any(s["st_value"] == original["address"] and s["st_size"] == original["size"]
                   and s["st_shndx"] == original["section"] for s in symbols)
        span = text[offset:offset + original["size"]]
        assert hashlib.sha256(span).hexdigest() == original["range_sha256"]
        assert span.hex() == original["range_hex"]

        clock = divide = None
        if "castTo" in original["mangled"]:
            def literal(i):
                word, = struct.unpack_from("<I", span, i)
                assert word & 0xfffff000 == 0xe59f3000
                return struct.unpack_from("<i", span, i + 8 + (word & 0xfff))[0]
            args = [literal(i) for i in (0, 24, 36)] + [0, -1, 0x53726575, 0x7fffffff]
        elif "getSystemTime" in original["mangled"]:
            def branch(i):
                word, = struct.unpack_from("<I", span, i)
                assert word >> 24 == 0xeb
                displacement = (word & 0xffffff) << 2
                if displacement & 0x2000000:
                    displacement -= 0x4000000
                return original["address"] + i + 8 + displacement
            clock, divide = branch(16), branch(28)
            assert clock in addresses("_ZN4Core15GetAbsoluteTimeEv")
            assert divide in addresses("__aeabi_ldivmod")
            args = [0, 1, 999999, 1000000, 1000001, 65535999999, 4294967296000000,
                    8999999999999999999, 9223372036854775807, -1, -999999, -1000000, -1000001,
                    -9223372036854775808]
        else:
            args = [0]
        loads = [s for s in elf.iter_segments() if s["p_type"] == "PT_LOAD"]
        load_base = min(s["p_vaddr"] for s in loads)
        image_bytes = bytearray(max(s["p_vaddr"] + s["p_memsz"] for s in loads) - load_base)
        for seg in loads:
            start = seg["p_vaddr"] - load_base
            image_bytes[start:start + seg["p_filesz"]] = seg.data()
        return dict(original=original, cases=[execute(original, bytes(image_bytes), load_base, arg, clock, divide)
                                              for arg in args],
                    clock_target=clock, division_target=divide)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("context", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    document = json.loads(args.context.read_text())
    document = dict(unicorn=unicorn_version,
                    executions=[run(row["original"]) for row in document["originals"]])
    args.output.write_text(json.dumps(document, indent=2) + "\n")


if __name__ == "__main__":
    main()
