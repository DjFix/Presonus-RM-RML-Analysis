"""Replay exact Panel element methods against bounded local receiver memory."""

import argparse
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path

import unicorn as uc
from elftools.elf.elffile import ELFFile
from unicorn import arm_const as arm

TASK = "12"
THIS, DISPLAY, TABLE, TEXT = range(0x40000000, 0x40004000, 0x1000)
STACK, STOP, VIRTUAL = 0x50000800, 0x71000F00, 0x71000000
REGS = (arm.UC_ARM_REG_R0, arm.UC_ARM_REG_R1, arm.UC_ARM_REG_R2, arm.UC_ARM_REG_R3)
ELEMENT = "_ZN8Presonus5Panel7ElementC2Eii"
OFFSCREEN = "_ZN8Presonus5Panel16OffscreenElementC2Eii"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_symbol(elf, name):
    row, = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    section = elf.get_section(row["st_shndx"])
    address, size = row["st_value"], row["st_size"]
    offset = address - section["sh_addr"]
    assert 0 <= offset <= offset + size <= section["sh_size"]
    body = section.data()[offset:offset + size]
    return body, {"mangled": name, "address": address, "size": size,
                  "section": row["st_shndx"], "file_offset": section["sh_offset"] + offset,
                  "sha256": sha(body)}


def targets(body, address):
    result = set()
    for offset in range(0, len(body), 4):
        word, = struct.unpack_from("<I", body, offset)
        if word >> 24 == 0xEB:
            imm = word & 0xFFFFFF
            result.add(address + offset + 8 + 4 * (imm - 0x1000000 if imm & 0x800000 else imm))
    return result


