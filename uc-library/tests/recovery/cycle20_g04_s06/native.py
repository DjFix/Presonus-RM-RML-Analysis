"""Replay the exact original ARM body through direct and vtable-selected entry."""

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

ELF_SHA = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
NAME = "_ZN8Presonus5Mixer16ChannelComponent17setGEQFaderScalerEff"
ADDRESS = 0x3FB9C
BODY_SHA = "60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad"
TABLES = [
    ("_ZTVN8Presonus5Mixer16ChannelComponentE", 0x173500, 112,
     "04c960c5455ce2fe2c18146daada31d1bcc9a377247e56965b85edb965fd2be5"),
    ("_ZTVN8Presonus5Mixer14InputComponentE", 0x174228, 144,
     "0c14cf2d6061823c103a0ba63c751fd77ba8e23e59e9330d8fa68795940e1d9b"),
    ("_ZTVN8Presonus5Mixer15OutputComponentE", 0x1764F0, 116,
     "49def5209a2cf9f139ca3262aa0e9ac8e198b4fe728c692f1d6b27d79ee2cb0f"),
]
SLOT = 72
RECEIVER, STACK, RETURN, DISPATCH = 0x600000, 0x602000, 0x603000, 0x604000
# Harness executes ldr ip, [r0]; ldr pc, [ip, #72] against the original table.
DISPATCH_CODE = struct.pack("<II", 0xE590C000, 0xE59CF000 | SLOT)
WORDS = [(0, 0x80000000), (0x3F800000, 0xBF800000),
         (0x00000001, 0x00800000), (0x7F800000, 0xFF800000),
         (0x7FC01234, 0x3E800000)]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_range(elf, name, address, size, expected_sha, section_name, symbol_kind):
    symbol, = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    assert (symbol["st_value"], symbol["st_size"], symbol["st_info"]["type"]) == (
        address, size, symbol_kind)
    section = elf.get_section(symbol["st_shndx"])
    offset = address - section["sh_addr"]
    assert section.name == section_name and 0 <= offset <= section["sh_size"] - size
    memory = section.data()[offset:offset + size]
    assert digest(memory) == expected_sha
    return dict(mangled=name, address=address, size=size, section=section_name,
                section_index=symbol["st_shndx"], range_sha256=expected_sha,
                file_offset=section["sh_offset"] + offset), memory


def case(body, route, table, words):
    arm = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
    arm.mem_map(ADDRESS & ~0xFFF, 0x1000)
    arm.mem_write(ADDRESS, body)
    arm.mem_map(RECEIVER, 0x5000)
    state = bytearray(bytes(range(256)) * 4)
    start = ADDRESS
    address_point = None
    if table is not None:
        table_info, table_bytes = table
        address = table_info["address"]
        address_point = address + 8
        page = address & ~0xFFF
        arm.mem_map(page, 0x2000)
        arm.mem_write(address, table_bytes)
        state[0:4] = struct.pack("<I", address_point)
        arm.mem_write(DISPATCH, DISPATCH_CODE)
        start = DISPATCH
    arm.mem_write(RECEIVER, bytes(state))
    instructions = []
    stack_accesses = []
    dispatch_reads = []

    def instruction(_, pc, size, __):
        assert size == 4
        instructions.append(pc)

    def memory(_, access, address, size, __, ___):
        pc = arm.reg_read(reg.UC_ARM_REG_PC)
        if pc in (DISPATCH, DISPATCH + 4):
            assert access == unicorn.UC_MEM_READ and size == 4
            dispatch_reads.append(address)
        else:
            assert STACK - 16 <= address <= STACK - size
            stack_accesses.append([access, address - STACK, size])

    arm.hook_add(unicorn.UC_HOOK_CODE, instruction)
    arm.hook_add(unicorn.UC_HOOK_MEM_READ | unicorn.UC_HOOK_MEM_WRITE, memory)
    for register, value in ((reg.UC_ARM_REG_R0, RECEIVER), (reg.UC_ARM_REG_R1, words[0]),
                            (reg.UC_ARM_REG_R2, words[1]), (reg.UC_ARM_REG_SP, STACK),
                            (reg.UC_ARM_REG_LR, RETURN)):
        arm.reg_write(register, value)
    arm.emu_start(start, RETURN, count=12)
    assert arm.reg_read(reg.UC_ARM_REG_PC) == RETURN
    assert arm.reg_read(reg.UC_ARM_REG_SP) == STACK
    assert dispatch_reads == ([] if table is None else [RECEIVER, address_point + SLOT])
    body_trace = list(range(ADDRESS, ADDRESS + len(body), 4))
    assert instructions == (body_trace if table is None else [DISPATCH, DISPATCH + 4, *body_trace])
    after = bytes(arm.mem_read(RECEIVER, len(state)))
    assert after == state
    return dict(inputs=[route, *words], state_unchanged=after == state,
                state_sha256=digest(after), executed=instructions,
                stack_accesses=stack_accesses, dispatch_reads=dispatch_reads,
                observed_r0=arm.reg_read(reg.UC_ARM_REG_R0))


def observe(path):
    data = path.read_bytes()
    assert digest(data) == ELF_SHA
    elf = ELFFile(io.BytesIO(data))
    assert elf["e_machine"] == "EM_ARM" and elf.little_endian
    original, body = read_range(elf, NAME, ADDRESS, 16, BODY_SHA, ".text", "STT_FUNC")
    tables = [read_range(elf, *row, ".rodata", "STT_OBJECT") for row in TABLES]
    for _, contents in tables:
        assert struct.unpack_from("<I", contents, 8 + SLOT)[0] == ADDRESS
    cases = [case(body, route, table, words)
             for route, table in enumerate([None, *tables]) for words in WORDS]
    return dict(elf_sha256=ELF_SHA, original=original, vtable_slot_from_address_point=SLOT,
                observed_vtables=[table for table, _ in tables], cases=cases,
                unicorn_version=unicorn.__version__, pyelftools_version=elftools.__version__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--out", type=Path)
    mode.add_argument("--verify", type=Path)
    args = parser.parse_args()
    observed = observe(args.elf)
    if args.out:
        with args.out.open("x") as stream:
            json.dump(observed, stream, indent=2)
            stream.write("\n")
    else:
        assert observed == json.loads(args.verify.read_text())
        print(f"{len(observed['cases'])} original ARM cases reproduced")
