"""Offline ARM oracle for the seven exact RM LimiterController entry ranges."""
import ctypes
import hashlib
import itertools
import json
import struct
import sys
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
    UC_ARM_REG_SP,
)

packet = Path(sys.argv[1])
source = json.loads(packet.read_text())["originals"][0]["original"]
symbol = source["mangled"]
start = source["address"]
sha = lambda value: hashlib.sha256(value).hexdigest()

libm = ctypes.CDLL("libm.so.6")
libc = ctypes.CDLL("libc.so.6")
libc.malloc.argtypes = [ctypes.c_size_t]
libc.malloc.restype = ctypes.c_void_p
libc.free.argtypes = [ctypes.c_void_p]
libc.free.restype = None
math_calls = {0xacac: ("log10f", 1), 0xae5c: ("powf", 2), 0xae2c: ("expf", 1)}
for function, arity in math_calls.values():
    provider = getattr(libm, function)
    provider.argtypes = [ctypes.c_float] * arity
    provider.restype = ctypes.c_float

pack = lambda *words: struct.pack(f"<{len(words)}I", *words)
words = lambda data: list(struct.unpack(f"<{len(data) // 4}I", data))
word = lambda value: words(struct.pack("<f", value))[0]
fp = lambda bits: struct.unpack("<f", pack(bits))[0]

elf_image = Path(source["elf_path"]).read_bytes()
assert sha(elf_image) == source["elf"]
with Path(source["elf_path"]).open("rb") as stream:
    elf = ELFFile(stream)
    table = elf.get_section_by_name(".symtab")
    exact, = table.get_symbol_by_name(symbol)
    assert [exact[k] for k in ("st_value", "st_size", "st_shndx")] == [
        start, source["size"], source["section"],
    ]
    section = elf.get_section(source["section"])
    assert section.name == source["section_name"]
    offset = section["sh_offset"] + start - section["sh_addr"]
    body = elf_image[offset:offset + source["size"]]
    assert offset == source["file_offset"]
    assert body.hex() == source["range_hex"] and sha(body) == source["range_sha256"]
    segments = [(seg["p_vaddr"], seg["p_memsz"], seg.data())
                for seg in elf.iter_segments() if seg["p_type"] == "PT_LOAD"]
    dependencies = []
    for address in (0xcd1dc, 0xb251c, 0xb3388, 0xcd8a8, 0xb27e8, 0xb2764, 0xb29d8):
        dependency = next(s for s in table.iter_symbols()
                          if s["st_value"] == address
                          and s["st_info"]["type"] == "STT_FUNC")
        dependency_section = elf.get_section(dependency["st_shndx"])
        dependency_offset = (dependency_section["sh_offset"] + address
                             - dependency_section["sh_addr"])
        size = dependency["st_size"]
        dependencies.append(dict(mangled=dependency.name, address=address, size=size,
                                 section=dependency["st_shndx"], file_offset=dependency_offset,
                                 sha256=sha(elf_image[dependency_offset:dependency_offset + size])))

receiver, target, target_table = 0x38000000, 0x39000000, 0x39000010
callback, release, stop = 0x39000100, 0x39000104, 0x39000200
set_range, interpolator_table = 0x39000108, 0x39000040
heap, stack = 0x40000000, 0x60000000
guard, singleton = 0x493e74, 0x498230

uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
mapped = set()
for base, span, data in segments:
    for page in range(base & -4096, (base + span + 4095) & -4096, 4096):
        if page not in mapped:
            uc.mem_map(page, 4096)
            mapped.add(page)
    uc.mem_write(base, data)
for base, size in ((receiver, 4096), (target, 4096), (heap, 65536), (stack, 4096)):
    uc.mem_map(base, size)
uc.mem_write(target, pack(target_table))
uc.mem_write(target_table, pack(callback, 0, release))
# Fixture callbacks are hooked before execution. Map explicit BX LR words.
uc.mem_write(callback, pack(0xe12fff1e, 0xe12fff1e, 0xe12fff1e))
store_placeholder = pack(0, 0, set_range)
uc.mem_write(interpolator_table, store_placeholder)

trace, writes, output, calls = [], [], [], []
allocated = None
target_allocation = None
next_heap = heap

def read(address, count=1):
    return words(uc.mem_read(address, count * 4))

def store(address, *values):
    uc.mem_write(address, pack(*values))

