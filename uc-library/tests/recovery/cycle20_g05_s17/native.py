"""Replay original ARM instructions from two hash-identified firmware files."""
import argparse
import hashlib
import io
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc, UcError
from unicorn.arm_const import (UC_ARM_REG_FP, UC_ARM_REG_LR, UC_ARM_REG_PC,
                               UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
                               UC_ARM_REG_R3, UC_ARM_REG_SP)

PAGE = 4096


def digest(data):
    return hashlib.sha256(data).hexdigest()


def execute(origin, code, inputs):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    receiver, arg, stack, stop = 0x500000, 0x510000, 0x520000, 0x530000
    initial_sp = stack + PAGE // 2
    start = origin["address"]
    effect = origin["boundaries"]
    code_pages = {start & -PAGE, (start + len(code) - 1) & -PAGE,
                  *(int(target) & -PAGE for target in effect)}
    for addr in [*code_pages, receiver, arg, stack, stop]:
        uc.mem_map(addr, PAGE)
    uc.mem_write(start, code)
    uc.mem_write(receiver, b"\x63" * PAGE)
    uc.mem_write(arg, b"\x52" * PAGE)
    uc.mem_write(initial_sp, bytes(range(16)))
    for reg, value in ((UC_ARM_REG_SP, initial_sp), (UC_ARM_REG_FP, stack + 3000),
                       (UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, arg),
                       (UC_ARM_REG_R2, inputs[0]), (UC_ARM_REG_R3, inputs[1]),
                       (UC_ARM_REG_LR, stop)):
        uc.reg_write(reg, value)
    calls, writes = [], []

    def at_code(machine, address, size, data):
        kind = effect.get(str(address))
        if not kind:
            if not start <= address < start + len(code):
                raise AssertionError(f"Unexpected external target {address:#x}")
            return
        assert machine.reg_read(UC_ARM_REG_R0) == receiver
        calls.append(kind)
        if kind == "delete":
            machine.mem_unmap(receiver, PAGE)
        machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

    def on_write(machine, access, address, size, value, data):
        outside_stack = not stack <= address < address + size <= stack + PAGE
        if outside_stack:
            writes.append([address - receiver, size, value])

    uc.hook_add(UC_HOOK_CODE, at_code)
    uc.hook_add(UC_HOOK_MEM_WRITE, on_write)
    uc.emu_start(start, stop, count=80)
    assert uc.reg_read(UC_ARM_REG_PC) == stop
    assert uc.reg_read(UC_ARM_REG_SP) == initial_sp
    assert uc.reg_read(UC_ARM_REG_FP) == stack + 3000
    disposed = False
    try:
        updated = uc.mem_read(receiver, PAGE)
    except UcError:
        disposed = True
        updated = None
    assert uc.mem_read(arg, PAGE) == b"\x52" * PAGE
    if effect:
        assert calls == list(effect.values()) and disposed
        assert len(writes) == 1 and writes[0][:2] == [0, 4]
    else:
        assert not calls
        assert len(writes) == 1 and writes[0][:2] == [0, 4]
        assert updated[4:] == b"\x63" * (PAGE - 4)
        assert updated[:4] == writes[0][2].to_bytes(4, "little")
    return {"inputs": list(inputs), "calls": calls, "object_writes": writes,
            "receiver_disposed": disposed}


def observe(origin, path):
    raw = path.read_bytes()
    assert digest(raw) == origin["elf_sha256"]
    elf = ELFFile(io.BytesIO(raw))
    sym, = elf.get_section_by_name(".symtab").get_symbol_by_name(origin["mangled"])
    section = elf.get_section(sym["st_shndx"])
    va, size = sym["st_value"], sym["st_size"]
    offset = section["sh_offset"] + va - section["sh_addr"]
    assert (va, size, offset, section.name, sym["st_shndx"]) == (
        origin["address"], origin["size"], origin["file_offset"], origin["section"],
        origin["section_index"])
    if origin["boundaries"]:
        relocations = elf.get_section_by_name(".rel.plt")
        imported = elf.get_section(relocations["sh_link"])
        delete_index, = (idx for idx, relation in enumerate(relocations.iter_relocations())
                         if imported.get_symbol(relation["r_info_sym"]).name == "_ZdlPv")
        plt = elf.get_section_by_name(".plt")
        delete_entry = plt["sh_addr"] + 20 + 12 * delete_index
        assert origin["boundaries"][str(delete_entry)] == "delete"
        if "ControlD2" in origin["boundaries"].values():
            base, = elf.get_section_by_name(".symtab").get_symbol_by_name(
                "_ZN8Presonus5Panel7ControlD2Ev")
            assert origin["boundaries"][str(base["st_value"])] == "ControlD2"
    if origin["mangled"].endswith("D1Ev"):
        assert not elf.get_section_by_name(".symtab").get_symbol_by_name(
            origin["mangled"].replace("D1Ev", "D2Ev"))
    code = raw[offset:offset + size]
    assert digest(code) == origin["range_sha256"]
    cases = ((0, 0), (0xffffffff, 0x80000000), (1, 17))
    return [execute(origin, code, pair) for pair in cases]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--elf-client", required=True, type=Path)
    parser.add_argument("--elf-server", required=True, type=Path)
    parser.add_argument("--generate", action="store_true")
    args = parser.parse_args()
    fixture = json.loads(args.fixture.read_bytes())
    for origin in [*fixture["originals"], *fixture["uncredited_D1"]]:
        cases = observe(origin, getattr(args, "elf_" + origin["role"]))
        if args.generate:
            origin["observations"] = cases
        elif cases != origin["observations"]:
            raise SystemExit("Native replay diverged from sealed fixture")
    if args.generate:
        args.fixture.write_text(json.dumps(fixture, indent=2) + "\n")
    print(f"Replayed {sum(len(o['observations']) for o in fixture['originals'])} exact ARM D0 cases "
          f"and {sum(len(o['observations']) for o in fixture['uncredited_D1'])} companion D1 cases")


if __name__ == "__main__":
    main()
