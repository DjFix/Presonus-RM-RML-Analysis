"""Run exact RM13731 mixer ARM code with an offline status response."""
import hashlib
import io
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_LR, UC_ARM_REG_SP, UC_ARM_REG_PC,
)

ELF = Path("/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261121/"
           "packeting/post39-tail-batch02/snapshot/rootfs/RML16AI_Rack_13731/home/root/mixer")
ELF_SHA = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
START, SIZE = 0x2F578, 152
RANGE_SHA = "4d2584d81ade69eb51eeac7b30e9fc213f1a599bc026cc0e7f714b6cc08ab6d8"
MIXER, HANDLER, STACK, STOP = 0x600000, 0x601000, 0x620000, 0x630000
TABLE, GETTER = 0x35A7B0, 0x9E984
CASES = ("none", "0", "1", "2", "3", "4294967295", "2147483650")
INITIALIZED = (
    *range(8, 36), 36, 37, 38, 40, 41, 42,
    *range(44, 48), *range(52, 60),
)


def generate():
    image = ELF.read_bytes()
    assert hashlib.sha256(image).hexdigest() == ELF_SHA
    elf = ELFFile(io.BytesIO(image))
    section = elf.get_section(12)
    offset = section["sh_offset"] + START - section["sh_addr"]
    assert section.name == ".text" and section["sh_addr"] <= START
    assert START + SIZE <= section["sh_addr"] + section["sh_size"]
    assert hashlib.sha256(image[offset:offset + SIZE]).hexdigest() == RANGE_SHA
    segments = [(s["p_vaddr"], s["p_memsz"], s.data()) for s in elf.iter_segments()
                if s["p_type"] == "PT_LOAD"]
    rows = []
    for mode in CASES:
        cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        first = min(start for start, _, _ in segments) & ~0xFFF
        end = max(start + size for start, size, _ in segments)
        cpu.mem_map(first, (end - first + 4095) & ~0xFFF)
        for start, _, data in segments:
            cpu.mem_write(start, data)
        cpu.mem_map(MIXER, 0x40000)
        put = lambda at, value: cpu.mem_write(at, struct.pack("<I", value))
        word = lambda at: struct.unpack("<I", cpu.mem_read(at, 4))[0]
        assert word(TABLE + 4) == GETTER
        put(MIXER + 0x380, HANDLER)
        put(HANDLER, TABLE)
        cpu.mem_write(STACK, bytes([0xA7]) * 0x1000)
        trace, outside_stack = [], []

        def hook(machine, pc, instruction_size, unused):
            if START <= pc < START + SIZE:
                return
            if pc != GETTER or machine.reg_read(UC_ARM_REG_R0) != HANDLER:
                raise ValueError(f"Unexpected native control flow at 0x{pc:x}")
            prop = machine.reg_read(UC_ARM_REG_R1)
            assert STACK <= prop < STACK + 0x1000 - 60
            assert (word(prop), word(prop + 4)) == (0x73746174, 60)
            payload = bytes(machine.mem_read(prop, 60))
            assert all(payload[i] == 0 for i in INITIALIZED)
            assert all(payload[i] == 0xA7 for i in range(8, 60) if i not in INITIALIZED)
            trace.append({"address": pc, "receiver": HANDLER, "property": payload.hex(),
                          "mode_written": None if mode == "none" else int(mode)})
            if mode != "none":
                put(prop + 8, int(mode))
            machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

        def write(machine, access, at, length, value, unused):
            if not STACK <= at < STACK + 0x1000:
                outside_stack.append([at, length, value])

        cpu.reg_write(UC_ARM_REG_R0, MIXER)
        cpu.reg_write(UC_ARM_REG_SP, STACK + 0xF00)
        cpu.reg_write(UC_ARM_REG_LR, STOP)
        cpu.hook_add(UC_HOOK_CODE, hook)
        cpu.hook_add(UC_HOOK_MEM_WRITE, write)
        cpu.emu_start(START, STOP, count=1000)
        assert cpu.reg_read(UC_ARM_REG_PC) == STOP
        assert len(trace) == 1 and not outside_stack
        rows.append({"mode": mode, "native_getter_calls": trace,
                     "return": cpu.reg_read(UC_ARM_REG_R0), "nonstack_writes": outside_stack})
    return {"elf_sha256": ELF_SHA, "address": START, "size": SIZE, "section": 12,
            "file_offset": offset, "range_sha256": RANGE_SHA, "cases": rows}


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
