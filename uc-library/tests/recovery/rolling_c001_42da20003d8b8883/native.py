"""Replay the hash-bound original ARM leaf on isolated memory."""
import argparse
import hashlib
import io
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile
import unicorn as u
from unicorn import arm_const as r

ELF_SHA256 = "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0"
MANGLED = "_ZN8Presonus7Surface20PresetsPageComponent12getTargetUrlERN4Core13CStringBufferILi256EEE"
RANGE_SHA256 = "60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad"
ADDRESS, SIZE, SECTION, OFFSET = 0xB6140, 16, 12, 0xAE140


def observe(body, index, initial_buffer, selected):
    machine = u.Uc(u.UC_ARCH_ARM, u.UC_MODE_ARM)
    code_page = ADDRESS & ~0xFFF
    machine.mem_map(code_page, 0x1000)
    machine.mem_write(ADDRESS, body)
    base = 0x100000 + index * 0x10000
    receiver, url, sp = base, base + 0x1000, base + 0x2FF0
    receiver_bytes = bytes([0x41 + index]) * 256
    machine.mem_map(base, 0x3000)
    machine.mem_write(receiver, receiver_bytes)
    machine.mem_write(url, initial_buffer)
    returned = code_page + 0x800
    registers = {
        getattr(r, f"UC_ARM_REG_R{number}"): 0x11000000 + number * 256 + index
        for number in range(13)
    }
    registers.update({r.UC_ARM_REG_R0: receiver, r.UC_ARM_REG_R1: url,
                      r.UC_ARM_REG_SP: sp, r.UC_ARM_REG_LR: returned})
    for register, value in registers.items():
        machine.reg_write(register, value)

    writes, instructions = [], []
    machine.hook_add(u.UC_HOOK_MEM_WRITE,
                     lambda _uc, _access, addr, size, _value, _data:
                     writes.append([addr - sp, size]))
    machine.hook_add(u.UC_HOOK_CODE,
                     lambda _uc, addr, _size, _data: instructions.append(addr))
    machine.emu_start(ADDRESS, returned, count=8)
    assert instructions == list(range(ADDRESS, ADDRESS + SIZE, 4))
    assert machine.reg_read(r.UC_ARM_REG_PC) == returned
    assert all(machine.reg_read(reg) == value for reg, value in registers.items()
               if reg != r.UC_ARM_REG_IP)
    assert machine.reg_read(r.UC_ARM_REG_IP) == sp
    assert sorted(writes) == [[-16, 4], [-12, 4], [-8, 4], [-4, 4]]
    observed_buffer = bytes(machine.mem_read(url, len(initial_buffer)))
    assert observed_buffer == initial_buffer
    assert bytes(machine.mem_read(receiver, len(receiver_bytes))) == receiver_bytes
    return {
        "initial_buffer": initial_buffer.hex(), "observed_buffer": observed_buffer.hex(),
        "portable_selected_sentinel": selected, "native_r0": receiver,
        "native_r1": url, "native_sp": sp, "native_pc": returned,
        "native_frame_writes": writes, "native_instruction_trace": instructions,
    }


def collect(path):
    contents = path.read_bytes()
    assert hashlib.sha256(contents).hexdigest() == ELF_SHA256
    elf = ELFFile(io.BytesIO(contents))
    section = elf.get_section(SECTION)
    assert section.name == ".text" and section["sh_type"] == "SHT_PROGBITS"
    assert section["sh_addr"] <= ADDRESS <= section["sh_addr"] + section["sh_size"] - SIZE
    assert section["sh_offset"] + ADDRESS - section["sh_addr"] == OFFSET
    matches = elf.get_section_by_name(".symtab").get_symbol_by_name(MANGLED)
    assert any((sym["st_value"], sym["st_size"], sym["st_shndx"]) ==
               (ADDRESS, SIZE, SECTION) for sym in matches)
    body = contents[OFFSET:OFFSET + SIZE]
    assert hashlib.sha256(body).hexdigest() == RANGE_SHA256
    cases = [
        (bytes(256), -1),
        (b"preset:/scene/7\0" + b"Q" * 240, 7),
        (bytes(33 + index % 90 for index in range(255)) + b"\0", 31),
    ]
    assert all(len(buffer) == 256 for buffer, _ in cases)
    return {"elf_sha256": ELF_SHA256, "mangled": MANGLED, "address": ADDRESS,
            "size": SIZE, "section": SECTION, "section_name": section.name,
            "offset": OFFSET, "range_sha256": RANGE_SHA256, "unicorn": u.__version__,
            "cases": [observe(body, index, *case) for index, case in enumerate(cases)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", type=Path)
    action.add_argument("--verify", type=Path)
    args = parser.parse_args()
    report = collect(args.elf)
    if args.write:
        with args.write.open("x") as output:
            output.write(json.dumps(report, indent=2) + "\n")
    else:
        assert json.loads(args.verify.read_text()) == report
    print(f"Native ARM execution passed for {len(report['cases'])} cases")


if __name__ == "__main__":
    main()
