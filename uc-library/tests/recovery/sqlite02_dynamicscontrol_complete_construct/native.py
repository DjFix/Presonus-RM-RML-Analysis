"""Offline ARM oracle for exact SQLite-issued DynamicsControl ranges."""
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from struct import pack, unpack

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, Uc
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_SP, UC_ARM_REG_R0,
    UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
)

ROOT = Path(__file__).resolve().parents[4]
TASK_PREFIX = "sqlite02_dynamicscontrol_"
REGS = (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)
OBJECT, STACK, STOP = 0x3000000, 0x3048000, 0x3050000
RECT, EVENT, OUT, STYLE = 0x3010000, 0x3010100, 0x3010200, 0x3010300
PRIMARY, THRESHOLD, RATIO, EXPANDER = (0x3020000 + n * 0x100 for n in range(4))
IMAGE, HANDLE = 0x3010400, 0x3010500
GET_VALUE, SET_VALUE, GET_NORMALIZED = 0x3050010, 0x3050020, 0x3050030
PARAMETER_NAMES = {PRIMARY: "primary", THRESHOLD: "threshold", RATIO: "ratio",
                   EXPANDER: "expander"}


def args_for(suffix):
    if suffix.endswith("construct"):
        return [{"rect": rect} for rect in ([4, 5, 37, 44], [-3, 7, 5, 15])]
    if suffix.endswith("destroy"):
        return [{"presence": mask} for mask in (0, 5, 7)]
    if suffix == "calculate_pivot_points":
        return [{"mode": m, "threshold": t, "ratio": r, "expander": e, "size": wh}
                for m, t, r, e, wh in (
                    (0, None, None, None, [1, 1]),
                    (0, .25, None, 0, [41, 17]),
                    (0, .25, None, 1, [40, 17]),
                    (0, .24, None, 1, [40, 17]),
                    (0, .26, None, 1, [40, 17]),
                    (1, .35, 3, None, [41, 17]),
                    (1, .35, 0, None, [41, 17]),
                    (1, 1, 4, None, [41, 17]),
                    (1, .5, None, None, [41, 17]),
                )]
    if suffix == "on_idle":
        return [{"last": 2000, "now": now, "pending": pending}
                for now, pending in ((1999, 1), (2099, 1), (2100, 1), (2101, 1), (2101, 0))]
    if suffix == "on_touch_input":
        return [{"primary": p, "enabled": enabled, "event": event, "value": value}
                for p, enabled, event, value in (
                    (0, 1, 0, 0), (1, 0, 0, 0), (1, 1, 0, 0),
                    (1, 1, 0, -2), (1, 1, 1, 0), (1, 1, 2, 1))]
    if suffix == "param_changed":
        return [{"changed": who, "message": message, "cached": cache, "pending": pending}
                for who, message, cache, pending in (
                    ("primary", 5, [0]*4, 0), ("threshold", 5, [0]*4, 0),
                    ("expander", 5, [0]*4, 0), ("ratio", 5, [0]*4, 0),
                    ("threshold", 4, [0]*4, 0), ("threshold", 3, [10, 15, 10, 0], 0),
                    ("threshold", 3, [10, 15, 9, 0], 0), ("threshold", 3, [10, 15, 10, 0], 1))]
    if suffix == "set_size":
        return [{"rect": rect} for rect in ([11, 3, 35, 27], [-15, 4, 25, 24], [1, 2, 2, 3])]
    raise ValueError(suffix)


