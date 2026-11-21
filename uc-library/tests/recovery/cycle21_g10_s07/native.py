"""Execute verified ARM range and retain explicit dependency-boundary traces."""
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import struct

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM, Uc
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0,
                               UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP)

ROOT = Path("/home/rs/projects/opencs/ai-line-analysis")
RUN = ROOT / "temp/recovery-work/reconstruction10x10-20261121/packeting"
TASK = Path(__file__).resolve().parent.name
PACKET = RUN / "post39-tail-batch02/packets" / TASK
READS = RUN / "READ_INPUTS-post39-tail-batch02-cycle21_g10-post39-tail-scoped01-dispatch02.json"
ELF = "rootfs/CS18_v13840/home/root/surface"
OBJ, SUB, PAR, STACK, STOP = [0x1000000 + 0x1000 * i for i in range(5)]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def word(machine, address, value=None):
    if value is not None:
        machine.mem_write(address, struct.pack("<I", value & 0xFFFFFFFF))
    else:
        return struct.unpack("<I", machine.mem_read(address, 4))[0]


def run(image, address, argument, init, intercept):
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    machine.mem_map(0x8000, 0x300000)
    for segment in image.iter_segments():
        if segment["p_type"] == "PT_LOAD":
            machine.mem_write(segment["p_vaddr"], segment.data())
    machine.mem_map(OBJ, 0x5000)
    for register, value in ((UC_ARM_REG_R0, OBJ), (UC_ARM_REG_R1, argument),
                            (UC_ARM_REG_SP, STACK + 0x800), (UC_ARM_REG_LR, STOP)):
        machine.reg_write(register, value)
    init(machine)
    trace = []

    def hook(uc, site, size, _):
        assert address <= site < address + TARGET["size"] or site in BOUNDARIES, hex(site)
        if site not in BOUNDARIES:
            return
        a, b, c = (uc.reg_read(reg) for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2))
        result = intercept(uc, trace, site, a, b, c)
        if result is not None:
            uc.reg_write(UC_ARM_REG_R0, result)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    machine.hook_add(UC_HOOK_CODE, hook)
    machine.emu_start(address, STOP, count=1000)
    assert machine.reg_read(UC_ARM_REG_PC) == STOP
    return machine, trace


def generate():
    read_map = json.loads(READS.read_text())
    path = Path(read_map[ELF]["frozen_read_path"])
    binary = path.read_bytes()
    assert sha(binary) == TARGET["original_elf_sha256"] == read_map[ELF]["sha256"]
    e = ELFFile(BytesIO(binary))
    sect = e.get_section(TARGET["section"])
    assert sect.name == ".text"
    address, size = TARGET["address"], TARGET["size"]
    assert sect["sh_addr"] <= address and address + size <= sect["sh_addr"] + sect["sh_size"]
    offset = sect["sh_offset"] + address - sect["sh_addr"]
    exact = sha(binary[offset:offset + size])
    packet_hash = re.search(r"section \.text; SHA256 `([0-9a-f]{64})`",
                            (PACKET / "ELF_CONTEXT.md").read_text())[1]
    assert exact == packet_hash
    symbols = e.get_section_by_name(".symtab").get_symbol_by_name(TARGET["mangled"])
    assert any(s["st_value"] == address and s["st_size"] == size
               and s["st_shndx"] == TARGET["section"] for s in symbols)
    rows = cases(e, address)
    return dict(original=TARGET, elf_path=str(path), section=sect.name, file_offset=offset,
                range_sha256=exact, cases=rows)


TARGET = json.loads((PACKET / "request.json").read_text())["targets"][0]

SETTING, SECTION, WRITER, SAVE = 0x26AC0C, SUB + 0x200, SUB + 0x400, 0x1004200
GUARD, KEY = 0x26AC08, 0x195E64
BOUNDARIES = {0x124108, 0x123978, 0x1188EC, SAVE, 0x80DB0, 0x124AE8,
              0x1260EC, 0xB1C4, 0x1184F8, 0xAB7C, 0xAF24}


def cases(elf, address):
    result = []
    for present, initialized, dirty in [(False, False, False), (False, True, True),
                                         (True, True, False), (True, True, True)]:
        def init(uc):
            word(uc, GUARD, int(initialized))
            word(uc, SETTING + 0x20C, 4 if dirty else 0)
            word(uc, SETTING + 0x218, WRITER)
            word(uc, OBJ, OBJ + 0x800)
            word(uc, OBJ + 0x824, SAVE)
            assert bytes(uc.mem_read(KEY, 8)) == b"surface\0"

        def provider(uc, trace, pc, a, b, c):
            if pc == 0xB1C4:
                assert a == GUARD
                trace.append(["guard_acquire", a])
                return 1
            if pc == 0x1184F8:
                assert a == SETTING
                trace.append(["setting_init", a])
                return None
            if pc == 0xAB7C:
                assert a == GUARD
                trace.append(["guard_release", a])
                word(uc, GUARD, 1)
                return None
            if pc == 0xAF24:
                assert a == SETTING
                trace.append(["atexit", a])
                return 0
            if pc == 0x124108:
                assert b == KEY
                trace.append(["get_section", "surface"])
                return SECTION if present else 0
            if pc == 0x124AE8:
                assert b == KEY
                trace.append(["lookup_or_add", "surface"])
                return SECTION
            if pc == 0x1260EC:
                assert (a, b) == (SECTION, WRITER)
                trace.append(["make_attributes", a, b])
                return SECTION
            if pc == 0x123978:
                assert a == SECTION
                trace.append(["remove_all", a])
                return None
            if pc == 0x1188EC:
                assert b == SECTION and c == 1
                trace.append(["builder", a, b, c])
                return None
            if pc == SAVE:
                assert a == OBJ and STACK <= b < STACK + 0x1000
                assert word(uc, b + 0x2C) == SECTION or STACK <= word(uc, b + 0x2C) < STACK + 0x1000
                trace.append(["save", a, b, word(uc, SETTING + 0x20C)])
                return 1
            assert pc == 0x80DB0
            trace.append(["destroy_builder_vector", a])
            return None

        uc, trace = run(elf, address, 0, init, provider)
        result.append(dict(present=present, initialized=initialized, dirty=dirty,
                           events=trace, final_flags=word(uc, SETTING + 0x20C)))
    return result


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
