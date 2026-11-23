"""Execute exact native color-update routing with independently bound provider values."""

import argparse
import hashlib
import json
import struct
from pathlib import Path

from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
from elftools.elf.elffile import ELFFile
import unicorn as uc
from unicorn import arm_const as arm

UP = False
TASK = "17" if UP else "18"
PREFIX = "_ZN8Presonus13SLChannelBase"
PALETTE = ("_ZNK19MixerColorConverter19getColorIndexForRGBERKN4Core5ColorE",
           "_ZNK19MixerColorConverter20getRGBFromColorIndexEi")
THIS, MIXER, TABLE, CONVERTER, NUM, COLOR = (0x41000000 + i * 0x1000 for i in range(6))
STACK, STOP, RM_SLOT = 0x50000800, 0x70000F00, 0x70000000
INPUTS = [
    [0, 1, 1, 1, 0xFF573412, 3.25], [1, 0, 1, 1, 0xFF123456, 2.5],
    [1, 1, 0, 1, 0xFF0000FF, .75], [1, 1, 1, 0, 0xFF4E4931, -2.25],
    [1, 1, 1, 1, 0x01A3C721, 7.75], [1, 1, 1, 1, 0xFFA31842, -3.25],
    [1, 1, 1, 1, 0xFF0000FF, 1.0], [1, 1, 1, 1, 0xFF123456, 13.75],
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def bits(value):
    return struct.unpack("<I", struct.pack("<f", value))[0]


def number(word):
    return struct.unpack("<f", struct.pack("<I", word))[0]


def exact(elf, name):
    sym, = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    sec = elf.get_section(sym["st_shndx"])
    addr, size = sym["st_value"], sym["st_size"]
    offset = addr - sec["sh_addr"]
    assert 0 <= offset < offset + size <= sec["sh_size"]
    data = sec.data()[offset:offset + size]
    return data, {"mangled": name, "address": addr, "size": size, "section": sym["st_shndx"],
                  "sha256": sha(data), "file_offset": sec["sh_offset"] + offset}


def edges(data, addr):
    return [int(i.op_str[1:], 0) for i in Cs(CS_ARCH_ARM, CS_MODE_ARM).disasm(data, addr)
            if i.mnemonic in ("bl", "b") and not addr <= int(i.op_str[1:], 0) < addr + len(data)]


def prepare(elf, target, context, role):
    archives = {}
    def add(label, name):
        data, info = exact(elf, name)
        archives[label] = (data, info)
        return info["address"]
    body = add("target", target["mangled"])
    info = archives["target"][1]
    assert all(info[k] == target[k] for k in ("address", "size", "section"))
    raw, = (r for r in context["bodies"].values() if r["address"] == body)
    assert (raw["bytes_sha256"], raw["file_offset"]) == (info["sha256"], info["file_offset"])
    getter = add("mappableGetter", "_ZNK8Presonus13MappableMixer17getColorConverterEv")
    channel_vt = add("channelVtable", "_ZTVN8Presonus13SLChannelBaseE")
    numeric_vt = add("numericVtable", "_ZTVN4Core8Portable12NumericParamE")
    symbols = elf.get_section_by_name(".symtab")

    def address(name):
        item, = symbols.get_symbol_by_name(name)
        return item["st_value"]
    color_property = address("_ZNK8Presonus13SLChannelBase17getColorParameterEv")
    color_get = address("_ZNK4Core8Portable10ColorParam8getColorEv")
    color_set = address("_ZN4Core8Portable10ColorParam8setColorEjb")
    numeric_get = address("_ZNK4Core8Portable12NumericParam8getValueEv")
    numeric_set = address("_ZN4Core8Portable12NumericParam8setValueEfb")
    assert struct.unpack_from("<I", archives["channelVtable"][0], 8 + 0x40)[0] == color_property
    assert struct.unpack_from("<I", archives["numericVtable"][0], 8 + 0x44)[0] == numeric_get
    assert struct.unpack_from("<I", archives["numericVtable"][0], 8 + 0x58)[0] == numeric_set
    virtual = 8 if UP else 12
    name = PALETTE[0 if UP else 1]
    if role == "client":
        palette = address(name)
        palette_vt = add("paletteVtable", "_ZTV19MixerColorConverter")
        assert struct.unpack_from("<I", archives["paletteVtable"][0], 8 + virtual)[0] == palette
    else:
        # The server defines the caller's typed slot without a concrete converter.
        palette = RM_SLOT
        palette_vt = TABLE
    conversion = address("__floatsisf" if UP else "__fixsfsi")
    if UP:
        color = add("channelColor", "_ZNK8Presonus13SLChannelBase8getColorEv")
        assert edges(archives["channelColor"][0], color) == [color_get]
        assert edges(archives["target"][0], body) == [getter, color, conversion]
    else:
        assert edges(archives["target"][0], body) == [getter, conversion, color_set]
    slots = {"color_property": color_property, "color_get": color_get, "color_set": color_set,
             "numeric_get": numeric_get, "numeric_set": numeric_set, "palette": palette,
             "conversion": conversion}
    rows = {"channel_vt": channel_vt + 8, "numeric_vt": numeric_vt + 8,
            "palette_vt": palette_vt + 8, "palette_slot": virtual}
    return archives, slots, rows


def replay(archives, slots, rows, inputs, result, role):
    owner, numeric, converter, color, color_word, initial = inputs
    m = uc.Uc(uc.UC_ARCH_ARM, uc.UC_MODE_ARM)
    pages = {THIS, MIXER, TABLE, CONVERTER, NUM, COLOR, STACK & ~4095, STOP & ~4095}
    pages.update(address & ~4095 for address in slots.values())
    for data, row in archives.values():
        address = row["address"]
        pages.update(range(address & ~4095, (address + len(data) + 4095) & ~4095, 4096))
    for page in sorted(pages):
        m.mem_map(page, 4096)
    for data, row in archives.values():
        m.mem_write(row["address"], data)
    def put(addr, word):
        m.mem_write(addr, struct.pack("<I", word & 0xFFFFFFFF))
    for addr, word in (
        (THIS, rows["channel_vt"]), (THIS + 0x1D8, MIXER if owner else 0),
        (THIS + 0x1D4, NUM if numeric else 0), (MIXER + 0x24, CONVERTER if converter else 0),
        (NUM, rows["numeric_vt"]), (CONVERTER, rows["palette_vt"]),
    ):
        put(addr, word)
    if role == "server":
        put(rows["palette_vt"] + rows["palette_slot"], slots["palette"])
    observed = [initial, color_word, 0, 0]
    events, writes = [], []
    code_labels = ("target", "mappableGetter", "channelColor") if UP else ("target", "mappableGetter")
    ranges = {name: archives[name][1] for name in code_labels}
    handlers = {v: k for k, v in slots.items()}

    def hook(machine, pc, _size, _opaque):
        for label, row in ranges.items():
            if row["address"] <= pc < row["address"] + row["size"]:
                if pc == row["address"]:
                    events.append(label)
                return
        who = handlers[pc]
        r0, r1, r2 = (machine.reg_read(reg) for reg in (arm.UC_ARM_REG_R0, arm.UC_ARM_REG_R1, arm.UC_ARM_REG_R2))
        events.append(who)
        if who == "color_property":
            assert r0 == THIS
            ret = COLOR if color else 0
        elif who == "color_get":
            assert r0 == COLOR
            ret = color_word
        elif who == "numeric_get":
            assert r0 == NUM
            ret = bits(initial)
        elif who == "palette":
            assert r0 == CONVERTER
            if UP:
                assert int.from_bytes(machine.mem_read(r1, 4), "little") == (color_word if color else 0xFF000000)
            else:
                assert r1 == (int(initial) & 0xFFFFFFFF)
            ret = result
        elif who == "conversion":
            assert r0 == (result if UP else bits(initial))
            ret = bits(result) if UP else int(number(r0)) & 0xFFFFFFFF
        elif who == "numeric_set":
            assert UP and (r0, r1, r2) == (NUM, bits(result), 1)
            observed[0] = number(r1)
            observed[2] = int(initial != observed[0])
            ret = r0
        else:
            assert not UP and (r0, r1, r2) == (COLOR, result, 1)
            observed[1] = r1
            observed[3] = int(color_word != r1)
            ret = r0
        machine.reg_write(arm.UC_ARM_REG_R0, ret)
        machine.reg_write(arm.UC_ARM_REG_PC, machine.reg_read(arm.UC_ARM_REG_LR))

    def write(_machine, _kind, address, size, value, _opaque):
        if not (STACK & ~4095) <= address < STACK:
            writes.append([address, size, value])

    m.hook_add(uc.UC_HOOK_CODE, hook)
    m.hook_add(uc.UC_HOOK_MEM_WRITE, write)
    for reg, val in ((arm.UC_ARM_REG_R0, THIS), (arm.UC_ARM_REG_SP, STACK), (arm.UC_ARM_REG_LR, STOP)):
        m.reg_write(reg, val)
    m.emu_start(ranges["target"]["address"], STOP, count=300)
    assert (m.reg_read(arm.UC_ARM_REG_PC), m.reg_read(arm.UC_ARM_REG_SP)) == (STOP, STACK)
    assert not writes
    assert ("mappableGetter" in events) == bool(owner and numeric)
    assert ("palette" in events) == bool(owner and numeric and converter)
    assert (("numeric_set" if UP else "color_set") in events) == bool(
        owner and numeric and converter and (UP or color))
    return {"inputs": inputs, "independent_palette_output": result, "output": observed,
            "native_application_and_provider_events": events, "nonstack_writes": writes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("client", "server", "packet", "basis"):
        parser.add_argument("--" + name, required=True, type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", type=Path)
    group.add_argument("--check", type=Path)
    args = parser.parse_args()
    request = json.loads((args.packet / "request.json").read_text())
    context = json.loads((args.packet / "native-context.json").read_text())
    basis = json.loads(args.basis.read_text())
    assert [row["inputs"] for row in basis] == INPUTS
    originals = []
    for target in request["targets"]:
        role = target["role"]
        path = getattr(args, role)
        elf_hash = sha(path.read_bytes())
        assert elf_hash == target["original_elf_sha256"]
        with path.open("rb") as stream:
            elf = ELFFile(stream)
            assert elf["e_machine"] == "EM_ARM" and elf.little_endian
            bound, handlers, slots = prepare(elf, target, context, role)
        ranges = {name: r for name, (_, r) in bound.items()}
        originals.append({"role": role, "elf_sha256": elf_hash, "range": ranges["target"],
                          "verified_app_and_table_ranges": ranges, "modeled_addresses": handlers,
                          "cases": [replay(bound, handlers, slots, row["inputs"], row["output"], role)
                                    for row in basis]})
    result = {"task": TASK, "unicorn": uc.__version__, "palette_basis_sha256": sha(args.basis.read_bytes()),
              "originals": originals}
    if args.write:
        args.write.write_text(json.dumps(result, indent=2) + "\n")
    else:
        assert result == json.loads(args.check.read_text())
    print(sum(len(row["cases"]) for row in originals), "exact ARM application cases")


if __name__ == "__main__":
    main()
