"""Replay the original ARM entry through its branch to the rendering path."""

import hashlib
from itertools import product
from pathlib import Path
from struct import pack

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM, Uc
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP,
)

ROOT = Path(__file__).absolute().parents[4]
ELF = ROOT / "rootfs/CS18_v13840/home/root/surface"
MANGLED = "_ZN8Presonus10PanControl4drawERKN4Core8Portable9DrawEventE"
ELF_SHA = "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0"
RANGE_SHA = "520749c1346b13d28931c3414175107d19817a3575fe1ffa220d2f55ae440243"
ENTRY, END, RENDER_ENTRY = 0x68FB8, 0x69240, 0x69008
MEMORY, PARAMETER, VTABLE = 0x400000, 0x401000, 0x402000
CALLBACK, RETURN, STACK = 0x403000, 0x403004, 0x408000


def original():
    assert hashlib.sha256(ELF.read_bytes()).hexdigest() == ELF_SHA
    with ELF.open("rb") as stream:
        elf = ELFFile(stream)
        symbol, = elf.get_section_by_name(".symtab").get_symbol_by_name(MANGLED)
        assert (symbol["st_value"], symbol["st_size"], symbol["st_shndx"]) == (
            ENTRY, END - ENTRY, 12,
        )
        section = elf.get_section(12)
        relative = ENTRY - section["sh_addr"]
        assert section["sh_offset"] + relative == 397240
        body = section.data()[relative:relative + END - ENTRY]
    assert hashlib.sha256(body).hexdigest() == RANGE_SHA
    return body


def execute(body, vertical, view_disabled, parameter_enabled):
    arm = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    arm.mem_map(ENTRY & ~0xFFF, 0x2000)
    arm.mem_write(ENTRY, body)
    arm.mem_map(MEMORY, 0x10000)
    arm.mem_write(MEMORY + 0x40, pack("<I", vertical << 16 | view_disabled))
    arm.mem_write(MEMORY + 0x48, pack("<I", PARAMETER))
    arm.mem_write(PARAMETER, pack("<I", VTABLE))
    arm.mem_write(VTABLE + 0x20, pack("<I", CALLBACK))
    arm.reg_write(UC_ARM_REG_R0, MEMORY)
    arm.reg_write(UC_ARM_REG_SP, STACK)
    arm.reg_write(UC_ARM_REG_LR, RETURN)
    trace = []
    calls = 0

    def observe(cpu, address, size, _):
        nonlocal calls
        trace.append(hex(address))
        if address == RENDER_ENTRY:
            cpu.emu_stop()
        elif address == CALLBACK:
            assert cpu.reg_read(UC_ARM_REG_R0) == PARAMETER
            calls += 1
            cpu.reg_write(UC_ARM_REG_R0, parameter_enabled)
            cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))
        elif not (ENTRY <= address < RENDER_ENTRY and size == 4):
            raise RuntimeError(f"Unexpected ARM address {address:#x}")

    arm.hook_add(UC_HOOK_CODE, observe)
    arm.emu_start(ENTRY, RETURN, count=40)
    terminal = arm.reg_read(UC_ARM_REG_PC)
    assert terminal in (RETURN, RENDER_ENTRY) and calls == 1
    gate = "reached_render_path" if terminal == RENDER_ENTRY else "returned_before_render"
    return gate, trace


def run():
    body = original()
    cases, traces = [], []
    for vertical, disabled, enabled in product((0, 1), repeat=3):
        gate, trace = execute(body, vertical, disabled, enabled)
        cases.append(dict(vertical_bit=vertical, view_disabled_bit=disabled,
                          parameter_enabled=enabled, gate=gate))
        traces.append(trace)
    return cases, traces
