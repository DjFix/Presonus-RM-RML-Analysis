"""Replay the exact original ARM AlertBook leaf using its own vtable entry."""

import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

import unicorn
from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_FP, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R2, UC_ARM_REG_SP

ELF_SHA256 = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
MANGLED = "_ZN8Presonus5Panel9AlertBook8previousEv"
VTABLE = "_ZTVN8Presonus5Panel9AlertBookE"
ADDRESS = 0x6ebec
SLOT = 52
STACK = 0x60000000
SP = STACK + 0x800
RECEIVER = 0x61000000
DATA = 0x62000000
RETURN = 0x100000


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


def observe(leaf, slot_address, case):
    arm = unicorn.Uc(UC_ARCH_ARM, UC_MODE_ARM)
    for address in (slot_address & ~0xfff, STACK, RECEIVER, DATA, RETURN):
        arm.mem_map(address, 0x1000)
    arm.mem_write(slot_address, leaf)
    seed = case["seed"]
    # Mock byte windows test memory preservation; they do not model the original layout.
    receiver = bytes((seed + n * 17) % 256 for n in range(256))
    data = bytes((seed ^ n) % 256 for n in range(256))
    arm.mem_write(RECEIVER, receiver)
    arm.mem_write(DATA, data)
    arm.reg_write(UC_ARM_REG_R0, RECEIVER)
    arm.reg_write(UC_ARM_REG_R2, seed)
    arm.reg_write(UC_ARM_REG_LR, RETURN)
    arm.reg_write(UC_ARM_REG_SP, SP)
    arm.reg_write(UC_ARM_REG_FP, SP + 0x80)
    instructions, accesses = [], []
    arm.hook_add(UC_HOOK_CODE, lambda uc, address, size, _: instructions.append(address))
    arm.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE,
                 lambda uc, access, address, size, value, _: accesses.append([access, address, size]))
    arm.emu_start(slot_address, RETURN, count=16)
    if (arm.reg_read(UC_ARM_REG_PC) != RETURN or arm.reg_read(UC_ARM_REG_SP) != SP
            or arm.reg_read(UC_ARM_REG_FP) != SP + 0x80
            or instructions != list(range(slot_address, slot_address + len(leaf), 4))
            or any(not SP - 16 <= address <= SP - size for _, address, size in accesses)):
        raise ValueError("Unexpected leaf control flow, memory access, or stack restoration")
    unchanged = (bytes(arm.mem_read(RECEIVER, len(receiver))) == receiver
                 and bytes(arm.mem_read(DATA, len(data))) == data)
    if not unchanged:
        raise ValueError("Navigation leaf changed a synthetic state region")
    return dict(case, observed_unchanged=unchanged, instructions=instructions,
                stack_accesses=accesses, arm_r0=arm.reg_read(UC_ARM_REG_R0))


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
    if table_range["range_sha256"] != "0cee2f5008f081e4da005fc8346615f9c16a8a4644c15bdc3c8b01b0c8f495a9":
        raise ValueError("Original vtable binding differs")
    address, = struct.unpack_from("<I", table, SLOT)
    if address != ADDRESS:
        raise ValueError("Original vtable slot points to another leaf")
    inputs = [
        dict(seed=0, mode=0, page=0, selection=0, duplicate=0, nanoseconds=0, shape=0),
        dict(seed=17, mode=1, page=1, selection=1, duplicate=0, nanoseconds=1750001, shape=0),
        dict(seed=193, mode=3, page=1, selection=1, duplicate=1, nanoseconds=9020012345, shape=1),
        dict(seed=255, mode=-3, page=0, selection=1, duplicate=0, nanoseconds=5400111, shape=2),
    ]
    return dict(elf_sha256=ELF_SHA256, original_range=original, vtable_range=table_range,
                slot_offset=SLOT, slot_target=address, cases=[observe(leaf, address, row) for row in inputs])


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
