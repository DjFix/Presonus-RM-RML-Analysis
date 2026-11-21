"""Run the verified wrapper with bounded provider and helper call boundaries."""
import hashlib
import itertools
import json
from pathlib import Path
from io import BytesIO

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP

BASE = Path("/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261121/packeting")
MAP = BASE / "READ_INPUTS-post15-wave-compatible35-batch04-cycle21_g04.json"
ORIGINAL = "rootfs/RML16AI_Rack_13731/home/root/mixer"
ELF_SHA = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
MANGLED = "_ZN8Presonus17LinkableComponent4loadERKN4Core8Portable12InputStorageE"
ADDRESS, SIZE, OFFSET = 0x82E94, 56, 0x7AE94
BODY_SHA = "962d71ada60a3a5cec60c262eae1773de520313a87c0aa62d750b010f7289ec7"


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
    for result in (0, 1):
        target = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        target.mem_map(0x80000, 0x10000)
        target.mem_map(0x119000, 0x1000)
        target.mem_map(0x200000, 0x10000)
        target.mem_write(ADDRESS, body)
        self_ptr, storage_ptr, stop = 0x202000, 0x203000, 0x20F000
        events = []

        def call(uc, pc, size, _):
            if pc not in (0x119A28, 0x82DC0):
                return
            assert uc.reg_read(UC_ARM_REG_R0) == self_ptr
            assert uc.reg_read(UC_ARM_REG_R1) == storage_ptr
            events.append("base_load" if pc == 0x119A28 else "loadAltMemory")
            uc.reg_write(UC_ARM_REG_R0, result if pc == 0x119A28 else 0xAA)
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

        target.hook_add(UC_HOOK_CODE, call)
        for register, value in ((UC_ARM_REG_R0, self_ptr), (UC_ARM_REG_R1, storage_ptr),
                                (UC_ARM_REG_SP, 0x20E000), (UC_ARM_REG_LR, stop)):
            target.reg_write(register, value)
        target.emu_start(ADDRESS, stop, count=100)
        assert target.reg_read(UC_ARM_REG_PC) == stop
        cases.append({"base_result": result, "events": events,
                      "return": target.reg_read(UC_ARM_REG_R0)})
    return cases


if __name__ == "__main__":
    print(json.dumps({"elf_observations": observe_elf(), "local_domains":
                      list(itertools.product((0, 1), repeat=3))}, indent=2))