class Original:
    def __init__(self, row):
        self.blob = (ROOT / row["elf_path"]).read_bytes()
        assert sha256(self.blob).hexdigest() == row["elf"]
        self.elf = ELFFile(BytesIO(self.blob))
        self.symbols = self.elf.get_section_by_name(".symtab")
        self.row = row
        entry, size, index = row["address"], row["size"], row["section"]
        symbol, = self.symbols.get_symbol_by_name(row["mangled"])
        assert (symbol["st_value"], symbol["st_size"], symbol["st_shndx"]) == (entry, size, index)
        section = self.elf.get_section(index)
        delta = entry - section["sh_addr"]
        offset = section["sh_offset"] + delta
        body = self.blob[offset:offset + size]
        assert 0 <= delta <= section["sh_size"] - size and section.name == row["section_name"]
        assert offset == row["file_offset"] and sha256(body).hexdigest() == row["range_sha256"]
        assert body.hex() == row["range_hex"]

    def addr(self, name):
        symbol, = self.symbols.get_symbol_by_name(name)
        return symbol["st_value"]

    def plt_addr(self, name):
        entries = self.elf.get_section_by_name(".rel.plt")
        names = self.elf.get_section(entries["sh_link"])
        idx, = (i for i, rel in enumerate(entries.iter_relocations())
                if names.get_symbol(rel["r_info_sym"]).name == name)
        return self.elf.get_section_by_name(".plt")["sh_addr"] + 20 + idx * 12


def float_word(f):
    return unpack("<I", pack("<f", f))[0]


def word_float(i):
    return unpack("<f", pack("<I", i))[0]


