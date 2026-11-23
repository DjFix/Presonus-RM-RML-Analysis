"""Execute the sealed original application ranges in an offline ARM harness."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

import elftools
import unicorn
from elftools.elf.elffile import ELFFile
from unicorn import arm_const as regs

R0, R1, R2, R3 = (regs.UC_ARM_REG_R0, regs.UC_ARM_REG_R1,
                  regs.UC_ARM_REG_R2, regs.UC_ARM_REG_R3)
SP, LR, PC = regs.UC_ARM_REG_SP, regs.UC_ARM_REG_LR, regs.UC_ARM_REG_PC
RECEIVER, ARG, BUFFER, STACK, END = 0x40000000, 0x40100000, 0x40200000, 0x40301000, 0x40400000


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_elf(path, expected):
    data = path.read_bytes()
    assert sha(data) == expected
    elf = ELFFile(io.BytesIO(data))
    assert elf["e_machine"] == "EM_ARM" and elf.little_endian
    return elf


def section_range(elf, name):
    symbol, = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    sec = elf.get_section(symbol["st_shndx"])
    start = symbol["st_value"] - sec["sh_addr"]
    size = symbol["st_size"]
    assert 0 <= start <= sec["sh_size"] - size
    code = bytes(size) if sec["sh_type"] == "SHT_NOBITS" else sec.data()[start:start+size]
    return dict(mangled=name, address=symbol["st_value"], size=size,
                section=sec.name, section_index=symbol["st_shndx"],
                section_type=sec["sh_type"], kind=symbol["st_info"]["type"],
                file_offset=sec["sh_offset"] + start, range_sha256=sha(code)), code


def app(elf):
    uc = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
    uc.mem_map(0x8000, 0x600000 - 0x8000)
    for segment in elf.iter_segments():
        if segment["p_type"] == "PT_LOAD":
            uc.mem_write(segment["p_vaddr"], segment.data())
    for address in (RECEIVER, ARG, BUFFER, STACK - 0x1000):
        uc.mem_map(address, 0x1000)
    return uc


def put(uc, address, *words):
    uc.mem_write(address, struct.pack(f"<{len(words)}I", *words))


def get(uc, address):
    return struct.unpack("<I", uc.mem_read(address, 4))[0]


def call(uc, identity, second=0, third=0, allowed=(), hook=None):
    trace = []
    def execute(cpu, pc, size, _):
        if identity["address"] <= pc < identity["address"] + identity["size"]:
            trace.append(pc)
        elif not any(start <= pc < start + size for start, size in allowed):
            assert hook is not None, hex(pc)
            hook(cpu, pc)
    uc.hook_add(unicorn.UC_HOOK_CODE, execute)
    for reg, value in ((SP, STACK), (LR, END), (R0, RECEIVER), (R1, second), (R2, third)):
        uc.reg_write(reg, value & 0xFFFFFFFF)
    uc.emu_start(identity["address"], END, count=700)
    assert (uc.reg_read(PC), uc.reg_read(SP)) == (END, STACK)
    return uc.reg_read(R0), trace


def ret(uc, value):
    uc.reg_write(R0, value & 0xFFFFFFFF)
    uc.reg_write(PC, uc.reg_read(LR))


def row(elf, spec):
    sha256, firmware, role, mangled, address, size, body = spec
    identity, code = section_range(elf, mangled)
    assert (identity["address"], identity["size"], identity["range_sha256"]) == (
        address, size, body)
    assert identity["section"] == ".text" and identity["kind"] == "STT_FUNC"
    return {**identity, "elf_sha256": sha256, "firmware": firmware, "role": role}, code


TASK = 'cycle20_g04_s18'
SPECS = [
    ('304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0', 'CS18AI surface 13840', 'client', '_ZNK8Presonus24MixerClientComponentBase9getPresetENS_14IPresetHandler10PresetTypeEiPKc', 383520, 92, '2afde4d21461cd4d982d808d18db2dfdafec438b96f50032fdcf8639818d3e04'),
    ('9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07', 'RM/RML mixer 13731', 'server', '_ZNK8Presonus24MixerClientComponentBase9getPresetENS_14IPresetHandler10PresetTypeEiPKc', 60464, 92, '6020aca845b84b769a5913093d9ddba0f5bdb9dec7579062b5de0a59ebb1bf14'),
]


CASES = [
    (0, 0, 0, 0), (0, -1, 0, 1), (1, -3, 3, 0), (1, 0, 3, 1),
    (2, 0, 1, 2), (3, 1, 2, 0), (4, 1, 3, 1), (5, 0, 1, 2),
    (6, 2, 2, 0), (7, 3, 3, 1), (8, 2, 3, 2), (8, 0, 0, 0),
    (9, 0, 3, 1), (255, 0, 3, 2), (2147483647, -1, 3, 0),
]
PRESET_ERROR = "_ZN4Core11ConstVectorIPN8Presonus14IPresetHandler6PresetEE5errorE"
PRESET_POINTERS = [0, 0x40500100, 0x40500300, 0x40600000]


def observe(elf, identity, code):
    count_only = TASK.endswith("17")
    dependencies = []
    if not count_only:
        fallback, _ = section_range(elf, PRESET_ERROR)
        assert fallback["size"] == 4 and fallback["section_type"] == "SHT_NOBITS"
        assert struct.unpack("<I", code[-4:])[0] == fallback["address"]
        dependencies.append(fallback)
    results = []
    for preset_type, index, present, label_state in CASES:
        uc = app(elf)
        roster = BUFFER + 0x100
        put(uc, roster, PRESET_POINTERS[1], 0, PRESET_POINTERS[2])
        uc.mem_write(ARG, b"ignored local label\0")
        label = (0, ARG, ARG + len(b"ignored local label"))[label_state]
        if preset_type <= 8:
            put(uc, RECEIVER + 0x698 + 20 * preset_type, roster, present)
        original_state = bytes(uc.mem_read(RECEIVER, 0x800))
        original_roster = bytes(uc.mem_read(roster, 12))
        if not count_only:
            put(uc, fallback["address"], PRESET_POINTERS[-1])
            uc.reg_write(R3, label)
        result, trace = call(uc, identity, preset_type, label if count_only else index)
        assert bytes(uc.mem_read(RECEIVER, 0x800)) == original_state
        assert bytes(uc.mem_read(roster, 12)) == original_roster
        output = result if count_only else PRESET_POINTERS.index(result)
        results.append(dict(input=f"{preset_type} {index} {present} {label_state}",
                            output=str(output), executed=trace))
    return results, dependencies


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rm", type=Path, required=True)
    parser.add_argument("--cs18", type=Path, required=True)
    output = parser.add_mutually_exclusive_group(required=True)
    output.add_argument("--out", type=Path)
    output.add_argument("--verify", type=Path)
    args = parser.parse_args()
    results = []
    for spec in SPECS:
        sha256, _, role, *_ = spec
        elf = load_elf(args.rm if role == "server" else args.cs18, sha256)
        identity, code = row(elf, spec)
        cases, dependencies = observe(elf, identity, code)
        results.append(dict(original=identity, cases=cases, dependencies=dependencies))
    fixture = dict(task=TASK, originals=results, unicorn_version=unicorn.__version__,
                   pyelftools_version=elftools.__version__)
    if args.out:
        with args.out.open("x") as stream:
            json.dump(fixture, stream, indent=2)
            stream.write("\n")
    else:
        assert fixture == json.loads(args.verify.read_text())
        print(sum(len(item["cases"]) for item in results), "exact original cases reproduced")


if __name__ == "__main__":
    main()