def replay(ranges, boundaries, values, variant):
    m = uc.Uc(uc.UC_ARCH_ARM, uc.UC_MODE_ARM)
    pages = {THIS, DISPLAY, TABLE, TEXT, STACK & ~4095, STOP & ~4095}
    pages.update(pc & ~4095 for pc in boundaries)
    for body, row in ranges:
        addr = row["address"]
        pages.update(range(addr & ~4095, (addr + len(body) + 4095) & ~4095, 4096))
    for page in sorted(pages):
        m.mem_map(page, 4096)
    for body, row in ranges:
        m.mem_write(row["address"], body)
    seed = bytes((i * 37 + 11) % 256 for i in range(4096))
    m.mem_write(THIS, seed)

    def write_words(addr, *values):
        m.mem_write(addr, struct.pack("<" + "I" * len(values),
                                     *(value & 0xFFFFFFFF for value in values)))

    def words(addr, count):
        return list(struct.unpack("<" + "i" * count, m.mem_read(addr, 4 * count)))

    input_args = [THIS, 0, 0, 0]
    if TASK == "09":
        state, flag = values
        write_words(THIS + 0x74, state)
        input_args[1] = flag
    elif TASK == "10":
        x, y, width, height, value = values
        input_args = [THIS, x, y, width]
        write_words(STACK, height, value)
    elif TASK == "11":
        x, y, width, height, flag = values
        write_words(THIS + 0x64, x, y, width, height, 1)
        write_words(DISPLAY, TABLE)
        write_words(TABLE + 0x24, VIRTUAL)
        input_args = [THIS, DISPLAY, flag, 0]
    else:
        x, y, text = values
        input_args = [THIS, x, y, TEXT]
        m.mem_write(TEXT, text.encode() + b"\0")
    before = bytes(m.mem_read(THIS, 4096))
    calls, stores = [], []
    allowed = {pc for _, row in ranges for pc in range(row["address"], row["address"] + row["size"], 4)}

    def code(u, pc, _size, _opaque):
        kind = boundaries.get(pc)
        if not kind:
            assert pc in allowed, hex(pc)
            return
        a, b, c, _ = (u.reg_read(reg) for reg in REGS)
        if kind == "memset":
            assert (a, b, c) == (THIS + 4, 0, 0x60)
            u.mem_write(a, bytes(c))
            calls.append({"provider": kind, "receiver_offset": 4, "length": c})
        elif kind == "strcpy":
            assert (a, b) == (THIS + 0x18, TEXT)
            copied = bytes(u.mem_read(TEXT, 64)).split(b"\0", 1)[0] + b"\0"
            u.mem_write(a, copied)
            calls.append({"provider": kind, "receiver_offset": 0x18, "bytes": copied.hex()})
        else:
            assert a == DISPLAY and b == THIS + 0x64
            assert words(THIS + 0x74, 1) == [0]
            calls.append({"provider": kind, "rectangle": words(b, 4)})
        u.reg_write(arm.UC_ARM_REG_PC, u.reg_read(arm.UC_ARM_REG_LR))

    def write(_u, _kind, addr, size, value, _data):
        if THIS <= addr < THIS + 4096:
            stores.append([addr - THIS, size, value])
        else:
            assert STACK - 0x800 <= addr < STACK

    m.hook_add(uc.UC_HOOK_CODE, code)
    m.hook_add(uc.UC_HOOK_MEM_WRITE, write)
    for reg, value in zip(REGS, input_args):
        m.reg_write(reg, value & 0xFFFFFFFF)
    m.reg_write(arm.UC_ARM_REG_SP, STACK)
    m.reg_write(arm.UC_ARM_REG_LR, STOP)
    m.emu_start(ranges[0][1]["address"], STOP, count=200)
    assert m.reg_read(arm.UC_ARM_REG_PC) == STOP
    args = values
    if TASK == "09":
        assert bytes(m.mem_read(THIS, 4096)) == before and not calls and not stores
        output = words(THIS + 0x74, 1)[0]
    elif TASK == "10":
        assert len(calls) == 1 and calls[0]["provider"] == "memset"
        output = words(THIS + 8, 4) + words(THIS + 0x64, 4) + words(THIS + 0x58, 1) + words(THIS + 0x74, 1)
        args = [variant, *values]
    elif TASK == "11":
        assert len(calls) == 1 and stores == [[0x74, 4, 0]]
        output = calls[0]["rectangle"] + words(THIS + 0x74, 1)
    else:
        assert [row["provider"] for row in calls] == ["memset", "strcpy"]
        assert words(THIS + 0x97C, 1) == [0]
        output = words(THIS + 8, 2) + words(THIS + 0x74, 1) + list(
            bytes(m.mem_read(THIS + 0x18, 64)).split(b"\0", 1)[0])
        args = [variant, *values]
    return {"inputs": args, "output": output, "native_observed_calls": calls,
            "native_receiver_writes": stores}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("client", "server", "packet"):
        parser.add_argument("--" + name, required=True, type=Path)
    options = parser.add_mutually_exclusive_group(required=True)
    options.add_argument("--write", type=Path)
    options.add_argument("--check", type=Path)
    args = parser.parse_args()
    request = json.loads((args.packet / "request.json").read_text())
    native = json.loads((args.packet / "native-context.json").read_text())
    domains = {
        "09": [[0, 0], [0, 1], [17, 0], [17, 1]],
        "10": [[1, 2, 3, 4, 5], [-4, 9, 21, 13, -2], [0, 0, 0, 0, 0]],
        "11": [[1, 2, 3, 4, 0], [1, 2, 3, 4, 1], [6, 3, 1, 1, 0]],
        "12": [[5, 8, ""], [-3, 16, "panel"], [0, -4, "offline label"]],
    }
    originals = []
    for target in request["targets"]:
        path = getattr(args, target["role"])
        elf_sha = sha(path.read_bytes())
        assert elf_sha == target["original_elf_sha256"]
        with path.open("rb") as stream:
            elf = ELFFile(stream)
            assert elf["e_machine"] == "EM_ARM" and elf.little_endian
            body, row = read_symbol(elf, target["mangled"])
            assert all(row[key] == target[key] for key in ("address", "size", "section"))
            old, = (entry for entry in native["bodies"].values() if entry["address"] == row["address"])
            assert (old["bytes_sha256"], old["file_offset"]) == (row["sha256"], row["file_offset"])
            ranges = [(body, row)]
            if TASK == "12":
                ranges.append(read_symbol(elf, OFFSCREEN))
            if TASK in ("10", "12"):
                ranges.append(read_symbol(elf, ELEMENT))
        boundaries = {VIRTUAL: "fillRect"} if TASK == "11" else {}
        if TASK in ("10", "12"):
            names = ("memset", "strcpy") if TASK == "12" else ("memset",)
            relocs = subprocess.check_output(["readelf", "-rW", str(path)], text=True)
            for name in names:
                line, = (line for line in relocs.splitlines()
                         if re.search(r"R_ARM_JUMP_SLOT\s+[0-9a-f]+\s+" + name + r"@GLIBC_", line))
                boundaries[int(line.split()[3], 16)] = name
            branch_sites = set().union(*(targets(data, i["address"]) for data, i in ranges))
            assert branch_sites == set(boundaries) | {i["address"] for _, i in ranges[1:]}
        variant = row["mangled"].split("Element")[-1][:2]
        originals.append({"role": target["role"], "elf_sha256": elf_sha, "range": row,
                          "provider_ranges": [r for _, r in ranges[1:]],
                          "cases": [replay(ranges, boundaries, values, variant) for values in domains[TASK]]})
    data = {"task": TASK, "unicorn": uc.__version__, "originals": originals}
    if args.write:
        args.write.write_text(json.dumps(data, indent=2) + "\n")
    else:
        assert data == json.loads(args.check.read_text())
    print(sum(len(row["cases"]) for row in originals), "exact ARM observations")


if __name__ == "__main__":
    main()
