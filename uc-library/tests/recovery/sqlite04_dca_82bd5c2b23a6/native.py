"""Replay original ARM control paths with CCL behavior at setter boundaries."""
import ctypes
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
import sys

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_SP,
)

WORD = struct.Struct("<I")
FLOAT = struct.Struct("<f")
LIBM = ctypes.CDLL("libm.so.6")
LIBM.log10f.argtypes = [ctypes.c_float]
LIBM.log10f.restype = ctypes.c_float
LIBM.powf.argtypes = [ctypes.c_float, ctypes.c_float]
LIBM.powf.restype = ctypes.c_float
OWNER, LEVEL, TRIM, MASTER, INFO, DATA, TABLE, STOP = range(0x800000, 0x808000, 4096)
MIN, VALUE, SET = 0x809000, 0x809004, 0x809008


def bits(value):
    return WORD.unpack(FLOAT.pack(value))[0]


def floating(value):
    return FLOAT.unpack(WORD.pack(value))[0]


def execute(uc, address, binary, case):
    mode, minimum, level, trim, flags, action, tag, alias, *masters = case
    assert not alias
    points = {LEVEL: ("L", level), TRIM: ("T", trim)}
    points.update({MASTER + i*4: ("M", item) for i, item in enumerate(masters)})

    def put(at, word):
        uc.mem_write(at, WORD.pack(word & 0xffffffff))

    uc.mem_write(OWNER, bytes(256))
    for offset, target in ((0x38, MIN), (0x44, VALUE), (0x58, SET)):
        put(TABLE + offset, target)
    for point in points:
        put(point, TABLE)
    for at, word in ((LEVEL+0xc, INFO), (INFO+0x3c, flags), (OWNER+0x84, LEVEL),
                     (OWNER+0x88, TRIM), (OWNER+0x90, DATA), (OWNER+0x94, len(masters)),
                     (OWNER+0x98, len(masters)+1), (OWNER+0xa0, tag)):
        put(at, word)
    for i in range(len(masters)):
        put(DATA + 4*i, MASTER + 4*i)

    trace = []
    boundaries = []

    def hook(machine, pc, _size, _):
        nonlocal level, trim
        r0, r1, r2 = (machine.reg_read(reg) for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
        if pc == MIN:
            assert r0 == LEVEL
            trace.append(f"min L {minimum}")
            result = minimum
        elif pc == VALUE:
            name, result = points[r0]
            if name == "M":
                boundaries.append(["master", (r0-MASTER)//4, result])
            else:
                trace.append(f"get {name} {result}")
        elif pc == SET:
            name = points[r0][0]
            busy = machine.mem_read(OWNER+0xa4, 1)[0]
            assert r2 == busy == (name == "L")
            args = [minimum, level, r1] if name == "L" else [minimum, r1, trim]
            command = [binary, "provider-"+name, *map(str, [*args, flags, r2, 0, 0])]
            *calls, final = subprocess.check_output(command, text=True).splitlines()
            _, post_level, post_trim = final.split()
            if name == "L":
                level = int(post_level)
            else:
                trim = int(post_trim)
            assert calls[0] == f"set {name} {r1} {r2}"
            trace.extend(calls)
            boundaries.append(["set", name, r1, r2, busy])
            result = r0
        elif pc == 0xacac:
            result = bits(LIBM.log10f(floating(r0)))
        else:
            assert pc == 0xae5c
            result = bits(LIBM.powf(floating(r0), floating(r1)))
        machine.reg_write(UC_ARM_REG_R0, result)
        machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

    hooks = [uc.hook_add(UC_HOOK_CODE, hook, begin=start, end=end)
             for start, end in ((MIN, SET), (0xacac, 0xacac), (0xae5c, 0xae5c))]
    arg1 = {0: LEVEL, 1: TRIM}.get(tag, 0) if mode == "param" else action
    for reg, value in ((UC_ARM_REG_R0, OWNER), (UC_ARM_REG_R1, arg1),
                       (UC_ARM_REG_R2, action), (UC_ARM_REG_SP, 0x80eff0),
                       (UC_ARM_REG_LR, STOP)):
        uc.reg_write(reg, value & 0xffffffff)
    uc.emu_start(address, STOP, count=20000)
    assert uc.reg_read(UC_ARM_REG_PC) == STOP
    for entry in hooks:
        uc.hook_del(entry)
    assert uc.mem_read(OWNER+0xa4, 1)[0] == 0
    trace.append(f"final {level} {trim}")
    return {"args": case, "expected": trace, "native_boundaries": boundaries}


def fixture(context, binary):
    entry, = json.loads(Path(context).read_bytes())["originals"]
    original = entry["original"]
    image = Path(original["elf_path"]).read_bytes()
    assert hashlib.sha256(image).hexdigest() == original["elf"]
    elf = ELFFile(io.BytesIO(image))
    row, = elf.get_section_by_name(".symtab").get_symbol_by_name(original["mangled"])
    index = row["st_shndx"]
    section = elf.get_section(index)
    relative = row["st_value"] - section["sh_addr"]
    offset = section["sh_offset"] + relative
    size = row["st_size"]
    assert row["st_info"]["type"] == "STT_FUNC"
    assert 0 <= relative <= section["sh_size"] - size
    assert (index, section.name, offset, row["st_value"], size) == (
        original["section"], original["section_name"], original["file_offset"],
        original["address"], original["size"])
    payload = image[offset:offset+size]
    assert payload.hex() == original["range_hex"]
    assert hashlib.sha256(payload).hexdigest() == original["range_sha256"]

    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    for segment in elf.iter_segments():
        if segment["p_type"] == "PT_LOAD":
            start = segment["p_vaddr"] & ~4095
            end = (segment["p_vaddr"] + segment["p_memsz"] + 4095) & ~4095
            uc.mem_map(start, end - start)
            uc.mem_write(segment["p_vaddr"], segment.data())
    uc.mem_map(OWNER, 0x10000)

    mangled = original["mangled"]
    mode = next(mode for mode in ("onLevel", "onDCA", "param") if mode in mangled)
    states = [[0, bits(1.), bits(-2.)], [bits(-10000.), bits(13.5), bits(-2.)],
              [bits(-10000.), bits(float("nan")), bits(float("inf"))]]
    rosters = [[], [bits(2.)], [bits(1e10), bits(-1e10), bits(1.)],
               [bits(1.)]*17, [bits(-0.)], [bits(float("inf")), bits(-float("inf"))]]
    if mode == "param":
        cases = [[mode, *states[0], 0, msg, tag, 0, *rosters[(msg+tag)%3]]
                 for msg in (-2**31, -1, 0, 2, 3, 4, 5, 2**31-1) for tag in (0, 1, 2)]
    else:
        choices = [(0, 0), (0, 1), (8, 0), (8, 1)] if mode == "onDCA" else [(0, 0)]
        cases = [[mode, *state, flags, action, -17, 0, *members]
                 for state in states for members in rosters for flags, action in choices]
    return {"original": {k: v for k,v in original.items() if k != "range_hex"},
            "cases": [execute(uc, original["address"], binary, case) for case in cases]}


if __name__ == "__main__":
    print(json.dumps(fixture(*sys.argv[1:]), indent=2))
