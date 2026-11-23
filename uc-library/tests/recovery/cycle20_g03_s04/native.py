"""Replay exact ARM callback instructions against a bounded offline receiver."""
import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_ARM
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP

ELF_SHA = "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0"
BASE = 0x64674
STOP = 0x200000
RECEIVER = 0x300000
STACK = 0x410000
SUB = False
NAME = "_ZN8Presonus7Surface23AssignEditPageComponent6onShowEb"
START = 0x96E2C
WRAPPER_SHA = "21972e56826617df5ea1305979a7c661c24f10d4f6a0c79d5fb37d271d71dca0"


def collect(image):
    if hashlib.sha256(image).hexdigest() != ELF_SHA:
        raise ValueError("Unexpected source ELF")
    elf = ELFFile(io.BytesIO(image))
    text = elf.get_section_by_name(".text")
    table = elf.get_section_by_name(".symtab")
    ranges = {}
    for name, address in (
        (NAME, START),
        ("_ZN8Presonus13PageComponent6onShowEb", BASE),
        *(
            (("_ZN8Presonus7Surface22SubAssignPageComponent12updateParamsEv", 0x96EF8),)
            if SUB else (
                ("_ZN8Presonus7Surface23AssignEditPageComponent18updateAliasTargetsEv", 0x96A68),
                ("_ZN8Presonus7Surface23AssignEditPageComponent16updateVisibilityEv", 0x95CD0),
            )
        ),
    ):
        [symbol] = table.get_symbol_by_name(name)
        size = symbol["st_size"]
        offset = address - text["sh_addr"] + text["sh_offset"]
        assert symbol["st_value"] == address and elf.get_section(symbol["st_shndx"]).name == ".text"
        digest = hashlib.sha256(image[offset:offset + size]).hexdigest()
        if address == START:
            assert size == 44 and digest == WRAPPER_SHA
        if address == BASE:
            assert size == 16
        ranges[name] = dict(address=address, size=size, section=".text", file_offset=offset, sha256=digest)
    return text["sh_addr"], text.data(), ranges


def execute(text_address, text, show, visible, initial):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    text_page = text_address & ~4095
    uc.mem_map(text_page, (text_address - text_page + len(text) + 4095) & ~4095)
    uc.mem_write(text_address, text)
    uc.mem_map(STOP, 4096)
    uc.mem_map(RECEIVER, 4096)
    uc.mem_map(STACK - 4096, 8192)

    def word(at):
        return struct.unpack("<I", uc.mem_read(at, 4))[0]

    def put(at, value):
        uc.mem_write(at, struct.pack("<I", value))

    def ret(value=None):
        if value is not None:
            uc.reg_write(UC_ARM_REG_R0, value)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    put(RECEIVER + 0xD4, initial)
    uc.reg_write(UC_ARM_REG_R0, RECEIVER)
    uc.reg_write(UC_ARM_REG_R1, show)
    uc.reg_write(UC_ARM_REG_SP, STACK)
    uc.reg_write(UC_ARM_REG_LR, STOP)
    events = []
    base_instructions = []
    stopped = False

    def code(_, address, size, __):
        nonlocal stopped
        if BASE <= address < BASE + 16:
            base_instructions.append(address)
            if address == BASE:
                assert uc.reg_read(UC_ARM_REG_R0) == RECEIVER
                events.append(["page_hook", uc.reg_read(UC_ARM_REG_R1), word(RECEIVER + 0xD4)])
            return
        if START <= address < START + 44:
            return
        if address == STOP:
            stopped = True
            uc.emu_stop()
            return
        if SUB:
            if address == 0x96EF8:
                assert uc.reg_read(UC_ARM_REG_R0) == RECEIVER
                events.append(["update_params", word(RECEIVER + 0xD4)])
            if 0x96EF8 <= address < 0x96EF8 + 536:
                return
            if address == 0x681D4:
                events.append(["visibility", visible])
                ret(visible)
                return
            if address == 0x958C0:
                assert uc.reg_read(UC_ARM_REG_R0) == RECEIVER
                events.append(["build_items", word(RECEIVER + 0xD4)])
                ret()
                return
        elif address in (0x96A68, 0x95CD0):
            assert uc.reg_read(UC_ARM_REG_R0) == RECEIVER
            events.append(["update_alias_targets" if address == 0x96A68 else "update_visibility"])
            ret()
            return
        raise ValueError(f"Unexpected native boundary {address:#x}")

    def written(_, access, address, size, value, user):
        if STACK - 4096 <= address < STACK:
            return
        if SUB and address == RECEIVER + 0xD4 and size == 4:
            events.append(["offset_write", value])
            return
        raise ValueError(f"Unexpected native write {address:#x}")

    uc.hook_add(UC_HOOK_CODE, code)
    uc.hook_add(UC_HOOK_MEM_WRITE, written)
    uc.emu_start(START, STOP + 4, count=500)
    assert stopped and uc.reg_read(UC_ARM_REG_SP) == STACK
    assert base_instructions == list(range(BASE, BASE + 16, 4))
    return dict(show=show, visible=visible, initial_offset=initial, final_offset=word(RECEIVER + 0xD4),
                events=events, base_instructions=base_instructions)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", required=True, type=Path)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--write", type=Path)
    modes.add_argument("--verify", type=Path)
    args = parser.parse_args()
    address, text, ranges = collect(args.elf.read_bytes())
    data = dict(elf_sha256=ELF_SHA, ranges=ranges, cases=[
        execute(address, text, show, visible, initial)
        for show in (0, 1)
        for visible in ((0, 1) if SUB else (0,))
        for initial in ((3, 9) if SUB else (3,))
    ])
    if args.write:
        with args.write.open("x") as output:
            output.write(json.dumps(data, indent=2) + "\n")
    elif json.loads(args.verify.read_text()) != data:
        raise SystemExit("Fresh native observations differ from the sealed fixture")
    print(f"Executed {len(data['cases'])} native ARM cases")


if __name__ == "__main__":
    main()
