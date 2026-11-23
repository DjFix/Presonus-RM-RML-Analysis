"""Observe one exact ARM callback with no provider stubs or device access."""

import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

import elftools
import unicorn
from elftools.elf.elffile import ELFFile
from unicorn import arm_const as reg

SCOPE = Path(__file__).parent.name
ELF_SHA = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
BODY_SHA = "60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad"
PREFIX = "_ZN8Presonus5Mixer18MixerComponentBase"
TARGETS = {
    "cycle20_g04_s02": (PREFIX + "11getPropertyERN4Core8PropertyE", 0x2F6B0),
    "cycle20_g04_s03": (PREFIX + "8Delegate13notifyStoringEb", 0x52BDC),
    "cycle20_g04_s04": (
        PREFIX + "8Delegate16faderLocateDirtyEPNS0_16ChannelComponentE", 0x52BEC),
}
RECEIVER, ARGUMENT, SECOND, STACK, RETURN = (
    0x600000, 0x601000, 0x602000, 0x604000, 0x605000,
)
MARKER = 0x12345678


def digest(data):
    return hashlib.sha256(data).hexdigest()


def range_bytes(elf, name, address, size, expected_hash):
    symbol, = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    assert (symbol["st_value"], symbol["st_size"], symbol["st_shndx"],
            symbol["st_info"]["type"]) == (address, size, 12, "STT_FUNC")
    section = elf.get_section(symbol["st_shndx"])
    offset = address - section["sh_addr"]
    assert section.name == ".text" and 0 <= offset <= section["sh_size"] - size
    body = section.data()[offset:offset + size]
    assert digest(body) == expected_hash
    return dict(mangled=name, address=address, size=size, section=section.name,
                section_index=12, range_sha256=expected_hash,
                file_offset=section["sh_offset"] + offset), body


def observe_case(address, body, inputs):
    arm = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
    page = address & ~0xFFF
    arm.mem_map(page, 0x1000)
    arm.mem_write(address, body)
    arm.mem_map(RECEIVER, 0x6000)
    arm.mem_write(RECEIVER, struct.pack("<I", MARKER) + b"\xA3" * 60)
    arm.mem_write(ARGUMENT, b"\x22" * 64)
    arm.mem_write(SECOND, b"\x55" * 64)

    if SCOPE.endswith("02"):
        type_id, size, sentinel = inputs
        arm.mem_write(ARGUMENT, struct.pack("<iiII", type_id, size, sentinel,
                                           sentinel ^ 0xFFFFFFFF))
        argument = ARGUMENT
    elif SCOPE.endswith("03"):
        argument, = inputs
    else:
        argument = (0, ARGUMENT, SECOND)[inputs[0]]

    receiver_before = bytes(arm.mem_read(RECEIVER, 64))
    payloads_before = [bytes(arm.mem_read(pointer, 64)) for pointer in (ARGUMENT, SECOND)]
    instructions = []
    stack_accesses = []

    def instruction(_, pc, size, __):
        assert address <= pc < address + len(body) and size == 4
        instructions.append(pc)

    def memory(_, access, memory_address, size, __, ___):
        assert STACK - 16 <= memory_address <= STACK - size
        stack_accesses.append([access, memory_address - STACK, size])

    arm.hook_add(unicorn.UC_HOOK_CODE, instruction)
    arm.hook_add(unicorn.UC_HOOK_MEM_READ | unicorn.UC_HOOK_MEM_WRITE, memory)
    for register, value in ((reg.UC_ARM_REG_R0, RECEIVER), (reg.UC_ARM_REG_R1, argument),
                            (reg.UC_ARM_REG_SP, STACK), (reg.UC_ARM_REG_LR, RETURN)):
        arm.reg_write(register, value)
    arm.emu_start(address, RETURN, count=16)
    assert arm.reg_read(reg.UC_ARM_REG_PC) == RETURN
    assert arm.reg_read(reg.UC_ARM_REG_SP) == STACK
    assert instructions == list(range(address, address + len(body), 4))
    receiver_after = bytes(arm.mem_read(RECEIVER, 64))
    payloads_after = [bytes(arm.mem_read(pointer, 64)) for pointer in (ARGUMENT, SECOND)]
    assert receiver_before == receiver_after and payloads_before == payloads_after
    projected = (struct.unpack_from("<iiII", payloads_after[0]) if SCOPE.endswith("02")
                 else struct.unpack_from("<I", receiver_after))
    return dict(inputs=list(inputs), projected=list(projected),
                instructions=instructions, stack_accesses=stack_accesses,
                outside_stack_accesses=0, receiver_sha256=digest(receiver_after),
                payload_sha256=[digest(payload) for payload in payloads_after],
                observed_r0=arm.reg_read(reg.UC_ARM_REG_R0))


def observe(path):
    data = path.read_bytes()
    assert digest(data) == ELF_SHA
    elf = ELFFile(io.BytesIO(data))
    assert elf["e_machine"] == "EM_ARM" and elf.little_endian
    name, address = TARGETS[SCOPE]
    row, body = range_bytes(elf, name, address, 16, BODY_SHA)
    extra = []
    if SCOPE.endswith("02"):
        thunk, _ = range_bytes(
            elf, "_ZThn260_" + name[2:], 0x2F6A8, 8,
            "cfb656f3dcbc16e3b363d117753d3bbdb92eabbf64c7860047d4782614be5e01",
        )
        extra.append(thunk)
        inputs = [(0, 16, 0), (0x53657475, 16, MARKER), (-1, 16, 0xFFFFFFFF)]
    elif SCOPE.endswith("03"):
        inputs = [(0,), (1,)]
    else:
        inputs = [(0,), (1,), (2,)]
    return dict(elf_sha256=ELF_SHA, original=row, observation_only_ranges=extra,
                unicorn_version=unicorn.__version__, pyelftools_version=elftools.__version__,
                cases=[observe_case(address, body, values) for values in inputs])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", required=True, type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--out", type=Path)
    group.add_argument("--verify", type=Path)
    args = parser.parse_args()
    observations = observe(args.elf)
    if args.out:
        with args.out.open("x") as stream:
            json.dump(observations, stream, indent=2)
            stream.write("\n")
    else:
        assert observations == json.loads(args.verify.read_text())
        print(f"{len(observations['cases'])} original ARM cases reproduced")
