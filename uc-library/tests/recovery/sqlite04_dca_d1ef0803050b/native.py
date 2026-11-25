"""Execute the ARM dB conversion paths with genuine numeric-parameter boundaries."""

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


def sha(data):
    return hashlib.sha256(data).hexdigest()


def word(value):
    return WORD.unpack(FLOAT.pack(value))[0]


def floating(value):
    return FLOAT.unpack(WORD.pack(value))[0]


def provider(binary, mode, minimum, initial, proposed):
    output = subprocess.check_output(
        [binary, "provider-" + mode, str(minimum), str(initial), str(proposed)],
        text=True,
    )
    return output.splitlines()


def observe(machine, original, binary, mode, initial, minimum, proposed):
    receiver, parameter, vtable = 0x800000, 0x801000, 0x802000
    get_min, get_value, set_value = 0x803000, 0x803004, 0x803008
    stop = 0x805000

    for address, target in ((0x38, get_min), (0x44, get_value), (0x58, set_value)):
        machine.mem_write(vtable + address, WORD.pack(target))
    machine.mem_write(parameter, WORD.pack(vtable))

    expected = []
    provider_read = provider(binary, "get", minimum, initial, 0)
    assert [line.split()[0] for line in provider_read] == ["min", "get"]
    minimum_bits, value_bits = (int(line.split()[1]) for line in provider_read)

    def run_boundary(uc, pc, _size, _unused):
        r0, r1, r2 = (uc.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
        if pc == get_min:
            assert r0 == parameter
            expected.append(provider_read[0])
            result = minimum_bits
        elif pc == get_value:
            assert r0 == parameter
            expected.append(provider_read[1])
            result = value_bits
        elif pc == set_value:
            assert r0 == parameter and r2 == 1
            expected.extend(provider(binary, "set", minimum, initial, r1))
            result = r0
        elif pc == 0xacac:
            result = word(LIBM.log10f(floating(r0)))
        elif pc == 0xae5c:
            result = word(LIBM.powf(floating(r0), floating(r1)))
        else:
            return
        uc.reg_write(UC_ARM_REG_R0, result)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    hooks = [
        machine.hook_add(UC_HOOK_CODE, run_boundary, begin=begin, end=end)
        for begin, end in ((get_min, set_value), (0xacac, 0xacac), (0xae5c, 0xae5c))
    ]
    for reg, value in ((UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, parameter),
                       (UC_ARM_REG_R2, proposed), (UC_ARM_REG_SP, 0x804ff0),
                       (UC_ARM_REG_LR, stop)):
        machine.reg_write(reg, value)
    machine.emu_start(original["address"], stop, count=10000)
    assert machine.reg_read(UC_ARM_REG_PC) == stop
    for hook in hooks:
        machine.hook_del(hook)
    if mode == "get":
        expected.append(f"return {machine.reg_read(UC_ARM_REG_R0)}")
    return expected


def fixture(context, binary):
    entry, = json.loads(Path(context).read_text())["originals"]
    original = entry["original"]
    raw = Path(original["elf_path"]).read_bytes()
    assert sha(raw) == original["elf"]
    elf = ELFFile(io.BytesIO(raw))
    row, = elf.get_section_by_name(".symtab").get_symbol_by_name(original["mangled"])
    index = row["st_shndx"]
    section = elf.get_section(index)
    offset = section["sh_offset"] + row["st_value"] - section["sh_addr"]
    assert row["st_info"]["type"] == "STT_FUNC"
    assert (index, section.name, offset, row["st_value"], row["st_size"]) == (
        original["section"], original["section_name"], original["file_offset"],
        original["address"], original["size"])
    code = raw[offset:offset + original["size"]]
    assert sha(code) == original["range_sha256"] and code.hex() == original["range_hex"]

    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    for segment in elf.iter_segments():
        if segment["p_type"] == "PT_LOAD":
            start = segment["p_vaddr"] & ~4095
            end = (segment["p_vaddr"] + segment["p_memsz"] + 4095) & ~4095
            uc.mem_map(start, end - start)
            uc.mem_write(segment["p_vaddr"], segment.data())
    uc.mem_map(0x800000, 0x6000)

    mode = "get" if "getDBValue" in original["mangled"] else "set"
    inputs = [word(n) for n in (-float("inf"), -145., -144., -0., 0., 1.,
                                1000., float("inf"), float("nan"))]
    eps = word(6.309573308271865e-08)
    inputs.extend((eps - 1, eps, eps + 1, word(-144.) - 1, word(-144.) + 1))
    cases = []
    for minimum in (0, word(-0.), word(-10000.)):
        for value in inputs:
            initial, proposed = (value, 0) if mode == "get" else (word(0.125), value)
            expected = observe(uc, original, binary, mode, initial, minimum, proposed)
            cases.append({"args": [mode, minimum, initial, proposed], "expected": expected})
    return {"original": {k: v for k, v in original.items() if k != "range_hex"}, "cases": cases}


if __name__ == "__main__":
    print(json.dumps(fixture(*sys.argv[1:]), indent=2))
