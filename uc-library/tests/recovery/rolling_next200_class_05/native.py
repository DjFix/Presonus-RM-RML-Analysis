"""Execute the sealed ARM method offline and emit deterministic observations."""
import hashlib
from io import BytesIO
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn.arm_const import (
    UC_ARM_REG_CPSR, UC_ARM_REG_IP, UC_ARM_REG_LR, UC_ARM_REG_PC,
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
    UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
    UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11, UC_ARM_REG_SP,
)

ELF = Path(
    "/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/"
    "rolling-c001-20261124/packeting/first10/snapshot/"
    "rootfs/RML16AI_Rack_13731/home/root/mixer"
)
ELF_SHA256 = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
RANGE_SHA256 = "60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad"
MANGLED = "_ZN8Presonus5Mixer20PermissionsComponent20onPermissionsChangedEv"
ADDRESS, SIZE, SECTION_INDEX, OFFSET = 0x5062C, 16, 12, 0x4862C
REGISTERS = (
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
    UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
    UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11,
)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def observe(body, case, fill):
    cpu = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
    page, receiver, stack, stop = ADDRESS & ~0xFFF, 0x710000, 0x730000, 0x750000
    sp = stack + 0x800
    for base in (page, receiver, stack, stop):
        cpu.mem_map(base, 0x1000)
    cpu.mem_write(ADDRESS, body)
    sentinel = bytes((fill + i * (case + 1)) % 256 for i in range(0x1000))
    stack_initial = bytes([fill]) * 0x1000
    cpu.mem_write(receiver, sentinel)
    cpu.mem_write(stack, stack_initial)
    values = [receiver + 0x100 + case * 0x100] + [
        (fill * 0x01010101 - i) & 0xFFFFFFFF for i in range(1, len(REGISTERS))
    ]
    for register, value in zip(REGISTERS, values):
        cpu.reg_write(register, value)
    for register, value in ((UC_ARM_REG_CPSR, 0xA0000010), (UC_ARM_REG_SP, sp),
                            (UC_ARM_REG_LR, stop)):
        cpu.reg_write(register, value)
    trace, reads, writes = [], [], []
    cpu.hook_add(unicorn.UC_HOOK_CODE, lambda _, addr, size, __: trace.append(addr))
    cpu.hook_add(unicorn.UC_HOOK_MEM_READ,
                 lambda _, kind, addr, size, value, data: reads.append([addr - sp, size]))
    cpu.hook_add(unicorn.UC_HOOK_MEM_WRITE,
                 lambda _, kind, addr, size, value, data: writes.append([addr - sp, size]))
    cpu.emu_start(ADDRESS, stop, count=5)
    stack_final = bytes(cpu.mem_read(stack, 0x1000))
    assert trace == list(range(ADDRESS, ADDRESS + SIZE, 4))
    assert cpu.reg_read(UC_ARM_REG_PC) == stop
    assert cpu.reg_read(UC_ARM_REG_SP) == sp
    assert cpu.reg_read(UC_ARM_REG_LR) == stop
    assert cpu.reg_read(UC_ARM_REG_IP) == sp
    assert cpu.reg_read(UC_ARM_REG_CPSR) == 0xA0000010
    assert [cpu.reg_read(reg) for reg in REGISTERS] == values
    assert cpu.mem_read(receiver, 0x1000) == sentinel
    assert stack_final[:0x7F0] == stack_initial[:0x7F0]
    assert stack_final[0x800:] == stack_initial[0x800:]
    assert sorted(writes) == [[offset, 4] for offset in (-16, -12, -8, -4)]
    assert sorted(reads) == [[offset, 4] for offset in (-16, -12, -8)]
    return dict(case=case, receiver_unchanged=True, frame_restored=True,
                trace=trace, reads_relative_to_sp=reads, writes_relative_to_sp=writes,
                saved_frame_hex=stack_final[0x7F0:0x800].hex())


def main():
    raw = ELF.read_bytes()
    assert digest(raw) == ELF_SHA256
    elf = ELFFile(BytesIO(raw))
    section = elf.get_section(SECTION_INDEX)
    assert elf["e_machine"] == "EM_ARM" and section.name == ".text"
    offset = section["sh_offset"] + ADDRESS - section["sh_addr"]
    assert offset == OFFSET
    assert 0 <= ADDRESS - section["sh_addr"] <= section["sh_size"] - SIZE
    matches = elf.get_section_by_name(".symtab").get_symbol_by_name(MANGLED)
    assert any((row["st_value"], row["st_size"], row["st_shndx"]) ==
               (ADDRESS, SIZE, SECTION_INDEX) for row in matches)
    body = raw[offset:offset + SIZE]
    assert digest(body) == RANGE_SHA256
    print(json.dumps(dict(
        elf_sha256=ELF_SHA256, mangled=MANGLED, address=ADDRESS, size=SIZE,
        section=section.name, section_index=SECTION_INDEX, offset=offset,
        range_sha256=RANGE_SHA256, unicorn_version=unicorn.__version__,
        cases=[observe(body, case, fill) for case, fill in enumerate((0, 0xA5, 0xFF))]
    ), indent=2))


if __name__ == "__main__":
    main()
