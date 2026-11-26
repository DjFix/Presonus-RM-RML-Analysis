"""Execute the native EQ8 lifecycle with pinned Core and runtime call boundaries."""

import argparse
import ctypes
import hashlib
import json
import struct
from pathlib import Path

import unicorn
from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM, Uc
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
    UC_ARM_REG_R3, UC_ARM_REG_SP,
)

REGISTERS = (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)
RECEIVER, OBSERVER, HEAP, STACK, STOP = 0x38000000, 0x39000000, 0x40000000, 0x60000000, 0x1000
GUARD, SINGLETON = 0x498198, 0x4981b8
BASE_CTOR, DEFAULTS, SET_VALUE = 0xc8d84, 0xb3388, 0xc4fd0
BASE_DTOR, DELETE, RELEASE = 0xb27e8, 0xac10, OBSERVER + 0x100
CTOR, COLD_CTOR = 0xc95c4, 0xc6044


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(packet, baseline_root):
    context = json.loads(packet.read_text())
    source = context["originals"][0]["original"]
    for path, digest in context["task"]["sources"].items():
        assert sha((baseline_root / path).read_bytes()) == digest, path
    image = Path(source["elf_path"]).read_bytes()
    assert sha(image) == source["elf"]
    with Path(source["elf_path"]).open("rb") as stream:
        elf = ELFFile(stream)
        table = elf.get_section_by_name(".symtab")

        def identity(symbol):
            address, size, index = [symbol[k] for k in ("st_value", "st_size", "st_shndx")]
            section = elf.get_section(index)
            offset = section["sh_offset"] + address - section["sh_addr"]
            body = image[offset:offset + size]
            result = dict(mangled=symbol.name, address=address, size=size, section=index,
                          section_name=section.name, file_offset=offset, range_sha256=sha(body))
            return result, body

        exact, = table.get_symbol_by_name(source["mangled"])
        verified, body = identity(exact)
        assert all(source[k] == v for k, v in verified.items())
        assert source["range_hex"] == body.hex()
        dependencies = [identity(s)[0] for s in table.iter_symbols()
                        if s["st_value"] in (BASE_CTOR, DEFAULTS, SET_VALUE, BASE_DTOR, CTOR, COLD_CTOR)
                        and s["st_info"]["type"] == "STT_FUNC"]
        segments = [(s["p_vaddr"], s["p_memsz"], s.data()) for s in elf.iter_segments()
                    if s["p_type"] == "PT_LOAD"]
    return source, dependencies, segments


