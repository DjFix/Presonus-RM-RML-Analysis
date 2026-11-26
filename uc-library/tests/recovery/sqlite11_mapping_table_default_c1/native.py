"""Execute a sealed constructor range and the real ARM Item C1 instructions."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

import elftools
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_SP,
)

TABLE, STACK, STOP = 0x500100, 0x530800, 0x540000
COUNT, STRIDE = 1024, 72
OBJECT_SIZE = 0x12014
CSTRING = 0x24268
ITEM_NAME = "_ZN8Presonus12MappingTable4ItemC1EPKcPN4Core8Portable10AliasParamE"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def extract(file, name):
    sym, = file.get_section_by_name(".symtab").get_symbol_by_name(name)
    section_index = sym["st_shndx"]
    section = file.get_section(section_index)
    addr, size = sym["st_value"], sym["st_size"]
    i = addr - section["sh_addr"]
    assert sym["st_info"]["type"] == "STT_FUNC"
    assert 0 <= i < i + size <= section["sh_size"]
    data = section.data()[i:i+size]
    return {
        "address": addr, "size": size, "section": section_index, "section_name": section.name,
        "file_offset": section["sh_offset"] + i, "range_sha256": digest(data),
    }, data


def observe(packet):
    original = json.loads(packet.read_text())["originals"][0]["original"]
    path = Path(original["elf_path"])
    assert digest(path.read_bytes()) == original["elf"]
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        assert elf["e_machine"] == "EM_ARM" and elf.little_endian
        target, target_bytes = extract(elf, original["mangled"])
        item, item_bytes = extract(elf, ITEM_NAME)
    assert all(original[k] == v for k, v in target.items())
    assert target_bytes.hex() == original["range_hex"]

    cases = [execute(target, target_bytes, item, item_bytes, poison) for poison in (0xA5, 0x5A)]
    return {
        "original": original, "support": {"mangled": ITEM_NAME, **item},
        "cases": cases, "versions": {"unicorn": unicorn.__version__, "pyelftools": elftools.__version__},
        "scope": "Exact application bodies executed. Two null fixed-string construction calls per slot use a provider hook which writes the first NUL only. ARM application stores are logged separately. No firm layout or source result is inferred for other bytes of native string buffers.",
    }


def execute(target, target_bytes, item, item_bytes, poison):
    arm = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    for address, data in ((target["address"], target_bytes), (item["address"], item_bytes)):
        page = address & ~4095
        if not any(start <= page <= end for start, end, _ in arm.mem_regions()):
            arm.mem_map(page, 4096)
        arm.mem_write(address, data)
    arm.mem_map(CSTRING & ~4095, 4096)
    arm.mem_map(TABLE & ~4095, 0x14000)
    arm.mem_map(STACK & ~4095, 0x1000)
    arm.mem_write(TABLE - 16, bytes([poison]) * (OBJECT_SIZE + 32))

    ctor_calls, string_calls, writes = [], [], []
    allowed = [(row["address"], row["address"] + row["size"]) for row in (target, item)]

    def observe_code(cpu, address, size, _):
        if address in (item["address"], CSTRING):
            this = cpu.reg_read(UC_ARM_REG_R0)
            name = cpu.reg_read(UC_ARM_REG_R1)
            assert name == 0
            if address == item["address"]:
                assert cpu.reg_read(UC_ARM_REG_R2) == 0
                ctor_calls.append(this - TABLE)
            else:
                string_calls.append(this - TABLE)
                cpu.mem_write(this, b"\0")
                cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))
                return
        assert size == 4 and any(lo <= address < hi for lo, hi in allowed), hex(address)

    def observe_write(cpu, _, address, size, value, __):
        if (STACK & ~4095) <= address < STACK:
            assert address + size <= STACK
            return
        assert TABLE <= address and address + size <= TABLE + OBJECT_SIZE, hex(address)
        writes.append((address - TABLE, size, value & ((1 << (size * 8)) - 1)))

    arm.hook_add(UC_HOOK_CODE, observe_code)
    arm.hook_add(UC_HOOK_MEM_WRITE, observe_write)
    for register, value in ((UC_ARM_REG_R0, TABLE), (UC_ARM_REG_LR, STOP), (UC_ARM_REG_SP, STACK)):
        arm.reg_write(register, value)
    arm.emu_start(target["address"], STOP, count=60000)
    assert arm.reg_read(UC_ARM_REG_PC) == STOP and arm.reg_read(UC_ARM_REG_SP) == STACK
    assert arm.reg_read(UC_ARM_REG_R0) == TABLE

    slots = [12 + i * STRIDE for i in range(COUNT)]
    assert ctor_calls == slots
    assert string_calls == [slot + field for slot in slots for field in (4, 40)]
    expected_writes = [(0, 4, 0), (4, 4, TABLE + 12), (8, 4, 0)]
    expected_writes += [(slot + field, 4, 0) for slot in slots for field in (0, 36)]
    expected_writes += [(0x1200C, 4, TABLE + 0x12014), (0x12010, 4, 0)]
    assert writes == expected_writes
    initial = bytearray([poison] * OBJECT_SIZE)
    for offset, _, value in writes:
        struct.pack_into("<I", initial, offset, value)
    for offset in string_calls:
        initial[offset] = 0
    assert bytes(arm.mem_read(TABLE, OBJECT_SIZE)) == initial
    for address in (TABLE - 16, TABLE + OBJECT_SIZE):
        assert bytes(arm.mem_read(address, 16)) == bytes([poison]) * 16

    return {
        "initial_poison": poison, "item_initialization_count": len(ctor_calls),
        "first_slot_offset": slots[0], "stride": STRIDE, "last_slot_offset": slots[-1],
        "distinct_null_string_calls": len(string_calls),
        "observed_arm_writes": len(writes), "arm_write_trace_sha256": digest(json.dumps(writes).encode()),
        "item_constructor_offsets_sha256": digest(json.dumps(ctor_calls).encode()),
        "output_with_modeled_first_nuls_sha256": digest(initial),
        "table_header_words": list(struct.unpack_from("<III", initial)),
        "auxiliary_words": list(struct.unpack_from("<II", initial, 0x1200C)),
        "returned_receiver_register": True,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    actual = observe(args.packet)
    if args.write:
        args.fixture.write_text(json.dumps(actual, indent=2) + "\n")
    else:
        assert actual == json.loads(args.fixture.read_text())
    fields = actual["cases"]
    print(f"{actual['original']['mangled']}: {len(fields)} native ARM runs × {fields[0]['item_initialization_count']} slots")
