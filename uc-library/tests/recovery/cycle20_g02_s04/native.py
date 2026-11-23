"""Run the exact CS18 attribute loader and lookup with explicit provider boundaries."""
import hashlib
import json
import struct
import sys
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP,
)

elf_path = Path(sys.argv[1])
elf_hash = "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0"
mangled = "_ZN8Presonus17MeterScaleControl13setAttributesERKN4Core8Portable10AttributesE"
with elf_path.open("rb") as stream:
    assert hashlib.file_digest(stream, "sha256").hexdigest() == elf_hash
    stream.seek(0)
    elf = ELFFile(stream)
    symbols = elf.get_section_by_name(".symtab")

    def symbol_range(name):
        symbol, = symbols.get_symbol_by_name(name)
        section = elf.get_section(symbol["st_shndx"])
        start, size = symbol["st_value"], symbol["st_size"]
        offset = start - section["sh_addr"]
        body = section.data()[offset:offset + size]
        return (start, size, str(section.name), section["sh_offset"] + offset,
                hashlib.sha256(body).hexdigest(), body)

    start, size, section, offset, body_hash, target = symbol_range(mangled)
    assert (start, size, section, offset, body_hash) == (
        0x693fc, 340, ".text", 0x613fc,
        "43f23fedc765d0a517d02de509855c532cac4271946652573d755ce139293c99")
    init, _, _, _, init_hash, init_body = symbol_range("_Z23__initMeterScaleControlv")
    assert init_hash == "f9ceddbba54eb906485388211502840ae8078631b1eac112a6a3a829790d6938"
    lookup, lookup_size, _, lookup_offset, lookup_hash, lookup_body = symbol_range(
        "_ZN8Presonus17MeterScaleControl6Ranges8getRangeEPKc")
    assert lookup == 0x64a7c
    entry, *_ = symbol_range("_ZN4Core12Interpolator8setRangeEfff")
    assert entry == 0x69908
    segments = [(s["p_vaddr"], s["p_memsz"], s.data()) for s in elf.iter_segments()
                if s["p_type"] == "PT_LOAD"]

R0, R1, R2, R3 = UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3
GUARD, REGISTRY = 0x2691a8, 0x2691b0
HEAP, STACK, STOP = 0x4000000, 0x4100000, 0x4200000
RECEIVER, ATTRIBUTES, SCALE = HEAP, HEAP + 0x100, HEAP + 0x200
POINTERS, RECORDS, TEXT = HEAP + 0x300, HEAP + 0x1000, HEAP + 0x2000
VTABLE = 0x19bd88