class Oracle:
    def __init__(self, segments):
        self.machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        mapped = set()
        for base, span, data in segments:
            for page in range(base & -4096, (base + span + 4095) & -4096, 4096):
                if page not in mapped:
                    self.machine.mem_map(page, 4096)
                    mapped.add(page)
            self.machine.mem_write(base, data)
        for base, span in ((RECEIVER, 4096), (OBSERVER, 4096), (HEAP, 65536), (STACK, 4096)):
            self.machine.mem_map(base, span)
        self.machine.mem_map(STOP, 4096)
        self.machine.hook_add(UC_HOOK_CODE, self.observe)
        self.store(OBSERVER, OBSERVER + 16)
        self.store(OBSERVER + 24, RELEASE)
        self.next_heap = HEAP
        self.calls = []
        self.descriptors = []
        self.libc = ctypes.CDLL("libc.so.6")
        self.libc.malloc.argtypes = [ctypes.c_size_t]
        self.libc.malloc.restype = ctypes.c_void_p
        self.libc.free.argtypes = [ctypes.c_void_p]
        self.libc.free.restype = None
        self.receiver_allocation = self.libc.malloc(4096)
        self.libm = ctypes.CDLL("libm.so.6")
        self.returned = False

    def read(self, address, count=1):
        return struct.unpack(f"<{count}I", self.machine.mem_read(address, count * 4))

    def store(self, address, *values):
        self.machine.mem_write(address, struct.pack(f"<{len(values)}I", *values))

    def allocate(self, size):
        base = self.next_heap
        self.next_heap += (size + 15) & -16
        assert self.next_heap <= HEAP + 65536
        return base

    def observe(self, machine, pc, _size, _data):
        a, b, c, d = (machine.reg_read(reg) for reg in REGISTERS)
        result = None
        if pc == STOP:
            self.returned = True
            machine.emu_stop()
        elif pc == BASE_CTOR:
            assert a == RECEIVER and d == SINGLETON
            self.calls.append(["EQControllerC2", b, c])
        elif pc == COLD_CTOR:
            assert a == SINGLETON
            self.calls.append(["Eq8ExtParamListC1"])
        elif pc == DEFAULTS:
            assert a == RECEIVER and self.read(a)[0] == 0x35e470
            self.calls.append(["setDefaultValues", self.read(a + 0x2c)[0]])
        elif pc == SET_VALUE:
            assert a == RECEIVER
            self.descriptors.append([b, c])
        elif pc == BASE_DTOR:
            assert a == RECEIVER
            self.calls.append(["ControllerD2"])
        elif pc == RELEASE:
            assert a == OBSERVER
            self.calls.append(["release"])
            result = 0
        elif pc == DELETE:
            assert a == RECEIVER and self.receiver_allocation
            self.libc.free(self.receiver_allocation)
            self.receiver_allocation = None
            machine.mem_unmap(RECEIVER, 4096)
            self.calls.append(["receiver_deallocated"])
            result = 0
        elif pc in (0xb030, 0xaa3c, 0xadb4):
            if pc == 0xb030:
                result = int(self.read(a)[0] == 0)
            elif pc == 0xaa3c:
                self.store(a, 1)
                result = 0
            else:
                result = 0
        elif pc == 0xae98:
            result = 0
            while machine.mem_read(a + result, 1)[0]:
                result += 1
        elif pc in (0xae68, 0xab5c):
            machine.mem_write(a, bytes(machine.mem_read(b, c)))
            result = a
        elif pc == 0xaa60:
            machine.mem_write(a, bytes([b & 255]) * c)
            result = a
        elif pc == 0xafe8:
            value = bytes(machine.mem_read(b, c)).split(b"\0")[0]
            machine.mem_write(a, value.ljust(c, b"\0"))
            result = a
        elif pc == 0xa7e4:
            result = self.allocate(a)
        elif pc == 0xb6d7c:
            pointers, count, capacity, delta = self.read(a + 4, 4)
            if b != capacity and b:
                new_capacity = ((b - 1) // delta + 1) * delta
                new_pointers = self.allocate(new_capacity * 4)
                if count:
                    machine.mem_write(new_pointers, bytes(machine.mem_read(pointers, count * 4)))
                self.store(a + 4, new_pointers, count, new_capacity)
            result = 1
        elif pc in (0x110810, 0x112844):
            result = 0
        elif pc == 0x111a78:
            self.store(a, OBSERVER + 0x40)
            self.store(OBSERVER + 0x48, OBSERVER + 0x104)
            result = a
        elif pc == OBSERVER + 0x104:
            result = 0
        elif pc in (0xacac, 0xae5c, 0xae2c):
            name, arity = {0xacac: ("log10f", 1), 0xae5c: ("powf", 2), 0xae2c: ("expf", 1)}[pc]
            fn = getattr(self.libm, name)
            fn.argtypes = [ctypes.c_float] * arity
            fn.restype = ctypes.c_float
            result = struct.unpack("<I", struct.pack("<f", fn(
                *(struct.unpack("<f", struct.pack("<I", v))[0] for v in [a, b][:arity]))))[0]
        elif pc < 0xb100:
            raise RuntimeError(f"Unmodeled native boundary at {pc:#x} from {machine.reg_read(UC_ARM_REG_LR):#x}, args {a:#x} {b:#x} {c:#x}")
        if result is not None:
            machine.reg_write(UC_ARM_REG_R0, result)
            machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

    def run(self, address, *args):
        self.returned = False
        self.machine.reg_write(UC_ARM_REG_SP, STACK + 4096)
        self.machine.reg_write(UC_ARM_REG_LR, STOP)
        for reg, value in zip(REGISTERS, args):
            self.machine.reg_write(reg, value)
        self.machine.emu_start(address, STOP + 4, count=300_000)
        assert self.returned, hex(address)

    def close(self):
        if self.receiver_allocation:
            self.libc.free(self.receiver_allocation)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("packet", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--baseline-root", type=Path, default=Path("."))
    args = parser.parse_args()
    source, dependencies, segments = load(args.packet, args.baseline_root)
    cases = []
    construction = "ControllerC" in source["mangled"]
    for identifier in (0, 8, 0xffffffff):
        oracle = Oracle(segments)
        try:
            if construction and identifier == 8:
                oracle.run(CTOR, RECEIVER, 0)
                oracle.calls.clear()
                oracle.descriptors.clear()
            oracle.run(source["address"] if construction else CTOR, RECEIVER, identifier)
            assert oracle.read(RECEIVER + 0x18)[0] == identifier
            count = oracle.read(RECEIVER + 0x2c)[0]
            case = dict(identifier=identifier, bands=count,
                        descriptor_count=oracle.read(SINGLETON + 8)[0],
                        descriptors=oracle.descriptors)
            if construction:
                conversions = {
                    0xc540c: [*range(17), 0x7fffffff, 0xffffffff],
                    0xc5444: [*range(12), 0x7fffffff],
                }
                case["conversions"] = []
                for address, inputs in conversions.items():
                    results = []
                    for value in inputs:
                        oracle.run(address, RECEIVER, value)
                        results.append([value, oracle.machine.reg_read(UC_ARM_REG_R0)])
                    case["conversions"].append(results)
                case["enabled"] = oracle.machine.mem_read(RECEIVER + 0xa30, 1)[0]
                case["dirty"] = oracle.machine.mem_read(RECEIVER + 0x1c, 1)[0]
                case["band_words"] = [
                    list(oracle.read(RECEIVER + 0x30 + 0x140 * index, 4))
                    + list(reversed(oracle.machine.mem_read(RECEIVER + 0x30 + 0x140 * index + 0x138, 3)))
                    + [oracle.machine.mem_read(RECEIVER + 0x30 + 0x140 * index + 0x58, 1)[0]]
                    for index in range(count)
                ]
            else:
                if identifier:
                    oracle.store(RECEIVER + 0x14, OBSERVER)
                if identifier == 0xffffffff:
                    oracle.machine.mem_write(RECEIVER + 0x1d, b"\x01")
                oracle.calls.clear()
                oracle.run(source["address"], RECEIVER)
                case["receiver_deallocated"] = oracle.receiver_allocation is None
                if case["receiver_deallocated"]:
                    try:
                        oracle.read(RECEIVER)
                    except unicorn.UcError as error:
                        assert error.errno == unicorn.UC_ERR_READ_UNMAPPED
                    else:
                        raise RuntimeError("Receiver remains mapped after native delete")
                if oracle.receiver_allocation:
                    assert oracle.read(RECEIVER + 0x14) == (0,)
            if construction:
                observed = oracle.calls
                assert observed[-2:] == [["EQControllerC2", count, identifier],
                                         ["setDefaultValues", count]]
                assert (["Eq8ExtParamListC1"] in observed) == (identifier != 8)
            case["native_calls"] = oracle.calls
            cases.append(case)
        finally:
            oracle.close()

    fixture = dict(version=1, original=source, dependencies=dependencies,
                   native_producer_sha256=sha(Path(__file__).read_bytes()),
                   packet_sha256=sha(args.packet.read_bytes()), unicorn=unicorn.__version__,
                   cases=cases)
    args.output.write_text(json.dumps(fixture, indent=2) + "\n")


if __name__ == "__main__":
    main()
