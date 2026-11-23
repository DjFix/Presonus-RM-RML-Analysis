"""Offline direct and bounded caller execution of the original ARM UI method."""

import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

import unicorn
from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, Uc
from unicorn.arm_const import UC_ARM_REG_FP, UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R2, UC_ARM_REG_R4, UC_ARM_REG_SP

ELF_SHA256 = "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0"
RANGE_SHA256 = "f4fc1200a4af6d09889b5ae7a9a8ab14566224ef17078675ef8021500729a481"
MANGLED = "_ZN8Presonus18ModalPageComponent8onCancelEv"
CALLER = "_ZN8Presonus18ModalPageComponent12paramChangedEPN4Core8Portable9ParameterEi"
VTABLE = "_ZTVN8Presonus18ModalPageComponentE"
ADDRESS = 0x646d0
DISPATCH = 0x680e0
SLOT = 56
LEAF_RETURN = 0x100000
CALLER_RETURN = 0x101000
CLOSE_ENTRY = 0x68054
STACK = 0x60000000
SP = STACK + 0x800
RECEIVER = 0x61000000


def digest(data):
    return hashlib.sha256(data).hexdigest()


def elf_range(elf, blob, name):
    matches = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    if len(matches) != 1:
        raise ValueError(f"Expected a unique symbol: {name}")
    symbol = matches[0]
    address, size, index = (symbol[key] for key in ("st_value", "st_size", "st_shndx"))
    section = elf.get_section(index)
    displacement = address - section["sh_addr"]
    if not 0 <= displacement <= section["sh_size"] - size or section["sh_type"] == "SHT_NOBITS":
        raise ValueError(f"Invalid symbol section mapping: {name}")
    offset = section["sh_offset"] + displacement
    code = blob[offset:offset + size]
    return code, dict(symbol=name, address=address, size=size, section=index,
                      section_name=section.name, file_offset=offset, range_sha256=digest(code))


def execute(leaf, leaf_range, caller, caller_range, table, table_range, seed, unused_r2, mode):
    arm = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    for base in (ADDRESS & ~0xfff, 0x68000, table_range["address"] & ~0xfff,
                 STACK, RECEIVER, LEAF_RETURN, CALLER_RETURN):
        arm.mem_map(base, 0x1000)
    arm.mem_write(ADDRESS, leaf)
    arm.mem_write(caller_range["address"], caller)
    arm.mem_write(table_range["address"], table)
    receiver = struct.pack("<I", table_range["address"] + 8) + bytes(
        (seed + 13 * index) % 256 for index in range(124)
    )
    arm.mem_write(RECEIVER, receiver)
    arm.reg_write(UC_ARM_REG_R0, RECEIVER)
    arm.reg_write(UC_ARM_REG_R2, unused_r2)
    arm.reg_write(UC_ARM_REG_R4, RECEIVER)
    arm.reg_write(UC_ARM_REG_FP, STACK + 0x980)
    arm.reg_write(UC_ARM_REG_SP, SP)
    arm.reg_write(UC_ARM_REG_LR, LEAF_RETURN)
    call_frame = struct.pack("<IIII", 0x1234, STACK + 0x980, SP + 24, CALLER_RETURN)
    arm.mem_write(SP + 4, call_frame)
    addresses, accesses = [], []
    arm.hook_add(UC_HOOK_CODE, lambda uc, address, size, _: addresses.append(address))
    arm.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE,
                 lambda uc, access, address, size, value, _: accesses.append([access, address, size]))
    start, stop = ADDRESS, LEAF_RETURN
    if mode == "dispatch":
        start, stop = DISPATCH, CLOSE_ENTRY
    if mode == "zero-result-branch":
        start, stop = DISPATCH + 16, CALLER_RETURN
        arm.reg_write(UC_ARM_REG_R0, 0)
    arm.emu_start(start, stop, count=40)
    if arm.reg_read(UC_ARM_REG_PC) != stop:
        raise ValueError(f"{mode} did not reach its expected boundary")
    if bytes(arm.mem_read(RECEIVER, len(receiver))) != receiver:
        raise ValueError(f"{mode} changed receiver bytes")
    if any(not STACK <= addr < STACK + 0x1000
           for access, addr, _ in accesses if access == unicorn.UC_MEM_WRITE):
        raise ValueError(f"{mode} wrote outside the stack")
    native_leaf_instructions = list(range(ADDRESS, ADDRESS + leaf_range["size"], 4))
    if mode == "leaf" and (addresses != native_leaf_instructions or
                           arm.reg_read(UC_ARM_REG_SP) != SP or
                           any(not STACK <= addr < STACK + 0x1000 for _, addr, _ in accesses)):
        raise ValueError("Leaf made an unexpected call, memory access, or stack change")
    if mode == "dispatch" and (
        addresses[4:4 + len(native_leaf_instructions)] != native_leaf_instructions or
        [unicorn.UC_MEM_READ, table_range["address"] + 8 + SLOT, 4] not in accesses
    ):
        raise ValueError("Caller did not dispatch the exact original vtable member")
    return dict(seed=seed, unused_r2=unused_r2, mode=mode, stop_pc=stop,
                result_r0=arm.reg_read(UC_ARM_REG_R0), instructions=addresses,
                memory_accesses=accesses, receiver_unchanged=True)


def generate(path):
    blob = path.read_bytes()
    if digest(blob) != ELF_SHA256:
        raise ValueError("Unexpected original ELF")
    elf = ELFFile(io.BytesIO(blob))
    leaf, leaf_range = elf_range(elf, blob, MANGLED)
    caller, caller_range = elf_range(elf, blob, CALLER)
    table, table_range = elf_range(elf, blob, VTABLE)
    if (leaf_range["address"], leaf_range["section"], leaf_range["size"],
            leaf_range["range_sha256"]) != (ADDRESS, 12, 20, RANGE_SHA256):
        raise ValueError("Unexpected target range")
    if struct.unpack_from("<I", table, 8 + SLOT)[0] != ADDRESS:
        raise ValueError("Unexpected native dispatch slot")
    args = (leaf, leaf_range, caller, caller_range, table, table_range)
    cases = [execute(*args, seed, r2, "leaf") for seed in (0, 17, 193, 255) for r2 in (0, 2)]
    callers = [execute(*args, seed, 2, mode)
               for seed in (17, 193) for mode in ("dispatch", "zero-result-branch")]
    return dict(elf_sha256=ELF_SHA256, original_range=leaf_range, caller_range=caller_range,
                vtable_range=table_range, vtable_slot=SLOT, leaf_cases=cases,
                caller_cases=callers)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, required=True)
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--check", type=Path)
    destination.add_argument("--generate", type=Path)
    args = parser.parse_args()
    receipt = generate(args.elf)
    if args.check:
        if json.loads(args.check.read_text()) != receipt:
            raise SystemExit("Original execution differed from the sealed fixture")
    else:
        with args.generate.open("x") as out:
            out.write(json.dumps(receipt, indent=2) + "\n")
    print(f"Unicorn {unicorn.__version__}: {len(receipt['leaf_cases'])} original leaf executions, "
          f"{len(receipt['caller_cases'])} original caller branch executions")


if __name__ == "__main__":
    main()
