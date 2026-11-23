"""Replay exact ARM AlertBook D0 and inspect the independent D1 companion."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UcError, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (UC_ARM_REG_R0, UC_ARM_REG_SP, UC_ARM_REG_LR,
                               UC_ARM_REG_PC)

PREFIX = "_ZN8Presonus5Panel"
ELF = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
VARIANTS = (
    ("D0", 453828, 96, "b57362976e5792e9a852fd4be10a836a8d94a89ef63051f4e6bfd3e3714755e5"),
    ("D1", 453932, 88, "753ac7a6db3caba1c30baadd8287742fe8bbb95e52c10fde8ab56c05bcb093e1"),
)
DELETE = 0xAC10
CCL_COMPONENT_D2 = 0x11A53C


def sha(data):
    return hashlib.sha256(data).hexdigest()


def replay(code, parent, element_vtable, vtables, roster, deletes):
    address, body = code
    base, base_body = parent
    element_table, element_body = element_vtable
    derived_table, base_table = vtables
    child_delete, = struct.unpack_from("<I", element_body, 12)
    receiver, vector, stack, end = [0x41000000 + i * 0x10000 for i in range(4)]
    children = [0x42000000 + i * 4096 for i in range(len(roster))]
    cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    for page in {a & ~4095 for a in (receiver, vector, stack, end, address, base, element_table,
                                     address + len(body) - 1, base + len(base_body) - 1,
                                     element_table + len(element_body) - 1,
                                     child_delete, DELETE, CCL_COMPONENT_D2, *children)}:
        cpu.mem_map(page, 4096)
    for ptr, payload in ((address, body), (base, base_body), (element_table, element_body)):
        cpu.mem_write(ptr, payload)

    def write_word(ptr, value):
        cpu.mem_write(ptr, struct.pack("<I", value))

    def read_word(ptr):
        return struct.unpack("<I", cpu.mem_read(ptr, 4))[0]

    write_word(receiver + 4, vector)
    write_word(receiver + 8, len(roster))
    for i, present in enumerate(roster):
        write_word(vector + i * 4, children[i] if present else 0)
        if present:
            write_word(children[i], element_table + 8)
    observed = []

    def hook(uc, pc, size, context):
        arg = uc.reg_read(UC_ARM_REG_R0)
        if pc == base:
            assert arg == receiver and read_word(receiver) == derived_table + 8
            observed.append("parent_d2")
        elif pc == CCL_COMPONENT_D2:
            assert arg == receiver + 0x98
            assert read_word(receiver) == derived_table + 8
            assert read_word(receiver + 0x98) == derived_table + 8 + 0x50
            assert read_word(receiver + 0x9c) == derived_table + 8 + 0x84
            observed.append("component_d2")
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
        elif pc == child_delete:
            assert arg in children
            observed.append(children.index(arg))
            uc.mem_unmap(arg, 4096)
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
        elif pc == DELETE:
            assert arg == receiver and read_word(receiver) == base_table + 8
            observed.append("receiver_delete")
            uc.mem_unmap(receiver, 4096)
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
        else:
            assert address <= pc < address + len(body) or base <= pc < base + len(base_body)

    for reg, val in ((UC_ARM_REG_R0, receiver), (UC_ARM_REG_SP, stack + 2048), (UC_ARM_REG_LR, end)):
        cpu.reg_write(reg, val)
    cpu.hook_add(UC_HOOK_CODE, hook)
    cpu.emu_start(address, end, count=260)
    assert cpu.reg_read(UC_ARM_REG_PC) == end and cpu.reg_read(UC_ARM_REG_SP) == stack + 2048
    try:
        assert read_word(receiver) == base_table + 8
    except UcError:
        disposed = True
    else:
        disposed = False
    assert disposed == deletes
    for i, present in enumerate(roster):
        if present:
            try:
                read_word(children[i])
            except UcError:
                pass
            else:
                raise AssertionError("child remains mapped")
    expected = ["component_d2", "parent_d2", *(i for i, present in enumerate(roster) if present)]
    assert observed == expected + (["receiver_delete"] if deletes else [])
    return dict(roster=list(roster), trace=observed, receiver_disposed=disposed)


def observe(path):
    assert sha(path.read_bytes()) == ELF
    with path.open("rb") as stream:
        binary = ELFFile(stream)
        symbols = binary.get_section_by_name(".symtab")

        def symbol(name):
            row, = symbols.get_symbol_by_name(name)
            address, length, index = row["st_value"], row["st_size"], row["st_shndx"]
            section = binary.get_section(index)
            offset = address - section["sh_addr"]
            assert 0 <= offset < offset + length <= section["sh_size"]
            return address, section["sh_offset"] + offset, section.data()[offset:offset + length], index

        parent_name = PREFIX + "4BookD2Ev"
        base, base_offset, base_body, _ = symbol(parent_name)
        assert (base, base_offset, len(base_body), sha(base_body)) == (
            621684, 588916, 96, "f57dae7fe8bad5b6f62eaa31510940231478eb4fe4bfde28a5ebace044376514")
        child_delete = symbol(PREFIX + "4PageD0Ev")[0]
        element_address, element_offset, element_table, _ = symbol("_ZTVN8Presonus5Panel4PageE")
        assert struct.unpack_from("<I", element_table, 12)[0] == child_delete == 623552
        derived_table = symbol("_ZTVN8Presonus5Panel9AlertBookE")[0]
        book_table = symbol("_ZTVN8Presonus5Panel4BookE")[0]
        assert symbol("_ZN4Core8Portable9ComponentD2Ev")[0] == CCL_COMPONENT_D2
        assert symbols.get_symbol_by_name(PREFIX + "9AlertBookD2Ev") is None

        def branch_target(address, body, offset):
            ins, = struct.unpack_from("<I", body, offset)
            assert ins >> 24 == 0xeb
            distance = (ins & 0xffffff) << 2
            return address + offset + 8 + distance - (1 << 26 if distance & (1 << 25) else 0)
        result = []
        for variant, expected_address, size, digest in VARIANTS:
            name = PREFIX + "9AlertBook" + variant + "Ev"
            address, offset, body, section = symbol(name)
            assert (address, len(body), sha(body), section) == (expected_address, size, digest, 12)
            assert struct.unpack_from("<I", body, len(body) - 4)[0] == derived_table + 8
            if variant == "D0":
                assert [branch_target(address, body, offset) for offset in (44, 52, 60, 80, 88)] == [
                    CCL_COMPONENT_D2, base, DELETE, base, 0xacd0]
            cases = [replay((address, body), (base, base_body), (element_address, element_table),
                            (derived_table, book_table), roster, variant == "D0")
                     for roster in ((), (False,), (True,), (True, False, True))]
            result.append(dict(elf_sha256=ELF, firmware="RM/RML mixer 13731", role="server",
                               mangled=name, address=address, size=size, section=section,
                               file_offset=offset, range_sha256=digest, cases=cases))
        return dict(originals=result[:1], related_companion=result[1],
                    parent=dict(mangled=parent_name, address=base, file_offset=base_offset,
                                size=len(base_body), range_sha256=sha(base_body)),
                    child_provider=dict(d0=child_delete, table=element_address,
                                        table_file_offset=element_offset, table_sha256=sha(element_table)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", required=True, type=Path)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--out", type=Path)
    action.add_argument("--check", type=Path)
    args = parser.parse_args()
    observations = observe(args.elf)
    if args.check is not None:
        assert json.loads(args.check.read_text()) == observations
    else:
        with args.out.open("x") as stream:
            stream.write(json.dumps(observations, indent=2) + "\n")
    print("Exact D0 and independent D1 observation passed over four rosters each")