class Machine:
    def __init__(self, original, data):
        self.o, self.data = original, data
        self.cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        self.cpu.mem_map(0x8000, 0x280000)
        self.cpu.mem_map(OBJECT, 0x60000)
        for seg in original.elf.iter_segments():
            if seg["p_type"] == "PT_LOAD":
                self.cpu.mem_write(seg["p_vaddr"], seg.data())
        self.deallocated = False
        self.trace, self.pcs = [], []
        self.values = {PRIMARY: data.get("value", 1), THRESHOLD: data.get("threshold", .25),
                       RATIO: data.get("ratio", 4), EXPANDER: data.get("expander", 0)}
        self.client_rect = [0, 0, *data.get("size", [40, 20])]
        for p in PARAMETER_NAMES:
            self.write(p, p + 16)
            self.write(p + 16 + 0x44, GET_VALUE)
            self.write(p + 16 + 0x58, SET_VALUE)
            self.write(p + 16 + 0x60, GET_NORMALIZED)
        self.return_hooks = {
            original.addr("_ZN4Core8Portable7ControlC2ERKNS_5TRectIiEEPNS0_9ParameterE"): self.base_ctor,
            original.addr("_ZN4Core8Portable7ControlD2Ev"): self.base_dtor,
            original.addr("_ZNK4Core8Portable4View13getClientRectERNS_5TRectIiEE"): self.client,
            original.addr("_ZN4Core8Portable4View7setSizeERKNS_5TRectIiEE"): self.size,
            original.addr("_ZNK4Core8Portable4View9isEnabledEv"): self.enabled,
            original.addr("_ZN4Core8Portable7Control12paramChangedEPNS0_9ParameterEi"): self.param,
            original.addr("_ZN4Core8Portable7Control6onIdleEv"): self.idle,
            original.addr("_ZN4Core15GetAbsoluteTimeEv"): self.clock,
            original.addr("_ZN4Core8Portable4View10invalidateEv"): self.invalidate,
            original.addr("_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE"): self.remove,
            original.plt_addr("_ZdlPv"): self.delete,
            GET_VALUE: self.get_value, SET_VALUE: self.set_value,
            GET_NORMALIZED: self.get_normalized,
        }
        self.linear_ctor = original.addr("_ZN4Core18LinearInterpolatorC1Eff")
        self.linear_norm = original.addr("_ZNK4Core18LinearInterpolator17normalizedToRangeEf")
        self.cpu.hook_add(UC_HOOK_CODE, self.on_code)

    def write(self, address, *words):
        self.cpu.mem_write(address, pack("<" + "I" * len(words), *(w & 0xffffffff for w in words)))

    def read(self, address, n=1, signed=False):
        return list(unpack("<" + ("i" if signed else "I") * n, self.cpu.mem_read(address, 4*n)))

    def note(self, *args):
        self.trace.append(list(args))

    def reg(self, value, index=0):
        self.cpu.reg_write(REGS[index], value & 0xffffffff)

    def base_ctor(self, r0, r1, r2, _):
        assert r0 == OBJECT and r2 == 0
        self.write(OBJECT + 0x2c, *self.read(r1, 4))
        self.write(OBJECT + 0x48, r2)
        self.note("control_construct", self.read(r1, 4, signed=True), r2)

    def base_dtor(self, r0, *_):
        assert r0 == OBJECT
        self.note("control_destroy")

    def client(self, r0, r1, *_):
        assert r0 == OBJECT
        self.write(r1, *self.client_rect)
        self.note("client_rect", self.client_rect)
        self.reg(r1)

    def size(self, r0, r1, *_):
        assert r0 == OBJECT
        self.write(OBJECT + 0x2c, *self.read(r1, 4))
        self.note("view_size", self.read(r1, 4, signed=True))

    def enabled(self, r0, *_):
        assert r0 == OBJECT
        value = self.data["enabled"]
        self.note("enabled", value)
        self.reg(value)

    def param(self, r0, r1, r2, _):
        assert r0 == OBJECT
        self.note("control_param", PARAMETER_NAMES[r1], r2)

    def idle(self, r0, *_):
        assert r0 == OBJECT
        self.note("control_idle")

    def clock(self, *_):
        ns = self.data["now"] * 1_000_000
        self.note("clock_ns", ns)
        self.reg(ns)
        self.reg(ns >> 32, 1)

    def invalidate(self, r0, *_):
        assert r0 == OBJECT
        self.note("invalidate")

    def remove(self, r0, r1, *_):
        assert r1 == OBJECT + 0x44
        self.note("remove_observer", PARAMETER_NAMES[r0])

    def delete(self, r0, *_):
        assert r0 == OBJECT
        self.cpu.mem_unmap(OBJECT, 0x1000)
        self.deallocated = True
        self.note("delete_receiver")

    def get_value(self, r0, *_):
        self.note("get_value", PARAMETER_NAMES[r0], self.values[r0])
        self.reg(float_word(self.values[r0]))

    def set_value(self, r0, r1, r2, _):
        self.values[r0] = word_float(r1)
        self.note("set_value", PARAMETER_NAMES[r0], self.values[r0], r2)

    def get_normalized(self, r0, *_):
        self.note("get_normalized", PARAMETER_NAMES[r0], self.values[r0])
        self.reg(float_word(self.values[r0]))

    def on_code(self, u, address, _width, _):
        start, size = self.o.row["address"], self.o.row["size"]
        if start <= address < start + size:
            self.pcs.append(address - start)
        values = [u.reg_read(reg) for reg in REGS]
        if address in self.return_hooks:
            self.return_hooks[address](*values)
            u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))
        elif address in [self.linear_ctor, self.linear_norm]:
            r0, r1, r2, _ = values
            assert r0 in [OBJECT + 0x78, OBJECT + 0x8c]
            label = "vertical" if r0 == OBJECT + 0x78 else "horizontal"
            if address == self.linear_ctor:
                self.note("linear_construct", label, word_float(r1), word_float(r2))
            else:
                self.note("linear_normalize", label, word_float(r1))

    def call(self, entry, args, extra=()):
        self.write(STACK, *extra)
        for i, value in enumerate(args):
            self.reg(value, i)
        self.cpu.reg_write(UC_ARM_REG_SP, STACK)
        self.cpu.reg_write(UC_ARM_REG_LR, STOP)
        self.cpu.emu_start(entry, STOP, count=30_000)
        assert self.cpu.reg_read(UC_ARM_REG_PC) == STOP and self.cpu.reg_read(UC_ARM_REG_SP) == STACK
        return self.cpu.reg_read(UC_ARM_REG_R0)

    def parameters(self, mask):
        for i, p in enumerate((THRESHOLD, RATIO, EXPANDER)):
            self.write(OBJECT + 0x6c + i*4, p if mask & (1 << i) else 0)

    def ranges(self):
        return [[word_float(w) for w in self.read(OBJECT + offset, 3)]
                for offset in (0x7c, 0x90)]

    def set_ranges(self, size):
        for field, value in ((0x7c, size[1]), (0x90, size[0])):
            self.write(OBJECT + field, 0, float_word(value), float_word(1))

    def execute(self, suffix):
        data, entry = self.data, self.o.row["address"]
        if suffix.endswith("construct"):
            self.cpu.mem_write(OBJECT, b"\xa5" * 0xc0)
            self.write(RECT, *data["rect"])
            self.call(entry, [OBJECT, RECT])
            zeros = [0x58, 0x5c, 0x60, 0x64, 0x6c, 0x70, 0x74, 0xa0, 0xa4,
                     0xa8, 0xac, 0xb0, 0xb4]
            result = [*self.read(OBJECT + 0x2c, 4, signed=True), *self.read(OBJECT + 0x48),
                      *[self.read(OBJECT + offset)[0] for offset in zeros],
                      *list(self.cpu.mem_read(OBJECT + 0x68, 4)),
                      self.cpu.mem_read(OBJECT + 0xb8, 1)[0], *sum(self.ranges(), [])]
        elif suffix.endswith("destroy"):
            self.parameters(data["presence"])
            self.write(OBJECT + 0x60, IMAGE, HANDLE)
            self.write(IMAGE + 0x34, 1)
            self.write(HANDLE + 0x34, 1)
            self.call(entry, [OBJECT])
            result = [self.read(IMAGE + 0x34)[0], self.read(HANDLE + 0x34)[0], int(self.deallocated)]
        elif suffix == "calculate_pivot_points":
            mask = sum(1 << i for i, key in enumerate(("threshold", "ratio", "expander"))
                       if data[key] is not None)
            self.parameters(mask)
            self.write(OBJECT + 0x58, data["mode"])
            self.set_ranges(data["size"])
            self.call(entry, [OBJECT, OUT, OUT+4, OUT+8], [OUT+12])
            result = self.read(OUT, 4, signed=True)
        elif suffix == "on_idle":
            self.write(OBJECT + 0xa0, data["last"], 0)
            self.write(OBJECT + 0xb8, data["pending"])
            self.call(entry, [OBJECT])
            result = [self.read(OBJECT + 0xa0)[0], self.read(OBJECT + 0xb8)[0],
                      int(["invalidate"] in self.trace)]
        elif suffix == "on_touch_input":
            self.write(OBJECT + 0x48, PRIMARY if data["primary"] else 0)
            self.write(EVENT, data["event"])
            status = self.call(entry, [OBJECT, EVENT])
            result = [status, self.values[PRIMARY]]
        elif suffix == "param_changed":
            self.write(OBJECT + 0x48, PRIMARY)
            self.parameters(7)
            self.set_ranges([40, 20])
            self.write(OBJECT + 0xa8, *data["cached"])
            self.write(OBJECT + 0xb8, data["pending"])
            changed, = (p for p, name in PARAMETER_NAMES.items() if name == data["changed"])
            self.call(entry, [OBJECT, changed, data["message"]])
            result = [*[int(p != 0) for p in self.read(OBJECT + 0x6c, 3)],
                      self.read(OBJECT + 0xb8)[0]]
        elif suffix == "set_size":
            self.write(RECT, *data["rect"])
            self.call(entry, [OBJECT, RECT])
            result = [*self.read(OBJECT + 0x2c, 4, signed=True), *sum(self.ranges(), [])]
        else:
            raise ValueError(suffix)
        assert self.pcs and self.pcs[0] == 0
        return dict(inputs=data, result=result, trace=self.trace, target_offsets=sorted(set(self.pcs)))


