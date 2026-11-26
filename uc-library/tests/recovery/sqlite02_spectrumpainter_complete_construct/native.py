"""Replay the sealed application ranges on ARM with bounded provider hooks."""

import ctypes
import hashlib
import io
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP,
)

ROOT = Path("temp/recovery-work/sqlite-issued/packet")
PREFIX = "sqlite02_spectrumpainter_"
OBJECT, GRID, GRID_VTABLE = 0x3100000, 0x3100100, 0x3100200
BOUNDS, RESULT, AMPLITUDE, FREQUENCY = 0x3100300, 0x3100400, 0x3100500, 0x3100600
EVENT, STYLE, GRAPHICS, GRAPHICS_VTABLE = (0x3100700, 0x3100800, 0x3100900, 0x3100A00)
HEAP, STOP, GRID_CALL, FILL_CALL = 0x3110000, 0x31F0000, 0x31F0100, 0x31F0200
REGS = (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)
LIBM = ctypes.CDLL("libm.so.6")
LIBM.log10f.argtypes = (ctypes.c_float,)
LIBM.log10f.restype = ctypes.c_float


def float_bits(value):
    return struct.unpack("<I", struct.pack("<f", value))[0]


def bits_float(value):
    return struct.unpack("<f", struct.pack("<I", value))[0]


def verify():
    originals = {
        p.parent.name.removeprefix(PREFIX): json.loads(p.read_text())["originals"][0]["original"]
        for p in sorted(ROOT.glob(PREFIX + "*/CONTEXT.json"))
    }
    assert len(originals) == 7
    image = Path(next(iter(originals.values()))["elf_path"]).read_bytes()
    elf = ELFFile(io.BytesIO(image))
    symbols = elf.get_section_by_name(".symtab")
    entire_hash = hashlib.sha256(image).hexdigest()
    for original in originals.values():
        assert original["elf"] == entire_hash
        candidates = symbols.get_symbol_by_name(original["mangled"])
        assert len(candidates) == 1
        symbol = candidates[0]
        index = symbol["st_shndx"]
        section = elf.get_section(index)
        size = symbol["st_size"]
        address = symbol["st_value"]
        delta = address - section["sh_addr"]
        assert 0 <= delta <= section["sh_size"] - size
        offset = section["sh_offset"] + delta
        exact = image[offset:offset + size]
        assert (address, size, index, section.name, offset) == (
            original["address"], original["size"], original["section"],
            original["section_name"], original["file_offset"],
        )
        assert exact.hex() == original["range_hex"]
        assert hashlib.sha256(exact).hexdigest() == original["range_sha256"]
    return elf, originals


