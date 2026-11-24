"""Replay the exact original ARM body in isolation, offline."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_FP, UC_ARM_REG_LR,
    UC_ARM_REG_SP, UC_ARM_REG_PC,
)

ELF_SHA = "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0"
BODY_SHA = "60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad"
MANGLED = "_ZN8Presonus5Panel18TemperatureControl14broadcastValueEi"
ADDRESS, SIZE, SECTION = 0x16F38, 16, 12


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, description):
    if not condition:
        raise ValueError(description)


def original(path):
    data = path.read_bytes()
    require(digest(data) == ELF_SHA, "ELF identity mismatch")
    elf = ELFFile(io.BytesIO(data))
    require(elf.elfclass == 32 and elf.little_endian and
            elf.header["e_machine"] == "EM_ARM", "Unexpected ELF architecture")
    entries = elf.get_section_by_name(".symtab").get_symbol_by_name(MANGLED)
    require(entries and len(entries) == 1, "Expected unique symbol")
    row = entries[0].entry
    require((row["st_value"], row["st_size"], row["st_shndx"]) ==
            (ADDRESS, SIZE, SECTION), "Symbol range mismatch")
    section = elf.get_section(SECTION)
    delta = ADDRESS - section["sh_addr"]
    require(section.name == ".text" and 0 <= delta <= section["sh_size"] - SIZE,
            "Range outside expected file-backed section")
    offset = section["sh_offset"] + delta
    body = data[offset:offset + SIZE]
    require(offset == 0xEF38 and digest(body) == BODY_SHA, "Body identity mismatch")
    return offset, body


def observe(body, value, seed, bound):
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    receiver, sp, lr, fp = 0x21000, 0x30800, 0x22000, 0x98765430
    machine.mem_map(0x16000, 0x1000)
    machine.mem_map(receiver, 0x1000)
    machine.mem_map(0x30000, 0x1000)
    sentinel = bytes(((i + seed + 71 * bound) & 255) for i in range(128))
    machine.mem_write(ADDRESS, body)
    machine.mem_write(receiver, sentinel)
    registers = {UC_ARM_REG_R0: receiver, UC_ARM_REG_R1: value & 0xffffffff,
                 UC_ARM_REG_SP: sp, UC_ARM_REG_LR: lr, UC_ARM_REG_FP: fp}
    for register, initial in registers.items():
        machine.reg_write(register, initial)
    trace = []
    writes = []
    machine.hook_add(UC_HOOK_CODE, lambda _m, address, _s, _u: trace.append(address))
    machine.hook_add(UC_HOOK_MEM_WRITE, lambda _m, _kind, address, size, value, _u:
                     writes.append([address, size, value]))
    machine.emu_start(ADDRESS, lr, count=5)
    unchanged = (machine.mem_read(receiver, len(sentinel)) == sentinel and
                 all(machine.reg_read(reg) == initial for reg, initial in registers.items()))
    require(machine.reg_read(UC_ARM_REG_PC) == lr, "Original failed to return")
    require(trace == list(range(ADDRESS, ADDRESS + SIZE, 4)), "Unexpected original trace")
    require([(a, s) for a, s, _ in writes] ==
            [(a, 4) for a in range(sp - 16, sp, 4)], "Unexpected memory writes")
    require(unchanged, "Original changed receiver sentinel or entry registers")
    return {"value": value, "seed": seed, "bound": bound, "unchanged": unchanged,
            "trace": trace, "stack_writes": writes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--out", type=Path)
    action.add_argument("--verify", type=Path)
    args = parser.parse_args()
    started = datetime.now(timezone.utc).isoformat()
    offset, body = original(args.elf)
    cases = [observe(body, value, seed, bound)
             for value in (-2147483648, -1, 0, 1, 1023, 2147483647)
             for seed in (-172, 17) for bound in (False, True)]
    result = {"elf_sha256": ELF_SHA, "mangled": MANGLED, "address": ADDRESS,
              "size": SIZE, "section": SECTION, "file_offset": offset,
              "range_sha256": BODY_SHA, "unicorn": unicorn.__version__, "cases": cases}
    if args.out:
        args.out.write_text(json.dumps(result, indent=2) + "\n")
    else:
        require(result == json.loads(args.verify.read_text()), "Fresh native observations differ")
    print(json.dumps({"native_cases": len(cases), "start_utc": started,
                      "end_utc": datetime.now(timezone.utc).isoformat()}))


if __name__ == "__main__":
    main()
