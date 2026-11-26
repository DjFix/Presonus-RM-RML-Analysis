"""Run the sealed ARM bodies with an offline allocation boundary."""

import argparse
import hashlib
import json
from pathlib import Path
import struct

import elftools
import unicorn
from elftools.elf.elffile import ELFFile
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP

PREFIX = "_ZN8Presonus7Surface19MuteGroupsComponent"
CTOR = "_ZN8Presonus10DelayTimerC1Ef"
DTOR = "_ZN8Presonus10DelayTimerD1Ev"
BASE_CTOR = "_ZN4Core8Portable9ComponentC2EPKc"
BASE_DTOR = "_ZN4Core8Portable9ComponentD2Ev"
VECTOR_DTOR = "_ZN4Core6VectorIPN8Presonus10DelayTimerEED1Ev"
RESIZE = "_ZN4Core6VectorIPN8Presonus10DelayTimerEE6resizeEi"
PARAMS_CTOR = "_ZN4Core8Portable9ParamListC1Ev"
RECEIVER, STACK, STOP = 0x40000000, 0x41001000, 0x42000000
PAGE = 0x1000

BOUNDARIES = {
    0xa90c: "_Znwj",
    0xac60: "_Znaj",
    0xad5c: "_ZdlPv",
    0xaec4: "_ZdaPv",
    0xb02c: "strlen",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def range_for(elf, name):
    symbol, = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    section_index = symbol["st_shndx"]
    section = elf.get_section(section_index)
    address, size = symbol["st_value"], symbol["st_size"]
    relative = address - section["sh_addr"]
    assert section.name == ".text" and symbol["st_info"]["type"] == "STT_FUNC"
    assert 0 <= relative <= section["sh_size"] - size
    data = section.data()[relative:relative + size]
    return dict(mangled=name, address=address, size=size, section=section_index,
                file_offset=section["sh_offset"] + relative,
                range_sha256=sha(data)), data


def read_u32(cpu, where):
    return struct.unpack("<I", cpu.mem_read(where, 4))[0]


def timer_state(cpu, where):
    start, duration, elapsed, reciprocal, running = struct.unpack(
        "<qqqIB3x", cpu.mem_read(where, 32))
    return [start, duration, elapsed, reciprocal, running]


def generate(packet):
    spec, = json.loads(packet.read_text())["originals"]
    original = spec["original"]
    elf_path = Path(original["elf_path"])
    assert sha(elf_path.read_bytes()) == original["elf"]
    with elf_path.open("rb") as stream:
        elf = ELFFile(stream)
        assert elf.little_endian and elf["e_machine"] == "EM_ARM"
        names = [PREFIX + v + "Ev" for v in ("C1", "C2", "D0", "D1", "D2")]
        names += [CTOR, DTOR, BASE_CTOR, BASE_DTOR, VECTOR_DTOR, RESIZE, PARAMS_CTOR]
        ranges = {name: range_for(elf, name)[0] for name in names}
        entry, data = range_for(elf, original["mangled"])
        assert all(original[key] == value for key, value in entry.items())
        assert data.hex() == original["range_hex"]
        dynsym = elf.get_section_by_name(".dynsym")
        relplt = elf.get_section_by_name(".rel.plt")
        plt = elf.get_section_by_name(".plt")["sh_addr"]
        bindings = {
            plt + 20 + 12 * index: dynsym.get_symbol(row["r_info_sym"]).name
            for index, row in enumerate(relplt.iter_relocations())
        }
        assert all(bindings[address] == name for address, name in BOUNDARIES.items())
        segments = [(p["p_vaddr"], p["p_memsz"], p.data())
                    for p in elf.iter_segments() if p["p_type"] == "PT_LOAD"]

    cpu = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
    start = min(address for address, _, _ in segments) & ~(PAGE - 1)
    end = max(address + size for address, size, _ in segments)
    cpu.mem_map(start, (end - start + PAGE - 1) & ~(PAGE - 1))
    for address, _, data in segments:
        cpu.mem_write(address, data)
    cpu.mem_map(STACK - PAGE, PAGE)
    cpu.mem_map(RECEIVER, PAGE)
    cpu.mem_write(RECEIVER, b"\x5a" * PAGE)
    live = {RECEIVER: "_Znwj"}
    group = []
    timer_inputs = []
    events = []
    history = []
    entries = {row["address"]: name for name, row in ranges.items()}
    next_address = RECEIVER + PAGE
    active = None
    backing = None
    trace = []

    def label(ptr):
        if ptr == RECEIVER:
            return "receiver"
        if ptr == RECEIVER + 0x98:
            return "refresh"
        return str(group.index(ptr))

    def observe(uc, address, _size, _data):
        nonlocal next_address
        r0, r1 = (uc.reg_read(reg) for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1))
        if active["address"] <= address < active["address"] + active["size"]:
            trace.append(address)
        name = entries.get(address)
        if name == BASE_CTOR:
            assert (r0, bytes(uc.mem_read(r1, 1))) == (RECEIVER, b"\0")
        elif name == PARAMS_CTOR:
            assert r0 == RECEIVER + 0x28
        elif name == CTOR:
            if r0 != RECEIVER + 0x98:
                assert live[r0] == "_Znwj"
                group.append(r0)
            timer_inputs.append([label(r0), r1])
        elif name == DTOR:
            events.append("destroy:" + label(r0))
        elif name == VECTOR_DTOR:
            assert r0 == RECEIVER + 0x84
            history.append(["vector-destructor", r0])
        elif name == BASE_DTOR:
            assert r0 == RECEIVER
            events.append("base")
        if address not in BOUNDARIES:
            return
        boundary = BOUNDARIES[address]
        history.append([boundary, r0])
        if boundary in ("_Znwj", "_Znaj"):
            assert 0 < r0 <= PAGE
            uc.mem_map(next_address, PAGE)
            live[next_address] = boundary
            uc.reg_write(UC_ARM_REG_R0, next_address)
            next_address += PAGE
        elif boundary in ("_ZdlPv", "_ZdaPv"):
            allocator = "_Znwj" if boundary == "_ZdlPv" else "_Znaj"
            assert live.pop(r0) == allocator
            if boundary == "_ZdlPv":
                events.append("free:" + label(r0))
            elif r0 == backing:
                events.append("free:backing")
            uc.mem_unmap(r0, PAGE)
            try:
                uc.mem_read(r0, 1)
            except unicorn.UcError as error:
                assert error.errno == unicorn.UC_ERR_READ_UNMAPPED
            else:
                raise AssertionError("Allocation is still mapped")
        else:
            assert boundary == "strlen" and bytes(uc.mem_read(r0, 1)) == b"\0"
            uc.reg_write(UC_ARM_REG_R0, 0)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    cpu.hook_add(unicorn.UC_HOOK_CODE, observe)

    def run(row):
        nonlocal active
        active = row
        trace.clear()
        for reg, value in ((UC_ARM_REG_R0, RECEIVER), (UC_ARM_REG_LR, STOP),
                           (UC_ARM_REG_SP, STACK)):
            cpu.reg_write(reg, value)
        cpu.emu_start(row["address"], STOP, count=20000)
        assert (cpu.reg_read(UC_ARM_REG_PC), cpu.reg_read(UC_ARM_REG_SP)) == (STOP, STACK)
        assert trace and trace[0] == row["address"]
        return list(trace)

    variant = entry["mangled"][-4:-2]
    constructor = variant if variant[0] == "C" else ("C2" if variant == "D2" else "C1")
    ctor_trace = run(ranges[PREFIX + constructor + "Ev"])
    assert len(group) == read_u32(cpu, RECEIVER + 0x8c) == 8
    backing = read_u32(cpu, RECEIVER + 0x88)
    assert [read_u32(cpu, backing + i * 4) for i in range(8)] == group
    states = [timer_state(cpu, RECEIVER + 0x98)] + [timer_state(cpu, p) for p in group]
    feedback = cpu.mem_read(RECEIVER + 0x28, 1)[0]
    uncoupled = read_u32(cpu, RECEIVER + 0xb8) == 0
    assert feedback == 1 and uncoupled
    assert bytes(cpu.mem_read(RECEIVER + 8, 1)) == b"\0"
    output = dict(timer_inputs=timer_inputs, states=states, feedback=feedback, empty_name=True)
    target_trace = ctor_trace
    if variant[0] == "D":
        history.clear()
        target_trace = run(entry)
        vector_drop = ["_ZdaPv", backing]
        assert ["vector-destructor", RECEIVER + 0x84] in history and vector_drop in history
        assert set(live) == (set() if variant == "D0" else {RECEIVER})
        assert events == sum(([f"destroy:{i}", f"free:{i}"] for i in range(8)), []) + (
            ["destroy:refresh", "free:backing", "base"] + (["free:receiver"] if variant == "D0" else []))
        output["events"] = events
    return dict(original=entry, elf_sha256=original["elf"], constructor=constructor,
                dependencies=ranges, plt_boundaries=BOUNDARIES, output=output,
                target_trace=target_trace, setup_trace=ctor_trace,
                boundary_trace=history, native_null_provider=uncoupled,
                feedback_binding="Component's ParamList at +0x28; ParamList constructor zeroes its first byte",
                unicorn_version=unicorn.__version__, pyelftools_version=elftools.__version__)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--out", type=Path)
    group.add_argument("--verify", type=Path)
    args = parser.parse_args()
    fixture = json.loads(json.dumps(generate(args.packet)))
    if args.out is not None:
        with args.out.open("x") as handle:
            handle.write(json.dumps(fixture, indent=2) + "\n")
    else:
        assert fixture == json.loads(args.verify.read_text())
        print("One exact native lifecycle case reproduced")


if __name__ == "__main__":
    main()
