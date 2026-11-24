"""Run only the sealed ARM leaf in isolation, with no device or firmware startup."""
import argparse
import hashlib
import importlib.metadata
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn import UC_MODE_ARM, UC_PROT_EXEC, UC_PROT_READ, UC_PROT_WRITE
from unicorn.arm_const import UC_ARM_REG_FP, UC_ARM_REG_LR, UC_ARM_REG_PC
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_SP

ELF_HASH = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
RANGE_HASH = "a572376e0ee06bc343b7da8c80c3ad7485494648223905bde63169a725321b0a"
SYMBOL = "_ZN8Presonus5Panel23WolverinePanelRegistrar16getPanelPortNameEv"


def observe(path):
    whole = path.read_bytes()
    assert hashlib.sha256(whole).hexdigest() == ELF_HASH
    with path.open("rb") as inp:
        elf = ELFFile(inp)
        assert elf.little_endian and elf.elfclass == 32 and elf["e_machine"] == "EM_ARM"
        symbol = next(s for s in elf.get_section_by_name(".symtab").iter_symbols()
                      if s.name == SYMBOL)
        address, size, section_index = (symbol[key] for key in ("st_value", "st_size", "st_shndx"))
        assert (address, size, section_index) == (0x7B138, 24, 12)
        section = elf.get_section(section_index)
        offset = section["sh_offset"] + address - section["sh_addr"]
        assert section.name == ".text" and section["sh_addr"] <= address
        assert address + size <= section["sh_addr"] + section["sh_size"]
        body = whole[offset:offset + size]
        assert hashlib.sha256(body).hexdigest() == RANGE_HASH
        literal_word, = struct.unpack_from("<I", body, 20)
        literal_section = next(s for s in elf.iter_sections() if s["sh_flags"] & 2
                               and s["sh_addr"] <= literal_word < s["sh_addr"] + s["sh_size"])
        assert literal_section["sh_type"] != "SHT_NOBITS" and not literal_section["sh_flags"] & 1
        assert any(p["p_type"] == "PT_LOAD" and not p["p_flags"] & 2 and
                   p["p_vaddr"] <= literal_word < p["p_vaddr"] + p["p_filesz"]
                   for p in elf.iter_segments())
        literal_offset = literal_section["sh_offset"] + literal_word - literal_section["sh_addr"]
        end = whole.index(0, literal_offset, literal_section["sh_offset"] + literal_section["sh_size"])
        literal = whole[literal_offset:end + 1]
        literal_section_name = literal_section.name

    cases = []
    stop = address + size
    sp = 0x10000800
    fp = 0x11223344
    for receiver, marker in ((0x20000100, 0xA5), (0x20000200, 0x5A), (0x20000100, 0xA5)):
        arm = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        arm.mem_map(address & ~4095, 4096, UC_PROT_READ | UC_PROT_EXEC)
        arm.mem_write(address, body)
        arm.mem_map(literal_word & ~4095, 4096, UC_PROT_READ)
        arm.mem_write(literal_word, literal)
        arm.mem_map(sp & ~4095, 4096, UC_PROT_READ | UC_PROT_WRITE)
        arm.mem_map(receiver & ~4095, 4096, UC_PROT_READ | UC_PROT_WRITE)
        state = bytes([marker]) * 64
        arm.mem_write(receiver, state)
        arm.reg_write(UC_ARM_REG_R0, receiver)
        arm.reg_write(UC_ARM_REG_SP, sp)
        arm.reg_write(UC_ARM_REG_FP, fp)
        arm.reg_write(UC_ARM_REG_LR, stop)
        instructions, writes, reads = [], [], []
        arm.hook_add(UC_HOOK_CODE, lambda _arm, pc, _size, _user: instructions.append(pc))
        arm.hook_add(UC_HOOK_MEM_WRITE,
                     lambda _arm, _access, at, width, _value, _user: writes.append([at, width]))
        arm.hook_add(UC_HOOK_MEM_READ,
                     lambda _arm, _access, at, width, _value, _user: reads.append([at, width]))
        arm.emu_start(address, stop, count=6)
        r0 = arm.reg_read(UC_ARM_REG_R0)
        assert r0 == literal_word and arm.reg_read(UC_ARM_REG_PC) == stop
        assert arm.reg_read(UC_ARM_REG_SP) == sp and arm.reg_read(UC_ARM_REG_FP) == fp
        assert instructions == [address + i * 4 for i in range(5)]
        assert writes and all(sp - 16 <= at < at + width <= sp for at, width in writes)
        assert all((sp - 16 <= at < at + width <= sp) or (at, width) == (address + 20, 4)
                   for at, width in reads)
        assert arm.mem_read(receiver, len(state)) == state
        cases.append(dict(receiver=receiver, marker=marker, returned_word=r0,
                          receiver_preserved=True, stack_restored=True,
                          instructions=instructions, reads=reads, writes=writes))
    return dict(elf_sha256=ELF_HASH, mangled=SYMBOL, address=address, size=size,
                section_index=section_index, section=".text", file_offset=offset,
                range_sha256=RANGE_HASH, encoded_bytes=body.hex(),
                literal=dict(address=literal_word, file_offset=literal_offset,
                             section=literal_section_name, bytes=literal.hex(),
                             text=literal[:-1].decode("ascii"), read_only=True),
                cases=cases, tool_versions={pkg: importlib.metadata.version(pkg)
                                            for pkg in ("pyelftools", "unicorn")})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", type=Path)
    group.add_argument("--verify", type=Path)
    args = parser.parse_args()
    observed = observe(args.elf)
    if args.write:
        with args.write.open("x") as out:
            json.dump(observed, out, indent=2)
            out.write("\n")
    else:
        assert observed == json.loads(args.verify.read_text()), "Native observation drift"
    print(f"Verified {len(observed['cases'])} offline ARM executions and mapped literal")