# Legacy drawing/attribute ABI scratch addresses. These are fixture storage.
GRAPHICS, ATTRIBUTES, PARAM_ATTRIBUTES, RESOLVER, VTBL = (
    0x3010600, 0x3010800, 0x3010900, 0x3010a00, 0x3010b00
)
DRAW_BITMAP, DRAW_LINE, LOOKUP_PARAM = 0x3050040, 0x3050050, 0x3050060
FOREGROUND, OFFLINE = 0xff304050, 0xff1294de


def display_args(suffix):
    if suffix == "draw":
        return [
            dict(primary=None, image=0, handle=0, mode=0),
            dict(primary=0, image=3, handle=2, mode=0),
            dict(primary=1, image=1, handle=2, mode=1),
            dict(primary=-1, image=2, handle=1, mode=1),
        ]
    if suffix == "set_attributes":
        return [
            dict(resolver=0, params=0, mask=0, image=0, handle=0, color=0, dimensions=[20, 30]),
            dict(resolver=1, params=1, mask=7, image=3, handle=1, color=1, dimensions=[0, 0]),
            dict(resolver=1, params=1, mask=5, image=1, handle=0, color=0, dimensions=[0, 30]),
            dict(resolver=1, params=0, mask=0, image=0, handle=0, color=1, dimensions=[20, 0]),
            dict(resolver=0, params=1, mask=7, image=1, handle=1, color=1, dimensions=[20, 30]),
        ]
    raise ValueError(suffix)


