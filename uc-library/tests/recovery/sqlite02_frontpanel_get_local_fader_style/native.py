"""Execute the sealed ARM code against initialized local panel state."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

import unicorn
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
    UC_ARM_REG_R3, UC_ARM_REG_SP,
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PanelOracle:
    def __init__(self, firmware, context, evidence):
        original = json.loads(context.read_text())["originals"][0]["original"]
        direct = json.loads(evidence.read_text())
        self.path = firmware / original["elf_path"]
        assert digest(self.path) == original["elf"] == direct["elf_sha256"]
        self.image = ELFFile(self.path.open("rb"))
        self.symbols = self.image.get_section_by_name(".symtab")
        self.original = original
        self.proofs = []
        self.verify_range(original)
        for name in (
            "_ZNK8Presonus5Panel16ControlRegistrar9findGroupEi",
            "_ZNK8Presonus5Panel12ControlGroup2atEi",
            "_ZNK8Presonus5Panel12ControlGroup5byTagEi",
        ):
            self.verify_range(next(item for item in direct["items"]
                                   if item["mangled"] == name))
        if "getFaderStyle" in original["mangled"]:
            name = "_ZNK8Presonus5Panel7Control12getParameterEv"
            symbol = self.symbols.get_symbol_by_name(name)[0]
            section = self.image.get_section(symbol["st_shndx"])
            offset = section["sh_offset"] + symbol["st_value"] - section["sh_addr"]
            code = self.path.read_bytes()[offset:offset + symbol["st_size"]]
            self.verify_range(dict(mangled=name, address=symbol["st_value"],
                                   size=symbol["st_size"], section=symbol["st_shndx"],
                                   file_offset=offset,
                                   range_sha256=hashlib.sha256(code).hexdigest()))
        self.uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        self.uc.mem_map(0x8000, 0x500000)
        self.map_image(self.image)
        self.uc.mem_map(0x70000000, 0x20000)
        self.finish = 0x7001F000
        self.trace = []
        self.rtti = {}
        self.uc.hook_add(UC_HOOK_CODE, self.observe)
        # Initialized process-static empty sentinel. ABI guards/registration
        # belong to initialization outside this bounded local operation.
        self.word(4803728, 1)
        self.word(4803732 + 8, 4803732 + 16)
        self.word(4803732 + 12, 0)
        self.word(0x70000000 + 0x90, 0x70000100)
        self.word(0x70000100 + 0x18, 0x70000200)
        self.cast_address = None

    def verify_range(self, item):
        symbol = self.symbols.get_symbol_by_name(item["mangled"])[0]
        section_index = item["section"]
        section = self.image.get_section(section_index)
        offset = section["sh_offset"] + item["address"] - section["sh_addr"]
        assert (symbol["st_value"], symbol["st_size"], symbol["st_shndx"], offset) == (
            item["address"], item["size"], section_index, item["file_offset"])
        raw = self.path.read_bytes()[offset:offset + item["size"]]
        assert raw == section.data()[offset - section["sh_offset"]:
                                     offset - section["sh_offset"] + item["size"]]
        assert hashlib.sha256(raw).hexdigest() == item["range_sha256"]
        if "range_hex" in item:
            assert raw.hex() == item["range_hex"]
        self.proofs.append({key: item[key] for key in (
            "mangled", "address", "size", "section", "file_offset", "range_sha256")})

    def map_image(self, elf, bias=0):
        for segment in elf.iter_segments(type="PT_LOAD"):
            self.uc.mem_write(bias + segment["p_vaddr"], segment.data())

    def word(self, address, value):
        self.uc.mem_write(address, struct.pack("<I", value & 0xFFFFFFFF))

    def read_word(self, address):
        return struct.unpack("<I", self.uc.mem_read(address, 4))[0]

    def observe(self, uc, address, size, _):
        names = {582828: "findGroup", 580008: "at", 580076: "byTag",
                 587136: "getParameter", 44276: "__dynamic_cast@plt"}
        if address == self.cast_address:
            names[address] = "libstdc++::__dynamic_cast"
        if address in names:
            self.trace.append([names[address], *[uc.reg_read(reg) for reg in (
                UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)]])

    def run(self, roster):
        self.trace.clear()
        self.word(0x70000100 + 0x1C, len(roster))
        controls = {}
        for group_index, (group_id, entries) in enumerate(roster):
            group = 0x70001000 + group_index * 0x100
            self.word(0x70000200 + group_index * 4, group)
            self.word(group + 4, group_id)
            self.word(group + 8, group + 0x10)
            self.word(group + 12, len(entries))
            for index, (control_tag, kind, parameter_tag) in enumerate(entries):
                control = 0x70003000 + group_index * 0x1000 + index * 0x100
                controls[control] = 1 + 10 * group_index + index
                self.word(group + 0x10 + 4 * index, control if kind != 0 else 0)
                self.word(control + 8, control + 0x40 if parameter_tag is not None else 0)
                self.word(control + 0x18, control_tag)
                self.word(control + 0x40 + 0xC, control + 0x70)
                self.word(control + 0x70 + 4, parameter_tag or 0)
                if self.rtti and kind:
                    self.word(control, self.rtti[kind])
        state = self.uc.mem_read(0x70000000, 0x10000)
        self.uc.reg_write(UC_ARM_REG_R0, 0x70000000)
        self.uc.reg_write(UC_ARM_REG_SP, self.finish - 16)
        self.uc.reg_write(UC_ARM_REG_LR, self.finish)
        self.uc.emu_start(self.original["address"], self.finish, count=2000)
        assert self.uc.reg_read(UC_ARM_REG_PC) == self.finish
        assert self.uc.mem_read(0x70000000, 0x10000) == state
        result = self.uc.reg_read(UC_ARM_REG_R0)
        return controls[result] if self.rtti and result else result


CASES = {
    "missing-group": [(16, [(0, 1, 15)])],
    "empty-group": [(12, [])],
    "null-first": [(12, [(0, 0, None), (1, 1, 15)])],
    "unbound-first": [(12, [(0, 1, None), (1, 1, 15)])],
    "style-one": [(12, [(20, 1, 15), (0, 1, 14)])],
    "tag-14": [(12, [(0, 1, 14), (1, 1, 15)])],
    "tag-16": [(12, [(0, 1, 16)])],
    "first-group": [(16, [(0, 1, 15)]), (12, [(0, 1, 14)]),
                    (12, [(0, 1, 15)])],
}


def collect(oracle, cases):
    observations = []
    for name, roster in cases.items():
        result = oracle.run(roster)
        observations.append(dict(name=name, roster=roster, result=result,
                                 calls=list(oracle.trace)))
    return dict(elf_sha256=oracle.original["elf"], unicorn=unicorn.__version__,
                ranges=oracle.proofs, initialized_roster_memory_unchanged=True,
                cases=observations)


def cli(generate):
    parser = argparse.ArgumentParser()
    parser.add_argument("--firmware", type=Path, required=True)
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(generate(args.firmware, args.context, args.evidence), indent=2))


def generate(firmware, context, evidence):
    return collect(PanelOracle(firmware, context, evidence), CASES)


if __name__ == "__main__":
    cli(generate)
