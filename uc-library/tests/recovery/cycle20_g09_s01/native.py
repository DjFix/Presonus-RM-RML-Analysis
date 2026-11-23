"""Replay the isolated original Rack capability in an offline ARM emulator."""

import argparse
import hashlib
import json
from pathlib import Path
import struct

import elftools
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import arm_const

MANGLED = "_ZNK8Presonus5Mixer18RackMixerComponent19supportSubgroupModeEv"
ELF_SHA256 = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
CODE_SHA256 = "f4fc1200a4af6d09889b5ae7a9a8ab14566224ef17078675ef8021500729a481"
ADDRESS = 0x7B108
SIZE = 20
STOP = ADDRESS + SIZE
RECEIVER = 0x100000
STACK = 0x200000
SP = STACK + 0x800
PATTERNS = (0, 0xAAAAAAAA, 0xFFFFFFFF, 0x12345678)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_original(path):
    if sha(path.read_bytes()) != ELF_SHA256:
        raise ValueError("Original ELF digest differs")
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        if elf["e_machine"] != "EM_ARM" or not elf.little_endian:
            raise ValueError("Expected little-endian ARM ELF")
        symbols = elf.get_section_by_name(".symtab")
        entries = symbols.get_symbol_by_name(MANGLED)
        metadata = {(e["st_value"], e["st_size"], e["st_shndx"]) for e in entries}
        if metadata != {(ADDRESS, SIZE, 12)}:
            raise ValueError(f"Unexpected original range: {metadata}")
        section = elf.get_section(12)
        offset = ADDRESS - section["sh_addr"]
        code = section.data()[offset:offset + SIZE]
        file_offset = section["sh_offset"] + offset
        stream.seek(file_offset)
        if section.name != ".text" or file_offset != 0x73108 or stream.read(SIZE) != code or sha(code) != CODE_SHA256:
            raise ValueError("Original section range check failed")
        table, = symbols.get_symbol_by_name("_ZTVN8Presonus5Mixer18RackMixerComponentE")
        table_section = elf.get_section(table["st_shndx"])
        slot = 196
        table_offset = table["st_value"] - table_section["sh_addr"]
        if table_offset < 0 or slot + 4 > table["st_size"]:
            raise ValueError("Rack vtable slot outside original symbol range")
        target, = struct.unpack_from("<I", table_section.data(), table_offset + slot)
        if target != ADDRESS:
            raise ValueError("Original Rack table slot differs")
        return code, {"elf_sha256": ELF_SHA256, "mangled": MANGLED, "address": ADDRESS,
                      "size": SIZE, "section": 12, "section_name": section.name,
                      "file_offset": file_offset, "range_sha256": sha(code),
                      "rack_table_address": table["st_value"], "rack_slot_offset": slot,
                      "rack_slot_target": target}


def observe(code, pattern):
    arm = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
    for region in (ADDRESS & ~0xfff, RECEIVER, STACK):
        arm.mem_map(region, 0x1000)
    arm.mem_write(ADDRESS, code)
    arm.mem_protect(ADDRESS & ~0xfff, 0x1000, unicorn.UC_PROT_READ | unicorn.UC_PROT_EXEC)
    receiver_before = struct.pack("<I", pattern) * 1024
    arm.mem_write(RECEIVER, receiver_before)
    arm.reg_write(arm_const.UC_ARM_REG_R0, RECEIVER)
    arm.reg_write(arm_const.UC_ARM_REG_SP, SP)
    arm.reg_write(arm_const.UC_ARM_REG_LR, STOP)
    trace = []
    accesses = []
    arm.hook_add(unicorn.UC_HOOK_CODE, lambda _, addr, size, ctx: trace.append((addr, size)))
    arm.hook_add(unicorn.UC_HOOK_MEM_READ | unicorn.UC_HOOK_MEM_WRITE,
                 lambda _, kind, addr, size, value, ctx: accesses.append((kind, addr, size)))
    arm.emu_start(ADDRESS, STOP, count=16)
    if trace != [(pc, 4) for pc in range(ADDRESS, STOP, 4)] or arm.reg_read(arm_const.UC_ARM_REG_PC) != STOP:
        raise ValueError("Original execution did not follow the isolated leaf range")
    if arm.reg_read(arm_const.UC_ARM_REG_SP) != SP or not accesses or any(
        addr < SP - 16 or addr + size > SP for _, addr, size in accesses
    ):
        raise ValueError("Original made an access outside its stack frame")
    return {"pattern": pattern, "return_r0": arm.reg_read(arm_const.UC_ARM_REG_R0),
            "state_unchanged": arm.mem_read(RECEIVER, 0x1000) == receiver_before,
            "instruction_addresses": [addr for addr, _ in trace],
            "stack_accesses": [["read" if kind == unicorn.UC_MEM_READ else "write", addr - SP, size]
                               for kind, addr, size in accesses],
            "external_calls": []}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", required=True, type=Path)
    output = parser.add_mutually_exclusive_group(required=True)
    output.add_argument("--write-fixtures", type=Path)
    output.add_argument("--verify-fixtures", type=Path)
    args = parser.parse_args()
    code, original = read_original(args.elf)
    report = {"original": original, "unicorn": unicorn.__version__,
              "pyelftools": elftools.__version__,
              "cases": [observe(code, pattern) for pattern in PATTERNS]}
    if args.write_fixtures:
        with args.write_fixtures.open("x") as stream:
            stream.write(json.dumps(report, indent=2) + "\n")
    elif json.loads(args.verify_fixtures.read_text()) != report:
        raise SystemExit("Fresh native observations differ from sealed fixtures")
    print(json.dumps({"native_replay_passed": True, "case_count": len(report["cases"]),
                      "original": original}))


if __name__ == "__main__":
    main()
