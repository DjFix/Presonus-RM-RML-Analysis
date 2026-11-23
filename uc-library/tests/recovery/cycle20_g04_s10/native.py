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


TASK = 'cycle20_g04_s10'
SPECS = [
    ('9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07', 'RM/RML mixer 13731', 'server', '_ZN8Presonus24MixerClientComponentBase14setMasterMixerEPS0_', 59584, 20, 'fb8884c5fb11fb106d0723fed8ae066bd2cb44b2e984add798c56c17fec5e286'),
    ('304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0', 'CS18AI surface 13840', 'client', '_ZN8Presonus24MixerClientComponentBase14setMasterMixerEPS0_', 382640, 20, 'fb8884c5fb11fb106d0723fed8ae066bd2cb44b2e984add798c56c17fec5e286'),
]


def observe(elf, identity, code):
    offset = 0x67C if TASK.endswith("09") else 0x678
    setter = TASK.endswith("10")
    values = (0, ARG, BUFFER, RECEIVER)
    cases = []
    for index, peer in enumerate(values):
        uc = app(elf)
        uc.mem_write(RECEIVER, b"\xA5" * 0x800)
        put(uc, RECEIVER + offset, 0x13572468 if setter else peer)
        before = bytes(uc.mem_read(RECEIVER, 0x800))
        result, trace = call(uc, identity, peer if setter else 0)
        after = bytes(uc.mem_read(RECEIVER, 0x800))
        if setter:
            actual = get(uc, RECEIVER + offset)
            assert after[:offset] == before[:offset] and after[offset+4:] == before[offset+4:]
        else:
            actual = result
            assert after == before
        cases.append(dict(input=str(index), output=str(values.index(actual)),
                          executed=trace, observed_r0=result))
    return cases, []


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
