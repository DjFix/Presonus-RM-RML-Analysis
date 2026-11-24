"""Replay hash-checked application ARM ranges with external call observations."""
import argparse
import hashlib
import io
import json
from pathlib import Path
from struct import pack, unpack

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM, Uc
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP,
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def observe(row, source_path, queue):
    raw = source_path.read_bytes()
    assert digest(raw) == row["elf_sha256"]
    elf = ELFFile(io.BytesIO(raw))
    section = elf.get_section(row["section"])
    start = row["address"]
    offset = start - section["sh_addr"]
    size = row["size"]
    assert 0 <= offset <= section["sh_size"] - size
    assert section["sh_offset"] + offset == row["file_offset"]
    symtab = elf.get_section_by_name(".symtab")
    symbol = symtab.get_symbol_by_name(row["mangled"])
    assert any((s["st_value"], s["st_size"], s["st_shndx"]) ==
               (start, size, row["section"]) for s in symbol)
    body = section.data()[offset:offset + size]
    assert digest(body) == row["range_sha256"]
    targets = {entry["address"]: entry["mangled"] for entry in row["providers"]}
    for address, mangled in targets.items():
        assert any(s["st_value"] == address for s in symtab.get_symbol_by_name(mangled))

    obj, item, previous, stack, stop = (
        0x51000000, 0x51000200, 0x51000300, 0x52000f00, 0x53000000,
    )
    cases = []
    for preexisting in (False, True):
        vm = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        for page in {address & ~4095 for address in
                     (start, start + size - 1, *targets, obj, stack, stop)}:
            vm.mem_map(page, 4096)
        vm.mem_write(start, body)
        vm.mem_write(obj, bytes([0xab if preexisting else 0x21]) * 256)

        def write_word(address, value):
            vm.mem_write(address, pack("<I", value))

        def read_word(address):
            return unpack("<I", vm.mem_read(address, 4))[0]

        if queue:
            write_word(obj + 28, previous if preexisting else 0)
            write_word(obj + 32, previous if preexisting else 0)
        before = bytes(vm.mem_read(obj, 256))
        calls = []

        def hook(cpu, address, _size, _data):
            if address in targets:
                assert cpu.reg_read(UC_ARM_REG_R0) == obj
                argument = cpu.reg_read(UC_ARM_REG_R1) if not queue else None
                calls.append([targets[address], argument])
                cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))

        vm.hook_add(UC_HOOK_CODE, hook)
        for register, value in ((UC_ARM_REG_R0, obj),
                                (UC_ARM_REG_R1, item if queue else 0),
                                (UC_ARM_REG_SP, stack), (UC_ARM_REG_LR, stop)):
            vm.reg_write(register, value)
        vm.emu_start(start, stop, count=100)
        assert vm.reg_read(UC_ARM_REG_PC) == stop
        assert vm.reg_read(UC_ARM_REG_SP) == stack
        assert [call[0] for call in calls] == list(targets.values())
        after = bytes(vm.mem_read(obj, 256))
        case = {"preexisting": preexisting, "calls": calls}
        if queue:
            assert after[:28] == before[:28] and after[36:] == before[36:]
            case["links"] = [read_word(address) for address in
                             (obj + 28, obj + 32, previous, item + 8)]
            assert case["links"] == ([previous, item + 4, item + 4, previous]
                                     if preexisting else [item + 4, item + 4, 0, 0])
            names = {previous: 1, item + 4: 2}
            head = read_word(obj + 28)
            order = []
            while head:
                order.append(names.pop(head))
                head = read_word(head)
            case["portable_line"] = [int(preexisting), *order]
        else:
            assert after == before and all(call[1] == 0 for call in calls)
            case["unchanged_object"] = True
        cases.append(case)
    return cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mixer", type=Path, required=True)
    parser.add_argument("--surface", type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--verify", type=Path)
    group.add_argument("--capture", type=Path)
    args = parser.parse_args()
    path = args.verify or args.capture
    fixture = json.loads(path.read_text())
    sources = {"server": args.mixer, "client": args.surface}
    for row in fixture["originals"]:
        cases = observe(row, sources[row["role"]], fixture["queue"])
        if args.verify:
            assert cases == row["cases"]
        else:
            row["cases"] = cases
    if args.capture:
        path.write_text(json.dumps(fixture, indent=2) + "\n")
    print(f"{len(sources)} exact original ARM ranges, two cases per range")


if __name__ == "__main__":
    main()
