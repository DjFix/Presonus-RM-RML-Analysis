"""Exercise the original ARM scene load around isolated stream boundaries."""
import hashlib
import json
import struct
import zlib
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM, Uc
from unicorn.arm_const import (UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0,
                               UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
                               UC_ARM_REG_SP)

ROOT = Path("/home/rs/projects/opencs/ai-line-analysis")
RUN = ROOT / "temp/recovery-work/reconstruction10x10-20261121"
TASK = "cycle21_g07_s10"
START, SIZE = 0x590D0, 372
ELF_SHA = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
RANGE_SHA = "37cfe95e75096463619d38dd6b457485c179e5507802438c097c917da22aa097"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def observe_case(segments, payload, compressed):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    first = min(a for a, n, b in segments) & ~4095
    last = (max(a + n for a, n, b in segments) + 4095) & ~4095
    uc.mem_map(first, last - first)
    for a, _, b in segments:
        uc.mem_write(a, b)
    base = 0x3000000
    uc.mem_map(base, 0x20000)
    obj, stream, attrs, table, input_buffer, raw, seek, stop = (base + n * 256 for n in range(8))
    data = zlib.compress(payload) if compressed else payload
    put = lambda address, value: uc.mem_write(address, struct.pack("<I", value))
    put(obj + 4, stream)
    put(obj + 0x10, compressed)
    put(stream, table)
    put(table + 12, seek)
    put(input_buffer, raw)
    uc.mem_write(raw, data)
    uc.reg_write(UC_ARM_REG_R0, obj)
    uc.reg_write(UC_ARM_REG_R1, attrs)
    uc.reg_write(UC_ARM_REG_SP, base + 0x1F000)
    uc.reg_write(UC_ARM_REG_LR, stop)
    trace, decoded = [], None
    output = None
    expanded = None

    def enter(machine, address, size, _):
        nonlocal decoded, output, expanded
        if address == stop:
            machine.emu_stop()
            return
        if START <= address < START + SIZE:
            return
        a, b, c, d = [machine.reg_read(reg) for reg in (UC_ARM_REG_R0,
                                                        UC_ARM_REG_R1,
                                                        UC_ARM_REG_R2,
                                                        UC_ARM_REG_R3)]
        result = 0
        if address == 0x10F010:
            assert compressed and b == 8192
            expanded = a
            trace.append("memory stream")
        elif address == 0x114C98:
            assert b == expanded and c == 15
            trace.append("inflate init")
        elif address == 0x10EBE4:
            assert a == stream
            result = input_buffer
            trace.append("input buffer")
        elif address == 0x10EC20:
            assert a == stream
            result = len(data)
            trace.append("input length")
        elif address == 0x115104:
            assert b == raw and c == len(data)
            decoded = zlib.decompress(bytes(machine.mem_read(b, c)))
            result = c
            trace.append("inflate write")
        elif address == 0x115340:
            trace.append("inflate destroy")
        elif address in (seek, 0x10EC8C):
            assert a == (expanded if compressed else stream) and c == d == 0
            assert bytes(machine.mem_read(machine.reg_read(UC_ARM_REG_SP), 4)) == bytes(4)
            trace.append("rewind")
        elif address == 0x116CCC:
            assert b == (expanded if compressed else stream) and c == d == 0
            trace.append("JSON archive")
        elif address == 0x117B5C:
            assert b == attrs
            try:
                output = json.loads(decoded if compressed else bytes(machine.mem_read(raw, len(data))))
                result = int(isinstance(output, dict))
            except ValueError:
                result = 0
            trace.append("attributes load")
        elif address == 0x10F578:
            trace.append("buffer destroy")
        else:
            raise AssertionError(f"Unexpected provider boundary {address:#x}")
        machine.reg_write(UC_ARM_REG_R0, result)
        machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

    uc.hook_add(UC_HOOK_CODE, enter)
    uc.emu_start(START, stop + 4, count=10000)
    assert uc.reg_read(UC_ARM_REG_PC) == stop
    return dict(compressed=compressed, input_hex=data.hex(), trace=trace,
                status=bool(uc.reg_read(UC_ARM_REG_R0)), attributes=output)


def observe():
    read_map = RUN / "packeting/READ_INPUTS-post15-wave-compatible35-batch04-cycle21_g07.json"
    entry = json.loads(read_map.read_text())["rootfs/RML16AI_Rack_13731/home/root/mixer"]
    elf_path = Path(entry["frozen_read_path"])
    elf_bytes = elf_path.read_bytes()
    assert sha(elf_bytes) == entry["sha256"] == ELF_SHA
    with elf_path.open("rb") as file:
        elf = ELFFile(file)
        section = elf.get_section(12)
        assert section["sh_addr"] <= START and START + SIZE <= section["sh_addr"] + section["sh_size"]
        offset = section["sh_offset"] + START - section["sh_addr"]
        assert sha(elf_bytes[offset:offset + SIZE]) == RANGE_SHA
        segments = [(s["p_vaddr"], s["p_memsz"], s.data()) for s in elf.iter_segments()
                    if s["p_type"] == "PT_LOAD"]
    payloads = (b'{"name":"scene","number":17}', b'_')
    cases = [observe_case(segments, payload, compressed)
             for compressed in (False, True) for payload in payloads]
    return dict(task=TASK, elf_sha256=ELF_SHA, mangled="_ZN16MixerSceneLoader4loadERN4Core8Portable10AttributesE",
                section=".text", address=START, size=SIZE, file_offset=offset,
                range_sha256=RANGE_SHA, cases=cases,
                oracle="Original ARM app code executed with explicitly controlled provider boundaries. "
                       "Python zlib and JSON supply independent boundary outcomes. Actual pinned CCL "
                       "providers run in the Linux replay.")


if __name__ == "__main__":
    print(json.dumps(observe(), indent=2))
