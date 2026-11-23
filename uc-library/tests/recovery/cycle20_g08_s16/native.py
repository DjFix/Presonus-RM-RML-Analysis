"""Replay the exact original ARM MainLCD callback using its own vtable entry."""

import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

import unicorn
from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_FP, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP

ELF_SHA256 = "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0"
MANGLED = "_ZN8Presonus16MainLCDComponent21onFocusControlChangedEPN4Core8Portable7ControlE"
VTABLE = "_ZTVN8Presonus16MainLCDComponentE"
ADDRESS = 0x74644
SLOT = 76
HAS_ADJUSTOR = True
STACK = 0x60000000
SP = STACK + 0x800
RECEIVER = 0x61000000
DATA = 0x62000000
RETURN = 0x100000
ENTRY = 0x101000


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def elf_range(elf, blob, name):
    matches = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    if len(matches) != 1:
        raise ValueError(f"Expected one ELF symbol: {name}")
    symbol = matches[0]
    address, size, index = (symbol[key] for key in ("st_value", "st_size", "st_shndx"))
    section = elf.get_section(index)
    displacement = address - section["sh_addr"]
    if not 0 <= displacement <= section["sh_size"] - size or section["sh_type"] == "SHT_NOBITS":
        raise ValueError(f"Invalid ELF section mapping for {name}")
    offset = displacement + section["sh_offset"]
    content = blob[offset:offset + size]
    return content, dict(mangled=name, address=address, size=size, section=index,
                         section_name=section.name, file_offset=offset, range_sha256=digest(content))


def observe(leaf, table, range_info, thunk, mode, case):
    arm = unicorn.Uc(UC_ARCH_ARM, UC_MODE_ARM)
    for address in (ADDRESS & ~0xfff, range_info["address"] & ~0xfff,
                    STACK, RECEIVER, DATA, RETURN, ENTRY):
        arm.mem_map(address, 0x1000)
    arm.mem_write(ADDRESS, leaf)
    arm.mem_write(range_info["address"], table)
    seed = case["seed"]
    # Synthetic windows over receiver and arguments test preservation only.
    receiver = bytearray((seed + n * 17) % 256 for n in range(256))
    receiver[:4] = struct.pack("<I", range_info["address"] + 8)
    data = bytes((seed ^ n) % 256 for n in range(256))
    arm.mem_write(RECEIVER, bytes(receiver))
    arm.mem_write(DATA, data)
    initial_r0 = RECEIVER
    entry = ADDRESS
    if mode == "primary-vtable":
        # Harness loads the real ELF primary slot from a synthetic receiver.
        arm.mem_write(ENTRY, struct.pack("<II", 0xe5903000, 0xe593f000 | (SLOT - 8)))
        entry = ENTRY
    elif mode == "native-adjustor":
        initial_r0 += 132
        entry = ADDRESS - len(thunk)
        arm.mem_write(entry, thunk)
    arm.reg_write(UC_ARM_REG_R0, initial_r0)
    arm.reg_write(UC_ARM_REG_R1, DATA if case["argument"] else 0)
    arm.reg_write(UC_ARM_REG_R2, DATA + 128 if case["previous"] else 0)
    arm.reg_write(UC_ARM_REG_LR, RETURN)
    arm.reg_write(UC_ARM_REG_SP, SP)
    arm.reg_write(UC_ARM_REG_FP, SP + 0x80)
    instructions, accesses = [], []
    arm.hook_add(UC_HOOK_CODE, lambda uc, address, size, _: instructions.append(address))
    arm.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE,
                 lambda uc, access, address, size, value, _: accesses.append([access, address, size]))
    arm.emu_start(entry, RETURN, count=20)
    expected = list(range(ADDRESS, ADDRESS + len(leaf), 4))
    if mode == "primary-vtable":
        expected = [ENTRY, ENTRY + 4] + expected
        known_reads = [[unicorn.UC_MEM_READ, RECEIVER, 4],
                       [unicorn.UC_MEM_READ, range_info["address"] + SLOT, 4]]
        if accesses[:2] != known_reads:
            raise ValueError("Primary dispatch did not read the exact vtable slot")
        stack_accesses = accesses[2:]
    else:
        stack_accesses = accesses
        if mode == "native-adjustor":
            expected = [entry, entry + 4] + expected
    if (arm.reg_read(UC_ARM_REG_PC) != RETURN or arm.reg_read(UC_ARM_REG_SP) != SP
            or arm.reg_read(UC_ARM_REG_FP) != SP + 0x80
            or arm.reg_read(UC_ARM_REG_R0) != RECEIVER or instructions != expected
            or any(not SP - 16 <= address <= SP - size for _, address, size in stack_accesses)):
        raise ValueError("Unexpected callback/adjustor control flow or data access")
    unchanged = (bytes(arm.mem_read(RECEIVER, len(receiver))) == bytes(receiver)
                 and bytes(arm.mem_read(DATA, len(data))) == data
                 and arm.reg_read(UC_ARM_REG_R1) == (DATA if case["argument"] else 0)
                 and arm.reg_read(UC_ARM_REG_R2) == (DATA + 128 if case["previous"] else 0))
    if not unchanged:
        raise ValueError("Callback changed receiver or argument state")
    return dict(case, mode=mode, observed_unchanged=unchanged, instructions=instructions,
                memory_accesses=accesses, initial_r0=initial_r0, arm_r0=arm.reg_read(UC_ARM_REG_R0))


