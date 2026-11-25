"""Execute the RM setValue and its local calculation path in ARM Unicorn."""
import importlib.util
import math
import struct
from pathlib import Path

from unicorn import UC_HOOK_CODE
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP,
)

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location(
    "native_info", HERE.parent / "sqlite02_slreverbcontroller_get_parameter_info/native.py"
)
info = importlib.util.module_from_spec(spec)
spec.loader.exec_module(info)
PACKET = Path(
    "temp/recovery-work/sqlite-issued/packet/sqlite02_slreverbcontroller_set_value/CONTEXT.json"
)


def bits(value):
    return struct.unpack("<I", struct.pack("<f", value))[0]


def number(word):
    return struct.unpack("<f", struct.pack("<I", word))[0]


def preset_bank():
    records = bytearray(9 * 216)
    for mode in range(9):
        values = {8: 1.5 + mode, 12: .5, 16: -201.25, 108: .5, 112: 25., 116: 1.5}
        for offset in (52, 56, 60, 64, 84, 88, 92, 96):
            values[offset] = offset / 16
        for offset in (68, 72, 76, 80, 184, 188, 192, 196):
            values[offset] = .5
        for offset, value in values.items():
            struct.pack_into("<f", records, mode * 216 + offset, value)
        for offset in (20, 36, 120, 136, 152, 168):
            struct.pack_into("<I", records, mode * 216 + offset, 100)
    return bytes(records)


def observe(original, segments, presets, mode, index, value, repeat):
    uc = info.machine(segments)
    receiver, stack, stop = 0x10000000, 0x20000800, 0x30000000
    initial = bytearray(1024)
    for offset, raw in [(0, 0x35D848), (0x24, bits(48000)), (0x28, 64), (0x2c, mode),
                        (0x38, bits(-200)), (0x54, bits(800)),
                        (0x58, bits(-200)), (0x5c, bits(.7))]:
        struct.pack_into("<I", initial, offset, raw)
    for slot in range(57):
        struct.pack_into("<I", initial, 0x144 + 4 * slot, bits(-1))
    for slot in range(5):
        struct.pack_into("<d", initial, 0x338 + 8 * slot, (slot + 1) / 8)
    if repeat:
        struct.pack_into("<I", initial, 0x60 + 4 * index, bits(value))
    if index == 8 and value == 0:
        struct.pack_into("<I", initial, 0x60 + 4 * index, bits(-0.0))
    uc.mem_write(receiver, bytes(initial))
    uc.mem_write(0x492134, presets)
    for reg, argument in [(UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, index),
                          (UC_ARM_REG_R2, bits(value)), (UC_ARM_REG_SP, stack),
                          (UC_ARM_REG_LR, stop)]:
        uc.reg_write(reg, argument)
    calls, paths = [], []

    def trace(machine, address, _size, _data):
        if address in (0xBD5A8, 0xBEE44, 0xBD6A8):
            paths.append(address)
        if address == 0xBB514:
            sp = machine.reg_read(UC_ARM_REG_SP)
            assert machine.reg_read(UC_ARM_REG_R0) == receiver + 0x2c0
            type_, frequency, q = (machine.reg_read(r) for r in (UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3))
            gain, = struct.unpack("<I", machine.mem_read(sp, 4))
            calls.append([address, type_, frequency, q, gain])
            machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))
        if address == 0xAE2C:
            exponent = number(machine.reg_read(UC_ARM_REG_R0))
            machine.reg_write(UC_ARM_REG_R0, bits(math.exp(exponent)))
            machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))
        if address == 0xAE5C:
            # The ELF's powf PLT target requires a loader. For these finite
            # fixture arguments compute its binary32 output at this boundary.
            base = number(machine.reg_read(UC_ARM_REG_R0))
            exponent = number(machine.reg_read(UC_ARM_REG_R1))
            machine.reg_write(UC_ARM_REG_R0, bits(base ** exponent))
            machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

    uc.hook_add(UC_HOOK_CODE, trace)
    uc.emu_start(original["address"], stop, count=20000)
    assert uc.reg_read(UC_ARM_REG_PC) == stop
    assert uc.reg_read(UC_ARM_REG_SP) == stack
    assert paths[0] == 0xBD5A8 and ((0xBEE44 in paths) == (index < 57))
    after = bytes(uc.mem_read(receiver, len(initial)))
    changes = [[offset, after[offset:offset + 4].hex()] for offset in range(0, len(after), 4)
               if after[offset:offset + 4] != initial[offset:offset + 4]]
    return {"mode": mode, "index": index, "value_bits": bits(value), "repeat": repeat,
            "input": initial.hex(), "changes": changes, "calls": calls, "paths": paths,
            "r0": uc.reg_read(UC_ARM_REG_R0)}


def result():
    original, segments = info.native_image(PACKET)
    inputs = [
        (mode, index, -201.25 if index == 4 else 1.25, repeat)
        for mode in (0, 8, 9, 10, 11, 12, 13)
        for index in (0, 2, 3, 4, 5, 6, 7, 56, 57, 2147483647)
        for repeat in (False, True) if not repeat or index < 57
    ]
    inputs += [(0, 1, mode + .75, repeat) for mode in (0, 8, 9, 10, 11, 12)
               for repeat in (False, True)]
    inputs += [(9, 8, 0.0, False)]
    presets = preset_bank()
    return {"original": original, "preset_bank": presets.hex(),
            "cases": [observe(original, segments, presets, *case) for case in inputs]}


if __name__ == "__main__":
    info.result = result
    info.main()
