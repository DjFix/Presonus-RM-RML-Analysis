"""Execute the selected RM13731 ARM method with explicit provider boundaries."""
import hashlib
import io
import json
import struct
import sys
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (
    UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
    UC_ARM_REG_PC, UC_ARM_REG_SP, UC_ARM_REG_LR,
)

SHA = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
ELF = Path("/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261121/"
           "packeting/wave0102-carried01/snapshot/rootfs/RML16AI_Rack_13731/home/root/mixer")
MIXER, VT, BUFFER, SETTINGS, RESULT = (0x3000000 + i * 0x1000 for i in range(5))
MASTER, OBJECT, PARAM, STACK, STUB, STOP = (0x3010000 + i * 0x1000 for i in range(6))
WORD = struct.Struct("<I")
ARM_TARGETS = {
    6: (0x308EC, 188, "d97294d3de031e9fa96460863e541b5a00d209b24476b9d7a85824a0a581e10a"),
    7: (0x2F7A4, 348, "0c4f4ed960bcf7f64f78a41221265d9c36a0286455c6c1df951fad1a75b890bb"),
    8: (0x30CA4, 356, "56b52c9f2736b9e77e4f00a021ad5c34eb2b2dedb5959720d5bbc71c3ff5a786"),
    9: (0x30E08, 320, "e8271e571eac2185030c6fe5131f3fcd5591c0bde18a124b5e5482d493b276c2"),
    10: (0x312E0, 52, "b76d89397e5a75a338ca50149c61516dfedef545b8f6320aaf7ecf1bbbb69f00"),
}
CASES = {
    6: [(1, 1, 1, 2), (1, 0, 0, 0), (0, 1, 0, 2), (0, 1, 1, 1), (0, 0, 1, 0)],
    7: [(-1, 0, 0, "none", "none", "none"), (-1, 1, 2, "none", "none", "none"),
        (-1, 0, 1, "0", "1", "-1"), (1, 0, 2, "1", "1", "1"),
        (1, 1, 2, "1", "0", "1"), (2, 1, 2, "-1", "0", "-1"),
        (0, 0, 2, "nan", "-0", "1e-45"), (1, 1, 1, "nan", "-0", "-1e-45"),
        (3, 0, 2, "1", "1", "1"), (-1, 1, 2, "inf", "-inf", "0")],
    8: [(1, 0, 0, 2, "none", 0), (4, 1, 0, 1, "-1", 0),
        (4, 2, 0, 1, "1", 0), (11, 2, 0, 4, "1", 0),
        (11, 1, 1, 0, "none", 1), (2, 9, 1, 5, "nan", 1),
        (3, 10, 1, 1, "0", 0)],
    9: [("none", "2.75", "-3.75", "1"), (0, "15.9", "1.9", "0"),
        (1, "10", "0", "1"), (2, "20", "1", "0"),
        (3, "-2.9", "-1", "1"), ("2.9", "1", "1", "1"),
        (-1, "0", "0", "0"), ("nan", "nan", "inf", "-inf"), ("inf", "2147483648", "-2147483648", "0")],
    10: [(0, 0, 1, 2), (0, 1, 1, 3), (0, 1, 0, 1), (0, 1, 1, 0)],
}


