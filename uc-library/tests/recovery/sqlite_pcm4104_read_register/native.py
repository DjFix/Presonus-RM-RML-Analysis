"""Execute original ARM register methods with offline boundary observations."""
import hashlib
import io
import itertools
import json
from pathlib import Path
import struct
import sys

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM, Uc
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_SP,
)

OWNER = 0x800000
OUTPUT = OWNER + 0x1000
ERRNO = OWNER + 0x2000
STACK = OWNER + 0x3FF0
STOP = OWNER + 0x4000
IOCTL = 0xACD8
ERRNO_LOCATION = 0xB134
DIAGNOSTIC = 0x1179D4
WORD = struct.Struct("<I")
DEFINED_TRANSFER = struct.Struct("<QQIIHBB")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def original_image(context):
    entry, = json.loads(Path(context).read_text())["originals"]
    original = entry["original"]
    image = Path(original["elf_path"]).read_bytes()
    assert digest(image) == original["elf"]
    elf = ELFFile(io.BytesIO(image))
    symbol, = elf.get_section_by_name(".symtab").get_symbol_by_name(original["mangled"])
    index = symbol["st_shndx"]
    section = elf.get_section(index)
    relative = symbol["st_value"] - section["sh_addr"]
    offset = section["sh_offset"] + relative
    size = symbol["st_size"]
    assert symbol["st_info"]["type"] == "STT_FUNC"
    assert 0 <= relative <= section["sh_size"] - size
    assert (index, section.name, offset, symbol["st_value"], size) == (
        original["section"], original["section_name"], original["file_offset"],
        original["address"], original["size"])
    payload = image[offset:offset + size]
    assert payload.hex() == original["range_hex"]
    assert digest(payload) == original["range_sha256"]
    return original, elf


def execute(machine, address, size, mode, case):
    descriptor, index, value, result, injected_errno, response = case
    owner = WORD.pack(descriptor & 0xFFFFFFFF) + bytes([0xff, 0xa1, 0x02, 0x80])
    output = bytes([0x75, value, 0x8e])
    machine.mem_write(OWNER, owner)
    machine.mem_write(OUTPUT, output)
    machine.mem_write(ERRNO, WORD.pack(33))
    # Mark undefined stack fields. The four trailing transfer bytes are outside
    # the initialized original transfer domain.
    machine.mem_write(STACK - 128, b"\xcd" * 128)
    transfer = []
    diagnostics = []
    calls = []

    def boundary(uc, pc, _size, _data):
        if address <= pc < address + size - 12:
            return
        assert pc in (IOCTL, ERRNO_LOCATION, DIAGNOSTIC), hex(pc)
        r0, r1, r2 = [uc.reg_read(reg) for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2)]
        if pc == IOCTL:
            calls.append("ioctl")
            tx, rx, length, *fields = DEFINED_TRANSFER.unpack(
                uc.mem_read(r2, DEFINED_TRANSFER.size))
            assert 0 < length <= 8
            transfer.append([r0, r1, length, *fields, *uc.mem_read(tx, length)])
            assert tx != rx
            if response >= 0:
                assert length == 2
                uc.mem_write(rx, bytes((response ^ 0xff, response)))
            if result < 0:
                uc.mem_write(ERRNO, WORD.pack(injected_errno))
            ret = result
        elif pc == ERRNO_LOCATION:
            calls.append("errno")
            ret = ERRNO
        else:
            assert pc == DIAGNOSTIC
            calls.append("diagnostic")
            message = bytearray()
            while len(message) < 120:
                char = uc.mem_read(r0 + len(message), 1)
                if not char[0]:
                    break
                message.extend(char)
            diagnostics.append([message.decode(), r1])
            ret = 0
        uc.reg_write(UC_ARM_REG_R0, ret & 0xFFFFFFFF)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    hook = machine.hook_add(UC_HOOK_CODE, boundary)
    argument = OUTPUT + 1 if mode == "read" else value
    for reg, item in ((UC_ARM_REG_R0, OWNER), (UC_ARM_REG_R1, index),
                      (UC_ARM_REG_R2, argument), (UC_ARM_REG_SP, STACK),
                      (UC_ARM_REG_LR, STOP)):
        machine.reg_write(reg, item & 0xFFFFFFFF)
    machine.emu_start(address, STOP, count=200)
    assert machine.reg_read(UC_ARM_REG_PC) == STOP
    machine.hook_del(hook)

    assert machine.mem_read(OWNER, len(owner)) == owner
    actual_output = machine.mem_read(OUTPUT, len(output))
    assert actual_output[0] == output[0] and actual_output[2] == output[2]
    return {"args": case,
            "observed": [machine.reg_read(UC_ARM_REG_R0), actual_output[1],
                         WORD.unpack(machine.mem_read(ERRNO, WORD.size))[0], transfer],
            "original_diagnostics": diagnostics, "original_calls": calls}


def fixtures(context):
    original, elf = original_image(context)
    mode = "read" if "readRegister" in original["mangled"] else "write"
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    for segment in elf.iter_segments():
        if segment["p_type"] == "PT_LOAD":
            start = segment["p_vaddr"] & ~4095
            end = (segment["p_vaddr"] + segment["p_memsz"] + 4095) & ~4095
            machine.mem_map(start, end - start)
            machine.mem_write(segment["p_vaddr"], segment.data())
    machine.mem_map(OWNER, 0x5000)

    indices = (-2147483648, -257, -1, 0, 1, 0x1f, 0x20, 0x5f, 0x80, 0xff, 256, 2147483647)
    values = (0, 1, 127, 128, 255)
    transport = ((-1, 5, 0x92), (-1, 9, -1), (0, 0, 0), (1, 0, 0xff), (2, 0, 0x81))
    cases = [(fd, index, value, *io) for fd, index, value, io in
             itertools.product((0, 17, 257), indices, values, transport)]
    return {"mode": mode, "original": {k: v for k, v in original.items() if k != "range_hex"},
            "cases": [execute(machine, original["address"], original["size"], mode, case) for case in cases]}


if __name__ == "__main__":
    print(json.dumps(fixtures(sys.argv[1]), separators=(",", ":")))