def generate(path):
    blob = path.read_bytes()
    if digest(blob) != ELF_SHA256:
        raise ValueError("Original ELF hash differs")
    elf = ELFFile(io.BytesIO(blob))
    leaf, original = elf_range(elf, blob, MANGLED)
    table, table_range = elf_range(elf, blob, VTABLE)
    if (original["address"], original["size"], original["section"], original["range_sha256"]) != (
            ADDRESS, 16, 12, "60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad"):
        raise ValueError("Original leaf binding differs")
    address, = struct.unpack_from("<I", table, SLOT)
    if address != ADDRESS:
        raise ValueError("Original vtable slot points to another leaf")
    modes = ["direct", "primary-vtable"]
    thunk, thunk_range = b"", None
    if HAS_ADJUSTOR:
        thunk, thunk_range = elf_range(elf, blob, "_ZThn132_" + MANGLED[2:])
        if thunk_range["address"] != ADDRESS - 8 or len(thunk) != 8:
            raise ValueError("Unexpected original adjustor range")
        if struct.pack("<I", thunk_range["address"]) not in table[80:]:
            raise ValueError("Missing native secondary adjustor link")
        modes.append("native-adjustor")
    inputs = [dict(seed=17, argument=1, previous=0), dict(seed=193, argument=1, previous=1),
              dict(seed=255, argument=0 if HAS_ADJUSTOR else 1, previous=0)]
    return dict(elf_sha256=ELF_SHA256, original_range=original, vtable_range=table_range,
                slot_offset=SLOT, slot_target=address, secondary_adjustor=thunk_range,
                cases=[observe(leaf, table, table_range, thunk, mode, row)
                       for mode in modes for row in inputs])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", required=True, type=Path)
    outputs = parser.add_mutually_exclusive_group(required=True)
    outputs.add_argument("--generate", type=Path)
    outputs.add_argument("--check", type=Path)
    args = parser.parse_args()
    observed = generate(args.elf)
    if args.check:
        if observed != json.loads(args.check.read_text()):
            raise SystemExit("Fresh original observations differ from sealed fixture")
    else:
        with args.generate.open("x") as output:
            output.write(json.dumps(observed, indent=2) + "\n")
    print(f"Unicorn {unicorn.__version__}: {len(observed['cases'])} exact original ARM leaf executions")


if __name__ == "__main__":
    main()