class Painter:
    def __init__(self, elf, originals):
        self.m = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        self.originals = originals
        segments = [s for s in elf.iter_segments() if s["p_type"] == "PT_LOAD"]
        self.m.mem_map(0x8000, 0x300000)
        for segment in segments:
            self.m.mem_write(segment["p_vaddr"], segment.data())
        self.m.mem_map(OBJECT, 0x100000)
        self.write(GRID, GRID_VTABLE)
        self.write(GRID_VTABLE + 4, GRID_CALL)
        self.write(GRAPHICS, GRAPHICS_VTABLE)
        self.write(GRAPHICS_VTABLE + 0x14, FILL_CALL)
        self.m.hook_add(UC_HOOK_CODE, self.hook)
        self.calls = []
        self.heap_next = HEAP
        self.m.mem_write(OBJECT, b"\xa5" * 0x50)

    def read(self, address, count=1, form="I"):
        return list(struct.unpack("<" + form * count, self.m.mem_read(address, 4 * count)))

    def write(self, address, *values):
        self.m.mem_write(address, struct.pack("<" + "I" * len(values), *(v & 0xFFFFFFFF for v in values)))

    def rect(self, address):
        return self.read(address, 4, "i")

    def hook(self, machine, address, _size, _data):
        if address not in (0x6F59C, 0xAE10, GRID_CALL, FILL_CALL):
            return
        arg0, arg1, arg2 = (machine.reg_read(r) for r in REGS[:3])
        result = 0
        if address == 0x6F59C:
            # Core vector allocation boundary. Native app accesses use these ARM
            # field offsets. The production replay uses the pinned CCL Vector.
            assert arg0 == OBJECT + 0x1C
            self.calls.append(["resize", arg1])
            if arg1 == 0:
                self.write(arg0 + 4, 0, 0, 0)
            else:
                old_items, count, old_capacity, delta = self.read(arg0 + 4, 4)
                capacity = ((arg1 - 1) // delta + 1) * delta
                if capacity != old_capacity:
                    items = self.heap_next
                    self.heap_next += capacity * 32
                    if count:
                        self.m.mem_write(items, bytes(self.m.mem_read(old_items, count * 32)))
                    self.write(arg0 + 4, items, count, capacity)
            result = 1
        elif address == 0xAE10:
            self.calls.append(["log10f", arg0])
            result = float_bits(LIBM.log10f(bits_float(arg0)))
        elif address == GRID_CALL:
            assert arg0 == GRID
            self.calls.append(["grid", arg1])
            result = int(bits_float(arg1))
        elif address == FILL_CALL:
            assert arg0 == GRAPHICS
            self.calls.append(["fill", *self.rect(arg1), self.read(arg2)[0]])
            result = 1
        machine.reg_write(UC_ARM_REG_R0, result & 0xFFFFFFFF)
        machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

    def execute(self, name, *args):
        self.calls.clear()
        for reg, value in zip(REGS, args):
            self.m.reg_write(reg, value)
        self.m.reg_write(UC_ARM_REG_SP, STOP - 0x100)
        self.m.reg_write(UC_ARM_REG_LR, STOP)
        self.m.emu_start(self.originals[name]["address"], STOP, count=25000)
        assert self.m.reg_read(UC_ARM_REG_PC) == STOP

    def observe(self, action):
        command, *args = action
        result = None
        if command == "construct":
            self.execute(args[0], OBJECT, GRID)
            assert self.read(OBJECT, 3) == [0x19BF40, float_bits(40.0), GRID]
        elif command == "bind":
            amplitude, frequency = args
            self.write(AMPLITUDE, *(float_bits(x) for x in amplitude))
            self.write(FREQUENCY, *(float_bits(x) for x in frequency))
            self.execute("set_data", OBJECT, AMPLITUDE, len(amplitude), FREQUENCY)
        elif command in ("mutate", "mutate_frequency"):
            self.calls.clear()
            index, value = args
            base = AMPLITUDE if command == "mutate" else FREQUENCY
            self.write(base + index * 4, float_bits(value))
        elif command == "init":
            self.write(BOUNDS, *args)
            self.execute("init", OBJECT, BOUNDS)
        elif command in ("calculate_bars", "calculate_next_draw_rect"):
            self.write(BOUNDS, *args)
            self.execute(command, RESULT, OBJECT, BOUNDS)
            result = self.rect(RESULT)
        elif command == "paint":
            clip, rgba = args
            self.write(EVENT, GRAPHICS, *clip)
            self.write(STYLE + 0x10, rgba)
            self.execute("paint", OBJECT, BOUNDS, EVENT, STYLE)
        else:
            raise ValueError(action)
        words = self.read(OBJECT, 20)
        items, count = words[8:10]
        state = {
            "initialized": words[3] & 0xFF,
            "retained": [words[4] == AMPLITUDE, words[5] == FREQUENCY, words[6]],
            "bars": [self.read(items + i * 32, 8, "i") for i in range(count)],
            "last": self.rect(OBJECT + 0x30),
            "next": self.rect(OBJECT + 0x40),
        }
        return {"action": action, "result": result, "calls": self.calls[:], "state": state}


def main():
    elf, originals = verify()
    result = []
    for constructor in ("complete_construct", "base_construct"):
        for origin, scale in (([0, 0], 30), ([9, -4], 50), ([-10, 17], 23)):
            x, y = origin
            bounds = [x, y, x + 37, y + scale]
            narrow_clip = [4, 5, 29, scale - 4]
            full_clip = [-30, -40, 60, 120]
            actions = [
                ["construct", constructor],
                ["paint", full_clip, 0xAADA1302],
                ["calculate_next_draw_rect", *bounds],
                ["bind", [1, 0.1, 0], [4, 17, 30]],
                ["mutate_frequency", 1, 19.0],
                ["init", *bounds],
                ["calculate_bars", *bounds],
                ["calculate_next_draw_rect", *bounds],
                ["paint", full_clip, 0xAADA1302],
                ["mutate", 1, 0.001],
                ["mutate", 2, 2.0],
                ["calculate_next_draw_rect", *bounds],
                ["paint", narrow_clip, 0x4002C824],
                ["paint", [30, 30, 30, 30], 0xB0112200],
                ["calculate_next_draw_rect", *bounds],
                ["bind", [-0.1, 1e-9, 0.03, 0.25, 0.8, 0.01], [5, 8, 10, 16, 24, 34]],
                ["calculate_next_draw_rect", *bounds],
                ["paint", full_clip, 0xFF016480],
                ["bind", [], []],
                ["calculate_next_draw_rect", *bounds],
                ["paint", full_clip, 0],
            ]
            painter = Painter(elf, originals)
            result.append([painter.observe(action) for action in actions])
    print(json.dumps({"runs": result}, indent=2))


if __name__ == "__main__":
    main()
