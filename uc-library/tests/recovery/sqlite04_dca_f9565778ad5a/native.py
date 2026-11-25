"""Execute each original lifecycle body with genuine CCL boundary observations."""

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
    UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP,
)

U32 = struct.Struct("<I")
F32 = struct.Struct("<f")
LEVEL, TRIM, TABLE, STACK, STOP = range(0x804000, 0x809000, 4096)
MIN, VALUE, SET = 0x809000, 0x809004, 0x809008
COMPONENT_CREATE = 0x119e8c
COMPONENT_DESTROY = 0x11a53c
RESIZE, DESTROY_VECTOR = 0x12640, 0x12740
ADD_OBSERVER, REMOVE_OBSERVER, CHANGED = 0x11d4f4, 0x11c2e4, 0x11dc28
NATIVE_CALLBACK = 0x5cd44
DELETE = 0xac10
LIBC = ctypes.CDLL("libc.so.6")
LIBC.malloc.argtypes = [ctypes.c_size_t]
LIBC.malloc.restype = ctypes.c_void_p
LIBC.free.argtypes = [ctypes.c_void_p]


def execute(uc, original, binary, case, receiver, prefill):
    mode, tag, count, gain, alias = case
    constructor = mode.startswith("ctor")
    trim = LEVEL if alias else TRIM
    trace = []
    expected = []
    registered = not constructor
    freed = False
    allocation = LIBC.malloc(200)
    assert allocation
    provider = "provider" if constructor else "provider-destroy"
    observations = subprocess.check_output(
        [binary, provider, *map(str, case[1:])], text=True).splitlines()

    def read(address):
        return U32.unpack(uc.mem_read(address, 4))[0]

    def put(address, value):
        uc.mem_write(address, U32.pack(value & 0xffffffff))

    word_name = read(original["address"]+original["size"]-12) if constructor else None
    word_vptr = read(original["address"]+original["size"]-(8 if constructor else 4))
    uc.mem_write(receiver, bytes([prefill])*200)
    for offset, target in ((0x38, MIN), (0x44, VALUE), (0x58, SET)):
        put(TABLE+offset, target)
    put(LEVEL, TABLE)
    put(TRIM, TABLE)
    if not constructor:
        put(receiver+0x84, LEVEL)
        put(receiver+0x88, trim)
        put(receiver+0x94, count)

    def hook(machine, pc, _size, _):
        nonlocal registered, freed
        r0, r1, r2 = (machine.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
        result = r0
        if pc == COMPONENT_CREATE:
            assert r0 == receiver and r1 == word_name
            assert machine.mem_read(r1, 1) == b"\0"
            trace.append(["component-create", r0, r1, ""])
        elif pc == RESIZE:
            assert (r0, r1) == (receiver+0x8c, 0)
            assert [read(receiver+i) for i in (0x90, 0x94, 0x98, 0x9c)] == [0, 0, 0, 5]
            trace.append(["vector-resize", r0, r1, read(receiver+0x9c)])
            result = 1
        elif pc == ADD_OBSERVER:
            assert (r0, r1) == (LEVEL, receiver+4) and not registered
            assert read(receiver+0x84) == LEVEL and read(receiver+0x88) == trim
            assert read(receiver+0xa0) == tag & 0xffffffff
            assert machine.mem_read(receiver+0xa4, 1) == b"\0"
            trace.append(["observer-add", r0, r1])
            registered = True
        elif pc == CHANGED:
            assert r0 == LEVEL and registered
            trace.append(["changed", r0])
            expected.extend(observations[:2])
            # The pinned provider issues kChanged to its registered observer.
            # Dispatch through the original application's paramChanged body.
            machine.reg_write(UC_ARM_REG_R0, receiver)
            machine.reg_write(UC_ARM_REG_R1, LEVEL)
            machine.reg_write(UC_ARM_REG_R2, 3)
            machine.reg_write(UC_ARM_REG_PC, NATIVE_CALLBACK)
            return
        elif pc == MIN:
            assert r0 == LEVEL
            result = U32.unpack(F32.pack(-10000.))[0]
        elif pc == VALUE:
            assert r0 == LEVEL
            result = U32.unpack(F32.pack(float(gain)))[0]
        elif pc == SET:
            assert (r0, r1, r2) == (trim, U32.unpack(F32.pack(float(gain)))[0], 0)
            trace.append(["callback-set", r0, r1, r2])
            expected.extend(observations[2:-1])
        elif pc == REMOVE_OBSERVER:
            assert (r0, r1) == (LEVEL, receiver+4) and registered
            trace.append(["observer-remove", r0, r1])
            registered = False
        elif pc == DESTROY_VECTOR:
            assert r0 == receiver+0x8c and not registered
            trace.append(["vector-destroy", r0, read(receiver+0x94)])
        elif pc == COMPONENT_DESTROY:
            assert r0 == receiver and trace[-1][0] == "vector-destroy"
            trace.append(["component-destroy", r0])
            expected.extend(observations[:2])
        elif pc == DELETE:
            assert r0 == receiver and trace[-1][0] == "component-destroy"
            assert not freed
            LIBC.free(allocation)
            freed = True
            trace.append(["operator-delete", r0])
            expected.append("receiver-freed")
        else:
            raise AssertionError(hex(pc))
        machine.reg_write(UC_ARM_REG_R0, result)
        machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

    hooks = [uc.hook_add(UC_HOOK_CODE, hook, begin=pc, end=pc)
             for pc in (COMPONENT_CREATE, COMPONENT_DESTROY, RESIZE, DESTROY_VECTOR,
                        ADD_OBSERVER, REMOVE_OBSERVER, CHANGED, MIN, VALUE, SET, DELETE)]
    for reg, value in ((UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, LEVEL),
                       (UC_ARM_REG_R2, trim), (UC_ARM_REG_R3, tag),
                       (UC_ARM_REG_SP, STACK+0xff0), (UC_ARM_REG_LR, STOP)):
        uc.reg_write(reg, value & 0xffffffff)
    try:
        uc.emu_start(original["address"], STOP, count=20000)
        assert uc.reg_read(UC_ARM_REG_PC) == STOP
        assert [read(receiver), read(receiver+4)] == [word_vptr, word_vptr+0x34]
        if constructor:
            assert registered and trace[-1][0] == "callback-set"
            mask = 0xffffffff
            signed_tag = (read(receiver+0xa0) ^ (1<<31)) - (1<<31)
            assert signed_tag == tag and read(receiver+0xa0) == tag & mask
            expected.append(f"state {signed_tag} {uc.mem_read(receiver+0xa4, 1)[0]} "
                            f"{read(receiver+0x94)} {read(receiver+0x98)} 1")
            expected.append(observations[-1])
        else:
            assert not registered and freed == (mode == "d0")
            expected.extend(observations[2:])
    finally:
        if not freed:
            LIBC.free(allocation)
        for entry in hooks:
            uc.hook_del(entry)
    return {"args": case, "expected": expected, "native_boundaries": trace,
            "receiver": receiver, "prefill": prefill,
            "native_vptrs": [word_vptr, word_vptr+0x34]}


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
    uc.mem_map(0x800000, 0xa000)
    if "HandlerC" in original["mangled"]:
        mode = "ctor-base" if "HandlerC2" in original["mangled"] else "ctor"
    else:
        mode = next(mode for mode in ("d0", "d1", "d2") if mode.upper()+"Ev" in original["mangled"])
    if mode.startswith("ctor"):
        inputs = [[mode, tag, 0, gain, alias] for tag in (-2**31, 19, 2**31-1)
                  for gain in (-7, 8) for alias in (0, 1)]
    else:
        inputs = [[mode, tag, count, gain, 0] for tag in (-2**31, 19, 2**31-1)
                  for count in (0, 1, 3, 17) for gain in (-7, 8)]
    cases = [execute(uc, original, binary, case, 0x800000+4096*(i%2),
                     (0xa5, 0x19)[i%2]) for i, case in enumerate(inputs)]
    return {"original": {k:v for k,v in original.items() if k != "range_hex"}, "cases": cases}


if __name__ == "__main__":
    print(json.dumps(fixture(*sys.argv[1:]), indent=2))
