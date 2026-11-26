"""Execute the ARM roster cleanup and real destructor bodies in bounded memory."""

import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
PACKET = ROOT / "temp/recovery-work/sqlite-issued/packet" / HERE.name / "CONTEXT.json"
TARGETS = {
    "caller": "_ZN8Presonus16MeterManagerBaseD2Ev",
    "base": "_ZN8Presonus9MeterMaidD0Ev",
    "derived": "_ZN8Presonus11GRMeterMaidD0Ev",
    "baseTable": "_ZTVN8Presonus9MeterMaidE",
    "derivedTable": "_ZTVN8Presonus11GRMeterMaidE",
    "resize": "_ZN4Core6VectorIPN8Presonus9MeterMaidEE6resizeEi",
    "delete": "_ZdlPv@@GLIBCXX_3.4",
    "deleteArray": "_ZdaPv@@GLIBCXX_3.4",
}
CASES = (("", 0), ("", 8), ("0", 8), ("b", 8), ("g", 8), ("b0gg0b", 8), ("0gb", 8))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def observe():
    original = json.loads(PACKET.read_text())["originals"][0]["original"]
    data = (ROOT / original["elf_path"]).read_bytes()
    assert sha(data) == original["elf"]
    elf = ELFFile(io.BytesIO(data))
    assert elf["e_machine"] == "EM_ARM" and elf.little_endian
    symbols = elf.get_section_by_name(".symtab")

    def bind(name):
        entries = symbols.get_symbol_by_name(name)
        assert len(entries) == 1, name
        entry = entries[0]
        index = entry["st_shndx"]
        address, size = entry["st_value"], entry["st_size"]
        if index == "SHN_UNDEF":
            assert name in (TARGETS["delete"], TARGETS["deleteArray"])
            index = elf.get_section_index(".plt")
            size = 12
        section = elf.get_section(index)
        delta = address - section["sh_addr"]
        assert size and 0 <= delta <= section["sh_size"] - size
        offset = section["sh_offset"] + delta
        body = data[offset:offset + size]
        return {"mangled": name, "address": address, "size": size, "section": index,
                "section_name": section.name, "file_offset": offset,
                "range_sha256": sha(body), "range_hex": body.hex()}

    refs = {key: bind(name) for key, name in TARGETS.items()}
    entry = bind(original["mangled"])
    assert all(original[key] == value for key, value in entry.items())
    receiver, vector, backing, stack, stop, heap = (
        0x800000, 0x810000, 0x820000, 0x901000, 0xA00000, 0xB00000,
    )
    starts = {refs[key]["address"]: key for key in ("base", "derived", "resize", "delete", "deleteArray")}
    allowed = [entry, *(refs[key] for key in ("base", "derived", "resize"))]
    cases = []
    for values, capacity in CASES:
        cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        cpu.mem_map(0, heap)
        for segment in elf.iter_segments():
            if segment["p_type"] == "PT_LOAD":
                cpu.mem_write(segment["p_vaddr"], segment.data())

        def load(addr):
            return struct.unpack("<I", cpu.mem_read(addr, 4))[0]

        def store(addr, value):
            cpu.mem_write(addr, struct.pack("<I", value))

        base = refs["baseTable"]["address"] + 8
        derived = refs["derivedTable"]["address"] + 8
        assert load(base + 4) == refs["base"]["address"]
        assert load(derived + 4) == refs["derived"]["address"]
        tables = {"b": base, "g": derived}
        store(vector + 4, backing if capacity else 0)
        store(vector + 8, len(values))
        store(vector + 12, capacity)
        store(vector + 16, 4)
        live = {}
        for index, variant in enumerate(values, 1):
            if variant == "0":
                continue
            pointer = heap + 4096 * index
            cpu.mem_map(pointer, 4096)
            store(pointer, tables[variant])
            store(backing + 4 * (index - 1), pointer)
            live[pointer] = (index, variant)

        events = []
        dispatched = []
        resize_calls = []

        def instruction(cpu, pc, width, _):
            edge = starts.get(pc)
            r0, r1 = cpu.reg_read(UC_ARM_REG_R0), cpu.reg_read(UC_ARM_REG_R1)
            if edge in ("base", "derived"):
                index, variant = live[r0]
                assert edge == ("base" if variant == "b" else "derived")
                assert load(vector + 8) == len(values)
                assert load(r0) == tables[variant]
                dispatched.append(index)
                return
            if edge == "resize":
                assert r0 == vector and r1 == 0 and not live
                resize_calls.append(load(vector + 8))
                return
            if edge == "delete":
                index, variant = live.pop(r0)
                assert dispatched[-1] == index
                assert load(vector + 8) == len(values)
                # The real D0 has already executed the vptr reset and reached
                # the scalar allocation boundary with the original receiver.
                literal = refs["base" if variant == "b" else "derived"]["address"] + 40
                assert load(r0) == load(literal)
                cpu.mem_unmap(r0, 4096)
                events.append(f"free:{index}")
            elif edge == "deleteArray":
                assert r0 == backing and not live and capacity
                cpu.mem_unmap(backing, 4096)
                events.append("free-array")
            else:
                assert any(ref["address"] <= pc < ref["address"] + ref["size"]
                           for ref in allowed), hex(pc)
                return
            cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))

        cpu.hook_add(UC_HOOK_CODE, instruction)
        for _ in range(2):
            for reg, value in ((UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, vector),
                               (UC_ARM_REG_SP, stack), (UC_ARM_REG_LR, stop)):
                cpu.reg_write(reg, value)
            cpu.emu_start(entry["address"], stop, count=1000)
            assert cpu.reg_read(UC_ARM_REG_PC) == stop
            assert cpu.reg_read(UC_ARM_REG_SP) == stack
            assert (load(vector + 4), load(vector + 8), load(vector + 12), load(vector + 16)) == (0, 0, 0, 4)
            events.append("clear")
        assert len(resize_calls) == 2
        cases.append({"slots": values, "capacity": capacity, "dispatch": dispatched,
                      "resize_counts": resize_calls, "events": events})
    return {"original": original, "bindings": refs, "cases": cases}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    fixture = HERE / "fixtures.json"
    observed = observe()
    result = json.dumps(observed, indent=2) + "\n"
    if args.verify:
        assert fixture.read_text() == result
    else:
        fixture.write_text(result)
    print(f"{len(observed['cases'])} ARM cases, 2 executions each")


if __name__ == "__main__":
    main()
