"""Execute just the verified ARM symbol range on synthetic initialized state."""
import argparse
import hashlib
import io
import json
from pathlib import Path

import unicorn
from elftools import __version__ as elftools_version
from elftools.elf.elffile import ELFFile
from unicorn import arm_const


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_original(original):
    data = Path(original["elf_path"]).read_bytes()
    if digest(data) != original["elf"]:
        raise ValueError("Unexpected ELF hash")
    elf = ELFFile(io.BytesIO(data))
    section = elf.get_section(original["section"])
    symbol, = elf.get_section_by_name(".symtab").get_symbol_by_name(original["mangled"])
    address = original["address"]
    size = original["size"]
    relative = address - section["sh_addr"]
    offset = section["sh_offset"] + relative
    if (elf["e_machine"] != "EM_ARM" or not elf.little_endian
            or section.name != original["section_name"]
            or symbol["st_value"] != address or symbol["st_size"] != size
            or symbol["st_shndx"] != original["section"]
            or not 0 <= relative <= section["sh_size"] - size
            or offset != original["file_offset"]):
        raise ValueError("Unexpected ELF symbol mapping")
    body = data[offset:offset + size]
    if digest(body) != original["range_sha256"] or body.hex() != original["range_hex"]:
        raise ValueError("Unexpected ELF range")
    return body


def run_sequence(original, body, initial_mode, initial_requested, serial, modes):
    address = original["address"]
    code_page = address & ~0xFFF
    receiver = 0x400000
    stack = 0x500000
    exit_pc = 0x600000
    uc = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
    uc.mem_map(code_page, 0x1000, unicorn.UC_PROT_READ | unicorn.UC_PROT_EXEC)
    uc.mem_write(address, body)
    uc.mem_map(receiver, 0x1000, unicorn.UC_PROT_READ | unicorn.UC_PROT_WRITE)
    uc.mem_map(stack, 0x1000, unicorn.UC_PROT_READ | unicorn.UC_PROT_WRITE)

    before = bytearray([0xA5] * 0x1000)
    before[0:4] = serial.to_bytes(4, "little")
    before[0x50:0x54] = initial_mode.to_bytes(4, "little")
    before[0x54] = initial_requested
    uc.mem_write(receiver, bytes(before))

    instructions = []
    writes = []

    def on_code(_uc, pc, size, _user):
        if not address <= pc <= address + len(body) - size:
            raise ValueError(f"Instruction escaped verified range: {pc:#x}")
        instructions.append(pc - address)

    def on_write(_uc, _access, target, size, value, _user):
        writes.append([target - receiver, size, value & ((1 << (size * 8)) - 1)])

    uc.hook_add(unicorn.UC_HOOK_CODE, on_code)
    uc.hook_add(unicorn.UC_HOOK_MEM_WRITE, on_write, begin=receiver, end=receiver + 0xFFF)

    steps = []
    for mode in modes:
        instructions.clear()
        writes.clear()
        uc.reg_write(arm_const.UC_ARM_REG_R0, receiver)
        uc.reg_write(arm_const.UC_ARM_REG_R1, mode)
        uc.reg_write(arm_const.UC_ARM_REG_SP, stack + 0x800)
        uc.reg_write(arm_const.UC_ARM_REG_LR, exit_pc)
        uc.emu_start(address, exit_pc, count=32)
        if uc.reg_read(arm_const.UC_ARM_REG_PC) != exit_pc:
            raise ValueError("Native invocation did not return to its sentinel")
        after = uc.mem_read(receiver, 0x1000)
        steps.append({
            "input_mode": mode,
            "observed_mode": int.from_bytes(after[0x50:0x54], "little"),
            "observed_requested": after[0x54],
            "observed_sentinel": int.from_bytes(after[0:4], "little"),
            "other_bytes_unchanged": after[:0x50] == before[:0x50] and after[0x55:] == before[0x55:],
            "receiver_writes": list(writes),
            "instruction_offsets": list(instructions),
            "calls": [],
        })
        before = after
    return {
        "initial_mode": initial_mode,
        "initial_requested": initial_requested,
        "sentinel": serial,
        "steps": steps,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    entry, = json.loads(args.packet.read_text())["originals"]
    original = entry["original"]
    body = read_original(original)
    result = {
        "original": original,
        "versions": {"unicorn": unicorn.__version__, "pyelftools": elftools_version},
        "sequences": [
            run_sequence(original, body, 0x7F7F7F7F, 0, 0x2468ACE0,
                         [0, 1, 0xFFFFFFFF, 0x12345678, 0x12345678, 0]),
            run_sequence(original, body, 0xFFFFFFFF, 1, 0xF0DEBC9A,
                         [0xFFFFFFFF, 0, 1, 0x12345678]),
        ],
    }
    if args.verify:
        if result != json.loads(args.fixture.read_text()):
            raise ValueError("Fresh native execution differs from sealed fixtures")
    else:
        args.fixture.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"Native ARM executions: {sum(len(s['steps']) for s in result['sequences'])}")


if __name__ == "__main__":
    main()
