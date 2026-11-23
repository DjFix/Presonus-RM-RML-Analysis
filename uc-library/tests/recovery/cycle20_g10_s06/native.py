"""Replay exact ARM UI destructors and verify disposal at the delete boundary."""

import argparse
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path

import unicorn as uc
from elftools.elf.elffile import ELFFile
from unicorn import arm_const as arm

CLASS = "FillElement"
PREFIX = f"_ZN8Presonus5Panel{len(CLASS)}{CLASS}"
VTABLE_PREFIX = "_ZTVN8Presonus5Panel"
IDENTITIES = {
    "client": (
        "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0",
        0xAD5C, 0x18BF48, {'D1': (134864, '9c51aeffd917ddf42874be353f392d0107aca84f2dd199fdae00e2d9e94af2fc'), 'D0': (135248, '811c1b0108961283da054fd30e36db269a11a4a93fbd4f841533c0ba6d29ee22')},
    ),
    "server": (
        "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07",
        0xAC10, 0x3599F0, {'D1': (631304, '1f1b6dcf1d98459e9d073e75ba39fcf26e9a05ac303092af276cf472305e4434'), 'D0': (631448, '34f4559bf2826b18826b69e4b959391034e367a9f587c806087823f2ed2ba811')},
    ),
}
RECEIVER, STACK, TRAMPOLINE, STOP = 0x40000000, 0x50000000, 0x70000000, 0x70000100
PAGE, STACK_TOP = 4096, STACK + 2048


def digest(data):
    return hashlib.sha256(data).hexdigest()


def range_of(elf, name, size):
    row, = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    assert row["st_size"] == size
    index = row["st_shndx"]
    section = elf.get_section(index)
    address = row["st_value"]
    offset = address - section["sh_addr"]
    assert 0 <= offset and offset + size <= section["sh_size"]
    body = section.data()[offset:offset + size]
    return body, {
        "mangled": name, "address": address, "size": size, "section": index,
        "section_name": section.name, "file_offset": section["sh_offset"] + offset,
        "sha256": digest(body),
    }


def run(code, code_pc, table, table_pc, base_word, allocator, variant, route, seed):
    machine = uc.Uc(uc.UC_ARCH_ARM, uc.UC_MODE_ARM)
    pages = {RECEIVER, STACK, TRAMPOLINE}
    regions = [(code_pc, code), (table_pc, table)]
    for address, body in regions:
        pages.update(range(address & ~(PAGE - 1), (address + len(body) + PAGE - 1) & ~(PAGE - 1), PAGE))
    if variant == "D0":
        pages.add(allocator & ~(PAGE - 1))
    for page in sorted(pages):
        machine.mem_map(page, PAGE)
    for address, body in regions:
        machine.mem_write(address, body)
    slot = 4 * (variant == "D0")
    machine.mem_write(TRAMPOLINE, struct.pack("<II", 0xE5901000, 0xE591F000 | slot))
    receiver = struct.pack("<I", table_pc + 8) + bytes((seed + i * 37) % 256 for i in range(124))
    machine.mem_write(RECEIVER, receiver)
    trace, deletes, stores = [], [], []
    was_reset = struct.pack("<I", base_word) + receiver[4:]

    def observe_instruction(emu, pc, _size, _opaque):
        trace.append(pc)
        if pc == allocator:
            pointer = emu.reg_read(arm.UC_ARM_REG_R0)
            assert variant == "D0" and pointer == RECEIVER
            assert bytes(emu.mem_read(pointer, len(receiver))) == was_reset
            deletes.append(pointer)
            emu.mem_unmap(pointer, PAGE)
            emu.reg_write(arm.UC_ARM_REG_PC, emu.reg_read(arm.UC_ARM_REG_LR))

    def observe_write(_emu, _kind, address, size, value, _opaque):
        if not STACK <= address < STACK + PAGE:
            stores.append([address, size, value])

    machine.hook_add(uc.UC_HOOK_CODE, observe_instruction)
    machine.hook_add(uc.UC_HOOK_MEM_WRITE, observe_write)
    for reg, value in (
        (arm.UC_ARM_REG_R0, RECEIVER), (arm.UC_ARM_REG_SP, STACK_TOP), (arm.UC_ARM_REG_LR, STOP),
    ):
        machine.reg_write(reg, value)
    machine.emu_start(code_pc if route == "direct" else TRAMPOLINE, STOP, count=32)
    assert machine.reg_read(arm.UC_ARM_REG_PC) == STOP
    assert machine.reg_read(arm.UC_ARM_REG_SP) == STACK_TOP
    expected = ([] if route == "direct" else [TRAMPOLINE, TRAMPOLINE + 4])
    instructions = list(range(code_pc, code_pc + len(code) - 4, 4))
    if variant == "D0":
        instructions.insert(8, allocator)
    assert trace == expected + instructions
    assert stores == [[RECEIVER, 4, base_word]]
    try:
        data = bytes(machine.mem_read(RECEIVER, len(receiver)))
    except uc.UcError as error:
        assert error.errno == uc.UC_ERR_READ_UNMAPPED
        unmapped = True
    else:
        assert data == was_reset
        unmapped = False
    assert unmapped == (variant == "D0") and len(deletes) == int(unmapped)
    return {"variant": variant, "route": route, "seed": seed, "delete_receivers": deletes,
            "receiver_unmapped_after_return": unmapped, "receiver_stores": stores, "trace": trace}


