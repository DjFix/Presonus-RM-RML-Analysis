"""Run ARM syncParams with instrumented parameter dispatch boundaries."""
import hashlib
import struct
import json
from pathlib import Path
from io import BytesIO

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP

BASE = Path("/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261121/packeting")
MAP = BASE / "READ_INPUTS-post15-wave-compatible35-batch04-cycle21_g04.json"
ORIGINAL = "rootfs/RML16AI_Rack_13731/home/root/mixer"
ELF_SHA = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
MANGLED = "_ZN8Presonus17LinkableComponent10syncParamsERN4Core8Portable9ParameterES4_b"
ADDRESS, SIZE, OFFSET = 0x8264C, 264, 0x7A64C
BODY_SHA = "2498b0e6dad06384693548bbe0c2a78d6313b30b02d83546b8e8c82f982e659b"


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
    cases = []
    color_id, = struct.unpack_from("<I", raw, OFFSET + SIZE - 4)
    for mode in ("numeric", "string", "color", "color_mismatch"):
        for edit in (0, 1):
            target = Uc(UC_ARCH_ARM, UC_MODE_ARM)
            for address, size in ((0x82000, 0x1000), (0x11C000, 0x1000),
                                  (0x11E000, 0x1000), (0x200000, 0x10000)):
                target.mem_map(address, size)
            target.mem_write(ADDRESS, body)
            src, dst, info = 0x201000, 0x202000, 0x203000
            src_vtable, dst_vtable = 0x204000, 0x205000
            stop = 0x20F000

            def word(address, value):
                target.mem_write(address, struct.pack("<I", value))

            word(src, src_vtable)
            word(dst, dst_vtable)
            word(src + 12, info)
            word(info, {"numeric": 3, "string": 4}.get(mode, 6))
            hooks = {
                0x206000: "src_cast", 0x206004: "dst_cast",
                0x206008: "get_value", 0x20600C: "set_value",
                0x206010: "to_string", 0x206014: "from_string",
                0x11C8B0: "get_color", 0x11EF9C: "set_color",
            }
            for table, slot, address in ((src_vtable, 0, 0x206000), (dst_vtable, 0, 0x206004),
                    (src_vtable, 0x44, 0x206008), (dst_vtable, 0x58, 0x20600C),
                    (src_vtable, 0x70, 0x206010), (dst_vtable, 0x74, 0x206014)):
                word(table + slot, address)
            events = []
            copied = []

            def call(uc, pc, size, _):
                if pc not in hooks:
                    return
                name = hooks[pc]
                r0, r1, r2 = [uc.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2)]
                events.append(name)
                assert r0 == (src if name in ("src_cast", "get_value", "to_string", "get_color") else dst)
                if name.endswith("_cast"):
                    assert r1 == color_id
                    uc.reg_write(UC_ARM_REG_R0, 0 if name == "dst_cast" and mode == "color_mismatch" else r0)
                elif name == "get_value":
                    uc.reg_write(UC_ARM_REG_R0, 0x40500000)  # 3.25
                elif name == "get_color":
                    uc.reg_write(UC_ARM_REG_R0, 0xFF127ABC)
                elif name == "to_string":
                    assert r2 == 256 and uc.mem_read(r1, 1) == b"\0"
                    uc.mem_write(r1, b"alpha\0")
                elif name == "from_string":
                    copied.extend([bytes(uc.mem_read(r1, 6)).rstrip(b"\0").decode(), r2])
                elif name == "set_value":
                    copied.extend([struct.unpack("<f", struct.pack("<I", r1))[0], r2])
                elif name == "set_color":
                    copied.extend([r1, r2])
                uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

            target.hook_add(UC_HOOK_CODE, call)
            for register, value in ((UC_ARM_REG_R0, 0x20A000), (UC_ARM_REG_R1, src),
                                    (UC_ARM_REG_R2, dst), (UC_ARM_REG_R3, edit),
                                    (UC_ARM_REG_SP, 0x20E000), (UC_ARM_REG_LR, stop)):
                target.reg_write(register, value)
            target.emu_start(ADDRESS, stop, count=200)
            assert target.reg_read(UC_ARM_REG_PC) == stop
            cases.append({"mode": mode, "edit": edit, "events": events, "copied": copied})
    return cases


if __name__ == "__main__":
    print(json.dumps({"elf_observations": observe_elf()}, indent=2))
