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


TASK = 'cycle20_g04_s05'
SPECS = [
    ('9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07', 'RM/RML mixer 13731', 'server', '_ZN8Presonus5Panel9SceneBookD1Ev', 453628, 44, 'd72e74d1b922bf6365abe401522afbc47227b566c3a701c37e3084b77620a43b'),
    ('9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07', 'RM/RML mixer 13731', 'server', '_ZN8Presonus5Panel9SceneBookD0Ev', 453716, 52, '568f1f5bcc5a51ab376f3bd5a90a511e750d5b434e6fd93b43bea1fa86d97588'),
]


def observe(elf, identity, code):
    dependencies = []
    specs = [
        ("_ZN8Presonus5Panel4BookD2Ev", "f57dae7fe8bad5b6f62eaa31510940231478eb4fe4bfde28a5ebace044376514"),
        ("_ZN8Presonus5Panel4PageD0Ev", "b106d9611f334b516431649ab32d402db77fada0c34dda75a84c3d3ec0135a30"),
        ("_ZTVN8Presonus5Panel4PageE", "76dce46024d7ebe5eb85c9c9cd613a42ee81d373b90ab6bdbb7c16478914f785"),
        ("_ZTVN8Presonus5Panel9SceneBookE", "dedd9050328a2038f38448fa6e179fb6cbf2426f47c4f476311493f15fe255d2"),
    ]
    for name, expected in specs:
        check, _ = section_range(elf, name)
        assert check["range_sha256"] == expected
        dependencies.append(check)
    book, page, page_table, scene_table = dependencies
    deleting = "D0Ev" in identity["mangled"]
    _, scene_table_data = section_range(elf, scene_table["mangled"])
    assert struct.unpack_from("<I", scene_table_data, 12 if deleting else 8)[0] == identity["address"]
    cases = []
    children = [0x40600000 + j * 0x1000 for j in range(3)]
    for presence in ("-", "0", "1", "01", "101"):
        uc = app(elf)
        put(uc, RECEIVER, scene_table["address"] + 8, ARG, 0 if presence == "-" else len(presence))
        if presence != "-":
            for j, flag in enumerate(presence):
                child = children[j]
                if flag == "1":
                    uc.mem_map(child, 0x1000)
                    put(uc, child, page_table["address"] + 8)
                put(uc, ARG + 4 * j, child if flag == "1" else 0)
        events = []
        deallocations = []
        def dependency(cpu, pc):
            this = cpu.reg_read(R0)
            if pc == 0xAC10:
                assert this == RECEIVER or this in children
                cpu.mem_unmap(this, 0x1000)
                deallocations.append(this)
                events.append(["delete", this])
                ret(cpu, this)
            elif book["address"] <= pc < book["address"] + book["size"]:
                if pc == book["address"]:
                    assert this == RECEIVER
                    events.append(["book", this])
            else:
                assert page["address"] <= pc < page["address"] + page["size"]
                if pc == page["address"]:
                    assert this in children
                    events.append(["page", this])
        _, trace = call(uc, identity, hook=dependency)
        mapped = [start for start, _, _ in uc.mem_regions()]
        receiver_alive = RECEIVER in mapped
        assert receiver_alive is not deleting
        released = [str(children.index(p)) for p in deallocations if p in children]
        assert all(children[int(index)] not in mapped for index in released)
        output = f"{int(receiver_alive)} " + ("".join(released) or "-")
        cases.append(dict(input=f"{int(deleting)} {presence}", output=output,
                          executed=trace, events=events, unmapped_allocations=deallocations))
    return cases, dependencies


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
