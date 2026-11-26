import hashlib
import json
import sys
import io
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, "uc-library/tests/recovery/sqlite02_spectrumpainter_complete_construct")
import importlib.util

PREDECESSOR = Path(sys.path[0]) / 'native.py'
spec = importlib.util.spec_from_file_location('spectrum_v1_oracle', PREDECESSOR)
n = importlib.util.module_from_spec(spec)
spec.loader.exec_module(n)
from unicorn import UC_HOOK_MEM_WRITE, UC_HOOK_MEM_READ, UC_HOOK_MEM_FETCH_UNMAPPED
from unicorn.arm_const import UC_ARM_REG_PC, UC_ARM_REG_LR, UC_ARM_REG_R0

NEW_ARRAY, DELETE_ARRAY, MEMCPY = 0xAC60, 0xAEC4, 0xAFFC
RESIZE = 0x6F59C
STORAGE_WORD = 0x2c


class Observed(n.Painter):
    def __init__(self, elf, originals, reuse, fresh_byte):
        self.reuse = reuse
        self.fresh_byte = fresh_byte
        self.active = {}
        self.available = []
        self.allocations = []
        self.accesses = []
        self.resize_calls = []
        self.recent = []
        super().__init__(elf, originals)
        self.m.hook_add(UC_HOOK_MEM_FETCH_UNMAPPED, lambda m, a, addr, s, v, d: print(hex(addr), "LR", hex(m.reg_read(UC_ARM_REG_LR)), "allocation", self.allocations, list(map(hex,self.recent)), file=sys.stderr) or False)
        self.m.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, self.memory_access, begin=n.HEAP, end=n.HEAP + 0x10000)

    def memory_access(self, machine, access, addr, size, value, _):
        pc = machine.reg_read(UC_ARM_REG_PC)
        self.accesses.append([pc, access, addr, size, value])

    def hook(self, machine, address, size, data):
        self.recent = (*self.recent[-11:], address)
        if address == RESIZE:
            self.resize_calls.append([machine.reg_read(n.REGS[0]), machine.reg_read(n.REGS[1])])
            return
        if address not in (NEW_ARRAY, DELETE_ARRAY, MEMCPY):
            return super().hook(machine, address, size, data)
        arg = machine.reg_read(UC_ARM_REG_R0)
        result = 0
        if address == NEW_ARRAY:
            same_class = next((entry for entry in self.available if entry[1] == arg), None)
            if self.reuse and same_class:
                self.available.remove(same_class)
                result = same_class[0]
                fresh = False
            else:
                result = self.heap_next
                self.heap_next += (arg + 15) & ~15
                self.m.mem_write(result, bytes([self.fresh_byte]) * arg)
                fresh = True
            self.active[result] = arg
            self.allocations.append(["new[]", result, arg, fresh, machine.reg_read(UC_ARM_REG_LR)])
        elif address == MEMCPY:
            source = machine.reg_read(n.REGS[1])
            size = machine.reg_read(n.REGS[2])
            machine.mem_write(arg, bytes(machine.mem_read(source, size)))
            self.allocations.append(["memcpy", arg, size, source, machine.reg_read(UC_ARM_REG_LR)])
            result = arg
        else:
            size = self.active.pop(arg)
            self.available.append((arg, size))
            self.allocations.append(["delete[]" if address == DELETE_ARRAY else "delete", arg, size, False, machine.reg_read(UC_ARM_REG_LR)])
        machine.reg_write(UC_ARM_REG_R0, result)
        machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

    def record(self, action):
        self.allocations.clear()
        self.accesses.clear()
        self.resize_calls.clear()
        row = self.observe(action)
        pointer, count, capacity = self.read(n.OBJECT + 0x20, 3)
        row.update({
            "allocation_calls": self.allocations[:],
            "resize_calls_executed": self.resize_calls[:],
            "storage": pointer,
            "count": count,
            "capacity": capacity,
        })
        if pointer and capacity >= 2:
            slot = pointer + STORAGE_WORD
            row["second_entry_words"] = self.read(pointer + 32, 8, "i")
            row["second_center_accesses"] = [
                [hex(pc), access, addr - pointer, size, value]
                for pc, access, addr, size, value in self.accesses
                if addr <= slot < addr + size
            ]
        self.execute("last_accessor", n.RESULT, n.OBJECT)
        row["native_last_accessor"] = self.rect(n.RESULT)
        assert row["native_last_accessor"] == row["state"]["last"]
        return row


