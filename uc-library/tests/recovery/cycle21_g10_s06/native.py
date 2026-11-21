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

BOUNDARIES = {0xAD8D4, 0xAD6D0, 0xAD978, 0xADC68, 0xADAF4, 0xADB40}
ROUTES = {0xAD8D4: "touchscreen", 0xAD6D0: "util", 0xAD978: "diagnostics",
          0xADC68: "calibrate", 0xADAF4: "fader", 0xADB40: "audio"}


def cases(elf, address):
    result = []
    for tag in [-2147483648, -1, 0, 1, *range(2, 40), 2147483647]:
        def init(uc):
            word(uc, PAR + 12, PAR + 0x100)
            word(uc, PAR + 0x104, tag)

        def provider(uc, trace, pc, a, b, c):
            assert (a, b) == (OBJ, PAR)
            trace.append([ROUTES[pc], pc, a, b])
            return None

        _, trace = run(elf, address, PAR, init, provider)
        result.append(dict(tag=tag, events=trace))
    return result


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
