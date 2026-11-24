"""Verify and execute the original mixer symbol on controlled ARM state."""
import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

import elftools
import unicorn
from elftools.elf.elffile import ELFFile
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP


def sha(data):
    return hashlib.sha256(data).hexdigest()


def oracle(original, elf_path):
    data = elf_path.read_bytes()
    assert sha(data) == original["elf"], "ELF SHA-256 mismatch"
    elf = ELFFile(io.BytesIO(data))
    assert elf["e_machine"] == "EM_ARM" and elf.elfclass == 32 and elf.little_endian
    symbol, = elf.get_section_by_name(".symtab").get_symbol_by_name(original["mangled"])
    address, size, section_index = (
        symbol["st_value"], symbol["st_size"], symbol["st_shndx"]
    )
    assert (address, size, section_index) == (
        original["address"], original["size"], original["section"]
    )
    assert symbol["st_info"]["type"] == "STT_FUNC"
    section = elf.get_section(section_index)
    assert section.name == original["section_name"]
    relative = address - section["sh_addr"]
    assert 0 <= relative and relative + size <= section["sh_size"]
    offset = section["sh_offset"] + relative
    body = data[offset:offset + size]
    assert offset == original["file_offset"]
    assert body.hex() == original["range_hex"] and sha(body) == original["range_sha256"]

    receiver, entries, stack, return_pc = 0x200000, 0x210000, 0x300000, 0x400000
    cases = []
    for count, capacity in [(0, 10), (1, 10), (4, 10), (9, 10), (10, 10), (11, 15)]:
        vm = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
        for page in (address & ~0xFFF, receiver, entries, stack, return_pc):
            vm.mem_map(page, 0x1000)
        vm.mem_write(address, body)
        # The observed receiver count is at +12. Surrounding words and the
        # mapped pointer array detect side effects and distinguish count from capacity.
        received = struct.pack("<IIIII", 0xA5A5A5A5, entries, capacity, count, 0x5A5A5A5A)
        borrowed = bytes(range(64))
        vm.mem_write(receiver, received)
        vm.mem_write(entries, borrowed)
        sp = stack + 0x800
        vm.reg_write(UC_ARM_REG_R0, receiver)
        vm.reg_write(UC_ARM_REG_SP, sp)
        vm.reg_write(UC_ARM_REG_LR, return_pc)
        executed, accesses = [], []
        vm.hook_add(unicorn.UC_HOOK_CODE,
                    lambda engine, pc, width, _: executed.append((pc, width)))
        vm.hook_add(unicorn.UC_HOOK_MEM_READ | unicorn.UC_HOOK_MEM_WRITE,
                    lambda engine, op, addr, width, value, _: accesses.append([op, addr, width]))
        vm.emu_start(address, return_pc, count=12)
        assert vm.reg_read(UC_ARM_REG_PC) == return_pc
        assert vm.reg_read(UC_ARM_REG_SP) == sp
        assert executed == [(pc, 4) for pc in range(address, address + size, 4)]
        assert [access for access in accesses if not stack <= access[1] < stack + 0x1000] == [
            [unicorn.UC_MEM_READ, receiver + 12, 4]
        ]
        assert bytes(vm.mem_read(receiver, len(received))) == received
        assert bytes(vm.mem_read(entries, len(borrowed))) == borrowed
        cases.append({
            "count": count,
            "capacity": capacity,
            "observed_return": vm.reg_read(UC_ARM_REG_R0),
            "instructions": len(executed),
            "memory_accesses": accesses,
            "receiver_and_entries_unchanged": True,
        })
    return {"original": original, "unicorn": unicorn.__version__,
            "pyelftools": elftools.__version__, "cases": cases}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--elf", type=Path, required=True)
    destination = parser.add_mutually_exclusive_group(required=True)
    destination.add_argument("--out", type=Path)
    destination.add_argument("--verify", type=Path)
    args = parser.parse_args()
    original = json.loads(args.packet.read_text())["originals"][0]["original"]
    result = oracle(original, args.elf)
    if args.out:
        with args.out.open("x") as output:
            output.write(json.dumps(result, indent=2) + "\n")
    else:
        assert result == json.loads(args.verify.read_text()), "native fixture mismatch"
    print(f"{len(result['cases'])} independent original ARM cases")


if __name__ == "__main__":
    main()