def allocate(size):
    global next_heap
    pointer = next_heap
    next_heap += (size + 15) & -16
    assert next_heap <= heap + 65536
    uc.mem_write(pointer, bytes(size))
    return pointer

def observe(machine, address, _length, _):
    global allocated, target_allocation
    trace.append(address)
    a, b, c = [machine.reg_read(reg) for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2)]
    result = None
    if address in math_calls:
        function, arity = math_calls[address]
        result = word(getattr(libm, function)(*[fp(v) for v in [a, b][:arity]]))
        calls.append([function, *[a, b][:arity], result])
    elif address == 0xb030:  # process-local C++ static guard, single thread
        result = int(read(a)[0] == 0)
        calls.append(["guard_acquire", a, result])
    elif address == 0xaa3c:
        store(a, 1)
        calls.append(["guard_release", a])
        result = 0
    elif address == 0xadb4:
        calls.append(["atexit_registration", a, b, c])
        result = 0
    elif address == 0xa7e4:
        result = allocate(a)
        calls.append(["operator_new", a, result])
    elif address == 0xb6d7c:  # observed Core vector metadata used by this caller
        # C1 sets capacity/count/items to zero, delta to 5, and explicitly
        # calls resize(0) at 0xcd8dc. Its first insert requests resize(1)
        # at 0xcdca0. Mirror pinned Core::Vector::resize's equal-capacity
        # fast path and delta rounding at this boundary; no native Core body.
        items, count, capacity, delta = read(a + 4, 4)
        assert a == singleton and (items, count, capacity, delta) == (0, 0, 0, 5)
        assert b in (0, 1)
        if b:
            new_capacity = ((b - 1) // delta + 1) * delta
            store(a + 4, allocate(new_capacity * 4), count, new_capacity)
        calls.append(["Core::Vector::resize", a, b])
        result = 1
    elif address == 0x110810:  # formatter payload never invoked in this replay
        calls.append(["Core::FormatterRegistry::find", a, b])
        result = 0
    elif address == 0x112844:  # caller takes its linear-interpolator fallback
        calls.append(["Core::InterpolatorFactory::create", a, b])
        result = 0
    elif address == 0x111a78:  # observer does not consume interpolator internals
        calls.append(["Core::LinearInterpolator", a, b, c])
        store(a, interpolator_table)
        result = a
    elif address == set_range:
        calls.append(["Core::LinearInterpolator::setRange", a, b, c])
        result = 0
    elif address == callback:
        assert a == target
        output.extend(read(b, 6))
        result = 0
    elif address == release:
        assert a == target and target_allocation
        libc.free(target_allocation)
        target_allocation = None
        output.append(1)
        result = 0
    elif address == 0xac10:
        assert a == receiver and allocated
        libc.free(allocated)
        allocated = None
        uc.mem_unmap(receiver, 4096)
        output.append(2)
        result = 0
    elif address == 0xcd344:
        calls.append(["setValue", b, c])
    if result is not None:
        machine.reg_write(UC_ARM_REG_R0, result)
        machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

def write(_machine, _kind, address, length, value, _):
    if receiver <= address < receiver + 56:
        writes.append([address - receiver, length, value])

uc.hook_add(UC_HOOK_CODE, observe)
uc.hook_add(UC_HOOK_MEM_WRITE, write)

def invoke(a, b=0, c=0):
    trace.clear()
    writes.clear()
    calls.clear()
    output.clear()
    for reg, value in [(UC_ARM_REG_R0, a), (UC_ARM_REG_R1, b), (UC_ARM_REG_R2, c),
                       (UC_ARM_REG_SP, stack + 4096 - 16), (UC_ARM_REG_LR, stop)]:
        uc.reg_write(reg, value & 0xffffffff)
    try:
        uc.emu_start(start, stop, count=20000)
    except Exception as error:
        raise RuntimeError([hex(pc) for pc in trace[-16:]], calls) from error
    assert uc.reg_read(UC_ARM_REG_PC) == stop, hex(uc.reg_read(UC_ARM_REG_PC))
    return uc.reg_read(UC_ARM_REG_R0)

def seed(dirty, enable, threshold, smoothing, reduction):
    uc.mem_write(receiver, bytes(56))
    uc.mem_write(receiver + 0x1c, bytes([dirty]))
    store(receiver + 0x28, enable, threshold, smoothing, reduction)

def fields():
    return [uc.mem_read(receiver + 0x1c, 1)[0], *read(receiver + 0x28, 4)]

cases = []
tags = (0x80000000, 0xffffffff, 0, 1, 2, 3, 0x7fffffff)
samples = (0, 0x80000000, word(-1.), 0x33877f3e, 0x33877f3f, 0x33877f40,
           word(1.), word(78.), 0x7f7fffff, 0x7f800000, 0xff800000, 0x7fc01234)
if "ControllerC" in symbol:
    mode = "ctor"
    for index, identity in enumerate((0x80000000, 0xffffffff, 0, 1, 0x7fffffff)):
        uc.mem_write(receiver, bytes([0xa5]) * 56)
        assert invoke(receiver, identity) == receiver
        assert read(receiver + 0xc) == [singleton]
        setters = [call[1:] for call in calls if call[0] == "setValue"]
        assert len(setters) == 3 and [pair[0] for pair in setters] == [0, 1, 2]
        assert (0xcd8a8 in trace) == (index == 0)
        assert read(receiver + 0x18) == [identity]
        cases.append(dict(inputs=[identity], expected=[identity, *fields(), len(setters),
                                                      *itertools.chain.from_iterable(setters)],
                          calls=calls[:], writes=writes[:]))
elif "ControllerD" in symbol:
    deleting = "D0" in symbol
    mode = "d0" if deleting else "d1"
    for present, owner in itertools.product(range(2), repeat=2):
        seed(0, 0, 0, 0, 0)
        store(receiver + 0x14, target if present else 0)
        uc.mem_write(receiver + 0x1d, bytes([owner]))
        if present:
            target_allocation = libc.malloc(4)
            assert target_allocation
        if deleting:
            allocated = libc.malloc(56)
            assert allocated
        assert invoke(receiver) == receiver
        assert 0xb27e8 in trace and 0xb2764 in trace
        assert len([write for write in writes if write[0] == 0]) == 2
        assert (allocated is None and 0xac10 in trace) if deleting else read(receiver + 0x14) == [0]
        cases.append(dict(inputs=[present, owner], expected=output[:], writes=writes[:],
                          runtime_free=0xac10 in trace))
        assert bool(target_allocation) == bool(present and not owner)
        if target_allocation:
            libc.free(target_allocation)
            target_allocation = None
        if deleting:
            uc.mem_map(receiver, 4096)
elif "getValue" in symbol:
    mode = "get"
    for tag, enabled, sample in itertools.product(tags, (0, 1, 0x81234567), samples):
        seed(255, enabled, sample, word(0.875), sample)
        before = fields()
        result = invoke(receiver, tag)
        assert fields() == before and not writes and not output
        cases.append(dict(inputs=[tag, *before], expected=[result, *before], calls=calls[:]))
elif "setValue" in symbol:
    mode = "set"
    levels = (0, 0x80000000, word(-3.5), word(3.5), 0x430fffff, 0x43100000,
              0x43100001, 0x7f800000, 0xff800000, 0x7fc01234)
    for tag, dirty, enabled, value in itertools.product(tags, (0, 1, 255), (0, 1, 7), levels):
        seed(dirty, enabled, word(1.25), word(0.875), word(2.75))
        before = fields()
        result = invoke(receiver, tag, value)
        assert not output and writes and writes[0][0] == 0x1c
        cases.append(dict(inputs=[tag, value, *before], expected=fields(),
                          writes=writes[:], native_r0=result, calls=calls[:]))
else:
    assert "doUpdates" in symbol
    mode = "update"
    for present, rate, enabled, threshold in itertools.product(
        (0, 1), (0, word(44100.), word(48000.), word(96000.), 0x7f800000, 0x7fc01234),
        (0, 1, 7), (0x80000000, word(0.75), 0x7fc01234),
    ):
        seed(255, enabled, threshold, word(0.875), word(2.75))
        before = fields()
        channel = 0x80000001
        store(receiver + 4, channel)
        store(receiver + 0x14, target if present else 0)
        store(receiver + 0x24, rate)
        invoke(receiver)
        assert 0xcd1dc in trace and 0xb29d8 in trace
        assert bool(output) == bool(present)
        cases.append(dict(inputs=[present, channel, rate, *before], expected=[*fields(), *output],
                          writes=writes[:], calls=calls[:]))

print(json.dumps(dict(mode=mode, original=source, dependencies=dependencies,
                      native_cases=cases), indent=2))
