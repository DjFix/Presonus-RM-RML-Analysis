"""Execute the sealed ColorButton callback with controlled Core call boundaries."""
import hashlib
import itertools
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
                               UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC)

PACKETS = Path("temp/recovery-work/reconstruction10x10-20261121/packeting")
PACKET = PACKETS / "post15-wave-compatible35-batch04/packets/cycle21_g05_s10"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def generate():
    request = json.loads((PACKET / "request.json").read_text())
    target = request["targets"][0]
    source = request["work_binding"]["binary_releases"][0]["original_path"]
    inputs = json.loads((PACKETS / "READ_INPUTS-post15-wave-compatible35-batch04-cycle21_g05.json").read_text())
    original = Path(inputs[source]["frozen_read_path"])
    elf_hash = digest(original.read_bytes())
    assert elf_hash == target["original_elf_sha256"] == inputs[source]["sha256"]
    with original.open("rb") as stream:
        elf = ELFFile(stream)
        section = elf.get_section(target["section"])
        base, size = target["address"], target["size"]
        assert section.name == ".text"
        section_offset = base - section["sh_addr"]
        assert 0 <= section_offset <= section["sh_size"] - size
        file_offset = section["sh_offset"] + section_offset
        stream.seek(file_offset)
        body = stream.read(size)
    assert digest(body) == "22c32bcdaffe2a34d480e5cf8644c43e2d19b5445bedf3f6b9526aa777c10bc1"

    cases = []
    for color_is_primary, message, notify_primary in itertools.product(
            (False, True), (0, 2, 3, 4), (False, True)):
        uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        uc.mem_map(0x90000, 0x90000)
        uc.mem_write(base, body)
        receiver, primary, other, stack, stop = (
            0x300000, 0x301000, 0x302000, 0x304000, 0x305000)
        uc.mem_map(receiver, 0x6000)
        uc.mem_write(receiver + 0xec, struct.pack("<I", primary if color_is_primary else other))
        parameter = primary if notify_primary else other
        for reg, value in ((UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, parameter),
                           (UC_ARM_REG_R2, message), (UC_ARM_REG_SP, stack), (UC_ARM_REG_LR, stop)):
            uc.reg_write(reg, value)
        calls = []

        def observe(machine, address, _, __):
            if base <= address < base + size:
                return
            assert machine.reg_read(UC_ARM_REG_R0) == receiver
            if address == 0xf8768:
                assert machine.reg_read(UC_ARM_REG_R1) == parameter
                assert machine.reg_read(UC_ARM_REG_R2) == message
                calls.append("Control::paramChanged")
            elif address == 0x10e9fc:
                calls.append("View::invalidate")
            else:
                raise AssertionError(hex(address))
            machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

        uc.hook_add(UC_HOOK_CODE, observe)
        uc.emu_start(base, stop, count=100)
        assert uc.reg_read(UC_ARM_REG_PC) == stop and uc.reg_read(UC_ARM_REG_SP) == stack
        cases.append(dict(color_is_primary=color_is_primary, message=message,
                          notify_primary=notify_primary, calls=calls))
    return dict(target=target, elf_sha256=elf_hash, file_offset=file_offset,
                range_sha256=digest(body), section=section.name,
                unicorn=unicorn.__version__, cases=cases)


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
