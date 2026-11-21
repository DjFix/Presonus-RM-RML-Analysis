"""Run original alias registration with bounded CCL and vector boundaries."""
import hashlib
import struct
import json
from pathlib import Path
from io import BytesIO

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP

BASE = Path("/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261121/packeting")
MAP = BASE / "READ_INPUTS-post15-wave-compatible35-batch04-cycle21_g04.json"
ORIGINAL = "rootfs/CS18_v13840/home/root/surface"
ELF_SHA = "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0"
MANGLED = "_ZN8Presonus21MappablePageComponent8addAliasEiPKc"
ADDRESS, SIZE, OFFSET = 0x5CE98, 148, 0x54E98
BODY_SHA = "ac2dbaadfe1105727725bf36ecf4cef9ba9e73c768f384f80d79897fec0d7cdf"


def observe_elf():
    path = Path(json.loads(MAP.read_text())[ORIGINAL]["frozen_read_path"])
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == ELF_SHA
    elf = ELFFile(BytesIO(raw))
    symbol = elf.get_section_by_name(".symtab").get_symbol_by_name(MANGLED)[0]
    section = elf.get_section(symbol["st_shndx"])
    assert section.name == ".text"
    assert (symbol["st_value"], symbol["st_size"]) == (ADDRESS, SIZE)
    assert section["sh_offset"] + ADDRESS - section["sh_addr"] == OFFSET
    body = raw[OFFSET:OFFSET + SIZE]
    assert hashlib.sha256(body).hexdigest() == BODY_SHA
    cast_id, = struct.unpack_from("<I", body, 0x90)
    cases = []
    for tag, count, capacity, result in ((42, 0, 0, "ok"), (-1, 3, 0, "ok"),
                                         (-7, 4, 7, "ok"), (8, 2, 0, "no_param"),
                                         (9, 2, 0, "no_cast"), (10, 2, 0, "no_resize")):
        target = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        for address, length in ((0x5C000, 0x2000), (0x120000, 0x1000),
                                (0x200000, 0x10000)):
            target.mem_map(address, length)
        target.mem_write(ADDRESS, body)
        obj, param, table, data, name, cast, stop = (
            0x201000, 0x202000, 0x203000, 0x204000, 0x205000, 0x206000, 0x20F000
        )

        def word(address, value):
            target.mem_write(address, struct.pack("<I", value & 0xffffffff))

        def get(address):
            return struct.unpack("<I", target.mem_read(address, 4))[0]

        word(obj + 0x38, count)
        word(obj + 0xB8, data)
        word(obj + 0xBC, 0)
        word(obj + 0xC0, capacity)
        word(param, table)
        word(table, cast)
        target.mem_write(name, b"level_alias\0")
        events = []
        used_tag = None

        def call(uc, pc, size, _):
            nonlocal used_tag
            if pc not in (0x120BB0, cast, 0x5D26C):
                return
            r0, r1, r2 = [uc.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2)]
            if pc == 0x120BB0:
                assert r0 == obj + 0x28 and r2 == name
                used_tag = r1
                events.append("add_alias")
                value = 0 if result == "no_param" else param
            elif pc == cast:
                assert r0 == param and r1 == cast_id
                events.append("cast_alias")
                value = 0 if result == "no_cast" else param
            else:
                assert r0 == obj + 0xB4 and r1 == 1
                events.append("resize")
                value = int(result != "no_resize")
                if value:
                    word(obj + 0xC0, 1)
            uc.reg_write(UC_ARM_REG_R0, value)
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

        target.hook_add(UC_HOOK_CODE, call)
        for register, value in ((UC_ARM_REG_R0, obj), (UC_ARM_REG_R1, tag & 0xffffffff),
                                (UC_ARM_REG_R2, name), (UC_ARM_REG_SP, 0x20E000),
                                (UC_ARM_REG_LR, stop)):
            target.reg_write(register, value)
        target.emu_start(ADDRESS, stop, count=200)
        assert target.reg_read(UC_ARM_REG_PC) == stop
        cases.append({"tag": tag, "initial_param_count": count, "capacity": capacity,
                      "boundary": result, "events": events, "used_tag": used_tag,
                      "collected": get(obj + 0xBC), "stored_alias": get(data) == param})
    return cases


if __name__ == "__main__":
    print(json.dumps({"elf_observations": observe_elf()}, indent=2))
