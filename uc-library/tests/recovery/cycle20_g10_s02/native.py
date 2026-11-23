"""Replay one sealed base entry against the two original ELF roles offline."""
import argparse
import hashlib
import json
from pathlib import Path

from elftools import __version__ as elftools_version
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R11, UC_ARM_REG_SP


def observe(code, entry, receiver_mapped):
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    stack, stop, receiver = 0x60000000, 0x70000000, 0x50000000
    text_page = entry & ~4095
    text_size = 8192 if entry + len(code) > text_page + 4096 else 4096
    machine.mem_map(text_page, text_size)
    for page in (stack, stop):
        machine.mem_map(page, 4096)
    image = bytes(range(256))
    if receiver_mapped:
        machine.mem_map(receiver, 4096)
        machine.mem_write(receiver, image)
    machine.mem_write(entry, code)
    sp, fp = stack + 0xff0, stack + 0x250
    for register, value in ((UC_ARM_REG_SP, sp), (UC_ARM_REG_R11, fp),
                            (UC_ARM_REG_LR, stop), (UC_ARM_REG_R0, receiver)):
        machine.reg_write(register, value)
    instructions, memory = [], []
    machine.hook_add(UC_HOOK_CODE, lambda _, addr, size, __: instructions.append([addr, size]))
    machine.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE,
                     lambda _, kind, addr, size, value, __: memory.append([kind, addr, size, value]))
    machine.emu_start(entry, stop, count=16)
    assert instructions == [[entry + byte, 4] for byte in range(0, len(code), 4)]
    assert memory and all(sp - 16 <= address and address + size <= sp
                          for _, address, size, _ in memory)
    assert machine.reg_read(UC_ARM_REG_PC) == stop
    assert machine.reg_read(UC_ARM_REG_SP) == sp and machine.reg_read(UC_ARM_REG_R11) == fp
    if receiver_mapped:
        assert bytes(machine.mem_read(receiver, len(image))) == image
    return {"receiver_mapped": receiver_mapped, "instructions": instructions,
            "stack_accesses": memory, "restored_sp": sp, "restored_fp": fp, "stop_pc": stop}


def replay(inputs, paths):
    observations = []
    assert len(inputs) == len(paths) == 2
    for row, path in zip(inputs, paths):
        with path.open("rb") as stream:
            assert hashlib.file_digest(stream, "sha256").hexdigest() == row["elf_sha256"]
            stream.seek(0)
            elf = ELFFile(stream)
            assert elf.little_endian and elf.elfclass == 32 and elf["e_machine"] == "EM_ARM"
            symbol, = elf.get_section_by_name(".symtab").get_symbol_by_name(row["mangled"])
            assert symbol["st_info"]["type"] == "STT_FUNC"
            assert symbol["st_value"] == row["address"] and symbol["st_size"] == row["size"]
            assert symbol["st_shndx"] == row["section"]
            section = elf.get_section(symbol["st_shndx"])
            assert section.name == ".text"
            delta = row["address"] - section["sh_addr"]
            assert 0 <= delta <= section["sh_size"] - row["size"]
            offset = section["sh_offset"] + delta
            assert offset == row["file_offset"]
            stream.seek(offset)
            code = stream.read(row["size"])
            assert hashlib.sha256(code).hexdigest() == row["range_sha256"]
        observations.append([observe(code, row["address"], mapped) for mapped in (False, True)])
    return observations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--elf", type=Path, action="append", required=True)
    parser.add_argument("--capture", action="store_true")
    args = parser.parse_args()
    payload = json.loads(args.fixtures.read_text())
    observations = replay(payload["originals"], args.elf)
    if args.capture:
        payload.update(native_observations=observations,
                       oracle_versions={"unicorn": unicorn.__version__, "pyelftools": elftools_version})
        args.fixtures.write_text(json.dumps(payload, indent=2) + "\n")
    else:
        assert observations == payload["native_observations"]
    print("4 native calls matched across CS18 and RM")


if __name__ == "__main__":
    main()
