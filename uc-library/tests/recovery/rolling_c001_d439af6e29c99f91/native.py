"""Offline execution of the sealed ARM mixer range."""
import argparse
import hashlib
import io
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_MODE_ARM, Uc, __version__
from unicorn import arm_const as arm

IS_ELEMENT = True
ORIGINALS = [('9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07',
  'RM/RML mixer 13731',
  'server',
  '_ZN8Presonus5Panel7Element14setNeedsToDrawEb',
  618820,
  20,
  '11752880ea70fd2254204dd6db3817a8a3acad4e8827b1231b0d6b53bbaf5e79',
  'rootfs/RML16AI_Rack_13731/home/root/mixer',
  586052,
  3512828),
 ('304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0',
  'CS18AI surface 13840',
  'client',
  '_ZN8Presonus5Panel7Element14setNeedsToDrawEb',
  122068,
  20,
  '11752880ea70fd2254204dd6db3817a8a3acad4e8827b1231b0d6b53bbaf5e79',
  'rootfs/CS18_v13840/home/root/surface',
  89300,
  1621844)]
STACK = 0x200000
MEMORY = 0x300000
STOP = 0x410000
REGS = [getattr(arm, f"UC_ARM_REG_R{i}") for i in range(13)] + [
    arm.UC_ARM_REG_SP, arm.UC_ARM_REG_LR
]


def observe(ADDRESS, SIZE, body, seed, receiver):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    uc.mem_map(ADDRESS & ~0xfff, 0x1000)
    uc.mem_write(ADDRESS, body)
    uc.mem_map(STACK, 0x1000)
    uc.mem_map(MEMORY, 0x2000)
    uc.mem_map(STOP, 0x1000)
    stack = STACK + 0x800
    sentinel = bytes((i + seed) % 256 for i in range(0x2000))
    uc.mem_write(MEMORY, sentinel)
    uc.mem_write(STACK, sentinel[:0x1000])
    uc.reg_write(arm.UC_ARM_REG_CPSR, 0xa0000010)
    registers = [seed * 0x100001 + i for i in range(13)] + [stack, STOP]
    registers[:4] = [receiver, seed % 2 if IS_ELEMENT else MEMORY + 0x1000, seed, MEMORY + 0x1008]
    for register, value in zip(REGS, registers):
        uc.reg_write(register, value)
    trace, reads, writes = [], [], []
    uc.hook_add(UC_HOOK_CODE, lambda _, address, size, data: trace.append(address))
    uc.hook_add(UC_HOOK_MEM_READ,
                lambda _, access, address, size, value, data: reads.append([address, size]))
    uc.hook_add(UC_HOOK_MEM_WRITE,
                lambda _, access, address, size, value, data: writes.append([address, size, value]))
    uc.emu_start(ADDRESS, STOP, count=8)
    after = [uc.reg_read(register) for register in REGS]
    assert trace == list(range(ADDRESS, ADDRESS + SIZE, 4))
    assert uc.reg_read(arm.UC_ARM_REG_PC) == STOP
    assert after[:12] == registers[:12] and after[12] == stack
    assert after[13:] == registers[13:]
    assert uc.reg_read(arm.UC_ARM_REG_CPSR) == 0xa0000010
    external_writes = [write for write in writes if not stack - 16 <= write[0] < stack]
    assert reads and all(stack - 16 <= address < address + size <= stack
                         for address, size in reads)
    if IS_ELEMENT:
        assert external_writes == [[receiver + 0x74, 4, seed % 2]]
        offset = receiver + 0x74 - MEMORY
        assert bytes(uc.mem_read(MEMORY, 0x2000)) == (
            sentinel[:offset] + (seed % 2).to_bytes(4, "little") + sentinel[offset + 4:])
        contract = [seed % 2, 1, 0]
    else:
        assert not external_writes
        assert bytes(uc.mem_read(MEMORY, 0x2000)) == sentinel
        contract = [1, 0]
    return {"seed": seed, "registers_before": registers, "registers_after": after,
            "trace": trace, "returned_to": STOP, "reads": reads, "writes": writes,
            "contract": contract}


def fixtures(path, metadata):
    ELF_HASH, firmware, role, MANGLED, ADDRESS, SIZE, RANGE_HASH, _, OFFSET, table_slot = metadata
    data = path.read_bytes()
    assert hashlib.sha256(data).hexdigest() == ELF_HASH
    elf = ELFFile(io.BytesIO(data))
    assert elf["e_machine"] == "EM_ARM" and elf.little_endian
    matches = elf.get_section_by_name(".symtab").get_symbol_by_name(MANGLED)
    assert len(matches) == 1
    symbol = matches[0]
    assert (symbol["st_value"], symbol["st_size"], symbol["st_shndx"]) == (ADDRESS, SIZE, 12)
    assert symbol["st_info"]["type"] == "STT_FUNC"
    section = elf.get_section(12)
    offset = section["sh_offset"] + ADDRESS - section["sh_addr"]
    assert section.name == ".text" and offset == OFFSET
    assert 0 <= ADDRESS - section["sh_addr"] <= section["sh_size"] - SIZE
    body = data[offset:offset + SIZE]
    assert hashlib.sha256(body).hexdigest() == RANGE_HASH

    table = elf.get_section_by_name(".symtab")
    table_name = "Element" if IS_ELEMENT else "Page"
    table_symbol, = table.get_symbol_by_name(f"_ZTVN8Presonus5Panel{len(table_name)}{table_name}E")
    table_section = elf.get_section(table_symbol["st_shndx"])
    assert table_symbol["st_value"] <= table_slot < table_symbol["st_value"] + table_symbol["st_size"]
    slot_offset = table_section["sh_offset"] + table_slot - table_section["sh_addr"]
    assert int.from_bytes(data[slot_offset:slot_offset + 4], "little") == ADDRESS
    receivers = (MEMORY, MEMORY + 0x100, MEMORY + 0x200, MEMORY + 0x300) if IS_ELEMENT else (
        MEMORY, MEMORY + 0x100, 0, 0x500000)
    return {"elf_sha256": ELF_HASH, "mangled": MANGLED, "address": ADDRESS, "size": SIZE,
            "role": role, "firmware": firmware, "section": 12, "section_name": ".text",
            "file_offset": offset, "range_sha256": RANGE_HASH, "original_bytes": body.hex(),
            "vtable_word_address": table_slot, "unicorn_version": __version__,
            "cases": [observe(ADDRESS, SIZE, body, seed, receiver)
                      for seed, receiver in enumerate(receivers, 1)]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, required=True, action="append")
    output = parser.add_mutually_exclusive_group(required=True)
    output.add_argument("--out", type=Path)
    output.add_argument("--verify", type=Path)
    args = parser.parse_args()
    assert len(args.elf) == len(ORIGINALS)
    result = [fixtures(path, row) for path, row in zip(args.elf, ORIGINALS)]
    if args.out:
        args.out.write_text(json.dumps(result, indent=2) + "\n")
    elif json.loads(args.verify.read_text()) != result:
        parser.exit(1, "Fresh original observations differ from sealed fixtures\n")
    print(f"Verified {sum(len(row['cases']) for row in result)} exact original ARM executions")
