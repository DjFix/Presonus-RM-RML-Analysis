"""Execute exact application ranges and their called ELF code with allocator boundary hooks."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

import unicorn
from elftools.elf.elffile import ELFFile
from unicorn.arm_const import (
    UC_ARM_REG_LR,
    UC_ARM_REG_PC,
    UC_ARM_REG_R0,
    UC_ARM_REG_R1,
    UC_ARM_REG_R2,
    UC_ARM_REG_SP,
)

TASK_PREFIX = "sqlite02_midiendpointregistry_"
TASKS = ("complete_construct", "base_construct", "complete_destroy",
         "base_destroy", "has_listeners", "remove_listener")
ROSTERS = (0x24, 0x38, 0x4C)
OBJECT = 0x600000
STACK = 0x610000
END = 0x620000
BORROWED = 0x630000
ALLOCATIONS = 0x700000

def words(values):
    return struct.pack("<" + "I" * len(values), *values)

def digest(data):
    return hashlib.sha256(data).hexdigest()

class Original:
    def __init__(self, firmware_root, record):
        self.record = record
        self.raw = (firmware_root / record["elf_path"]).read_bytes()
        assert digest(self.raw) == record["elf"]
        self.elf = ELFFile(io.BytesIO(self.raw))
        self.symbols = self.elf.get_section_by_name(".symtab")
        self.boundaries = {}
        for name, version in (("_Znaj", "GLIBCXX_3.4"), ("_ZdaPv", "GLIBCXX_3.4"),
                              ("memset", "GLIBC_2.4")):
            self.boundaries[self.find(f"{name}@@{version}")["st_value"]] = name
        symbol = self.find(record["mangled"])
        assert (symbol["st_value"], symbol["st_size"], symbol["st_shndx"]) == (
            record["address"], record["size"], record["section"])
        section = self.elf.get_section(record["section"])
        offset = section["sh_offset"] + record["address"] - section["sh_addr"]
        data = self.raw[offset:offset + record["size"]]
        assert offset == record["file_offset"] and section.name == record["section_name"]
        assert data.hex() == record["range_hex"] and digest(data) == record["range_sha256"]

    def find(self, name):
        return self.symbols.get_symbol_by_name(name)[0]

    def address(self, suffix):
        return self.find("_ZN8Presonus2UC20MidiEndpointRegistry" + suffix)["st_value"]

class Machine:
    def __init__(self, original):
        self.uc = unicorn.Uc(unicorn.UC_ARCH_ARM, unicorn.UC_MODE_ARM)
        self.uc.mem_map(0x8000, 0x4F8000)
        for segment in original.elf.iter_segments():
            if segment["p_type"] == "PT_LOAD":
                self.uc.mem_write(segment["p_vaddr"], segment.data())
        for address in (OBJECT, STACK, END, BORROWED):
            self.uc.mem_map(address, 0x1000)
        self.uc.mem_write(OBJECT, b"\xA5" * 0x1000)
        self.uc.mem_write(BORROWED, b"\xB6" * 0x1000)
        self.active = {}
        self.calls = []
        self.next_allocation = ALLOCATIONS
        self.boundaries = original.boundaries
        self.uc.hook_add(unicorn.UC_HOOK_CODE, self.hook)

    def allocate(self, size):
        assert 0 < size <= 0x1000
        address = self.next_allocation
        self.next_allocation += 0x1000
        self.uc.mem_map(address, 0x1000)
        self.uc.mem_write(address, b"\xD9" * 0x1000)
        self.active[address] = size
        return address

    def hook(self, uc, address, size, _):
        boundary = self.boundaries.get(address)
        if not boundary:
            return
        value = uc.reg_read(UC_ARM_REG_R0)
        if boundary == "_Znaj":
            result = self.allocate(value)
            self.calls.append(["allocate", result, value])
            uc.reg_write(UC_ARM_REG_R0, result)
        elif boundary == "_ZdaPv":
            if value:
                self.calls.append(["release", value, self.active.pop(value)])
                self.uc.mem_unmap(value, 0x1000)
        elif boundary == "memset":
            byte = uc.reg_read(UC_ARM_REG_R1) & 255
            length = uc.reg_read(UC_ARM_REG_R2)
            self.uc.mem_write(value, bytes([byte]) * length)
            self.calls.append(["memset", value, length, byte])
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    def store(self, address, values):
        self.uc.mem_write(address, words(values))

    def read_words(self, address, count):
        return list(struct.unpack("<" + "I" * count, self.uc.mem_read(address, count * 4)))

    def run(self, address, listener=0):
        self.uc.reg_write(UC_ARM_REG_R0, OBJECT)
        self.uc.reg_write(UC_ARM_REG_R1, listener)
        self.uc.reg_write(UC_ARM_REG_SP, STACK + 0xF00)
        self.uc.reg_write(UC_ARM_REG_LR, END)
        self.uc.emu_start(address, END, count=30000)
        assert self.uc.reg_read(UC_ARM_REG_PC) == END
        return self.uc.reg_read(UC_ARM_REG_R0)

    def roster(self, offset, items):
        if items:
            capacity = 5
            buffer = self.allocate(4 * capacity)
            self.store(buffer, items)
            self.store(OBJECT + offset + 4, [buffer, len(items), capacity])

def observe(task, original):
    entry = original.record["address"]
    cases = []
    if task.endswith("construct"):
        m = Machine(original)
        assert m.run(entry) == OBJECT
        count = m.read_words(OBJECT + 4, 1)[0]
        pointer, total, capacity, delta, id_start, id_delta = m.read_words(OBJECT + 12, 6)
        bit_words = m.read_words(pointer, total)
        rosters = [m.read_words(OBJECT + offset + 4, 4) for offset in ROSTERS]
        assert count == id_delta and total == capacity and delta == 1
        assert all(w == 0 for w in bit_words)
        assert all(item[0] == 0 for item in rosters)
        comparison = [id_start, id_delta, *sum([entry[1:] for entry in rosters], [])]
        cases.append(dict(comparison=comparison, allocator=m.calls, bit_words=bit_words,
                          receiver=m.read_words(OBJECT, 24)))
    elif task.endswith("destroy"):
        m = Machine(original)
        ctor = "C2Ev" if task == "base_destroy" else "C1Ev"
        m.run(original.address(ctor))
        for index, offset in enumerate(ROSTERS):
            m.roster(offset, [BORROWED + index * 16])
        buffers = [m.read_words(OBJECT + offset + 4, 1)[0] for offset in (*ROSTERS, 8)]
        m.calls.clear()
        assert m.run(entry) == OBJECT
        assert [event[1] for event in m.calls] == list(reversed(buffers[:3])) + buffers[3:]
        assert not m.active
        assert m.uc.mem_read(BORROWED, 0x1000) == b"\xB6" * 0x1000
        assert m.uc.mem_read(OBJECT, 4)
        cases.append(dict(comparison=[len(m.calls)], released_buffers=m.calls))
    elif task == "has_listeners":
        for count in (0, 1, 3, 5):
            m = Machine(original)
            m.run(original.address("C1Ev"))
            m.roster(ROSTERS[2], [BORROWED + i * 16 for i in range(count)])
            before = m.uc.mem_read(OBJECT, 96)
            m.calls.clear()
            present = m.run(entry)
            assert m.uc.mem_read(OBJECT, 96) == before and not m.calls
            cases.append(dict(comparison=[count, present], allocator=m.calls))
    else:
        roster_cases = (([], 1), ([1, 2, 3], 4), ([1, 2, 3], 1), ([1, 2, 3], 2),
                        ([1, 2, 3], 3), ([1, 2, 1, 3], 1), ([1], 1))
        for items, removed in roster_cases:
            m = Machine(original)
            m.run(original.address("C1Ev"))
            m.roster(ROSTERS[2], [BORROWED + i * 16 for i in items])
            m.calls.clear()
            m.run(entry, BORROWED + removed * 16)
            buffer, count, capacity = m.read_words(OBJECT + ROSTERS[2] + 4, 3)
            after = m.read_words(buffer, count) if count else []
            after = [(value - BORROWED) // 16 for value in after]
            assert not m.calls
            cases.append(dict(comparison=[len(items), *items, removed, count, *after],
                              capacity=capacity, allocator=m.calls))
    return cases

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--firmware-root", type=Path, required=True)
    parser.add_argument("--packet-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--task", choices=TASKS, required=True)
    args = parser.parse_args()
    packet = args.packet_root / (TASK_PREFIX + args.task) / "CONTEXT.json"
    records = json.loads(packet.read_text())["originals"]
    observations = [dict(original=row["original"],
                         cases=observe(args.task, Original(args.firmware_root, row["original"])))
                    for row in records]
    args.output.write_text(json.dumps(dict(task=args.task, unicorn=unicorn.__version__,
                                           observations=observations), indent=2) + "\n")
    print(sum(len(row["cases"]) for row in observations), args.task, "native cases")

if __name__ == "__main__":
    main()