def main():
    elf, originals = n.verify()
    resize = elf.get_section_by_name(".symtab").get_symbol_by_name(
        "_ZN4Core6VectorIN8Presonus15SpectrumPainter3BarEE6resizeEi"
    )[0]
    addr = resize["st_value"]
    size = resize["st_size"]
    off = next(elf.address_offsets(addr, size))
    elf.stream.seek(off)
    resize_range = {"address": addr, "size": size, "file_offset": off,
                    "sha256": hashlib.sha256(elf.stream.read(size)).hexdigest()}
    symtab = elf.get_section_by_name(".symtab")
    getter_name = "_ZNK8Presonus15SpectrumPainter16getLastDrawnRectEv"
    getter, = symtab.get_symbol_by_name(getter_name)
    getter_address = getter["st_value"]
    getter_size = getter["st_size"]
    getter_section = getter["st_shndx"]
    getter_offset = next(elf.address_offsets(getter_address, getter_size))
    section = elf.get_section(getter_section)
    assert getter_offset == section["sh_offset"] + getter_address - section["sh_addr"]
    elf.stream.seek(getter_offset)
    getter_range = {"mangled": getter_name, "address": getter_address, "size": getter_size,
                    "section": getter_section, "file_offset": getter_offset,
                    "range_sha256": hashlib.sha256(elf.stream.read(getter_size)).hexdigest()}
    originals["last_accessor"] = getter_range
    bounds = [7, 9, 44, 39]
    out = []
    for reuse, fresh_byte, history, center in (
        (False, 0, [], 11),
        (False, 1, [], 11),
        (False, 0xFF, [], -11),
        (False, 0xA5, [], 10),
        (False, 0xA5, [], 0),
        (False, 0xA5, [], 26),
        (True, 0, [4,17,30], 11),
        (True, 0, [4,28,30], 11),
        (False, 0, [4,17,30], 11),
        (True, 0, [3,6,10,16,21,31], 11),
    ):
        p = Observed(elf, originals, reuse, fresh_byte)
        actions = [["construct", "complete_construct"]]
        if history:
            actions += [["bind", [1] * len(history), history], ["init", *bounds], ["paint", [0,0,64,64], 0xff000080]]
        actions.append(["bind", [1], [center]])
        if center != 26:
            actions.append(["init", *bounds])
        if center == 10:
            actions.extend([
                ["calculate_bars", *bounds],
                ["mutate", 0, 0.1],
            ])
        actions.extend([
            ["calculate_next_draw_rect", *bounds],
            ["paint", [0, 0, 64, 64], 0xff000080],
        ])
        out.append({"reuse_same_size": reuse, "fresh_allocator_fill_byte": fresh_byte,
                    "populated_history": history, "center": center, "rows": [p.record(a) for a in actions]})
    elf_sha256 = next(iter(originals.values()))["elf"]
    with redirect_stdout(io.StringIO()) as previous:
        n.main()
    prior_fixtures = json.loads(previous.getvalue())
    assert prior_fixtures == json.loads(PREDECESSOR.with_name("fixtures.json").read_text())
    runs = prior_fixtures["runs"] + [record["rows"] for record in out]
    print(json.dumps({"runs": runs, "last_accessor_original": getter_range, "resize_range": resize_range, "elf": next(iter(originals.values()))["elf"],
                      "allocation_boundary": "Exact native application plus exact linked Core resize body executed on ARM. Only global new[]/delete[] and memcpy imports hooked using fresh or same-size-free-list storage. No direct writes to spare entries. Grid, fill and log10f hooked as in existing replay.",
                      "one_bin_sequences": [{k: v for k, v in row.items() if k != "rows"} for row in out]}, indent=2))


if __name__ == "__main__":
    main()
