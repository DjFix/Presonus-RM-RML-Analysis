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


TASK = 'cycle20_g04_s16'
SPECS = [
    ('304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0', 'CS18AI surface 13840', 'client', '_ZNK8Presonus24MixerClientComponentBase22getSuggestedPresetNameENS_14IPresetHandler10PresetTypeERN4Core13CStringBufferILi128EEE', 385036, 152, 'a32509d60bac427cfa830df4a145dffc520481b3963556c2e0e3d24bfd84f2be'),
    ('9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07', 'RM/RML mixer 13731', 'server', '_ZNK8Presonus24MixerClientComponentBase22getSuggestedPresetNameENS_14IPresetHandler10PresetTypeERN4Core13CStringBufferILi128EEE', 61980, 152, '955672e6d79fdb0b3f9cbd9670789c3bc0209f0950c04cc31a0948c6e03449ba'),
]


def cstr(uc, address):
    return bytes(uc.mem_read(address, 128)).split(b"\0", 1)[0]


def observe(elf, identity, code):
    translate = TASK.endswith("14")
    table_address = struct.unpack("<I", code[-4:])[0]
    memory = app(elf)
    labels = []
    for index in range(16):
        string = get(memory, table_address + 8 * index)
        if not string:
            break
        labels.append([cstr(memory, string).decode("ascii"), get(memory, table_address+8*index+4)])
    assert len(labels) == 7
    if identity["role"] == "client":
        helpers = {0xB0F8: "strcmp", 0xB02C: "strlen", 0xB170: "strncpy"}
    else:
        helpers = {0xAF70: "strcmp", 0xAE98: "strlen", 0xAFE8: "strncpy"}
    values = [None, "", *(name for name, _ in labels), "Scene", "not-a-type"] if translate else [
        -1, *(code for _, code in labels), 7, 255, 2147483647]
    cases = []
    for value in values:
        uc = app(elf)
        uc.mem_write(BUFFER, b"\x7D" * 256)
        if translate and value is not None:
            uc.mem_write(ARG, value.encode("ascii") + b"\0")
        events = []
        def provider(cpu, pc):
            operation = helpers[pc]
            events.append(operation)
            a, b, n = (cpu.reg_read(reg) for reg in (R0, R1, R2))
            if operation == "strcmp":
                left, right = (cstr(cpu, address) for address in (a, b))
                ret(cpu, (left > right) - (left < right))
            elif operation == "strlen":
                ret(cpu, len(cstr(cpu, a)))
            else:
                assert a == BUFFER and 0 <= n <= 127
                cpu.mem_write(a, cstr(cpu, b)[:n].ljust(n, b"\0"))
                ret(cpu, a)
        argument = (ARG if value is not None else 0) if translate else value
        result, trace = call(uc, identity, argument, BUFFER, hook=provider)
        if translate:
            inputs = "-" if value is None else ":" + value
            output = str(result)
        else:
            inputs = str(value)
            actual = bytes(uc.mem_read(BUFFER, 256))
            assert actual[128:] == b"\x7D" * 128
            output = actual[:128].hex()
        cases.append(dict(input=inputs, output=output, executed=trace, providers=events))
    return cases, [dict(address=table_address, labels=labels)]


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
