"""Execute the named ARM entries against independently arranged CCL state."""

import hashlib
import io
import json
import struct
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (
    UC_ARM_REG_LR as LR, UC_ARM_REG_PC as PC, UC_ARM_REG_R0 as R0,
    UC_ARM_REG_R1 as R1, UC_ARM_REG_SP as SP,
)

SLOT = "13DAWDeviceSlot"
FOLDER = "15DAWDeviceFolder"
RECEIVER = 0x51001000
PARENT = 0x51002000
CHILDREN = 0x51003000
PARAMETERS = 0x51004000
STOP = 0x5200FF00
BASE_CTOR = "_ZN4Core8Portable9ComponentC2EPKc"
CLIENT_CTOR = "_ZN8Presonus2UC15ClientComponentC2EPKc"
BASE_DTOR = "_ZN4Core8Portable9ComponentD2Ev"
FEEDBACK = "_ZN4Core8Portable9Parameter17setFeedbackNeededEb"
FIND = "_ZNK4Core8Portable9ParamList4findEPKc"
BY_TAG = "_ZNK4Core8Portable9ParamList5byTagEi"
GET_VALUE = "_ZNK4Core8Portable12NumericParam8getValueEv"
GET_USED = "_ZNK8Presonus15DAWDeviceFolder12getUsedCountEv"
GET_FOLDER = "_ZNK8Presonus13DAWDeviceSlot9getFolderEv"
CAST_SLOT = "_ZN8Presonus13DAWDeviceSlot6castToEi"
CAST_FOLDER = "_ZN8Presonus15DAWDeviceFolder6castToEi"
INIT_SLOT = "_ZN8Presonus13DAWDeviceSlot4initEv"
INIT_FOLDER = "_ZN8Presonus15DAWDeviceFolder4initEv"
CAST_BASE = "_ZN4Core8Portable9Component6castToEi"


def digest(data):
    return hashlib.sha256(data).hexdigest()


@lru_cache(maxsize=2)
def read_elf(path):
    raw = Path(path).read_bytes()
    elf = ELFFile(io.BytesIO(raw))
    syms = {sym.name: sym for sym in elf.get_section_by_name(".symtab").iter_symbols()
            if sym.name}
    rel = elf.get_section_by_name(".rel.plt")
    dynsym = elf.get_section(rel["sh_link"])
    plt = elf.get_section_by_name(".plt")
    assert plt["sh_size"] == 20 + 12 * rel.num_relocations()
    imports = {dynsym.get_symbol(reloc["r_info_sym"]).name:
               plt["sh_addr"] + 20 + index * 12
               for index, reloc in enumerate(rel.iter_relocations())}
    return elf, syms, imports, digest(raw)


def check_range(original):
    elf, symbols, _, sha = read_elf(original["elf_path"])
    assert sha == original["elf"]
    sym = symbols[original["mangled"]]
    assert sym["st_shndx"] == original["section"]
    assert sym["st_value"] == original["address"]
    assert sym["st_size"] == original["size"]
    sec = elf.get_section(sym["st_shndx"])
    delta = sym["st_value"] - sec["sh_addr"]
    assert sec.name == original["section_name"]
    assert 0 <= delta <= delta + sym["st_size"] <= sec["sh_size"]
    assert sec["sh_offset"] + delta == original["file_offset"]
    raw = sec.data()[delta:delta + sym["st_size"]]
    assert raw.hex() == original["range_hex"] and digest(raw) == original["range_sha256"]


def word(value):
    return struct.pack("<I", value & 0xFFFFFFFF)


def signed(value):
    return struct.unpack("<i", word(value))[0]


@dataclass
class Allocation:
    size: int
    live: bool = True