class DisplayMachine(Machine):
    def __init__(self, original, data):
        super().__init__(original, data)
        for flags, pointer in (("image", IMAGE), ("handle", HANDLE)):
            width, height = ((48, 24) if pointer == IMAGE else (5, 10))
            self.write(pointer + 8, data[flags], width, height)
        for address, value in ((GRAPHICS, GRAPHICS + 4), (RESOLVER, RESOLVER + 4)):
            self.write(address, value)
        self.write(GRAPHICS + 4 + 0x28, DRAW_BITMAP)
        self.write(GRAPHICS + 4 + 0x1c, DRAW_LINE)
        self.write(RESOLVER + 4 + 0x0c, LOOKUP_PARAM)
        self.write(STYLE + 4, FOREGROUND)
        self.write(VTBL + 0x18, original.addr("_ZN8Presonus15DynamicsControl7setSizeERKN4Core5TRectIiEE"))
        self.write(OBJECT, VTBL)
        self.strings = {}
        for i, name in enumerate(("th", "rat", "exp")):
            pointer = 0x3010c00 + 16*i
            self.cpu.mem_write(pointer, name.encode() + b"\0")
            self.strings[name] = pointer
        self.return_hooks.update({
            original.addr("_ZNK4Core8Portable4View8getStyleEv"): self.style,
            original.addr("_ZN4Core8Portable4View13setAttributesERKNS0_10AttributesE"): self.apply_view_attributes,
            original.addr("_ZN4Core8Portable14ViewAttributes8getColorERKNS0_10AttributesEPKcNS_5ColorE"): self.color,
            original.addr("_ZN4Core8Portable14ViewAttributes9getBitmapERKNS0_10AttributesEPKc"): self.bitmap,
            original.addr("_ZN4Core8Portable14ViewAttributes16autoSizeToBitmapERNS_5TRectIiEEPNS0_6BitmapE"): self.auto_size,
            original.addr("_ZNK4Core8Portable10Attributes13getAttributesEPKc"): self.find_attributes,
            original.addr("_ZNK4Core8Portable10Attributes9getStringEPKc"): self.find_string,
            original.addr("_ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE"): self.add,
            DRAW_BITMAP: self.draw_bitmap, DRAW_LINE: self.draw_line, LOOKUP_PARAM: self.lookup,
        })

    def string(self, addr):
        return bytes(self.cpu.mem_read(addr, 64)).split(b"\0", 1)[0].decode()

    def style(self, r0, *_):
        assert r0 == OBJECT
        self.note("style")
        self.reg(STYLE)

    def draw_bitmap(self, r0, r1, r2, r3):
        assert r0 == GRAPHICS and r2 in (IMAGE, HANDLE)
        self.note("draw_bitmap", "image" if r2 == IMAGE else "handle",
                  self.read(r1, 2, signed=True), self.read(r3, 4, signed=True))

    def draw_line(self, r0, r1, r2, r3):
        assert r0 == GRAPHICS
        self.note("draw_line", self.read(r1, 2, signed=True), self.read(r2, 2, signed=True), self.read(r3)[0])

    def apply_view_attributes(self, r0, r1, *_):
        assert r0 == OBJECT and r1 == ATTRIBUTES
        size = self.data["dimensions"]
        self.write(OBJECT + 0x2c, 0, 0, *size)
        self.set_ranges(size)
        self.note("view_attributes", size)

    def color(self, r0, r1, r2, _):
        assert r0 == ATTRIBUTES and self.string(r1) == "offLineColor"
        self.note("color", self.string(r1), r2)
        self.reg(OFFLINE if self.data["color"] else r2)

    def bitmap(self, r0, r1, r2, _):
        assert r1 == ATTRIBUTES
        name = self.string(r2)
        pointer = {"image": IMAGE, "handle": HANDLE}[name]
        if self.data[name]:
            ref = self.read(pointer + 0x34)[0]
            self.write(pointer + 0x34, ref + 1)
        else:
            pointer = 0
        self.write(r0, pointer)
        self.note("bitmap", name, bool(pointer))

    def auto_size(self, r0, r1, *_):
        assert r1 in (IMAGE, 0)
        self.note("auto_size", bool(r1))
        if r1:
            frames, width, height = self.read(r1 + 8, 3)
            self.write(r0, 0, 0, width, height // max(frames, 1))
        self.reg(bool(r1))

    def find_attributes(self, r0, r1, *_):
        assert r0 == ATTRIBUTES and self.string(r1) == "params"
        self.note("find_attributes", self.string(r1))
        self.reg(PARAM_ATTRIBUTES if self.data["params"] else 0)

    def find_string(self, r0, r1, *_):
        assert r0 == PARAM_ATTRIBUTES
        schemas = {"threshold": [1, "th"], "ratio": [2, "rat"], "expander": [4, "exp"]}
        name = self.string(r1)
        bit, value = schemas[name]
        present = self.data["mask"] & bit
        self.note("find_string", name, bool(present))
        self.reg(self.strings[value] if present else 0)

    def lookup(self, r0, r1, r2, _):
        assert r0 == RESOLVER and self.string(r2) == "Param"
        name = self.string(r1)
        self.note("lookup", name, self.string(r2))
        self.reg({"th": THRESHOLD, "rat": RATIO, "exp": EXPANDER}[name])

    def add(self, r0, r1, *_):
        assert r1 == OBJECT + 0x44
        self.note("add_observer", PARAMETER_NAMES[r0])

    def execute(self, suffix):
        data, entry = self.data, self.o.row["address"]
        if suffix == "draw":
            self.write(EVENT, GRAPHICS)
            self.values[PRIMARY] = data["primary"]
            self.write(OBJECT + 0x48, PRIMARY if data["primary"] is not None else 0)
            self.write(OBJECT + 0x58, data["mode"])
            self.write(OBJECT + 0x60, IMAGE if data["image"] else 0, HANDLE if data["handle"] else 0, OFFLINE)
            self.parameters(7)
            self.set_ranges([40, 20])
            self.call(entry, [OBJECT, EVENT])
            result = self.read(OBJECT + 0xa8, 4, signed=True)
        elif suffix == "set_attributes":
            self.write(OBJECT + 0x5c, RESOLVER if data["resolver"] else 0)
            self.call(entry, [OBJECT, ATTRIBUTES])
            result = [*self.read(OBJECT + 0x2c, 4, signed=True),
                      self.read(OBJECT + 0x68)[0],
                      *[int(p != 0) for p in self.read(OBJECT + 0x6c, 3)],
                      self.read(IMAGE + 0x34)[0], self.read(HANDLE + 0x34)[0]]
        else:
            raise ValueError(suffix)
        assert self.pcs and self.pcs[0] == 0
        return dict(inputs=data, result=result, trace=self.trace, target_offsets=sorted(set(self.pcs)))


def observe(task):
    packet = ROOT / "temp/recovery-work/sqlite-issued/packet" / task / "CONTEXT.json"
    row, = (item["original"] for item in json.loads(packet.read_text())["originals"])
    original = Original(row)
    suffix = task.removeprefix(TASK_PREFIX)
    display = suffix in ("draw", "set_attributes")
    machine = DisplayMachine if display else Machine
    cases = display_args(suffix) if display else args_for(suffix)
    return dict(task=task, original=row,
                cases=[machine(original, case).execute(suffix) for case in cases])


if __name__ == "__main__":
    import sys

    print(json.dumps(observe(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent.name), indent=2))
