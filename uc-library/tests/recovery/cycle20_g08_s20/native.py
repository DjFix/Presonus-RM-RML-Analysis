"""Observe both exact ARM AlertBook constructor entry points offline."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
                               UC_ARM_REG_R3, UC_ARM_REG_LR, UC_ARM_REG_SP,
                               UC_ARM_REG_PC)

ELF_SHA = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
CONSTRUCTORS = (
    ("_ZN8Presonus5Panel9AlertBookC1Ei", 448688, "ba62f9cf4ca6d6486d645a62434cfdb056d250aab73711f6c924a119d3c6ce10"),
    ("_ZN8Presonus5Panel9AlertBookC2Ei", 448856, "d6a8314e242d4386bfe1eef00b80e0690c54e1becf39ad4c51c77fc0c2ef36c1"),
)
BOUNDARIES = (
    (24, 621564, "book_ctor"),
    (36, 1154700, "component_ctor"),
    (108, 1174612, "add_parameters"),
    (128, 621684, "book_cleanup"),
    (136, 44240, "runtime_cleanup"),
    (148, 1156412, "component_cleanup"),
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def observe(path):
    raw = path.read_bytes()
    assert sha(raw) == ELF_SHA
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        symbols = elf.get_section_by_name(".symtab")

        def read_memory(address, length):
            section, = (s for s in elf.iter_sections()
                        if s["sh_flags"] & 2 and s["sh_type"] != "SHT_NOBITS"
                        and s["sh_addr"] <= address
                        and address + length <= s["sh_addr"] + s["sh_size"])
            offset = section["sh_offset"] + address - section["sh_addr"]
            return offset, raw[offset:offset + length]

        def cstring(address):
            return read_memory(address, 24)[1].split(b"\0", 1)[0].decode()

        originals = []
        for symbol, address, expected in CONSTRUCTORS:
            row, = symbols.get_symbol_by_name(symbol)
            assert (row["st_value"], row["st_size"], row["st_shndx"]) == (address, 168, 12)
            file_offset, code = read_memory(address, 168)
            assert sha(code) == expected
            for offset, callee, _ in BOUNDARIES:
                ins, = struct.unpack_from("<I", code, offset)
                assert ins >> 24 == 0xEB
                delta = (ins & 0xFFFFFF) << 2
                if delta & (1 << 25):
                    delta -= 1 << 26
                assert address + offset + 8 + delta == callee
            name, vtable, table = struct.unpack_from("<III", code, 156)
            table_offset, rows = read_memory(table, 252)
            assert sha(rows) == "b9dd12d1d767a8fd772f48bd7f3d9efed316e48227b708d3ec794e127452eb73"
            roster = []
            for at in range(0, len(rows), 84):
                kind, tag, param, *fields = struct.unpack_from("<II32s5f6I", rows, at)
                assert fields[:-2] == [0] * 9 and fields[-1] == 0
                roster.append(dict(kind=kind, tag=tag, name=param.split(b"\0", 1)[0].decode(),
                                   title=cstring(fields[-2])))
            results = []
            for value in (0, 41, -1):
                receiver, stack, end = 0x24000000, 0x28000000, 0x29000000
                cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
                for page in {a & ~4095 for a in (receiver, stack, end, address, address + 167,
                                                 name, table, *(p for _, p, _ in BOUNDARIES))}:
                    cpu.mem_map(page, 4096)
                cpu.mem_write(address, code)
                cpu.mem_write(table, rows)
                cpu.mem_write(receiver, b"\xa6" * 0x130)
                marks = {p: label for _, p, label in BOUNDARIES}
                events = []

                def hook(uc, current, size, context):
                    if current not in marks:
                        return
                    label = marks[current]
                    events.append(label)
                    registers = [uc.reg_read(r) for r in (UC_ARM_REG_R0, UC_ARM_REG_R1,
                                                           UC_ARM_REG_R2, UC_ARM_REG_R3)]
                    if label == "book_ctor":
                        assert registers[:2] == [receiver, value & 0xFFFFFFFF]
                    elif label == "component_ctor":
                        assert registers[:2] == [receiver + 0x98, name]
                    else:
                        assert label == "add_parameters"
                        assert registers == [receiver + 0xc0, table, len(roster), 0]
                    uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

                cpu.hook_add(UC_HOOK_CODE, hook)
                for reg, argument in ((UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, value & 0xffffffff),
                                       (UC_ARM_REG_SP, stack + 2048), (UC_ARM_REG_LR, end)):
                    cpu.reg_write(reg, argument)
                cpu.emu_start(address, end, count=120)
                assert cpu.reg_read(UC_ARM_REG_PC) == end
                assert cpu.reg_read(UC_ARM_REG_SP) == stack + 2048
                assert cpu.reg_read(UC_ARM_REG_R0) == receiver
                assert events == ["book_ctor", "component_ctor", "add_parameters"]
                assert [struct.unpack("<I", cpu.mem_read(receiver + off, 4))[0] for off in
                        (0, 0x98, 0x9c)] == [vtable, vtable + 0x50, vtable + 0x84]
                assert cpu.mem_read(receiver + 0x11c, 20) == bytes(20)
                results.append(dict(initial_value=value, events=events, state_zero=True,
                                    component=cstring(name), roster=roster))
            originals.append(dict(elf_sha256=ELF_SHA, firmware="RM/RML mixer 13731",
                                  role="server", mangled=symbol, address=address, size=168,
                                  section=12, file_offset=file_offset, range_sha256=expected,
                                  table_offset=table_offset, table_sha256=sha(rows), cases=results))
    return {"elf_sha256": ELF_SHA, "originals": originals}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", required=True, type=Path)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--out", type=Path)
    action.add_argument("--check", type=Path)
    args = parser.parse_args()
    observed = observe(args.elf)
    if args.check is not None:
        assert json.loads(args.check.read_text()) == observed
    else:
        with args.out.open("x") as stream:
            stream.write(json.dumps(observed, indent=2) + "\n")
    print("Both original ranges and six native constructor observations verified")