class Machine:
    def __init__(self, original):
        elf, self.symbols, imports, _ = read_elf(original["elf_path"])
        self.uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        segments = [s for s in elf.iter_segments() if s["p_type"] == "PT_LOAD"]
        start = min(s["p_vaddr"] for s in segments) & ~0xFFF
        end = max(s["p_vaddr"] + s["p_memsz"] for s in segments)
        self.uc.mem_map(start, ((end + 0xFFF) & ~0xFFF) - start)
        for seg in segments:
            self.uc.mem_write(seg["p_vaddr"], seg.data())
        self.uc.mem_map(0x51000000, 0x10000)
        self.uc.mem_map(0x52000000, 0x10000)
        self.allocations = {}
        self.events = []
        self.import_hooks = {imports[n]: n for n in ("strlen", "strcmp", "_ZdlPv", "_ZdaPv", "free")
                             if n in imports}
        self.around = {
            self.address(name): name for name in (
                CLIENT_CTOR, BASE_CTOR, BASE_DTOR, FEEDBACK, FIND, BY_TAG,
                GET_VALUE, CAST_SLOT, CAST_FOLDER, CAST_BASE, INIT_SLOT, "__aeabi_f2iz"
            )
        }
        for address in sorted(set(self.around) | set(self.import_hooks)):
            self.uc.hook_add(UC_HOOK_CODE, self.trace, begin=address, end=address)

    def address(self, name):
        return self.symbols[name]["st_value"]

    def store(self, address, value):
        self.uc.mem_write(address, word(value))

    def load(self, address):
        return struct.unpack("<I", self.uc.mem_read(address, 4))[0]

    def string(self, address):
        data = bytes(self.uc.mem_read(address, 64))
        assert b"\0" in data
        return data.split(b"\0", 1)[0].decode("ascii")

    def trace(self, uc, address, size, data):
        first, second = uc.reg_read(R0), uc.reg_read(R1)
        if address in self.import_hooks:
            name = self.import_hooks[address]
            if name == "strlen":
                uc.reg_write(R0, len(self.string(first)))
            elif name == "strcmp":
                uc.reg_write(R0, int(self.string(first) != self.string(second)))
            else:
                self.events.append([name, first])
                if first:
                    self.release(first)
        else:
            name = self.around[address]
            detail = [name, first]
            if name in (CLIENT_CTOR, BASE_CTOR, FIND):
                detail.extend([second, self.string(second)])
            elif name == BASE_DTOR:
                detail.extend([self.load(first), self.load(first + 4)])
            elif name in (FEEDBACK, BY_TAG, CAST_SLOT, CAST_FOLDER, CAST_BASE):
                detail.append(second)
            self.events.append(detail)
            return
        uc.reg_write(PC, uc.reg_read(LR))

    def release(self, address):
        allocation = self.allocations[address]
        assert allocation.live, (address, self.events)
        allocation.live = False
        self.uc.mem_protect(address, allocation.size, 0)

    def invoke(self, name, receiver, argument=0):
        self.uc.reg_write(R0, receiver)
        self.uc.reg_write(R1, argument & 0xFFFFFFFF)
        self.uc.reg_write(SP, STOP - 0x100)
        self.uc.reg_write(LR, STOP)
        self.uc.emu_start(self.address(name), STOP, count=25000)
        assert self.uc.reg_read(PC) == STOP and self.uc.reg_read(SP) == STOP - 0x100
        return self.uc.reg_read(R0)

    def construct(self, cls, receiver, fill=0x55, variant="C1"):
        self.uc.mem_write(receiver, bytes([fill]) * 0x88)
        if cls:
            return self.invoke(f"_ZN8Presonus{cls}{variant}Ev", receiver)
        return self.invoke("_ZN4Core8Portable9ComponentC1EPKc", receiver)

    def parameter(self, address, name, tag, value):
        vtable = self.address("_ZTVN4Core8Portable12NumericParamE") + 8
        assert self.load(vtable + 0x44) == self.address(GET_VALUE)
        self.store(address, vtable)
        self.store(address + 4, 0)
        self.store(address + 0xC, address + 0x200)
        self.store(address + 0x204, tag)
        self.uc.mem_write(address + 0x208, name.encode("ascii") + b"\0")
        # NumericParam::getValue has the same value slot in both role images.
        self.uc.mem_write(address + 0x2C, struct.pack("<f", value))

    def parameters(self, receiver, addresses, array=None):
        array = array or receiver + 0x190
        self.store(receiver + 0x34, array if addresses else 0)
        self.store(receiver + 0x38, len(addresses))
        self.store(receiver + 0x3C, len(addresses))
        self.store(receiver + 0x4C, 0)  # Use the native unsorted lookup path.
        for index, address in enumerate(addresses):
            self.store(array + index * 4, address)

    def children(self, receiver, addresses, array=None):
        array = array or receiver + 0x1C0
        self.store(receiver + 0x58, array if addresses else 0)
        self.store(receiver + 0x5C, len(addresses))
        self.store(receiver + 0x60, len(addresses))
        for index, address in enumerate(addresses):
            self.store(array + index * 4, address)

    def feedback(self, parameter):
        flags = self.load(parameter + 4)
        assert flags & ~8 == 0
        return int(bool(flags & 8))


