"""Execute ARM roster operations against a genuine CCL lookup and resize boundary."""
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
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP,
)

WORD = struct.Struct("<I")
OWNER, GROUP, PARAMETERS, STORAGE, STACK, STOP = range(0x800000, 0x806000, 4096)


def execute(uc, original, binary, case):
    mode, count, selected, tag = case
    trace = []

    def put(at, word):
        uc.mem_write(at, WORD.pack(word & 0xffffffff))

    def read(at):
        return WORD.unpack(uc.mem_read(at, 4))[0]

    def probe(size):
        args = [binary, "provider", str(size), str(selected), str(tag)]
        result = subprocess.check_output(args, text=True).split()
        return [int(item) for item in result]

    lookup, success, capacity = probe(count)
    assert success
    uc.mem_write(OWNER, bytes(256))
    uc.mem_write(STORAGE, bytes(256))
    for index in range(count):
        put(STORAGE + 4*index, PARAMETERS + 4*index)
    for at, word in ((OWNER+0x90, STORAGE), (OWNER+0x94, count),
                     (OWNER+0x98, capacity), (OWNER+0x9c, 5), (OWNER+0xa0, tag)):
        put(at, word)

    def hook(machine, pc, _size, _):
        r0 = machine.reg_read(UC_ARM_REG_R0)
        r1 = machine.reg_read(UC_ARM_REG_R1)
        if pc == 0x119c4c:
            assert r0 == GROUP and r1 == tag & 0xffffffff
            trace.append(["lookup", tag, lookup])
            result = PARAMETERS + 4*lookup if lookup >= 0 else 0
        else:
            assert pc == 0x12640 and r0 == OWNER+0x8c
            assert r1 == count+1
            _, result, reserved = probe(r1)
            trace.append(["resize", r1, result, reserved])
            if result:
                put(OWNER+0x98, reserved)
        machine.reg_write(UC_ARM_REG_R0, result)
        machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

    hooks = [uc.hook_add(UC_HOOK_CODE, hook, begin=pc, end=pc)
             for pc in (0x119c4c, 0x12640)]
    for reg, value in ((UC_ARM_REG_R0, OWNER), (UC_ARM_REG_R1, GROUP),
                       (UC_ARM_REG_SP, STACK+0xff0), (UC_ARM_REG_LR, STOP)):
        uc.reg_write(reg, value)
    uc.emu_start(original["address"], STOP, count=10000)
    assert uc.reg_read(UC_ARM_REG_PC) == STOP
    for entry in hooks:
        uc.hook_del(entry)
    final_count = read(OWNER+0x94)
    roster = [(read(STORAGE+4*i)-PARAMETERS)//4 for i in range(final_count)]
    results = [" ".join(["roster", *map(str, roster)]), f"capacity {read(OWNER+0x98)}"]
    if mode == "remove" and final_count != count:
        # The final word of this original function points to its vector error object.
        sentinel_address = read(original["address"] + original["size"] - 4)
        tail = read(STORAGE + 4*(count-1))
        trace.append(["sentinel", sentinel_address, read(sentinel_address), tail])
        results.append(f"tail-cleared {int(tail == read(sentinel_address))}")
    return {"args": case, "expected": results, "native_boundaries": trace}


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
    uc.mem_map(OWNER, 0x6000)
    mode = "add" if "addDCAMaster" in original["mangled"] else "remove"
    cases = [[mode, count, selected, tag] for tag in (-2**31, 59, 2**31-1)
             for count in (0, 1, 3, 5, 6, 17)
             for selected in sorted({-1, 0, count//2, max(count-1, 0), count})]
    return {"original": {k:v for k,v in original.items() if k != "range_hex"},
            "cases": [execute(uc, original, binary, case) for case in cases]}


if __name__ == "__main__":
    print(json.dumps(fixture(*sys.argv[1:]), indent=2))