def original(path, role):
    expected_elf, allocator, base_word, expected = IDENTITIES[role]
    assert digest(path.read_bytes()) == expected_elf
    relocations = subprocess.check_output(["readelf", "-rW", str(path)], text=True)
    candidates = [line for line in relocations.splitlines()
                  if re.search(r"\bR_ARM_JUMP_SLOT\s+[0-9a-f]+\s+_ZdlPv@GLIBCXX_3\.4\b", line)]
    relocation, = candidates
    assert int(relocation.split()[3], 16) == allocator
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        assert elf["e_machine"] == "EM_ARM" and elf.little_endian
        assert not elf.get_section_by_name(".symtab").get_symbol_by_name(PREFIX + "D2Ev")
        table, table_info = range_of(elf, f"{VTABLE_PREFIX}{len(CLASS)}{CLASS}E", 60)
        _, base_table = range_of(elf, VTABLE_PREFIX + "7ElementE", 60)
        assert base_table["address"] + 8 == base_word
        ranges, cases = [], []
        for index, (variant, size) in enumerate((("D1", 28), ("D0", 44))):
            code, info = range_of(elf, PREFIX + variant + "Ev", size)
            address, sha = expected[variant]
            assert (info["address"], info["sha256"], info["section"]) == (address, sha, 12)
            assert info["file_offset"] == address - 0x8000
            assert struct.unpack_from("<I", table, 8 + 4 * index)[0] == address
            assert struct.unpack_from("<I", code, size - 4)[0] == base_word
            if variant == "D0":
                branch, = struct.unpack_from("<i", code, 28)
                assert (branch >> 24) & 0xFF == 0xEB
                immediate = (branch << 8) & 0xFFFFFFFF
                displacement = (immediate - (1 << 32) if immediate & (1 << 31) else immediate) >> 6
                assert address + 28 + 8 + displacement == allocator
            ranges.append({"variant": variant, **info})
            cases.extend(run(code, address, table, table_info["address"], base_word, allocator,
                             variant, route, seed)
                         for route in ("direct", "vtable") for seed in (5, 173))
    return {"role": role, "elf_sha256": expected_elf, "ranges": ranges, "vtable": table_info,
            "base_vtable_address_point": base_word, "allocator_plt": allocator,
            "allocator_relocation": relocation.strip(), "cases": cases}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", required=True, type=Path)
    parser.add_argument("--server", required=True, type=Path)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--write", type=Path)
    target.add_argument("--check", type=Path)
    args = parser.parse_args()
    result = {"unicorn": uc.__version__, "class": CLASS,
              "originals": [original(getattr(args, role), role) for role in IDENTITIES]}
    if args.write:
        args.write.write_text(json.dumps(result, indent=2) + "\n")
    else:
        assert json.loads(args.check.read_text()) == result
    print(f"{CLASS}: 16 native teardown observations across four exact originals")


if __name__ == "__main__":
    main()
