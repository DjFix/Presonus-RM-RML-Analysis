"""Offline execution of the exact RM FX selector default and its ELF-backed vtable slot."""
import hashlib
import json
import struct
import sys
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (
    UC_ARM_REG_FP, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP,
)

ELF = Path(
    "/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/"
    "control10x20-after-4fed70d11/packeting/actual07-authorized-wave01-capture02/"
    "snapshot/rootfs/RML16AI_Rack_13731/home/root/mixer"
)
ELF_SHA256 = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
CLASS_NAME = "FXComponent"
NAME = f"_ZN8Presonus5Mixer{len(CLASS_NAME)}{CLASS_NAME}6mapIDsEi"
VTABLE = f"_ZTVN8Presonus5Mixer{len(CLASS_NAME)}{CLASS_NAME}E"
ADDRESS = 0x3c958
TABLE = 0x16fc38
TABLE_SLOT_OFFSET = 88


def digest(data):
    return hashlib.sha256(data).hexdigest()


def bound_symbol(elf, raw, name, address, size, section_name, expected_sha):
    symbols = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    assert len(symbols) == 1, name
    symbol = symbols[0]
    assert (symbol["st_value"], symbol["st_size"]) == (address, size), name
    section = elf.get_section(symbol["st_shndx"])
    delta = address - section["sh_addr"]
    assert section.name == section_name and 0 <= delta <= section["sh_size"] - size
    offset = section["sh_offset"] + delta
    data = raw[offset:offset + size]
    assert digest(data) == expected_sha, name
    return data, {
        "mangled": name, "address": address, "size": size, "section": section.name,
        "section_index": symbol["st_shndx"], "file_offset": offset,
        "sha256": expected_sha,
    }


REFERENCE_PATH = Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/control10x20-after-4fed70d11/packeting/actual07-authorized-wave01-capture02/snapshot/temp/recovery-work/control10x20-after-4fed70d11/selection/fx-map-ids/FX_MAP_IDS_GROUP_REVIEW_NATIVE01.json')
REFERENCE_SHA256 = '2b37d05e05a3352ab5aead4e800eed4a27d04bcca3d2ad693f93342e6b782d08'

def generate():
    raw = ELF.read_bytes()
    assert digest(raw) == ELF_SHA256
    with ELF.open("rb") as source:
        elf = ELFFile(source)
        body, body_range = bound_symbol(
            elf, raw, NAME, ADDRESS, 20, ".text",
            "3407647c635a7af28924cded332ab9fa36bef97c6deea10605b2f5ef387b382b",
        )
        table, table_range = bound_symbol(
            elf, raw, VTABLE, TABLE, 116, ".rodata", "62096bd7e53a5e14a047fd224980965b82406bf07da07e6073bf0d0c6c400a95",
        )
        reverb, reverb_table_range = bound_symbol(
            elf, raw, "_ZTVN8Presonus5Mixer15ReverbComponentE", 0x16fbc0, 116,
            ".rodata", "0bc132ed49b343fb0fd484bb5e57a5f700ff478ae899168caba48b2307e9db38",
        )
        override = struct.unpack_from("<I", reverb, TABLE_SLOT_OFFSET)[0]
        [method] = elf.get_section_by_name(".symtab").get_symbol_by_name(
            "_ZN8Presonus5Mixer15ReverbComponent6mapIDsEi")
        assert override == method["st_value"] and override != ADDRESS
        for name in (".rel.dyn", ".rel.plt"):
            assert all(rel["r_offset"] != TABLE + TABLE_SLOT_OFFSET
                       for rel in elf.get_section_by_name(name).iter_relocations())
    assert struct.unpack_from("<I", table, TABLE_SLOT_OFFSET)[0] == ADDRESS
    assert body_range["section_index"] == 12

    cases = []
    for route in (0, 1):
        for seed, selector in enumerate((0, 1, 42, -1, -2147483648, 2147483647, -7)):
            entry, end, stack, receiver = 0x810000, 0x810008, 0x820f00, 0x830100 + seed * 128
            machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
            for page in {ADDRESS & ~4095, TABLE & ~4095, entry, stack & ~4095, receiver & ~4095}:
                machine.mem_map(page, 4096)
            machine.mem_write(ADDRESS, body)
            machine.mem_write(TABLE, table)
            # Synthetic caller helper: ldr ip,[r0]; ldr pc,[ip,#80].
            # ELF table address point follows offset-to-top and RTTI words.
            machine.mem_write(entry, struct.pack("<II", 0xE590C000, 0xE59CF050))
            before = struct.pack("<I", TABLE + 8) + bytes([0x5A ^ seed]) * 60
            machine.mem_write(receiver, before)
            machine.reg_write(UC_ARM_REG_R0, receiver)
            machine.reg_write(UC_ARM_REG_R1, selector & 0xffffffff)
            machine.reg_write(UC_ARM_REG_SP, stack)
            machine.reg_write(UC_ARM_REG_LR, end)
            machine.reg_write(UC_ARM_REG_FP, 0x12345678 + seed)
            instructions, writes = [], []

            def instruction(_uc, addr, _size, _user):
                instructions.append(addr)

            def write(_uc, _access, addr, size, _value, _user):
                writes.append((addr, size))

            machine.hook_add(UC_HOOK_CODE, instruction)
            machine.hook_add(UC_HOOK_MEM_WRITE, write)
            machine.emu_start(entry if route else ADDRESS, end, count=12)
            assert machine.reg_read(UC_ARM_REG_PC) == end
            assert machine.reg_read(UC_ARM_REG_SP) == stack
            assert machine.reg_read(UC_ARM_REG_FP) == 0x12345678 + seed
            result = machine.reg_read(UC_ARM_REG_R0)
            assert result == 0xffffffff
            assert instructions == ([entry, entry + 4] if route else []) + list(range(ADDRESS, ADDRESS + 20, 4))
            assert sorted(writes) == [(address, 4) for address in range(stack - 16, stack, 4)]
            unchanged = (bytes(machine.mem_read(receiver, len(before))) == before
                         and bytes(machine.mem_read(TABLE, len(table))) == table)
            assert unchanged
            cases.append({
                "input": [route, selector], "expected": result,
                "r0_after": result, "instructions": instructions,
                "stack_write_addresses": sorted(address for address, _ in writes),
            })
    historical = REFERENCE_PATH.read_bytes()
    assert digest(historical) == REFERENCE_SHA256
    expected = json.loads(historical)["selected_observation"]["tests"]
    actual = [{"route": "vtable" if route else "direct",
               "signed_input_bits": selector & 0xffffffff,
               "return_r0": case["expected"],
               "receiver_unchanged": True}
              for case in cases for route, selector in [case["input"]]
              if selector in (0, 1, 42, -1, -2147483648)]
    assert actual == expected
    return {
        "elf_sha256": ELF_SHA256, "ranges": [body_range], "vtable": table_range,
        "vtable_slot_offset": TABLE_SLOT_OFFSET, "cases": cases,
        "reverb_table": reverb_table_range, "reverb_override": override,
    }


if __name__ == "__main__":
    Path(sys.argv[1]).write_text(json.dumps(generate(), indent=2) + "\n")
