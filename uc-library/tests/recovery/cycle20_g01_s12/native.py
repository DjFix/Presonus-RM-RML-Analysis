"""Independently replay the separately section-mapped CS18 C1 and C2 entries."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC


STACK, RECEIVER, RETURN = 0x2000000, 0x3000000, 0x4000000
NAMES = [f"_ZN8Presonus22AssignmentHandlerTableC{variant}Ev" for variant in (1, 2)]


def capture(elf_path, reference_path):
    reference = json.loads(reference_path.read_text())
    expected = {row["original_mangled"]: row for row in reference["checks"].values()}
    with elf_path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
        stream.seek(0)
        elf = ELFFile(stream)
        symbols = elf.get_section_by_name(".symtab")
        cases_by_symbol = []
        for name in NAMES:
            record = expected[name]
            assert record["elf_sha256"] == digest
            matches = symbols.get_symbol_by_name(name)
            assert len(matches) == 1
            symbol = matches[0]
            start, size, section_index = (symbol[key] for key in
                                           ("st_value", "st_size", "st_shndx"))
            section = elf.get_section(section_index)
            relative = start - section["sh_addr"]
            assert section.name == ".text" and 0 <= relative <= section["sh_size"] - size
            offset = section["sh_offset"] + relative
            stream.seek(offset)
            body = stream.read(size)
            assert (start, size, offset, hashlib.sha256(body).hexdigest()) == (
                record["address"], record["size"], record["file_offset"], record["range_sha256"]
            )

            cases = []
            for receiver in (RECEIVER + 0x100, RECEIVER + 0x200):
                for seed in (1, 99, 255):
                    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
                    code = start & ~4095
                    for area in (code, STACK, RECEIVER, RETURN):
                        uc.mem_map(area, 4096)
                    uc.mem_write(start, body)
                    uc.mem_write(receiver - 16, bytes([seed]) * 80)
                    uc.reg_write(UC_ARM_REG_R0, receiver)
                    uc.reg_write(UC_ARM_REG_SP, STACK + 0x800)
                    uc.reg_write(UC_ARM_REG_LR, RETURN)
                    writes = []

                    def validate_pc(machine, pc, length, _):
                        assert start <= pc < start + size

                    def capture_write(machine, access, addr, length, value, _):
                        if STACK <= addr < STACK + 4096:
                            return
                        writes.append([addr - receiver, length, value])

                    uc.hook_add(UC_HOOK_CODE, validate_pc)
                    uc.hook_add(UC_HOOK_MEM_WRITE, capture_write)
                    uc.emu_start(start, RETURN, count=60)
                    assert uc.reg_read(UC_ARM_REG_PC) == RETURN
                    assert uc.reg_read(UC_ARM_REG_R0) == receiver
                    assert writes == [[0, 4, receiver + 8], [4, 4, 0]]
                    assert bytes(uc.mem_read(receiver - 16, 80)) == (
                        bytes([seed]) * 16 + struct.pack("<II", receiver + 8, 0) +
                        bytes([seed]) * 56
                    )
                    cases.append(dict(receiver=receiver, seed=seed, writes=writes,
                                      count=0, inline_offset=8, r0_preserved=True))
            cases_by_symbol.append(dict(mangled=name, address=start, size=size,
                                        section=section.name, section_index=section_index,
                                        file_offset=offset, range_sha256=record["range_sha256"],
                                        cases=cases))
    assert len({row["address"] for row in cases_by_symbol}) == 2
    return dict(elf_sha256=digest, reference_sha256=hashlib.sha256(reference_path.read_bytes()).hexdigest(),
                originals=cases_by_symbol)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("elf", type=Path)
    parser.add_argument("reference", type=Path)
    args = parser.parse_args()
    print(json.dumps(capture(args.elf, args.reference), indent=2))
