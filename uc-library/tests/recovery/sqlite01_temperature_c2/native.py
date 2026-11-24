"""Execute the two sealed ARM receiver initializers without hardware or stubs."""

import argparse
import hashlib
import json
from pathlib import Path
import struct

import elftools
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn.arm_const import (
    UC_ARM_REG_LR,
    UC_ARM_REG_PC,
    UC_ARM_REG_R0,
    UC_ARM_REG_R1,
    UC_ARM_REG_SP,
)

ROOT = Path(__file__).resolve().parents[4]
TASK = Path(__file__).parent.name
CONTEXT = Path("temp/recovery-work/sqlite-issued/prepared-temperaturecontrol") / TASK / "CONTEXT.json"
VTABLE = "_ZTVN8Presonus5Panel18TemperatureControlE"
TAGS = (-(2**31), -1234567, -1, 0, 1, 1234567, 2**31 - 1)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def indexed_symbol(table, name):
    entries = table.get_symbol_by_name(name)
    assert entries is not None and len(entries) == 1, name
    return entries[0]


def verify_range(original):
    path = ROOT / original["elf_path"]
    data = path.read_bytes()
    assert digest(data) == original["elf"]
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        table = elf.get_section_by_name(".symtab")
        symbol = indexed_symbol(table, original["mangled"])
        section = elf.get_section(symbol["st_shndx"])
        address = symbol["st_value"]
        size = symbol["st_size"]
        offset = section["sh_offset"] + address - section["sh_addr"]
        assert (address, size, symbol["st_shndx"], section.name, offset) == (
            original["address"], original["size"], original["section"],
            original["section_name"], original["file_offset"],
        )
        assert 0 <= offset - section["sh_offset"] <= section["sh_size"] - size
        body = data[offset:offset + size]
        assert digest(body) == original["range_sha256"]
        assert body.hex() == original["range_hex"]

        alternate_name = original["mangled"].replace("C1Ei", "C2Ei") if TASK.endswith("c1") else original["mangled"].replace("C2Ei", "C1Ei")
        alternate = indexed_symbol(table, alternate_name)
        alternate_address = alternate["st_value"]
        assert alternate["st_size"] == size and alternate["st_shndx"] == symbol["st_shndx"]
        alternate_offset = section["sh_offset"] + alternate_address - section["sh_addr"]
        assert abs(alternate_address - address) >= size
        assert data[alternate_offset:alternate_offset + size] == body

        vtable = indexed_symbol(table, VTABLE)["st_value"]
        assert struct.unpack_from("<I", body, len(body) - 4)[0] == vtable + 8
    return body, vtable, alternate_address


def run_case(address, body, vtable, tag, index):
    machine = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
    code_page = address & ~4095
    receiver_page, stack_page, stop = (0x1000000, 0x2000000, 0x3000000)
    receiver = receiver_page + 0x100 + 0x20 * index
    stack_top = stack_page + 0x800
    machine.mem_map(code_page, 8192)
    machine.mem_write(address, body)
    for page in (receiver_page, stack_page, stop):
        machine.mem_map(page, 4096)
    initial = bytes((i * 17 + index * 31) % 256 for i in range(64))
    machine.mem_write(receiver - 16, initial)
    writes, pcs = [], []

    def trace_pc(uc, current, size, _):
        if current == stop:
            uc.emu_stop()
            return
        assert size == 4 and address <= current < address + len(body) - 4
        pcs.append(current)

    def trace_write(_uc, _access, location, size, value, _):
        if stack_page <= location and location + size <= stack_top:
            return
        assert receiver <= location and location + size <= receiver + 28
        writes.append([location - receiver, size, value])

    machine.hook_add(unicorn.UC_HOOK_CODE, trace_pc)
    machine.hook_add(unicorn.UC_HOOK_MEM_WRITE, trace_write)
    for register, value in (
        (UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, tag & 0xFFFFFFFF),
        (UC_ARM_REG_SP, stack_top), (UC_ARM_REG_LR, stop),
    ):
        machine.reg_write(register, value)
    machine.emu_start(address, stop + 4, count=32)
    assert machine.reg_read(UC_ARM_REG_PC) == stop
    assert machine.reg_read(UC_ARM_REG_R0) == receiver
    assert machine.reg_read(UC_ARM_REG_SP) == stack_top
    assert pcs == list(range(address, address + len(body) - 4, 4))
    observed = bytes(machine.mem_read(receiver - 16, len(initial)))
    assert observed[:16] == initial[:16] and observed[44:] == initial[44:]
    vptr, level, parameter, alternate, tertiary, io, saved_tag = struct.unpack_from("<IiIIIIi", observed, 16)
    assert (vptr, level, parameter, alternate, tertiary, io, saved_tag) == (vtable + 8, -1, 0, 0, 0, 0, tag)
    assert writes == [
        [0, 4, vptr], [4, 4, 0xFFFFFFFF], [20, 4, 0],
        [24, 4, tag & 0xFFFFFFFF], [8, 4, 0], [12, 4, 0], [16, 4, 0],
    ]
    return {
        "receiver": receiver, "input_tag": tag, "executed_pcs": pcs,
        "writes": writes, "outside_receiver_preserved": True,
        "initial_window_hex": initial.hex(), "final_window_hex": observed.hex(),
        "return_this": True, "stack_restored": True, "external_calls": [],
        "common_state": [saved_tag, level, parameter, alternate, tertiary, io],
    }


def generate():
    packet = (ROOT / CONTEXT).read_bytes()
    sets = []
    for entry in json.loads(packet)["originals"]:
        original = entry["original"]
        body, vtable, alternate_address = verify_range(original)
        sets.append({
            "original": original,
            "alternate_variant_address": alternate_address,
            "variants_share_entry": False,
            "vtable_address": vtable,
            "vtable_address_point": vtable + 8,
            "cases": [run_case(original["address"], body, vtable, tag, i) for i, tag in enumerate(TAGS)],
        })
    return {
        "task_id": TASK,
        "context_sha256": digest(packet),
        "producers": {"unicorn": unicorn.__version__, "pyelftools": elftools.__version__},
        "originals": sets,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--out", type=Path)
    choice.add_argument("--verify", type=Path)
    args = parser.parse_args()
    result = generate()
    if args.out:
        args.out.write_text(json.dumps(result, indent=2) + "\n")
    else:
        assert result == json.loads(args.verify.read_text())
    print(f"Executed {sum(len(entry['cases']) for entry in result['originals'])} native cases for {TASK}")


if __name__ == "__main__":
    main()
