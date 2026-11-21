"""Execute the original MonoBus callback and original compiler float comparator."""
import hashlib
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM, Uc
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0,
                               UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
                               UC_ARM_REG_SP)

ROOT = Path("/home/rs/projects/opencs/ai-line-analysis")
PACKETS = ROOT / "temp/recovery-work/reconstruction10x10-20261121/packeting"
READ_MAP = PACKETS / "READ_INPUTS-post32-next-batch02-cycle21_g07-post32-next39-scoped03-dispatch02.json"
ELF_SHA = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
START, SIZE = 0x46D04, 1040
MANGLED = "_ZN8Presonus5Mixer16MonoBusComponent12paramChangedEPN4Core8Portable9ParameterEi"
RANGE_SHA = "a2086efb344719d19909f283dca7313588c9e18016b964cebd1861e6f3f85ffb"
REGS = (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)
NUMERIC = dict(get=0x11C490, set=0x11F19C)
ALIAS = dict(min=0x11CB38, reset=0x11CCD8)
STRING = 0x11F350


def sha(data):
    return hashlib.sha256(data).hexdigest()


def execute(segments, message, tag, positive, mode_enabled, update_names, available):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    lo = min(a for a, n, b in segments) & ~4095
    hi = (max(a + n for a, n, b in segments) + 4095) & ~4095
    uc.mem_map(lo, hi - lo)
    for a, _, b in segments:
        uc.mem_write(a, b)
    base = 0x3000000
    uc.mem_map(base, 0x20000)
    (obj, trigger, info, mixer, channel, split0, split1, busmode,
     short, side1, side2, alias, vec, send1, send2, send3, stop) = [
         base + index * 0x200 for index in range(17)]
    put = lambda address, value: uc.mem_write(address, struct.pack("<I", value))
    get = lambda address: struct.unpack("<I", uc.mem_read(address, 4))[0]

    def cstring(address):
        return bytes(uc.mem_read(address, 32)).split(b"\0", 1)[0].decode()

    def set_text(address, text):
        uc.mem_write(address, text.encode().ljust(32, b"\0"))

    def float_bits(value):
        return struct.unpack("<I", struct.pack("<f", value))[0]

    def float_value(bits):
        return struct.unpack("<f", struct.pack("<I", bits))[0]

    for who in (trigger, split0, split1, busmode):
        put(who, 0x41B068)
    for who in (short, side1, side2):
        put(who, 0x41AF68)
        set_text(who + 0x20, "old")
    put(alias, 0x41AE50)
    put(trigger + 0xC, info)
    put(info + 4, tag)
    put(obj + 0x170, 2)
    put(obj + 0x174, mixer)
    put(obj + 0x1D4, alias if available else 0)
    uc.mem_write(obj + 0x8D, bytes([update_names]))
    set_text(mixer + 0x108, "Aux")
    for index, (offset, child) in enumerate(((0x1D4, channel), (0x148, send2), (0x15C, send3))):
        put(mixer + offset, vec + index * 4)
        put(mixer + offset + 4, 1)
        put(vec + index * 4, child)
    send1 = channel
    values = {trigger: float_bits(1 if positive else 0),
              busmode: float_bits(1 if mode_enabled else 0), split0: 0,
              split1: float_bits(0.25)}
    minimum = 0
    reset_count = 0
    trace = []
    view = {short: 0, side1: 1, side2: 2}
    assert get(0x41B068 + 0x44) == NUMERIC["get"]
    assert get(0x41B068 + 0x58) == NUMERIC["set"]
    assert get(0x41AE50 + 0x4C) == ALIAS["min"]
    assert get(0x41AE50 + 0x5C) == ALIAS["reset"]
    assert get(0x41AF68 + 0x74) == STRING

    def hook(machine, address, _size, _data):
        nonlocal minimum, reset_count
        a, b, c, d = [machine.reg_read(r) for r in REGS]
        ret = machine.reg_read(UC_ARM_REG_LR)
        if address == stop:
            machine.emu_stop()
            return
        if START <= address < START + SIZE or 0x157820 <= address < 0x157958:
            return
        result = 0
        if address == 0x46B98:
            assert (a, b, c, ret) == (obj, trigger, message, 0x46D24)
            trace.append(["send", tag, message])
        elif address == 0x119C4C:
            assert a in (obj, channel)
            if a == obj:
                result = {411: busmode, 0: short, 1: side1, 2: side2}.get(b, 0)
            else:
                result = {258: split0, 259: split1}.get(b, 0) if available else 0
            trace.append(["lookup", "bus" if a == obj else "channel", b])
        elif address == NUMERIC["get"]:
            result = values[a]
        elif address == NUMERIC["set"]:
            assert a in (split0, split1) and c == 1
            values[a] = b
            trace.append(["set", 0 if a == split0 else 1, float_value(b)])
        elif address == 0x1DEBC:
            assert b == 0
            set_text(a, "")
        elif address == 0x3987C:
            fmt = cstring(b)
            assert fmt in ("%s %d", "%c%d")
            prefix = cstring(c) if fmt == "%s %d" else chr(c)
            set_text(a, fmt % (prefix, d))
        elif address == STRING:
            assert a in view and c == 1
            name = cstring(b)
            set_text(a + 0x20, name)
            trace.append(["name", view[a], name])
        elif address == ALIAS["min"]:
            assert a == alias and available
            minimum = int(float_value(b))
            trace.append(["minimum", minimum])
        elif address == ALIAS["reset"]:
            assert a == alias and b == 1
            reset_count += 1
            trace.append(["reset", 1])
        else:
            raise AssertionError(f"Unexpected bound operation branch {address:#x}")
        machine.reg_write(UC_ARM_REG_R0, result)
        machine.reg_write(UC_ARM_REG_PC, ret)

    uc.reg_write(UC_ARM_REG_R0, obj)
    uc.reg_write(UC_ARM_REG_R1, trigger)
    uc.reg_write(UC_ARM_REG_R2, message)
    uc.reg_write(UC_ARM_REG_LR, stop)
    uc.reg_write(UC_ARM_REG_SP, base + 0x18000)
    uc.hook_add(UC_HOOK_CODE, hook)
    uc.emu_start(START, stop + 4, count=10000)
    assert uc.reg_read(UC_ARM_REG_PC) == stop
    read_byte = lambda addr: uc.mem_read(addr, 1)[0]
    dirty = [get(obj + 0x178), read_byte(obj + 0x85)]
    for remote in (send1, send2, send3):
        dirty += [get(remote + 0x18C), read_byte(remote + 0x85)]
    return dict(inputs=[message, tag, positive, mode_enabled, update_names, available], trace=trace,
                dirty=dirty, splits=[float_value(values[field]) for field in (split0, split1)],
                names=[cstring(field + 0x20) for field in (short, side1, side2)],
                minimum=minimum, resets=reset_count)