def execute(segments, runtimes, index, address, size, args):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    first = min(vaddr for vaddr, _, _ in segments) & ~4095
    end = max(vaddr + length for vaddr, length, _ in segments)
    uc.mem_map(first, (end - first + 4095) & ~4095)
    for start, _, content in segments:
        uc.mem_write(start, content)
    uc.mem_map(MIXER, 0x20000)
    put = lambda at, value: uc.mem_write(at, WORD.pack(value & 0xFFFFFFFF))
    get = lambda at: WORD.unpack(uc.mem_read(at, 4))[0]
    byte = lambda at: uc.mem_read(at, 1)[0]
    floats = lambda value: WORD.unpack(struct.pack("<f", float(value)))[0]
    trace, writes, machine_sites = [], [], set()
    names, values = {}, {}
    if index in (6, 10):
        active, initial, snapshot, count = args
        uc.mem_write(MIXER + 0x364, bytes((initial, 0, snapshot)))
        uc.reg_write(UC_ARM_REG_R1, active)
        put(MIXER, VT)
        put(VT + 0xB0, 0x2CAE4)
        put(MIXER + 0x134, BUFFER)
        put(MIXER + 0x138, count)
        put(MIXER + 0x2D8, MASTER)
        put(VT + 0x58, STUB)
        for i in range(count):
            channel = OBJECT + 0x100 * i
            param = PARAM + 0x100 * i
            put(BUFFER + 4 * i, channel)
            put(channel + 0xF8, param)
            put(param, VT)
            names[param] = i
            values[param] = 1
        uc.reg_write(UC_ARM_REG_R0, MIXER)
    elif index == 7:
        selected, initial, count, *parameter_values = args
        uc.mem_write(MIXER + 0x365, bytes((initial,)))
        put(MIXER + 0x44C, BUFFER)
        put(MIXER + 0x450, sum(value != "none" for value in parameter_values))
        put(MIXER + 0x120, SETTINGS)
        put(MIXER + 0x124, count)
        put(VT + 0x44, STUB)
        put(VT + 0x58, STUB + 4)
        for i, value in enumerate(parameter_values):
            if value == "none":
                break
            param = PARAM + 0x100 * i
            put(BUFFER + 4 * i, param)
            put(param, VT)
            names[param] = i
            values[param] = floats(value)
        extra = PARAM + 0x300
        put(extra, VT)
        names[extra] = 3
        values[extra] = floats(1)
        for i in range(count):
            channel = OBJECT + 0x400 * i
            put(SETTINGS + 4 * i, channel)
        uc.reg_write(UC_ARM_REG_R0, MIXER)
        uc.reg_write(UC_ARM_REG_R1, 0 if selected < 0 else PARAM + selected * 0x100)
    elif index == 8:
        output, selection, rack, count, enabled, initial = args
        put(MIXER, VT)
        put(VT + 0xC8, 0x80158 if rack else 0x2F900)
        put(VT, 0x9EE34)
        put(VT + 0x44, STUB)
        put(MIXER + 0x138, count)
        put(MIXER + 0x19C, 4)
        put(MIXER + 0x380, MASTER)
        put(MASTER, VT)
        put(MIXER + 0x2DC, SETTINGS)
        if enabled != "none":
            put(SETTINGS + 23 * 4, PARAM)
            put(PARAM, VT)
            values[PARAM] = floats(enabled)
        uc.mem_write(MIXER + 0x11A, bytes((initial,)))
        uc.reg_write(UC_ARM_REG_R0, MIXER)
        uc.reg_write(UC_ARM_REG_R1, output)
        uc.reg_write(UC_ARM_REG_R2, selection)
    elif index == 9:
        put(MIXER + 0x2DC, SETTINGS)
        put(VT + 0x44, STUB)
        for i, (tag, value) in enumerate(zip((20, 43, 5, 44), args)):
            if value != "none":
                param = PARAM + i * 0x100
                put(SETTINGS + tag * 4, param)
                put(param, VT)
                names[param] = tag
                values[param] = floats(value)
        uc.reg_write(UC_ARM_REG_R0, RESULT)
        uc.reg_write(UC_ARM_REG_R1, MIXER)
        uc.mem_write(RESULT, b"\x5a" * 40)

    def hook(machine, pc, instruction_size, unused):
        if address <= pc < address + size:
            return
        if index == 10 and 0x308EC <= pc < 0x308EC + 188:
            return
        if any(start <= pc < start + length for start, length in runtimes):
            if pc in (0x2F900, 0x80158):
                assert machine.reg_read(UC_ARM_REG_R0) == MIXER
                trace.append(f"route:{machine.reg_read(UC_ARM_REG_R1)}")
            machine_sites.add(pc)
            return
        r0, r1, r2, r3, lr = [machine.reg_read(r) for r in
                               (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
                                UC_ARM_REG_R3, UC_ARM_REG_LR)]
        if index in (6, 10):
            if pc == 0x116A38:
                pattern = bytes(machine.mem_read(r0, 80)).split(b"\x00")[0]
                trace.append(pattern.decode().rstrip("\n") % r1)
            elif pc == STUB:
                trace.append(f"set:{names[r0]}:{r1}:{r2}:{byte(MIXER + 0x364)}:{byte(MIXER + 0x366)}")
                values[r0] = r1
            elif pc == 0x2CAE4:
                assert r0 == MIXER and r1 == MIXER + 0x384
                trace.append(f"restore:{get(r2)}:{byte(MIXER + 0x364)}:{byte(MIXER + 0x366)}")
            elif index == 10 and pc == 0x4BF24:
                assert r0 == MASTER
                trace.append(f"master:{byte(MIXER + 0x364)}:{byte(MIXER + 0x366)}")
            else:
                raise RuntimeError(f"Unexpected SIP control flow 0x{pc:x}")
        elif index == 7:
            if pc == STUB:
                trace.append(f"read:{names[r0]}")
                machine.reg_write(UC_ARM_REG_R0, values[r0])
            elif pc == STUB + 4:
                trace.append(f"set:{names[r0]}:{r1}:{r2}")
                values[r0] = r1
            else:
                raise RuntimeError(f"Unexpected key-listen control flow 0x{pc:x}")
        elif index == 8:
            if pc == 0x9EE34:
                assert r0 == MASTER
                kind, property_size = get(r1), get(r1 + 4)
                fields = [get(r1 + i * 4) for i in range(2, property_size // 4)]
                trace.append(f"property:{kind}:{property_size}:" + ":".join(map(str, fields)))
            elif pc == 0x119C4C:
                assert r0 == SETTINGS and r1 == 23
                trace.append("tag:23")
                machine.reg_write(UC_ARM_REG_R0, get(SETTINGS + r1 * 4))
            elif pc == STUB:
                trace.append("value:23")
                machine.reg_write(UC_ARM_REG_R0, values[r0])
            else:
                raise RuntimeError(f"Unexpected route control flow 0x{pc:x}")
        elif index == 9:
            if pc == 0x119C4C:
                assert r0 == SETTINGS
                trace.append(f"tag:{r1}")
                machine.reg_write(UC_ARM_REG_R0, get(SETTINGS + 4 * r1))
            elif pc == STUB:
                trace.append(f"value:{names[r0]}")
                machine.reg_write(UC_ARM_REG_R0, values[r0])
            else:
                raise RuntimeError(f"Unexpected setup control flow 0x{pc:x}")
        machine.reg_write(UC_ARM_REG_PC, lr)

    def observe_write(machine, access, at, length, value, unused):
        if not STACK <= at < STACK + 0x1000:
            writes.append([at - (RESULT if index == 9 else MIXER), length, value])

    uc.mem_write(STUB, bytes.fromhex("1eff2fe11eff2fe1"))
    uc.hook_add(UC_HOOK_CODE, hook)
    uc.hook_add(UC_HOOK_MEM_WRITE, observe_write)
    uc.reg_write(UC_ARM_REG_SP, STACK + 0xF00)
    uc.reg_write(UC_ARM_REG_LR, STOP)
    uc.emu_start(address, STOP, count=10000)
    assert uc.reg_read(UC_ARM_REG_PC) == STOP
    if index in (6, 10):
        trace.append(f"flags:{byte(MIXER + 0x364)}:{byte(MIXER + 0x366)}")
        trace.append("solos:" + "".join(str(values[p]) for p in names))
    elif index == 7:
        states = [f"{get(OBJECT + 0x400 * i + 0x17C)}:{byte(OBJECT + 0x400 * i + 0x85)}"
                  for i in range(args[2])]
        trace.append(f"flag:{byte(MIXER + 0x365)}")
        trace.append("channels:" + ",".join(states))
    elif index == 8:
        trace.append(f"dirty:{byte(MIXER + 0x11A)}")
    elif index == 9:
        assert uc.reg_read(UC_ARM_REG_R0) == RESULT
        words = [get(RESULT + i * 4) for i in range(10)]
        trace.append("words:" + ",".join(str(word) for word in words))
    return {"args": [str(arg) for arg in args], "events": trace,
            "native_nonstack_writes": writes, "compiler_runtime_instruction_sites": sorted(machine_sites)}


def generate(index):
    data = ELF.read_bytes()
    assert hashlib.sha256(data).hexdigest() == SHA
    elf = ELFFile(io.BytesIO(data))
    section = elf.get_section(12)
    address, size, expected = ARM_TARGETS[index]
    offset = address - section["sh_addr"] + section["sh_offset"]
    assert section.name == ".text" and section["sh_offset"] <= offset <= section["sh_offset"] + section["sh_size"] - size
    assert hashlib.sha256(data[offset:offset + size]).hexdigest() == expected
    segments = [(s["p_vaddr"], s["p_memsz"], s.data()) for s in elf.iter_segments()
                if s["p_type"] == "PT_LOAD"]
    symbols = elf.get_section_by_name(".symtab")
    runtime = []
    runtime_records = []
    dependencies = {
        7: [("__aeabi_fcmpgt", 0x157940), ("__aeabi_cfrcmple", 0x1578B8), ("__cmpsf2", 0x157858)],
        8: [("__aeabi_fcmpgt", 0x157940), ("__aeabi_cfrcmple", 0x1578B8), ("__cmpsf2", 0x157858),
            ("_ZN8Presonus5Mixer18MixerComponentBase12getTDMRoutesEiRhS2_Rj", 0x2F900),
            ("_ZN8Presonus5Mixer18RackMixerComponent12getTDMRoutesEiRhS2_Rj", 0x80158)],
        9: [("__aeabi_f2iz", 0x157958)],
    }
    if index in dependencies:
        for name, expected_address in dependencies[index]:
            match = [origin for origin in symbols.get_symbol_by_name(name)
                     if origin["st_value"] == expected_address and origin["st_size"] > 0]
            assert len(match) == 1
            length = match[0]["st_size"]
            runtime_offset = expected_address - section["sh_addr"] + section["sh_offset"]
            runtime.append((expected_address, length))
            runtime_records.append({"symbol": name, "address": expected_address, "size": length,
                                    "file_offset": runtime_offset,
                                    "range_sha256": hashlib.sha256(data[runtime_offset:runtime_offset + length]).hexdigest()})
    app_dependencies = []
    if index == 10:
        start, length, expected_digest = ARM_TARGETS[6]
        start_offset = start - section["sh_addr"] + section["sh_offset"]
        assert hashlib.sha256(data[start_offset:start_offset + length]).hexdigest() == expected_digest
        app_dependencies.append({"address": start, "size": length, "range_sha256": expected_digest,
                                 "file_offset": start_offset, "section": 12})
    cases = [execute(segments, runtime, index, address, size, args) for args in CASES[index]]
    return {"elf_sha256": SHA, "section": 12, "address": address, "size": size,
            "file_offset": offset, "range_sha256": expected,
            "compiler_runtime_ranges": runtime_records,
            "executed_app_dependencies": app_dependencies, "cases": cases}


if __name__ == "__main__":
    print(json.dumps(generate(int(sys.argv[1])), indent=2))