def execute(warm, range_name, interpolator, seed):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    low = min(a for a, _, _ in segments) & ~4095
    high = max(a + n for a, n, _ in segments)
    uc.mem_map(low, (high - low + 4095) & ~4095)
    for address, _, data in segments:
        uc.mem_write(address, data)
    for address in (HEAP, STACK, STOP):
        uc.mem_map(address, 0x10000)
    for address, data in ((start, target), (init, init_body), (lookup, lookup_body)):
        assert bytes(uc.mem_read(address, len(data))) == data

    def word(address):
        return struct.unpack("<I", uc.mem_read(address, 4))[0]

    def words(address, *values):
        uc.mem_write(address, struct.pack(f"<{len(values)}I", *values))

    def cstring(address):
        return bytes(uc.mem_read(address, 64)).split(b"\0", 1)[0].decode("ascii")

    assert word(VTABLE + 8) == entry
    words(SCALE, VTABLE)
    words(RECEIVER + 0x58, seed, seed)
    trace, registrations = [], []
    calls = {"range": range_name, "interpolator": interpolator}

    def boundary(machine, pc, _size, _data):
        if pc == STOP:
            return
        if start <= pc < start + size or init <= pc < init + len(init_body):
            return
        if lookup <= pc < lookup + lookup_size or 0x187314 <= pc < 0x187420:
            if pc == lookup:
                trace.append(["lookup", cstring(machine.reg_read(R1))])
            return
        r0, r1, r2, r3 = [machine.reg_read(reg) for reg in (R0, R1, R2, R3)]
        if pc == 0x1147a4:
            assert (r0, r1) == (RECEIVER, ATTRIBUTES)
            trace.append(["view"])
        elif pc == 0x124200:
            assert r0 == ATTRIBUTES
            key = cstring(r1)
            value = calls[key]
            trace.append(["string", key, value])
            # A non-string behaves like an absent key at the typed boundary.
            address = 0
            if isinstance(value, str):
                address = TEXT
                uc.mem_write(address, value.encode("ascii") + b"\0")
            machine.reg_write(R0, address)
        elif pc == 0x64c38:
            raise AssertionError("unexpected cleanup during target")
        elif pc == 0x68558:
            assert r0 == REGISTRY and 0 < r2 <= 16
            record = RECORDS + 128 * len(registrations)
            name = cstring(r1)
            words(record, r3, r2)
            uc.mem_write(record + 8, name.encode("ascii") + b"\0")
            words(POINTERS + 4 * len(registrations), record)
            registrations.append(name)
            words(REGISTRY + 4, POINTERS, len(registrations))
        elif pc == 0xb0f8:
            left, right = cstring(r0), cstring(r1)
            trace.append(["compare", left, right])
            machine.reg_write(R0, int(left != right))
        elif pc == 0xe8f48:
            name = cstring(r0) if r0 else None
            trace.append(["factory", name])
            machine.reg_write(R0, SCALE if name in ("linear", "linrev") else 0)
        elif pc == entry:
            assert r0 == SCALE
            args = struct.unpack("<3f", struct.pack("<3I", r1, r2, r3))
            trace.append(["setRange", *args])
        elif pc == 0xb1c4:
            assert r0 == GUARD
            trace.append(["guard acquire"])
            machine.reg_write(R0, int(word(GUARD) == 0))
        elif pc == 0x69fcc:
            assert (r0, r1) == (REGISTRY, 0)
            trace.append(["empty vector"])
        elif pc == 0xab7c:
            assert r0 == GUARD
            words(GUARD, 1)
            trace.append(["guard release"])
        elif pc == 0xaf24:
            assert (r0, r1) == (REGISTRY, 0x64c38)
            trace.append(["register lifetime"])
        else:
            raise AssertionError(f"unexpected boundary {pc:#x}")
        machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

    def call(address):
        uc.reg_write(UC_ARM_REG_LR, STOP)
        uc.reg_write(UC_ARM_REG_SP, STACK + 0x8000)
        uc.emu_start(address, STOP, count=2000)
        assert uc.reg_read(UC_ARM_REG_PC) == STOP

    uc.hook_add(UC_HOOK_CODE, boundary)
    if warm:
        call(init)
        assert registrations == ["default", "recordArmed", "output"]
        trace.clear()
    uc.reg_write(R0, RECEIVER)
    uc.reg_write(R1, ATTRIBUTES)
    call(start)
    selected, scale = word(RECEIVER + 0x5c), word(RECEIVER + 0x58)
    assert scale in (0, SCALE)
    assert selected == 0 or selected in (RECORDS + i * 128 for i in range(len(registrations)))
    assert trace[0] == ["view"]
    assert trace[1] == ["string", "range", range_name]
    endpoints = next((row[1:] for row in trace if row[0] == "setRange"), None)
    ticks = []
    if selected:
        length = word(selected + 4)
        ticks = struct.unpack(f"<{length}i", uc.mem_read(word(selected), 4 * length))
    return dict(warm=warm, range=range_name, interpolator=interpolator,
                native_receiver_seed=seed, stored_range=cstring(selected + 8) if selected else None,
                stored_scale=bool(scale), configured=endpoints, ticks=ticks, trace=trace)


cases = [
    (False, "default", "linear"), (True, None, None), (True, None, "linear"),
    (True, "unknown", "linrev"), (True, "default", "linear"),
    (True, "recordArmed", "linrev"), (True, "output", "linear"),
    (True, "output", "not-registered"), (True, "", "linear"),
    (True, "output", ""), (True, 12, "linrev"), (True, "default", 12),
]
print(json.dumps(dict(
    elf={"path": str(elf_path), "sha256": elf_hash}, mangled=mangled,
    address=start, size=size, section=section, file_offset=offset, original_sha256=body_hash,
    init_sha256=init_hash, lookup={"address": lookup, "size": lookup_size,
        "file_offset": lookup_offset, "sha256": lookup_hash},
    original_set_range_slot={"address_point": VTABLE, "offset": 8, "target": entry},
    cases=[execute(*case, 0xa5a5a5a5) for case in cases]), indent=2))
