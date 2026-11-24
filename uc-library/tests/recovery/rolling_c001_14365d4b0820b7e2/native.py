"""Run the exact mixer ARM entry with mapped sentinels and no external stubs."""

import argparse
import hashlib
import json
from io import BytesIO
from pathlib import Path

import elftools
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import arm_const as arm

ELF_HASH = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
BODY_HASH = "60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad"
MANGLED = "_ZN8Presonus5Mixer18RackMixerComponent14controlChangedERKNS_5Panel16ControlRegistrarEhPh"
ADDRESS = 0x7B128
SIZE = 16
SECTION = 12
PAGE = 0x1000
DATA = 0x100000
STACK = 0x200000
STOP = 0x300000
REGISTERS = [getattr(arm, f"UC_ARM_REG_R{i}") for i in range(12)]
REGISTERS.extend([arm.UC_ARM_REG_SP, arm.UC_ARM_REG_LR])


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_body(raw):
    if sha(raw) != ELF_HASH:
        raise ValueError("Original ELF hash mismatch")
    elf = ELFFile(BytesIO(raw))
    symbol = elf.get_section_by_name(".symtab").get_symbol_by_name(MANGLED)
    if len(symbol or ()) != 1:
        raise ValueError("Expected exactly one original symbol row")
    row = symbol[0]
    section = elf.get_section(SECTION)
    if (elf["e_machine"], elf.little_endian, row["st_value"], row["st_size"],
        row["st_shndx"], section.name) != ("EM_ARM", True, ADDRESS, SIZE, SECTION, ".text"):
        raise ValueError("Original symbol identity differs")
    relative = ADDRESS - section["sh_addr"]
    if not 0 <= relative <= section["sh_size"] - SIZE:
        raise ValueError("Original range exceeds mapped section")
    offset = section["sh_offset"] + relative
    body = raw[offset : offset + SIZE]
    if sha(body) != BODY_HASH:
        raise ValueError("Original symbol range hash mismatch")
    return body, offset


def observe(machine, writes, instructions, tag, is_null):
    writes.clear()
    instructions.clear()
    machine.mem_write(STACK, bytes(PAGE))
    data = bytearray(b"\xa3" * PAGE)
    data[0x200 : 0x203] = bytes([0x31, tag, 0x79])
    machine.mem_write(DATA, bytes(data))
    regs = [DATA + 16 + tag, DATA + 0x500 + tag, tag,
            0 if is_null else DATA + 0x201]
    regs += [0x11220000 + i * 0x101 + tag for i in range(4, 12)]
    regs += [STACK + PAGE // 2, STOP]
    for register, value in zip(REGISTERS, regs):
        machine.reg_write(register, value)
    machine.reg_write(arm.UC_ARM_REG_R12, 0x56789ABC)
    machine.emu_start(ADDRESS, STOP, count=8)
    after = [machine.reg_read(register) for register in REGISTERS]
    sp = regs[-2]
    if (machine.reg_read(arm.UC_ARM_REG_PC) != STOP or
        instructions != list(range(ADDRESS, ADDRESS + SIZE, 4)) or
        after[1:] != regs[1:] or len(writes) != 4 or
        sorted(writes) != [(sp + offset, 4) for offset in range(-16, 0, 4)]):
        raise ValueError(f"Unexpected native frame/control observation at {tag}/{is_null}")
    observed = bytes(machine.mem_read(DATA, PAGE))
    changed = observed[:0x200] != data[:0x200] or observed[0x203:] != data[0x203:]
    return [tag, int(is_null), int(changed), *observed[0x200:0x203]]


def capture(elf):
    body, offset = read_body(elf.read_bytes())
    machine = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
    code_page = ADDRESS & ~(PAGE - 1)
    machine.mem_map(code_page, PAGE, unicorn.UC_PROT_READ | unicorn.UC_PROT_EXEC)
    machine.mem_write(ADDRESS, body)
    machine.mem_map(DATA, PAGE, unicorn.UC_PROT_READ | unicorn.UC_PROT_WRITE)
    machine.mem_map(STACK, PAGE, unicorn.UC_PROT_READ | unicorn.UC_PROT_WRITE)
    writes, instructions = [], []
    machine.hook_add(unicorn.UC_HOOK_MEM_WRITE,
                     lambda _, access, address, size, value, ctx: writes.append((address, size)))
    machine.hook_add(unicorn.UC_HOOK_CODE,
                     lambda _, address, size, ctx: instructions.append(address))
    cases = [observe(machine, writes, instructions, tag, null)
             for tag in range(256) for null in (False, True)]
    return {
        "elf_sha256": ELF_HASH,
        "firmware": "RM/RML mixer 13731",
        "role": "server",
        "mangled": MANGLED,
        "address": ADDRESS,
        "size": SIZE,
        "section": SECTION,
        "file_offset": offset,
        "range_sha256": sha(body),
        "unicorn": unicorn.__version__,
        "pyelftools": elftools.__version__,
        "frame": "All cases restore SP, FP and PC. Only four 4-byte frame writes; no calls.",
        "cases": cases,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, required=True)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--write", type=Path)
    modes.add_argument("--compare", type=Path)
    args = parser.parse_args()
    result = capture(args.elf)
    if args.write:
        args.write.write_text(json.dumps(result, separators=(",", ":")) + "\n")
    elif result != json.loads(args.compare.read_text()):
        parser.error("Fresh ARM execution differs from sealed fixture")
    print(f"Verified original range and independently executed {len(result['cases'])} ARM cases.")


if __name__ == "__main__":
    main()
