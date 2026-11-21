"""Exact RM ARM D0 with actual provider operations and guest deallocation."""
import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import struct
import subprocess

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UcError, UC_ARCH_ARM, UC_ERR_READ_UNMAPPED, UC_HOOK_CODE, UC_MODE_ARM
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP

PACKETING = Path("/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261121/packeting")
READ_MAP = PACKETING / "READ_INPUTS-post32-next-batch02-cycle21_g04-post32-next39-scoped01-dispatch02.json"
ELF_NAME = "rootfs/RML16AI_Rack_13731/home/root/mixer"
ELF_SHA = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
MANGLED = "_ZN8Presonus5Mixer12GEQComponentD0Ev"
ADDRESS, SIZE, OFFSET = 0x3CC3C, 104, 0x34C3C
BODY_SHA = "5f0eed2cafdc7c9793a603f45937ab0aee347efe7f5b9c88875c39855c5fa132"
DSPOBJ = "_ZN8Presonus12DspComponentD2Ev"
DSP, DELETE, UNWIND = 0x83130, 0xAC10, 0xACD0


def digest(data):
    return hashlib.sha256(data).hexdigest()


def bindings(elf):
    plt = elf.get_section_by_name(".plt")
    relocations = elf.get_section_by_name(".rel.plt")
    symbols = elf.get_section(relocations["sh_link"])
    result = {}
    for address, expected in ((DELETE, "_ZdlPv"), (UNWIND, "__cxa_end_cleanup")):
        offset = address - plt["sh_addr"]
        index, remainder = divmod(offset - 20, 12)
        assert remainder == 0
        relocation = list(relocations.iter_relocations())[index]
        name = symbols.get_symbol(relocation["r_info_sym"]).name
        assert name == expected
        result[name] = {"entry": address, "index": index, "got": relocation["r_offset"],
                        "plt_sha256": digest(plt.data()[offset:offset + 12])}
    return result


def observe(executable):
    raw = Path(json.loads(READ_MAP.read_text())[ELF_NAME]["frozen_read_path"]).read_bytes()
    assert digest(raw) == ELF_SHA
    elf = ELFFile(BytesIO(raw))
    symbols = elf.get_section_by_name(".symtab")
    sym = symbols.get_symbol_by_name(MANGLED)[0]
    assert (sym["st_value"], sym["st_size"], sym["st_shndx"]) == (ADDRESS, SIZE, 12)
    section = elf.get_section(sym["st_shndx"])
    assert section.name == ".text"
    assert section["sh_offset"] + ADDRESS - section["sh_addr"] == OFFSET
    body = raw[OFFSET:OFFSET + SIZE]
    assert digest(body) == BODY_SHA
    vtable, = struct.unpack_from("<I", body, 100)
    assert symbols.get_symbol_by_name(DSPOBJ)[0]["st_value"] == DSP
    rows = []
    for mode in ("null", "present", "modeled-unwind"):
        target = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        for start, length in ((0xAC0000, 0x1000), (0x8000, 0x90000), (0xB00000, 0x10000)):
            target.mem_map(start, length)
        obj, prop, prop_table = 0xAC0000, 0xB02000, 0xB03000
        release, stop, exception = 0xB04000, 0xB0F000, 0xB05000
        target.mem_write(ADDRESS, body)
        live = {obj}
        calls = []
        provider_events = []

        def word(address, value):
            target.mem_write(address, struct.pack("<I", value))

        word(obj + 0xE8, prop if mode != "null" else 0)
        word(prop, prop_table)
        word(prop_table + 8, release)

        def provider(name):
            output = subprocess.check_output([str(executable.resolve()), name], text=True)
            return list(map(int, output.split()))

        def call(uc, pc, size, _):
            if pc not in (release, DSP, DELETE, UNWIND):
                return
            receiver = uc.reg_read(UC_ARM_REG_R0)
            next_pc = uc.reg_read(UC_ARM_REG_LR)
            if pc == release:
                assert receiver == prop and obj in live
                assert bytes(uc.mem_read(obj, 8)) == struct.pack("<II", vtable, vtable + 0x50)
                calls.append(["property_release", receiver])
                provider_events.extend(provider("provider-release"))
                if mode == "modeled-unwind":
                    next_pc = 0x3CC8C
                    uc.reg_write(UC_ARM_REG_R0, exception)
            elif pc == DSP:
                assert receiver == obj and obj in live
                assert bytes(uc.mem_read(obj, 8)) == struct.pack("<II", vtable, vtable + 0x50)
                calls.append(["dsp_cleanup", receiver])
                provider_events.extend(provider("provider-dsp"))
            elif pc == DELETE:
                assert receiver == obj and obj in live
                # The PLT-bound provider consumes the live guest allocation.
                live.remove(receiver)
                uc.mem_unmap(receiver, 0x1000)
                try:
                    uc.mem_read(receiver, 1)
                except UcError as failure:
                    assert failure.errno == UC_ERR_READ_UNMAPPED
                else:
                    raise AssertionError("Deleted receiver remains mapped")
                calls.append(["unsized_delete_unmapped", receiver])
            else:
                assert receiver == exception and obj in live
                calls.append(["end_cleanup", receiver])
                next_pc = stop
            uc.reg_write(UC_ARM_REG_PC, next_pc)

        target.hook_add(UC_HOOK_CODE, call)
        target.reg_write(UC_ARM_REG_R0, obj)
        target.reg_write(UC_ARM_REG_LR, stop)
        target.reg_write(UC_ARM_REG_SP, 0xB0E000)
        target.emu_start(ADDRESS, stop, count=160)
        assert target.reg_read(UC_ARM_REG_PC) == stop
        deallocated = not live
        assert deallocated == (mode != "modeled-unwind")
        rows.append({"mode": mode, "calls": calls, "provider_events": provider_events,
                     "deallocated": deallocated, "guest_receiver": obj})
    return {"elf_sha256": ELF_SHA, "range_sha256": BODY_SHA, "section": ".text",
            "address": ADDRESS, "size": SIZE, "offset": OFFSET, "mangled": MANGLED,
            "dsp_target": {"mangled": DSPOBJ, "address": DSP},
            "plt_bindings": bindings(elf), "cases": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(observe(args.exe), indent=2))
