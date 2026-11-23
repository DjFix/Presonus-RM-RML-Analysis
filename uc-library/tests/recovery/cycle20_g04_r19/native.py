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

TASK = "cycle20_g04_r19"
NAME = "_ZN8Presonus24MixerClientComponentBase12clearPresetsERN4Core6VectorIPNS_14IPresetHandler6PresetEEE"
SPECS = [
    ("304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0",
     "CS18AI surface 13840", "client", NAME, 0x5EA84, 116,
     "9cede22de56ce7676f7dfc0c7be16bc7d3a6469f87fac967e1e3fcfcc96839bc"),
    ("9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07",
     "RM/RML mixer 13731", "server", NAME, 0xFC94, 116,
     "efdf0e699d0cc1cbfea3f41cac0d7c1f5130905a4f018925bd6a31ca27a3574b"),
]
TARGETS = {"client": (0xAD5C, 0x61424), "server": (0xAC10, 0x127A8)}
CASES = [(0, "-"), (8, "-"), (8, "1"), (8, "0"), (8, "101"), (8, "010")]
RESIZE = "_ZN4Core6VectorIPN8Presonus14IPresetHandler6PresetEE6resizeEi"
RAW = [0x40500000 + 0x1000 * i for i in range(3)]
BACKING = 0x40600000


def branch(address, code):
    word, = struct.unpack("<I", code)
    assert word >> 24 == 0xEB
    displacement = (word & 0xFFFFFF) << 2
    return address + 8 + displacement - (displacement & 0x2000000) * 2


def disposed(uc, address):
    try:
        uc.mem_read(address, 1)
    except unicorn.UcError as error:
        assert error.errno == unicorn.UC_ERR_READ_UNMAPPED
    else:
        raise AssertionError(f"allocation still readable: {address:#x}")


def observe(elf, identity, code):
    start = identity["address"]
    delete, resize = TARGETS[identity["role"]]
    assert branch(start + 76, code[76:80]) == delete
    assert branch(start + 96, code[96:100]) == resize
    resize_symbol, _ = section_range(elf, RESIZE)
    assert resize_symbol["address"] == resize
    error_slot, _ = section_range(elf, "_ZN4Core11ConstVectorIPN8Presonus14IPresetHandler6PresetEE5errorE")
    assert struct.unpack("<I", code[-4:])[0] == error_slot["address"]
    ident = "_ZdlPv"
    glibcxx = [sym for sym in elf.get_section_by_name(".dynsym").get_symbol_by_name(ident)
               if sym["st_shndx"] == "SHN_UNDEF"]
    assert len(glibcxx) == 1
    cases = []
    for capacity, layout in CASES:
        uc = app(elf)
        mask = [] if layout == "-" else list(layout)
        allocated = set()
        if capacity:
            uc.mem_map(BACKING, 0x1000)
        put(uc, ARG + 4, BACKING if capacity else 0, len(mask), capacity)
        before = bytes(uc.mem_read(RECEIVER, 0x100))
        pending = []
        for slot, occupied in enumerate(mask):
            value = RAW[slot] if occupied == "1" else 0
            if value:
                uc.mem_map(value, 0x1000)
                allocated.add(value)
            put(uc, BACKING + slot * 4, value)
            pending.append(value)
        events = []

        def boundary(cpu, pc):
            value = cpu.reg_read(R0)
            if pc == delete:
                assert len(events) < len(pending) and value == pending[len(events)]
                if value:
                    assert value in allocated
                    cpu.mem_unmap(value, 0x1000)
                    events.append(str(RAW.index(value)))
                else:
                    events.append("null")
            else:
                assert pc == resize and (value, cpu.reg_read(R1)) == (ARG, 0)
                assert len(events) == len(pending)
                if get(cpu, ARG + 4):
                    cpu.mem_unmap(BACKING, 0x1000)
                    events.append("backing")
                # The modeled provider drops backing/capacity. The original app
                # emits its own separate write setting count to zero.
                put(cpu, ARG + 4, 0)
                put(cpu, ARG + 12, 0)
            ret(cpu, 0)

        _, trace = call(uc, identity, ARG, hook=boundary)
        assert start + 104 in trace
        assert (get(uc, ARG + 4), get(uc, ARG + 8), get(uc, ARG + 12)) == (0, 0, 0)
        assert bytes(uc.mem_read(RECEIVER, 0x100)) == before
        for value in allocated:
            disposed(uc, value)
        if capacity:
            disposed(uc, BACKING)
        output = " ".join(events + ["0", "0", "0"])
        cases.append(dict(input=f"{capacity} {layout}", output=output, executed=trace,
                          bounded_delete_events=events, allocations_disposed=len(allocated)))
    return cases, [resize_symbol, error_slot,
                   dict(symbol=ident, plt_address=delete, binding="undefined dynamic operator delete")]


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
