"""Replay the sealed ARM routines, retaining runtime and source-provider boundaries."""
import argparse
import ctypes
import hashlib
import io
import itertools
import json
import struct
import subprocess
from pathlib import Path

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (
    UC_ARM_REG_CPSR, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
    UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC,
)

TASKS = {
    "update": "af797352ac55",
    "get": "382dbbcfe3da",
    "set": "65cb39e53e2f",
    "setup": "167ed6380220",
    "C1": "d72f4dcdda6c",
    "C2": "6fa2636334af",
    "D1": "1fdc38b2b9a9",
    "D0": "23ca35199f5b",
}
REGS = [UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3]
STOP, SELF, TARGET, VTABLE, PROPERTY = 0x600000, 0x610000, 0x611000, 0x612000, 0x613000
SEND, RELEASE, STACK = 0x600100, 0x600200, 0x62f000
LIST, GUARD, LIST_ARRAY = 0x497fac, 0x493e70, 0x616000
OFFSETS = [0x1c, 0x20, 0x58, 0x5c, 0x60, 0x3c, 0x40, 0x44, 0x48, 0x64, 0x68, 0x74]
MATH = {
    0xa820: ("sqrt", "d", 1), 0xaa30: ("cos", "d", 1),
    0xab50: ("pow", "d", 2), 0xacac: ("log10f", "f", 1),
    0xae2c: ("expf", "f", 1), 0xae5c: ("powf", "f", 2),
    0xae74: ("tan", "d", 1), 0xb06c: ("sin", "d", 1),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def packed(*words):
    return struct.pack("<" + "I" * len(words), *(word & 0xffffffff for word in words))


def words(data):
    return list(struct.unpack("<" + "I" * (len(data) // 4), data))


def bits(value):
    return words(struct.pack("<f", value))[0]


def inputs(mode):
    state = [0, 16, 0, 0, 0, bits(.01), bits(10), bits(.005), bits(.7), 7,
             bits(1200), bits(.8)]
    if mode == "get":
        variants = [0, 0x80000000, 0x33877f3e, 0x33877f3f, 0x33877f40,
                    bits(.25), bits(2), 0x7f7fffff, 0x7f800000, 0xff800000,
                    0x7fc00001]
        for tag, value in itertools.product([-2147483648, -1, *range(11), 2147483647],
                                            variants):
            x = state.copy()
            x[2:5] = [value] * 3
            for i in [5, 6, 7, 8, 10, 11]:
                x[i] = value
            yield [*x, tag & 0xffffffff]
    elif mode == "set":
        variants = [0, 0x80000000, bits(-144) + 1, bits(-144), bits(-144) - 1,
                    bits(144) - 1, bits(144), bits(144) + 1, bits(.1),
                    bits(40) - 1, bits(40), 0x42200106, 0x42200107,
                    0x7f7fffff, 0x7f800000, 0xff800000, 0x7fc00001]
        for tag, value, flags in itertools.product(
                [-2147483648, -1, *range(11), 2147483647], variants,
                [(0, 0), (7, 0), (0, 3)]):
            x = state.copy()
            x[0], x[2] = flags
            yield [*x, tag & 0xffffffff, value]
    elif mode == "setup":
        for old, rate, dirty, block in itertools.product(
                [44100., 48000., 96000.], [44100., 48000., 96000.],
                [0, 9], [16, 128]):
            yield [bits(old), 64, dirty, bits(rate), block]
    elif mode == "update":
        for rate, mode_word, on, expander, key, target, quick in itertools.product(
                [44100., 96000.], [7, -1], [0, 1], [0, 1], [0, 1], [0, 1],
                [0, 1]):
            x = state.copy()
            x[2:5] = [on, expander, key]
            x[9] = mode_word & 0xffffffff
            if quick:
                x[5:9] = [bits(.000064), bits(17782.), bits(0.), bits(.00002)]
            yield [bits(rate), 64, *x, 0xfedcab98 if quick else 23, target]
    elif mode in ("C1", "C2"):
        yield from ([v & 0xffffffff, warm] for v, warm in
                    itertools.product([-2147483648, -1, 17, 2147483647], [0, 1]))
    else:
        yield from ([target] for target in range(3))


class Image:
    def __init__(self, packet):
        self.raw = Path(packet["elf_path"]).read_bytes()
        assert sha(self.raw) == packet["elf"]
        elf = ELFFile(io.BytesIO(self.raw))
        symbols = list(elf.get_section_by_name(".symtab").iter_symbols())
        matching = [s for s in symbols if s.name == packet["mangled"]]
        assert len(matching) == 1
        symbol = matching[0]
        start, size, index = (symbol[k] for k in ("st_value", "st_size", "st_shndx"))
        assert (start, size, index) == (packet["address"], packet["size"], packet["section"])
        section = elf.get_section(index)
        offset = section["sh_offset"] + start - section["sh_addr"]
        body = self.raw[offset:offset + size]
        assert section.name == packet["section_name"] == ".text"
        assert (offset, sha(body), body.hex()) == (packet["file_offset"], packet["range_sha256"],
                                                packet["range_hex"])
        self.segments = [(s["p_vaddr"], s.data()) for s in elf.iter_segments()
                         if s["p_type"] == "PT_LOAD"]
        self.allowed = {}
        for s in symbols:
            n = s.name
            if s["st_shndx"] == index and s["st_size"] and (
                n.startswith(("_ZN8Presonus3Dsp14GateController", "_ZNK8Presonus3Dsp14GateController",
                              "_ZN8Presonus3Dsp10Controller", "_ZNK8Presonus3Dsp10Controller",
                              "_ZN3DSP10BiquadCalcIdLb0EE", "__aeabi_", "__mulsf", "__divsf",
                              "__adddf", "__subdf", "__muldf", "__divdf", "__nesf", "__nedf", "__eqsf", "__eqdf", "__lesf", "__gesf", "__ledf", "__gedf", "__gtsf", "__ltdf", "__ltsf", "__gtdf", "__fix", "__float", "__extend", "__trunc"))
                or n.startswith("_ZN3DSP13BiquadCoeffsT")):
                self.allowed[s["st_value"]] = (s["st_size"], n)
        self.names = {s["st_value"]: s.name for s in symbols if s.name and s["st_value"]}


class Trial:
    def __init__(self, image, descriptors):
        self.u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        self.u.mem_map(0, 0x500000)
        self.u.mem_map(0x600000, 0x30000)
        for address, data in image.segments:
            self.u.mem_write(address, data)
        self.image = image
        self.descriptors = list(zip(descriptors[::2], descriptors[1::2]))
        self.calls, self.writes, self.events, self.property = [], [], [], []
        self.entered = set()
        self.libm = ctypes.CDLL("libm.so.6")
        self.libc = ctypes.CDLL("libc.so.6")
        self.libc.malloc.argtypes = [ctypes.c_size_t]
        self.libc.malloc.restype = ctypes.c_void_p
        self.libc.free.argtypes = [ctypes.c_void_p]
        self.allocations = {}
        self.u.hook_add(UC_HOOK_CODE, self.code)
        self.u.hook_add(UC_HOOK_MEM_WRITE, self.write)
        self.put(TARGET, VTABLE)
        self.put(VTABLE, SEND, 0, RELEASE)

    def put(self, address, *data):
        self.u.mem_write(address, packed(*data))

    def word(self, address):
        return words(self.u.mem_read(address, 4))[0]

    def alloc(self, address):
        p = self.libc.malloc(0x200)
        assert p and address not in self.allocations
        self.allocations[address] = p

    def free(self, address):
        self.libc.free(self.allocations.pop(address))

    def install_descriptors(self, address):
        records = [LIST_ARRAY + 0x100 + 0x100 * j for j in range(len(self.descriptors))]
        self.put(address + 4, LIST_ARRAY, len(records))
        self.put(LIST_ARRAY, *records)
        for record, (tag, default) in zip(records, self.descriptors):
            self.put(record, tag)
            self.put(record + 0x14, default)

    def ret(self, *result):
        for reg, word in zip(REGS, result):
            self.u.reg_write(reg, word)
        self.u.reg_write(UC_ARM_REG_PC, self.u.reg_read(UC_ARM_REG_LR))

    def write(self, u, access, address, size, value, _):
        if SELF <= address < SELF + 0x200:
            self.writes.append([address - SELF, size, value & ((1 << (8 * size)) - 1)])

    def code(self, u, address, size, _):
        args = [u.reg_read(reg) for reg in REGS]
        a, b, c, _ = args
        if address in MATH:
            name, fmt, count = MATH[address]
            kind = ctypes.c_float if fmt == "f" else ctypes.c_double
            func = getattr(self.libm, name)
            func.argtypes, func.restype = [kind] * count, kind
            n = count * (1 if fmt == "f" else 2)
            result = words(struct.pack("<" + fmt, func(*struct.unpack(
                "<" + fmt * count, packed(*args[:n])))))
            self.calls.append([name, args[:n], result])
            self.ret(*result)
        elif address == SEND:
            assert a == TARGET
            self.property = words(u.mem_read(b, 72))
            self.calls.append(["target.setProperty", self.property])
            self.ret()
        elif address == RELEASE:
            assert a == TARGET and a in self.allocations
            self.free(a)
            self.events.append(1)
            self.calls.append(["target.release", a])
            self.ret()
        elif address == 0xac10:
            assert a == SELF and a in self.allocations
            self.free(a)
            self.events.append(2)
            self.calls.append(["operator delete(void*)", a])
            self.ret()
        elif address == 0xb030:
            assert a == GUARD
            self.calls.append(["guard.acquire", a])
            self.ret(int(self.word(a) == 0))
        elif address == 0xaa3c:
            assert a == GUARD
            self.put(a, 1)
            self.calls.append(["guard.release", a])
            self.ret()
        elif address == 0xadb4:
            assert a == LIST and b == 0xbd450 and c == 0x4539f4
            self.calls.append(["__aeabi_atexit", args[:3]])
            self.ret(0)
        elif address == 0xb84bc:
            assert a == LIST
            self.install_descriptors(a)
            self.calls.append(["GateParamList provider descriptors", self.descriptors])
            self.ret(a)
        elif address == 0xae68:
            u.mem_write(a, bytes(u.mem_read(b, c)))
            self.calls.append(["memcpy", args[:3]])
            self.ret(a)
        else:
            allowed = self.image.allowed.get(address)
            if allowed and address not in self.entered:
                self.entered.add(address)
            if address in (0xbb3e0, 0xbb514, 0xb9718, 0xb9518,
                           0xb744c, 0xb27e8, 0xb2664, 0xb29d8, 0xb3388):
                self.calls.append([self.image.names[address], args,
                                   self.word(u.reg_read(UC_ARM_REG_SP))])
            if not any(start <= address < start + self.image.allowed[start][0]
                       for start in self.entered):
                raise RuntimeError(f"Unbound code at {address:#x} ({self.image.names.get(address)})")

    def run(self, start, *args):
        self.u.reg_write(UC_ARM_REG_CPSR, 0x10)
        for reg, value in zip(REGS, [*args, 0, 0, 0, 0]):
            self.u.reg_write(reg, value)
        self.u.reg_write(UC_ARM_REG_SP, STACK)
        self.u.reg_write(UC_ARM_REG_LR, STOP)
        self.u.emu_start(start, STOP, count=250000)
        assert self.u.reg_read(UC_ARM_REG_PC) == STOP
        assert self.u.reg_read(UC_ARM_REG_SP) == STACK
        return self.u.reg_read(UC_ARM_REG_R0)

    def seed(self, x):
        for offset, word in zip(OFFSETS, x):
            if offset == 0x1c:
                self.u.mem_write(SELF + offset, bytes([word]))
            else:
                self.put(SELF + offset, word)

    def state(self):
        state = [self.word(SELF + offset) for offset in OFFSETS]
        state[0] &= 255
        return state

    def filter(self, rate_set):
        start = SELF + 0x78
        def narrow(offset):
            value, = struct.unpack("<d", self.u.mem_read(start + offset, 8))
            return bits(value)
        return ([self.word(start + p) for p in (0x50, 0x54, 0x4c)] +
                [narrow(p) for p in ([0x58] if rate_set else []) + [
                    0x68, 0x70, 0x60, 0x78, 0x80, 0x88, 0x90, 0x98, 0xb8,
                    0x0, 0x18, 0x30]])

    def setup(self, start, rate, block):
        self.put(PROPERTY, 1399157877, 28, rate, block, 1, 1, 0)
        self.run(start, SELF, PROPERTY)

    def case(self, mode, original, x):
        if mode in ("C1", "C2"):
            if x[1]:
                self.run(0xb92c0, SELF, 17)
        else:
            self.run(0xb92c0, SELF, 17)
        self.calls.clear()
        self.writes.clear()
        self.entered.clear()
        if mode in ("C1", "C2"):
            self.u.mem_write(SELF, b"\xcc" * 0x200)
            self.run(original, SELF, x[0])
            expected = (self.state() + [self.word(SELF + 0x18),
                                         self.word(self.word(SELF + 0x0c) + 8)]
                        + self.filter(False))
        elif mode in ("D1", "D0"):
            if mode == "D0":
                self.alloc(SELF)
            if x[0]:
                self.put(SELF + 0x14, TARGET)
            if x[0] == 1:
                self.alloc(TARGET)
                self.u.mem_write(SELF + 0x1d, b"\x01")
            self.run(original, SELF)
            assert self.word(SELF + 0x14) == 0
            assert not self.allocations
            expected = self.events
        elif mode in ("get", "set"):
            self.seed(x[:12])
            before = bytes(self.u.mem_read(SELF, 0x200))
            value = self.run(original, SELF, *x[12:])
            expected = self.state()
            if mode == "get":
                assert before == bytes(self.u.mem_read(SELF, 0x200))
                expected.append(value)
            else:
                assert all(w[0] in OFFSETS for w in self.writes)
        elif mode == "setup":
            self.setup(original, *x[:2])
            self.u.mem_write(SELF + 0x1c, bytes([x[2]]))
            self.calls.clear()
            self.writes.clear()
            self.setup(original, *x[3:])
            expected = [self.word(SELF + 0x24), self.word(SELF + 0x1c) & 255] + self.filter(True)
        else:
            self.setup(0xb7644, *x[:2])
            self.seed(x[2:14])
            self.put(SELF + 4, x[14])
            if x[15]:
                self.put(SELF + 0x14, TARGET)
            self.calls.clear()
            self.writes.clear()
            self.run(original, SELF)
            expected = (self.state() + words(self.u.mem_read(SELF + 0x28, 20))
                        + words(self.u.mem_read(SELF + 0x4c, 12))
                        + self.filter(True) + self.property)
        call_names = [call[0] for call in self.calls]
        if mode in ("C1", "C2"):
            assert call_names.count("GateParamList provider descriptors") == 1 - x[1]
            assert call_names.count("__aeabi_atexit") == 1 - x[1]
            default_calls = [call[1][1:3] for call in self.calls
                             if call[0] == "_ZN8Presonus3Dsp14GateController8setValueEif"]
            assert default_calls == [list(pair) for pair in self.descriptors]
        elif mode == "setup":
            assert call_names.count("_ZN3DSP10BiquadCalcIdLb0EE5setupEid") == (x[0] != x[3])
        elif mode == "update":
            assert call_names.count("_ZN3DSP10BiquadCalcIdLb0EE9setParamsEifff") == 1
            assert call_names.count("target.setProperty") == x[15]
        return {"input": x, "expected": expected, "calls": self.calls, "writes": self.writes}


def generate(mode, executable, small=False):
    packet = Path(f"temp/recovery-work/sqlite-issued/packet/sqlite04_gate_{TASKS[mode]}/CONTEXT.json")
    original = json.loads(packet.read_bytes())["originals"][0]["original"]
    image = Image(original)
    descriptors = [int(v) for v in subprocess.check_output(
        [executable], input="descriptors 0\n", text=True).split()]
    assert len(descriptors) % 2 == 0
    cases = inputs(mode)
    if small:
        cases = itertools.islice(cases, 1)
    return {
        "mode": mode, "range": original, "packet_sha256": sha(packet.read_bytes()),
        "producer_sha256": sha(Path(__file__).read_bytes()),
        "unicorn_version": unicorn.__version__,
        "cases": [Trial(image, descriptors).case(mode, original["address"], x) for x in cases],
        "limitations": [
            "Original application and compiler soft-float bodies execute. The host libm and memory transfer replace dynamic runtime imports at recorded PLT entries.",
            "The verified portable GateParamList and real EQ/Compressor/Gate CCL startup supply descriptor records at the native provider boundary. No Core firmware body executes. Single-threaded singleton guard and registration are modeled.",
            "The native synthetic target releases actual host-allocator memory; the verified native unsized-delete import receives the object token and frees its host allocation. Portable replay sees actual C++ target release and receiver deletion.",
            "No claim of original declarations, binary layout, ARM interoperability, hardware behavior, unset-rate updates or exceptional unwinding.",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=TASKS)
    parser.add_argument("executable")
    parser.add_argument("output", type=Path)
    parser.add_argument("--small", action="store_true")
    args = parser.parse_args()
    fixture = generate(args.mode, args.executable, args.small)
    args.output.write_text(json.dumps(fixture, separators=(",", ":")) + "\n")
    print(args.mode, len(fixture["cases"]), "native cases")
