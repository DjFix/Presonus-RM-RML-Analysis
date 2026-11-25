"""Replay exact ARM code with only the native absolute-clock input replaced."""

import hashlib
import io
import json
from pathlib import Path
import struct
import sys

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_HOOK_MEM_INVALID
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP,
)

CLOCK = "_ZN4Core15GetAbsoluteTimeEv"
DIVIDE = "__aeabi_ldivmod"
STOP = 0x810000
STACK = 0x820000
RECEIVERS = (0x830000, 0x830080)
TAGS = (0x436C5274, 0x436C436F, 0x436F6D70, 0, -1, 0x436C5275)
TICKS = (-1000001, -999999, 0, 1, 999999, 1000000, 1000001,
         1000000000, 4294967296000249, 86401234000567, 98765432112345678,
         8999999999999999998, 8999999999999999999, 9000000000000000000,
         9000000000000000001, -8999999999999999999, -9000000000000000000,
         -9000000000000000001, 9223372036854775807)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def function(elf, image, name):
    row, = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    address, size, index = row["st_value"], row["st_size"], row["st_shndx"]
    section = elf.get_section(index)
    assert row["st_info"]["type"] == "STT_FUNC" and (size > 0 or name == DIVIDE)
    assert section.name == ".text" and section["sh_type"] == "SHT_PROGBITS"
    relative = address - section["sh_addr"]
    assert 0 <= relative <= section["sh_size"] - size
    offset = section["sh_offset"] + relative
    code = image[offset:offset + size]
    return dict(mangled=name, address=address, size=size, section=index,
                section_name=section.name, file_offset=offset,
                range_hex=code.hex(), range_sha256=sha(code))


def signed_pair(low, high):
    return struct.unpack("<q", struct.pack("<II", low, high))[0]


def execute(emu, target, receiver, argument, providers):
    trace = []
    instructions = bytearray()
    write_addresses = []
    emu.mem_write(STACK, bytes(4096))
    emu.mem_write(RECEIVERS[0], bytes(range(256)))
    emu.reg_write(UC_ARM_REG_SP, STACK + 2048)
    emu.reg_write(UC_ARM_REG_LR, STOP)
    emu.reg_write(UC_ARM_REG_R0, receiver)
    emu.reg_write(UC_ARM_REG_R1, (argument or 0) & 0xffffffff)
    emu.reg_write(UC_ARM_REG_R2, 0)
    emu.reg_write(UC_ARM_REG_R3, 0)

    def observe(machine, address, size, data):
        instructions.extend(struct.pack("<I", address))
        instructions.extend(machine.mem_read(address, size))
        if providers and address == providers[CLOCK]["address"]:
            trace.append([CLOCK, argument])
            machine.reg_write(UC_ARM_REG_R0, argument & 0xffffffff)
            machine.reg_write(UC_ARM_REG_R1, (argument >> 32) & 0xffffffff)
            machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))
        elif providers and address == providers[DIVIDE]["address"]:
            raw = signed_pair(machine.reg_read(UC_ARM_REG_R0), machine.reg_read(UC_ARM_REG_R1))
            scale = signed_pair(machine.reg_read(UC_ARM_REG_R2), machine.reg_read(UC_ARM_REG_R3))
            trace.append([DIVIDE, raw, scale])

    def memory_write(machine, access, address, size, value, data):
        write_addresses.append((address, size))

    code_hook = emu.hook_add(UC_HOOK_CODE, observe)
    write_hook = emu.hook_add(UC_HOOK_MEM_WRITE, memory_write)
    def unmapped(machine, access, address, size, value, data):
        print(hex(machine.reg_read(UC_ARM_REG_PC)), hex(address), hex(machine.reg_read(UC_ARM_REG_SP)), argument, trace, file=sys.stderr)
        return False

    invalid_hook = emu.hook_add(UC_HOOK_MEM_INVALID, unmapped)
    emu.ctl_flush_tb()
    emu.emu_start(target, STOP, count=10000)
    emu.hook_del(code_hook)
    emu.hook_del(write_hook)
    emu.hook_del(invalid_hook)
    assert emu.reg_read(UC_ARM_REG_PC) == STOP
    assert all(STACK <= address <= STACK + 4096 - size
               for address, size in write_addresses), write_addresses
    assert bytes(emu.mem_read(RECEIVERS[0], 256)) == bytes(range(256))
    low, high = emu.reg_read(UC_ARM_REG_R0), emu.reg_read(UC_ARM_REG_R1)
    if providers:
        assert trace == [[CLOCK, argument], [DIVIDE, argument, 1000000]], trace
        value = signed_pair(low, high)
        magnitude = abs(argument) // 1000000
        assert value == (-magnitude if argument < 0 else magnitude)
    else:
        assert not trace and low in (0, receiver)
        value = int(low == receiver)
    return dict(receiver=receiver, argument=argument, result=value,
                call_trace=trace, stack_writes=len(write_addresses),
                instruction_trace_sha256=sha(instructions))


def run(packet):
    context = json.loads(Path(packet).read_bytes())
    mode = context["task"]["id"].removeprefix("sqlite02_clientrootcomponent_")
    arguments = {"cast_to": TAGS, "get_root": (None,), "get_system_time": TICKS}[mode]
    observed = []
    for receipt in context["originals"]:
        original = receipt["original"]
        image = Path(original["elf_path"]).read_bytes()
        assert sha(image) == original["elf"]
        elf = ELFFile(io.BytesIO(image))
        assert elf["e_machine"] == "EM_ARM" and elf.little_endian
        identity = function(elf, image, original["mangled"])
        assert all(original[key] == value for key, value in identity.items())
        emu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        segments = list(elf.iter_segments(type="PT_LOAD"))
        first = min(segment["p_vaddr"] for segment in segments) & ~4095
        end = max(segment["p_vaddr"] + segment["p_memsz"] for segment in segments)
        emu.mem_map(first, ((end + 4095) & ~4095) - first)
        for segment in segments:
            emu.mem_write(segment["p_vaddr"], segment.data())
        for base in (STOP, STACK, RECEIVERS[0]):
            emu.mem_map(base, 4096)
        providers = {}
        if mode == "get_system_time":
            providers = {name: function(elf, image, name) for name in (CLOCK, DIVIDE)}
            for offset, name in ((16, CLOCK), (28, DIVIDE)):
                instruction, = struct.unpack_from("<I", bytes.fromhex(identity["range_hex"]), offset)
                assert instruction >> 24 == 0xeb
                relative = (instruction & 0xffffff) << 2
                if relative & 0x2000000:
                    relative -= 0x4000000
                assert identity["address"] + offset + 8 + relative == providers[name]["address"]
        cases = [execute(emu, identity["address"], receiver, argument, providers)
                 for receiver in RECEIVERS for argument in arguments]
        if mode == "cast_to":
            assert all(case["result"] == int(case["argument"] in TAGS[:3]) for case in cases)
        if mode == "get_root":
            assert all(case["result"] == 1 for case in cases)
        observed.append(dict(original=original, providers=providers, cases=cases))
    return dict(mode=mode, observations=observed)


if __name__ == "__main__":
    print(json.dumps(run(sys.argv[1]), indent=2))
