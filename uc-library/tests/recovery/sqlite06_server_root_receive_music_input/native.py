"""Execute each exact ARM callback range and record memory and control flow."""
import argparse
import hashlib
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn import UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, __version__
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0
from unicorn.arm_const import UC_ARM_REG_R1, UC_ARM_REG_SP

RECEIVER = 0x71000000
PAYLOAD = 0x72000000
STACK = 0x73000000
RETURN = 0x74000000
SEEDS = (0, 17, 255)


def observe(original, instructions, seed, has_event):
    address = original["address"]
    cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    for addr in (address & ~0xfff, RECEIVER, PAYLOAD, STACK, RETURN):
        cpu.mem_map(addr, 0x1000)
    cpu.mem_write(address, instructions)
    receiver = bytes((seed + i) % 256 for i in range(128))
    payload = bytes((seed ^ i) for i in range(128))
    cpu.mem_write(RECEIVER, receiver)
    if has_event:
        cpu.mem_write(PAYLOAD, payload)
    initial_sp = STACK + 0x800
    cpu.reg_write(UC_ARM_REG_R0, RECEIVER)
    cpu.reg_write(UC_ARM_REG_R1, PAYLOAD if has_event else 0x90000000)
    cpu.reg_write(UC_ARM_REG_SP, initial_sp)
    cpu.reg_write(UC_ARM_REG_LR, RETURN)
    trace = []
    access = []
    cpu.hook_add(UC_HOOK_CODE, lambda _, pc, size, data: trace.append(pc))
    cpu.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE,
                 lambda _, kind, location, size, value, data:
                 access.append([kind, location, size]))
    cpu.emu_start(address, RETURN, count=32)
    terminal_pc = cpu.reg_read(UC_ARM_REG_PC)
    terminal_sp = cpu.reg_read(UC_ARM_REG_SP)
    assert terminal_pc == RETURN and terminal_sp == initial_sp
    assert trace == list(range(address, address + len(instructions), 4))
    assert access and all(STACK <= location and location + size <= initial_sp
                          for _, location, size in access)
    assert cpu.mem_read(RECEIVER, len(receiver)) == receiver
    if has_event:
        assert cpu.mem_read(PAYLOAD, len(payload)) == payload
    return dict(seed=seed, trace=trace, memory_access=access, calls=[],
                terminal_pc=terminal_pc, terminal_sp=terminal_sp, returned=True,
                receiver_unchanged=True, payload_unchanged=True if has_event else None)


def run(original):
    image = Path(original["elf_path"])
    with image.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == original["elf"]
    with image.open("rb") as stream:
        elf = ELFFile(stream)
        section = elf.get_section(original["section"])
        assert section.name == original["section_name"] == ".text"
        start = original["address"] - section["sh_addr"]
        assert original["file_offset"] == section["sh_offset"] + start
        symbols = elf.get_section_by_name(".symtab").get_symbol_by_name(original["mangled"])
        assert any(s["st_value"] == original["address"] and s["st_size"] == original["size"]
                   and s["st_shndx"] == original["section"] for s in symbols)
        instructions = section.data()[start:start + original["size"]]
    assert instructions.hex() == original["range_hex"]
    assert hashlib.sha256(instructions).hexdigest() == original["range_sha256"]
    has_event = "receiveEvent" in original["mangled"]
    return dict(original=original, cases=[observe(original, instructions, seed, has_event)
                                          for seed in SEEDS])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("context", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    rows = json.loads(args.context.read_text())["originals"]
    result = dict(unicorn=__version__, executions=[run(row["original"]) for row in rows])
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
