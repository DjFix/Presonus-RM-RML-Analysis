"""Run hash-bound MetaElement::isClass and observe its exact strcmp boundary."""
import ctypes
from hashlib import sha256
from itertools import product
import json
from pathlib import Path
import struct
import sys

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0,
                               UC_ARM_REG_R1, UC_ARM_REG_SP)

PAGE = 0x1000
OBJ = 0x1000000
LHS = OBJ + 0x100
RHS = OBJ + 0x200
STACK = OBJ + PAGE
STOP = STACK + PAGE
LIBC = ctypes.CDLL(None)
LIBC.strcmp.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
LIBC.strcmp.restype = ctypes.c_int


def observe(root, original, typed):
    path = root / original["elf_path"]
    raw = path.read_bytes()
    assert sha256(raw).hexdigest() == original["elf"] == typed["elf"]
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        table = elf.get_section_by_name(".symtab")
        symbol, = table.get_symbol_by_name(original["mangled"])
        section = elf.get_section(symbol["st_shndx"])
        start, size = symbol["st_value"], symbol["st_size"]
        offset = section["sh_offset"] + start - section["sh_addr"]
        content = raw[offset:offset + size]
        target = {"mangled": symbol.name, "address": start, "size": size,
                  "section": symbol["st_shndx"], "section_name": section.name,
                  "file_offset": offset, "range_sha256": sha256(content).hexdigest(),
                  "range_hex": content.hex()}
        assert all(original[key] == val for key, val in target.items())
        factory, = table.get_symbol_by_name(typed["factory"]["mangled"])
        assert factory["st_value"] == typed["factory"]["address"]
        rel = elf.get_section_by_name(".rel.plt")
        dyn = elf.get_section(rel["sh_link"])
        plt = elf.get_section_by_name(".plt")
        strcmp, = [plt["sh_addr"] + 20 + 12 * i for i, row in enumerate(rel.iter_relocations())
                   if dyn.get_symbol(row["r_info_sym"]).name == "strcmp"]
        image = [(seg["p_vaddr"], seg.data(), seg["p_memsz"])
                 for seg in elf.iter_segments() if seg["p_type"] == "PT_LOAD"]
    cases = []
    for lhs, rhs in product([None, "", "Channel", "channel", "Other"], repeat=2):
        uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        uc.mem_map(0, (max(a + n for a, _, n in image) + PAGE - 1) & -PAGE)
        for addr, data, _ in image:
            uc.mem_write(addr, data)
        uc.mem_map(OBJ, 3 * PAGE)
        fields = struct.pack("<II", LHS if lhs is not None else 0, factory["st_value"])
        uc.mem_write(OBJ, fields)
        for value, addr in ((lhs, LHS), (rhs, RHS)):
            if value is not None:
                uc.mem_write(addr, value.encode() + b"\0")
        uc.reg_write(UC_ARM_REG_R0, OBJ)
        uc.reg_write(UC_ARM_REG_R1, RHS if rhs is not None else 0)
        uc.reg_write(UC_ARM_REG_SP, STACK + PAGE - 16)
        uc.reg_write(UC_ARM_REG_LR, STOP)
        calls, pcs = [], []

        def code(machine, pc, size, _):
            if pc != strcmp:
                assert start <= pc < start + target["size"]
                pcs.append(pc)
                return
            x = machine.reg_read(UC_ARM_REG_R0)
            y = machine.reg_read(UC_ARM_REG_R1)
            for pointer, given, location in ((x, lhs, LHS), (y, rhs, RHS)):
                value = bytes(machine.mem_read(pointer, 32)).split(b"\0")[0].decode()
                assert value == (given or "")
                if given is not None:
                    assert pointer == location
            calls.append([x, y])
            machine.reg_write(UC_ARM_REG_R0, LIBC.strcmp((lhs or "").encode(),
                                                       (rhs or "").encode()) & 0xffffffff)
            machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

        def write(_, _kind, address, n, _value, _aux):
            assert STACK <= address and address + n <= STACK + PAGE

        uc.hook_add(UC_HOOK_CODE, code)
        uc.hook_add(UC_HOOK_MEM_WRITE, write)
        uc.emu_start(start, STOP, count=100)
        assert uc.reg_read(UC_ARM_REG_PC) == STOP
        assert bytes(uc.mem_read(OBJ, len(fields))) == fields and len(calls) == 1
        output = uc.reg_read(UC_ARM_REG_R0)
        assert output in (0, 1)
        cases.append({"inputs": [lhs, rhs], "output": output, "strcmp_args": calls[0],
                      "executed_pcs": pcs, "unchanged_metadata": True})
    return {"elf_sha256": original["elf"], "firmware": original["firmware"],
            "role": original["role"], "target": target, "strcmp_plt": strcmp, "cases": cases}


def main():
    context, root, evidence = map(Path, sys.argv[1:])
    data = evidence.read_bytes()
    assert sha256(data).hexdigest() == "4daf2b73c757f235f657913be40bc79a37f518c881c6e215d7b1a41600b3e711"
    binding = {item["elf"]: item for item in json.loads(data)["observations"]}
    print(json.dumps([observe(root, row["original"], binding[row["original"]["elf"]])
                      for row in json.loads(context.read_text())["originals"]], indent=2))


if __name__ == "__main__":
    main()