def observe():
    record = json.loads(READ_MAP.read_text())["rootfs/RML16AI_Rack_13731/home/root/mixer"]
    path = Path(record["frozen_read_path"])
    data = path.read_bytes()
    assert sha(data) == record["sha256"] == ELF_SHA
    with path.open("rb") as handle:
        elf = ELFFile(handle)
        (symbol,) = elf.get_section_by_name(".symtab").get_symbol_by_name(MANGLED)
        assert symbol["st_value"] == START and symbol["st_size"] == SIZE
        section = elf.get_section(symbol["st_shndx"])
        offset = section["sh_offset"] + START - section["sh_addr"]
        assert sha(data[offset:offset+SIZE]) == RANGE_SHA
        segments = [(s["p_vaddr"], s["p_memsz"], s.data())
                    for s in elf.iter_segments() if s["p_type"] == "PT_LOAD"]
    cases = [(message, tag, positive, enabled, names, available) for message, tag, positive, enabled, names, available in (
        (1, 411, True, True, True, True),
        (3, 410, True, True, True, True), (3, 411, True, True, True, True),
        (3, 409, True, True, True, True),
        (2, 21, True, True, True, True), (2, 21, False, True, True, True),
        (2, 21, True, False, True, True), (2, 21, True, True, True, False),
        (2, 411, True, True, True, True), (2, 411, False, True, True, True),
        (2, 411, True, True, False, True), (2, 411, False, True, False, True),
        (2, 411, True, True, True, False), (2, 411, False, True, False, False))]
    return dict(task="cycle21_g07_s06", elf_sha256=ELF_SHA, mangled=MANGLED, address=START,
                size=SIZE, section=section.name, file_offset=offset, range_sha256=RANGE_SHA,
                cases=[execute(segments, *case) for case in cases],
                oracle="Exact original MonoBus callback and ARM comparator execute. Base notification, "
                       "Core lookup/text and parameter calls are controlled instrumented boundaries after "
                       "checking exact linked vtable words. Host replays with actual canonical providers.")


if __name__ == "__main__":
    print(json.dumps(observe(), indent=2))
