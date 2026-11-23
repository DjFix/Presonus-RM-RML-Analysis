"""Replay the exact original callback, keeping external provider hooks explicit."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_SP
)

ELF_SHA = "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0"
BASE = ("_ZN8Presonus13PageComponent6onShowEb", 0x64674, 16,
        "60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad")
TARGET = ('_ZN8Presonus7Surface16GeqPageComponent6onShowEb', 581304, 52, '11f1776285d9c4d9862d52a67a69832c07971de5a6796ff59a3d65fb719ec8db')
NAME, START, SIZE, _ = TARGET
MODE = "geq"
GEO_UPDATE = ("_ZN8Presonus7Surface16GeqPageComponent11updateBandsEv", 0x8DCC0, 504, None)
HALT = 0x300000
STACK = 0x410000


def ranges_for(image, elf, text):
    table = elf.get_section_by_name(".symtab")
    expected = [TARGET]
    if MODE != "page":
        expected.append(BASE)
    if MODE == "geq":
        expected.append(GEO_UPDATE)
    results = {}
    for name, address, size, digest in expected:
        [symbol] = table.get_symbol_by_name(name)
        section = elf.get_section(symbol["st_shndx"]).name
        offset = address - text["sh_addr"] + text["sh_offset"]
        actual = hashlib.sha256(image[offset:offset+size]).hexdigest()
        assert (symbol["st_value"], symbol["st_size"], section) == (address, size, ".text")
        assert digest is None or digest == actual
        results[name] = dict(address=address, size=size, section=section, file_offset=offset, sha256=actual)
    return results


def execute(text, show, visible, offset, notified, initial, receiver):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    start = text["sh_addr"]
    page = start & ~4095
    image = text.data()
    uc.mem_map(page, (start - page + len(image) + 4095) & ~4095)
    uc.mem_write(start, image)
    uc.mem_map(HALT, 4096)
    uc.mem_map(receiver, 4096)
    uc.mem_map(STACK - 4096, 8192)
    uc.mem_write(receiver, bytes(range(256)) * 16)

    def word(address):
        return struct.unpack("<I", uc.mem_read(address, 4))[0]

    def put(address, value):
        uc.mem_write(address, struct.pack("<I", value & 0xffffffff))

    def ret(value=None):
        if value is not None:
            uc.reg_write(UC_ARM_REG_R0, value)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    events = []
    base = []
    state = dict(numeric=initial)
    if MODE == "geq":
        put(receiver + 0xC8, offset)
        put(receiver + 0xCC, notified)
        put(receiver + 0xD0, receiver + 0x200)
        put(receiver + 0xD4, 1)
        put(receiver + 0x200, receiver + 0x300)
        put(receiver + 0x300, receiver + 0x400)
        put(receiver + 0x400, HALT + 0x20)
    elif MODE == "eq":
        put(receiver + 0x200, receiver + 0x300)
        put(receiver + 0x358, HALT + 0x24)

    def code(_, address, size, unused):
        if BASE[1] <= address < BASE[1] + BASE[2]:
            base.append(address)
            if address == BASE[1]:
                assert uc.reg_read(UC_ARM_REG_R0) == receiver
                assert uc.reg_read(UC_ARM_REG_R1) == show
            return
        if START <= address < START + SIZE:
            return
        if address == HALT:
            return
        if MODE == "geq":
            if address == 0x8DCC0:
                assert uc.reg_read(UC_ARM_REG_R0) == receiver
                events.append(["update_bands", word(receiver + 0xC8), word(receiver + 0xCC)])
            if address == 0x8DD38:
                # Band label/alias rendering is verified separately through the
                # actual canonical provider. Continue to the native epilogue.
                events.append(["render_bands"])
                uc.reg_write(UC_ARM_REG_PC, 0x8DE84)
                return
            if 0x8DCC0 <= address < 0x8DCC0 + 504:
                return
            if address == 0x681D4:
                events.append(["visibility", visible])
                ret(visible)
                return
            if address == HALT + 0x20:
                assert uc.reg_read(UC_ARM_REG_R0) == receiver + 0x300
                events.append(["observer", word(receiver + 0xCC)])
                ret()
                return
        if MODE == "eq":
            if address == 0x11F24C:
                assert (uc.reg_read(UC_ARM_REG_R0), uc.reg_read(UC_ARM_REG_R1)) == (receiver + 0x28, 1000)
                events.append(["by_tag", 1000])
                ret(receiver + 0x200)
                return
            if address == HALT + 0x24:
                assert uc.reg_read(UC_ARM_REG_R0) == receiver + 0x200
                assert (uc.reg_read(UC_ARM_REG_R1), uc.reg_read(UC_ARM_REG_R2)) == (0, 1)
                events.append(["set_value_bits_and_edit", 0, 1])
                state["numeric"] = 0
                ret()
                return
        raise ValueError(f"Unexpected instruction {address:#x}")

    def write(_, access, address, size, value, unused):
        if STACK - 4096 <= address < STACK:
            return
        if MODE == "geq" and address - receiver in (0xC8, 0xCC) and size == 4:
            events.append(["store", address - receiver, value & 0xffffffff])
            return
        raise ValueError(f"Unexpected native write {address:#x}")

    before = bytes(uc.mem_read(receiver, 4096))
    uc.hook_add(UC_HOOK_CODE, code)
    uc.hook_add(UC_HOOK_MEM_WRITE, write)
    uc.reg_write(UC_ARM_REG_SP, STACK)
    uc.reg_write(UC_ARM_REG_LR, HALT)
    uc.reg_write(UC_ARM_REG_R0, receiver)
    uc.reg_write(UC_ARM_REG_R1, show)
    uc.emu_start(START, HALT, count=500)
    assert uc.reg_read(UC_ARM_REG_PC) == HALT and uc.reg_read(UC_ARM_REG_SP) == STACK
    assert base == list(range(BASE[1], BASE[1] + BASE[2], 4))
    if MODE in ("page", "eq"):
        assert before == uc.mem_read(receiver, 4096)
    return dict(show=show, visible=visible, offset=offset, notified=notified,
                initial=initial, receiver=receiver, events=events, base_instructions=base,
                final_numeric=state["numeric"], final_offset=word(receiver+0xC8) if MODE == "geq" else None,
                final_notified=struct.unpack("<i", uc.mem_read(receiver+0xCC, 4))[0] if MODE == "geq" else None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", required=True, type=Path)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--write", type=Path)
    actions.add_argument("--verify", type=Path)
    args = parser.parse_args()
    image = args.elf.read_bytes()
    assert hashlib.sha256(image).hexdigest() == ELF_SHA
    elf = ELFFile(io.BytesIO(image))
    text = elf.get_section_by_name(".text")
    if MODE == "page":
        cases = [(show, visible, 0, 0, 0, 0x310000 + visible*4096)
                 for show in (0, 1) for visible in (0, 1)]
    elif MODE == "geq":
        cases = [(show, visible, offset, prior, 0, 0x310000)
                 for show in (0, 1) for visible in (0, 1) for offset, prior in ((0, 0), (5, 2))]
    else:
        cases = [(show, 0, 0, 0, initial, 0x310000)
                 for show in (0, 1) for initial in (0, 3)]
    results = dict(elf_sha256=ELF_SHA, ranges=ranges_for(image, elf, text),
                   cases=[execute(text, *case) for case in cases])
    if args.write:
        with args.write.open("x") as out:
            out.write(json.dumps(results, indent=2) + "\n")
    elif json.loads(args.verify.read_text()) != results:
        raise SystemExit("Native observations changed")
    print(f"Executed {len(cases)} original ARM callback cases")


if __name__ == "__main__":
    main()
