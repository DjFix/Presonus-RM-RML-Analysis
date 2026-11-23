"""Execute the original ARM meter initializer and capture its provider boundary."""

import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP

ELF = Path("/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/control10x20-after-4fed70d11/packeting/seed-wave02-batch/snapshot/rootfs/CS18_v13840/home/root/surface")
SUPPLEMENT = Path("/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/control10x20-after-4fed70d11/packeting/g02-offline-runtime-supplement01")
SUPPLEMENT_SHA = "429eec958ee7632abc59e5604a9cf575149cdafbaf3264c4b39a386ae74d5966"
LIBM_BASE = 0x1000000

ELF_SHA = "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0"
MANGLED = "_Z18__initMeterControlv"
RANGE_SHA = "598357bf66b11f5b06bafd6915d7a77d6e66d31298ba623c076adc1817c9b560"


def map_libm(machine):
    raw = (SUPPLEMENT / "SUPPLEMENT.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SUPPLEMENT_SHA
    plan = json.loads(raw)["plans"][0]
    library = plan["bound_libraries"]["lib/libm.so.6"]
    source = SUPPLEMENT / "rootfs/CS18_v13840/lib/libm-2.9.so"
    data = source.read_bytes()
    assert hashlib.sha256(data).hexdigest() == library["sha256"]
    elf = ELFFile(io.BytesIO(data))
    (symbol,) = elf.get_section_by_name(".dynsym").get_symbol_by_name("powf")
    section = elf.get_section(symbol["st_shndx"])
    address, size = symbol["st_value"], symbol["st_size"]
    offset = section["sh_offset"] + address - section["sh_addr"]
    record = plan["runtime_symbol"]
    assert (address, size, section.name, offset) == (
        record["address"], record["size"], record["section"], record["file_offset"])
    assert hashlib.sha256(data[offset:offset+size]).hexdigest() == record["body_sha256"]

    segments = [segment for segment in elf.iter_segments() if segment["p_type"] == "PT_LOAD"]
    end = max(segment["p_vaddr"] + segment["p_memsz"] for segment in segments)
    machine.mem_map(LIBM_BASE, (end + 0xfff) & ~0xfff)
    for segment in segments:
        machine.mem_write(LIBM_BASE + segment["p_vaddr"], segment.data())
    # The finite table traverses the library-local arithmetic and the initialized
    # libm mode cell. Bind its relocation exactly as the runtime linker would.
    dynsym = elf.get_section_by_name(".dynsym")
    relocation, = [row for row in elf.get_section_by_name(".rel.dyn").iter_relocations()
                   if dynsym.get_symbol(row["r_info_sym"]).name == "_LIB_VERSION"]
    version, = dynsym.get_symbol_by_name("_LIB_VERSION")
    machine.mem_write(LIBM_BASE + relocation["r_offset"],
                      struct.pack("<I", LIBM_BASE + version["st_value"]))
    return LIBM_BASE + address, dict(record, library_sha256=library["sha256"],
                                   supplement_sha256=SUPPLEMENT_SHA)


def observe():
    data = ELF.read_bytes()
    assert hashlib.sha256(data).hexdigest() == ELF_SHA
    elf = ELFFile(io.BytesIO(data))
    table = elf.get_section_by_name(".symtab")
    entry, = table.get_symbol_by_name(MANGLED)
    section = elf.get_section(entry["st_shndx"])
    address, size = entry["st_value"], entry["st_size"]
    offset = section["sh_offset"] + address - section["sh_addr"]
    assert (address, size, section.name, offset) == (0x683bc, 196, ".text", 0x603bc)
    assert hashlib.sha256(data[offset:offset+size]).hexdigest() == RANGE_SHA

    def address_of(name):
        item, = table.get_symbol_by_name(name)
        return item["st_value"]

    segments = [segment for segment in elf.iter_segments() if segment["p_type"] == "PT_LOAD"]
    start = min(segment["p_vaddr"] for segment in segments) & ~0xfff
    end = max(segment["p_vaddr"] + segment["p_memsz"] for segment in segments)
    machine = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    machine.mem_map(start, ((end + 0xfff) & ~0xfff) - start)
    for segment in segments:
        machine.mem_write(segment["p_vaddr"], segment.data())
    machine.mem_map(0x800000, 0x4000)
    machine.reg_write(UC_ARM_REG_SP, 0x804000)
    machine.reg_write(UC_ARM_REG_LR, 0x800000)

    powf, powf_range = map_libm(machine)
    calls = []
    registration = {}
    native_powf = []

    def trace(uc, pc, _size, _user):
        arithmetic = {
            0x187314: "i2f", 0x1873f0: "fmul", 0x187798: "fcmplt",
            0xaff0: "powf",
        }
        if pc in arithmetic:
            left, right = uc.reg_read(UC_ARM_REG_R0), uc.reg_read(UC_ARM_REG_R1)
            operation = arithmetic[pc]
            calls.append([operation, left] if operation == "i2f" else [operation, left, right])
            if operation == "powf":
                uc.reg_write(UC_ARM_REG_PC, powf)
        if pc == powf:
            native_powf.append(pc - LIBM_BASE)
        if pc == 0xe8cb0:
            name_address, creator = uc.reg_read(UC_ARM_REG_R0), uc.reg_read(UC_ARM_REG_R1)
            name = bytes(uc.mem_read(name_address, 16)).partition(b"\0")[0].decode("ascii")
            symbol = "_ZN4Core19InterpolatorFactory18createInterpolatorI24DefaultMeterInterpolatorEEPNS_12InterpolatorEv"
            assert creator == address_of(symbol)
            registration.update(name=name, creator=creator, creator_symbol=symbol)
            uc.emu_stop()

    machine.hook_add(UC_HOOK_CODE, trace)
    machine.emu_start(address, 0x800000, count=100000)
    assert registration["name"] == "audiometer"
    literals = struct.unpack("<9I", machine.mem_read(0x6845c, 36))
    inputs = struct.unpack("<13I", machine.mem_read(literals[0], 52))
    points = list(struct.iter_unpack("<II", machine.mem_read(literals[1], 104)))
    assert len(calls) == 65 and len(points) == len(native_powf) == 13
    return {
        "elf_sha256": ELF_SHA, "mangled": MANGLED, "section": section.name,
        "address": address, "size": size, "file_offset": offset, "range_sha256": RANGE_SHA,
        "inputs": list(inputs), "points": [list(p) for p in points],
        "calls": calls, "registration": registration, "literals": list(literals),
        "libm_powf": powf_range, "original_powf_entries": native_powf,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", type=Path)
    args = parser.parse_args()
    observed = observe()
    if args.fixtures:
        assert observed == json.loads(args.fixtures.read_text()), "native meter fixture mismatch"
        print("13 native breakpoint writes and one registered factory boundary reproduced")
    else:
        print(json.dumps(observed, indent=2))
