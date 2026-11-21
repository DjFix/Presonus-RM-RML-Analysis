"""Observe the original Scenes deleting destructor's normal-path boundaries."""
import hashlib
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM, Uc, UcError
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP

ROOT = Path("/home/rs/projects/opencs/ai-line-analysis")
RUN = ROOT / "temp/recovery-work/reconstruction10x10-20261121/packeting"
READS = RUN / "READ_INPUTS-post39-tail-batch02-cycle21_g07-post39-tail-scoped03-dispatch02.json"
ELF_SHA = "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0"
START, SIZE = 0xB6398, 280
MANGLED = "_ZN8Presonus7Surface19ScenesPageComponentD0Ev"
RANGE_SHA = "e95411f901e78813bf7a16ccef0a802ed2712bc53d2a6c2966a58c78bd95425c"
PROVIDERS = {
    "_ZN4Core6VectorIPNS_8Portable9ParameterEED1Ev": (0x613BC, 48, "c14aea955fd29c85e28ad044322fcffc27a549eced291eaf926cf74e2fd30f94"),
    "_ZN4Core6VectorIPNS_8Portable10AliasParamEED1Ev": (0x5D36C, 48, "aec8579f99ee96d677285ec04a1dffb25c51b5676af2b0bbdba1466832c89cab"),
    "_ZN4Core8Portable9ComponentD2Ev": (0x11B5E0, 372, "7f8eead6380705e1afce15e6a0259c34531097fe2de4fca5f9a364d2f40912f2"),
    "_ZN8Presonus7Surface20PresetsPageComponentD2Ev": (0xB62D8, 184, "9be277bce511def46a5c7c43dadd5607187da0ed1a9bb52fec4346e1243cf5fe"),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def execute(segments):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    first = min(a for a, n, b in segments) & ~4095
    last = (max(a + n for a, n, b in segments) + 4095) & ~4095
    uc.mem_map(first, last - first)
    for a, _, b in segments:
        uc.mem_write(a, b)
    obj, extra, aliases, child, borrowed_parameter, borrowed_alias, stack, stop = (
        0x3000000 + n * 4096 for n in range(8))
    for address in (obj, extra, aliases, child, borrowed_parameter, borrowed_alias, stack, stop):
        uc.mem_map(address, 4096)
    uc.mem_write(extra, struct.pack("<I", borrowed_parameter))
    uc.mem_write(aliases, struct.pack("<I", borrowed_alias))
    uc.mem_write(borrowed_parameter, b"parameter")
    uc.mem_write(borrowed_alias, b"alias")
    trace = []
    entered_unwind = []

    def hook(machine, address, size, _):
        if address == stop:
            machine.emu_stop()
            return
        if 0xB645C <= address <= 0xB6498:
            entered_unwind.append(address)
        if START <= address < START + SIZE:
            return
        receiver = machine.reg_read(UC_ARM_REG_R0)
        ret = machine.reg_read(UC_ARM_REG_LR)
        if address == 0x613BC:
            assert receiver == obj + 0xEC and ret == 0xB63E8
            assert bytes(machine.mem_read(extra, 4)) == struct.pack("<I", borrowed_parameter)
            operation, storage = "extra vector", extra
        elif address == 0x5D36C:
            assert receiver == obj + 0xB4 and ret == 0xB642C
            assert bytes(machine.mem_read(aliases, 4)) == struct.pack("<I", borrowed_alias)
            operation, storage = "alias vector", aliases
        elif address == 0x11B5E0:
            assert receiver == obj and ret == 0xB644C
            operation, storage = "component child cleanup", child
        elif address == 0xAD5C:
            assert receiver == obj and ret == 0xB6454
            operation, storage = "operator delete", obj
        else:
            raise AssertionError(f"Unexpected exact target {address:#x}")
        machine.mem_unmap(storage, 4096)
        trace.append(dict(operation=operation, address=address, receiver_offset=receiver-obj, return_site=ret))
        machine.reg_write(UC_ARM_REG_PC, ret)

    uc.reg_write(UC_ARM_REG_R0, obj)
    uc.reg_write(UC_ARM_REG_SP, stack + 0x800)
    uc.reg_write(UC_ARM_REG_LR, stop)
    uc.hook_add(UC_HOOK_CODE, hook)
    uc.emu_start(START, stop + 4, count=1000)
    assert uc.reg_read(UC_ARM_REG_PC) == stop and not entered_unwind

    def released(address):
        try:
            uc.mem_read(address, 1)
            return False
        except UcError:
            return True

    assert all(released(a) for a in (obj, extra, aliases, child))
    assert bytes(uc.mem_read(borrowed_parameter, 9)) == b"parameter"
    assert bytes(uc.mem_read(borrowed_alias, 5)) == b"alias"
    return dict(trace=trace, receiver_released=True, borrowed_entries_survived=True)


def observe():
    record = json.loads(READS.read_text())["rootfs/CS18_v13840/home/root/surface"]
    path = Path(record["frozen_read_path"])
    data = path.read_bytes()
    assert digest(data) == ELF_SHA == record["sha256"]
    ranges = {}
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        symbols = elf.get_section_by_name(".symtab")
        for identity, (addr, size, expected) in {MANGLED: (START, SIZE, RANGE_SHA), **PROVIDERS}.items():
            (symbol,) = symbols.get_symbol_by_name(identity)
            assert symbol["st_size"] == size and symbol["st_value"] == addr
            section = elf.get_section(symbol["st_shndx"])
            offset = section["sh_offset"] + addr - section["sh_addr"]
            assert digest(data[offset:offset + size]) == expected
            ranges[identity] = dict(mangled=identity, address=addr, size=size, section=section.name,
                                     file_offset=offset, range_sha256=expected)
        (deallocator,) = symbols.get_symbol_by_name("_ZdlPv@@GLIBCXX_3.4")
        assert deallocator["st_value"] == 0xAD5C and deallocator["st_shndx"] == "SHN_UNDEF"
        segments = [(s["p_vaddr"], s["p_memsz"], s.data())
                    for s in elf.iter_segments() if s["p_type"] == "PT_LOAD"]
    return dict(task="cycle21_g07_r09", elf_sha256=ELF_SHA, **ranges.pop(MANGLED),
                dependency_ranges=list(ranges.values()), cases=[execute(segments)],
                unwind_excluded={"call_site": 0xB6464, "presets_d2": 0xB62D8},
                oracle="Original Scenes D0 ARM instructions execute to the exact ELF PLT call. "
                       "Core and allocator effects use explicit modeled heap boundaries that unmap "
                       "live tracked storage at actual calls. Host replay observes real providers "
                       "and allocator. No unwind execution.")


if __name__ == "__main__":
    print(json.dumps(observe(), indent=2))
