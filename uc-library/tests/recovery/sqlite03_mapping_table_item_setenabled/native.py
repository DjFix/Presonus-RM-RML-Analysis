"""Execute original MappingTable Item methods, with observed provider entries."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

import elftools
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_SP,
)

PANEL = "_ZN8Presonus5Panel"
VTABLE = "_ZTVN8Presonus5Panel"
OBJECT, ITEM, PARAM, STACK, STOP, TRANSMIT = (
    0x500100, 0x500200, 0x500300, 0x50F000, 0x500000, 0x500004,
)
CAST, DISABLE, IMMEDIATE, FULL_OFF, BROADCAST, TX = range(1, 7)
KINDS = {1: "7Control", 2: "10LEDControl", 3: "13SwitchControl"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def execute(packet_path):
    original = json.loads(packet_path.read_text())["originals"][0]["original"]
    elf_path = Path(original["elf_path"])
    assert sha(elf_path.read_bytes()) == original["elf"]
    with elf_path.open("rb") as stream:
        return run(ELFFile(stream), original)


def run(elf, original):
    symbols = {sym.name: sym for sym in elf.get_section_by_name(".symtab").iter_symbols()}
    ranges = {}

    def bound(name):
        sym = symbols[name]
        index = sym["st_shndx"]
        section = elf.get_section(index)
        address, size = sym["st_value"], sym["st_size"]
        relative = address - section["sh_addr"]
        assert 0 <= relative and relative + size <= section["sh_size"]
        data = section.data()[relative:relative + size]
        ranges[name] = {
            "address": address, "size": size, "section": index,
            "section_name": section.name, "file_offset": section["sh_offset"] + relative,
            "range_sha256": sha(data),
        }
        return address

    name = original["mangled"]
    target = bound(name)
    for key, value in ranges[name].items():
        assert original[key] == value, key
    site = elf.get_section(original["section"])
    begin = target - site["sh_addr"]
    assert site.data()[begin:begin + original["size"]].hex() == original["range_hex"]

    entries = {}
    for kind in KINDS.values():
        entries[bound(PANEL + kind + "6castToEi")] = CAST
        bound(VTABLE + kind + "E")
    entries[bound(PANEL + KINDS[1] + "14disableControlEbb")] = DISABLE
    entries[bound(PANEL + KINDS[3] + "14disableControlEbb")] = DISABLE
    entries[bound(PANEL + KINDS[3] + "12setImmediateEb")] = IMMEDIATE
    entries[bound(PANEL + KINDS[2] + "10setFullOffEv")] = FULL_OFF
    entries[bound(PANEL + KINDS[2] + "14broadcastValueEi")] = BROADCAST

    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    uc.mem_map(0x8000, 0x300000)
    for segment in elf.iter_segments():
        if segment["p_type"] == "PT_LOAD":
            uc.mem_write(segment["p_vaddr"], segment.data())
    uc.mem_map(0x500000, 0x10000)

    cases = []
    if "setEnabled" in name:
        cases = [(kind, attached, initial, [0, 0, 1, 1, 0])
                 for kind in (0, 1, 3) for attached in range(1 + (kind == 3))
                 for initial in (0, 1)]
    elif "setImmediate" in name:
        cases = [(kind, 0, initial, [1, 1, 0, 0, 1])
                 for kind in range(4) for initial in (0, 1)]
    elif "setFullOff" in name:
        cases = [(kind, 0, initial, [0, 0])
                 for kind in range(4) for initial in (-1, 0, 2, 3)]

    trace = []
    allowed = [(target, target + original["size"])] + [
        (row["address"], row["address"] + row["size"]) for row in ranges.values()
        if row["address"] in entries
    ]

    def observe(emu, pc, size, _):
        if pc == TRANSMIT:
            assert emu.reg_read(UC_ARM_REG_R0) == OBJECT
            trace.append([TX, 0, 0])
            emu.reg_write(UC_ARM_REG_PC, emu.reg_read(UC_ARM_REG_LR))
            return
        assert any(start <= pc < end for start, end in allowed), hex(pc)
        event = entries.get(pc)
        if event:
            assert emu.reg_read(UC_ARM_REG_R0) == OBJECT
            arg = emu.reg_read(UC_ARM_REG_R1) if event in (CAST, DISABLE, IMMEDIATE, BROADCAST) else 0
            reset = emu.reg_read(UC_ARM_REG_R2) if event == DISABLE else 0
            trace.append([event, arg, reset])

    uc.hook_add(UC_HOOK_CODE, observe)
    rows = []
    for kind, attached, initial, inputs in cases:
        block = bytearray(128)
        if kind:
            vtable = ranges[VTABLE + KINDS[kind] + "E"]["address"] + 8
            if kind in (2, 3):
                # Preserve all measured slots except the external transmission boundary.
                table = bytearray(uc.mem_read(vtable, 52))
                struct.pack_into("<I", table, 0x24, TRANSMIT)
                vtable = 0x500400
                uc.mem_write(vtable, bytes(table))
            struct.pack_into("<IiI", block, 0, vtable, initial, PARAM if attached else 0)
            block[0x3D] = block[0x3E] = initial & 0xff
        uc.mem_write(OBJECT, bytes(block))
        item = struct.pack("<I", OBJECT if kind else 0) + bytes(124)
        uc.mem_write(ITEM, item)
        parameter = struct.pack("<f", 0.75) + bytes(124)
        uc.mem_write(PARAM, parameter)
        steps = []
        for argument in inputs:
            trace.clear()
            uc.reg_write(UC_ARM_REG_R0, ITEM)
            uc.reg_write(UC_ARM_REG_R1, argument)
            uc.reg_write(UC_ARM_REG_SP, STACK)
            uc.reg_write(UC_ARM_REG_LR, STOP)
            before = bytes(uc.mem_read(OBJECT, 128))
            uc.emu_start(target, STOP, count=128)
            assert uc.reg_read(UC_ARM_REG_PC) == STOP
            assert uc.reg_read(UC_ARM_REG_SP) == STACK
            assert bytes(uc.mem_read(ITEM, 128)) == item
            assert bytes(uc.mem_read(PARAM, 128)) == parameter
            after = bytes(uc.mem_read(OBJECT, 128))
            permitted = (
                {0x3E} if "setEnabled" in name and kind == 3 else
                {0x3D} if "setImmediate" in name and kind == 3 else
                {4, 5, 6, 7} if "setFullOff" in name and kind in (2, 3) else set()
            )
            assert all(a == b or i in permitted for i, (a, b) in enumerate(zip(before, after)))
            state = 0
            if "setEnabled" in name and kind == 3:
                state = after[0x3E]
            elif "setImmediate" in name and kind == 3:
                state = after[0x3D]
            elif "setFullOff" in name and kind:
                state = struct.unpack_from("<i", after, 4)[0]
            steps.append({"input": argument, "state": state, "trace": trace.copy()})
        rows.append({"kind": kind, "attached": attached, "initial": initial, "steps": steps})
    assert rows
    return {
        "original": original, "ranges": ranges, "rows": rows,
        "oracle": {"unicorn": unicorn.__version__, "pyelftools": elftools.__version__,
                   "transmit": "Observed virtual dispatch via a copied original vtable with only the transmit slot replaced by a recording stub.",
                   "parameter": "Non-null opaque sentinel read only by ARM disableControl. No original or simulated Core method executed."},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    observed = execute(args.packet)
    if args.write:
        args.fixture.write_text(json.dumps(observed, indent=2) + "\n")
    else:
        assert observed == json.loads(args.fixture.read_text())
    print(f"native oracle: {len(observed['rows'])} cases, "
          f"{sum(len(row['steps']) for row in observed['rows'])} calls")


if __name__ == "__main__":
    main()