def cases(name):
    if name.endswith(("C1Ev", "C2Ev")):
        return [(0x55,), (0xAA,)]
    if name.endswith(("D0Ev", "D1Ev")):
        return [(0,), (1,)]
    if name in (CAST_SLOT, CAST_FOLDER):
        ids = [0x64774453, 0x64774446, 0x436C436F, 0x436F6D70]
        return [(n,) for n in sorted({0, -(2**31), 2**31-1,
                                     *(x + delta for x in ids for delta in (-1, 0, 1))})]
    if name == GET_FOLDER:
        return [(0,), (1,), (2,)]
    if name in (INIT_SLOT, INIT_FOLDER):
        return [(0,), (1,), (2,), (3,)]
    assert name == GET_USED
    return [(0, 0, 0), (0, 3, 0), (1, 0, 2.75), (1, 1, 1),
            (1, 1, -1.75), (1, 3, 9.25), (1, 3, 2.75),
            (1, 3, -2.75), (1, 3, -0.75)]


def execute_case(m, name, args):
    receiver = RECEIVER
    cls = SLOT if SLOT in name else FOLDER
    vptr = m.address(f"_ZTVN8Presonus{cls}E") + 8
    parm, other = PARAMETERS, PARAMETERS + 0x800
    if name.endswith(("C1Ev", "C2Ev")):
        result = m.construct(cls, receiver, *args, variant=name[-4:-2])
        constructors = [row for row in m.events if row[0] in (CLIENT_CTOR, BASE_CTOR)]
        assert [row[0] for row in constructors] == [CLIENT_CTOR, BASE_CTOR]
        assert all(row[1] == receiver and row[3] == "" for row in constructors)
        assert [m.load(receiver), m.load(receiver + 4)] == [vptr, vptr + 0x3C]
        return [int(result == receiver), len(m.string(receiver + 8)),
                int(m.load(receiver + 0x84) == 0), int(m.load(receiver + 0x50) == 0),
                m.load(receiver + 0x5C), m.load(receiver + 0x38)]
    if name.endswith(("D0Ev", "D1Ev")):
        m.construct(cls, receiver)
        m.allocations[receiver] = Allocation(0x1000)
        m.store(receiver, 0xAA112233)
        m.store(receiver + 4, 0xBB112233)
        if args[0]:
            m.construct(SLOT, CHILDREN)
            m.allocations[CHILDREN] = Allocation(0x1000)
            m.allocations[parm] = Allocation(0x1000)
            m.parameter(parm, "edit", 2, 0)
            parameter_array, child_array = 0x51007000, 0x51008000
            m.allocations[parameter_array] = Allocation(0x1000)
            m.allocations[child_array] = Allocation(0x1000)
            m.parameters(receiver, [parm], parameter_array)
            m.children(receiver, [CHILDREN], child_array)
        m.events.clear()
        m.invoke(name, receiver)
        base = [row for row in m.events if row[0] == BASE_DTOR and row[1] == receiver]
        vptr = m.address("_ZTVN8Presonus2UC15ClientComponentE") + 8
        assert base == [[BASE_DTOR, receiver, vptr, vptr + 0x3C]]
        deleting = name.endswith("D0Ev")
        assert (not m.allocations[receiver].live) == deleting
        if deleting:
            assert m.events[-1] == ["_ZdlPv", receiver]
        if args[0]:
            assert all(not allocation.live for address, allocation in m.allocations.items()
                       if address != receiver)
        return [int(not m.allocations[receiver].live),
                sum(row == ["_ZdlPv", receiver] for row in m.events),
                sum(row == ["_ZdlPv", CHILDREN] for row in m.events),
                sum(row == ["_ZdlPv", parm] for row in m.events)]
    if name in (CAST_SLOT, CAST_FOLDER):
        m.construct(cls, receiver)
        m.events.clear()
        result = m.invoke(name, receiver, args[0])
        assert result in (0, receiver)
        return [int(result == receiver)]
    if name == GET_FOLDER:
        m.construct(SLOT, receiver)
        if args[0]:
            m.construct(FOLDER if args[0] > 1 else None, PARENT)
            m.store(receiver + 0x50, PARENT)
        m.events.clear()
        result = m.invoke(name, receiver)
        assert result in (0, PARENT)
        assert all(row[1:] == [PARENT, 0x64774446] for row in m.events
                   if row[0] in (CAST_FOLDER, CAST_BASE))
        return [int(result == PARENT),
                sum(row[0] in (CAST_FOLDER, CAST_BASE) for row in m.events)]
    if name == INIT_SLOT:
        m.construct(SLOT, receiver)
        m.parameter(parm, "edit", 1, 0)
        m.parameter(other, "other", 2, 0)
        m.parameters(receiver, [[], [other], [other, parm], [parm]][args[0]])
        m.events.clear()
        for _ in range(2 if args[0] == 3 else 1):
            m.invoke(name, receiver)
        assert all(row[1] == receiver + 0x28 and row[3] == "edit"
                   for row in m.events if row[0] == FIND)
        assert m.load(receiver + 0x84) == (parm if args[0] >= 2 else 0)
        return [m.feedback(parm), m.feedback(other)]
    if name == INIT_FOLDER:
        m.construct(FOLDER, receiver)
        m.construct(SLOT, CHILDREN)
        m.construct(None, CHILDREN + 0x200)
        m.construct(SLOT, CHILDREN + 0x400)
        m.parameter(parm, "count", 0, 2.75)
        m.parameter(other, "edit", 1, 0)
        slot_other = other + 0x400
        m.parameter(slot_other, "other", 7, 0)
        m.parameters(receiver, [parm])
        m.parameters(CHILDREN, [other])
        m.parameters(CHILDREN + 0x400, [slot_other])
        children = [[], [CHILDREN], [CHILDREN + 0x200, CHILDREN, CHILDREN + 0x400],
                    [CHILDREN + 0x200, 0, CHILDREN, CHILDREN + 0x400]][args[0]]
        m.children(receiver, children)
        m.events.clear()
        m.invoke(name, receiver)
        assert [row[1] for row in m.events if row[0] in (CAST_SLOT, CAST_BASE)] == [
            child for child in children if child
        ]
        assert m.load(receiver + 0x84) == parm
        return [m.feedback(parm), m.feedback(other), m.feedback(slot_other),
                sum(row[0] == CAST_BASE for row in m.events)]
    assert name == GET_USED
    cache, count, value = args
    m.construct(FOLDER, receiver)
    m.parameter(parm, "count", 0, value)
    m.parameters(receiver, [parm])
    if cache:
        m.invoke(INIT_FOLDER, receiver)
    m.store(receiver + 0x5C, count)
    m.events.clear()
    return [signed(m.invoke(name, receiver))]


def observations(packet):
    originals = []
    for row in packet["originals"]:
        original = row["original"]
        check_range(original)
        results = []
        for args in cases(original["mangled"]):
            machine = Machine(original)
            output = execute_case(machine, original["mangled"], args)
            results.append(dict(args=list(args), output=output, native_trace=machine.events))
        originals.append(dict(original=original, cases=results))
    return originals
