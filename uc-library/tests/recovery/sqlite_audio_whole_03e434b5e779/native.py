"""Replay the sealed ARM constructor/destructor and application callees."""
import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM, Uc
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
    UC_ARM_REG_R3, UC_ARM_REG_SP,
)

PACKETS = Path("temp/recovery-work/sqlite-issued/packet")
OBJECT, CONTROLLER, PROCESS = 0x1000000, 0x1001000, 0x1003000
HANDLER, PARAMETER, ARRAY = 0x1004000, 0x1005000, 0x1006000
DESCRIPTOR, DESCRIPTORS, INFO = 0x1007000, 0x1008000, 0x1009000
NAME, STACK, EXIT = 0x100a000, 0x1018000, 0x100b000
HANDLER_RELEASE, SET_PARAMETER = 0x100c000, 0x100d000
ALLOCATE, DEALLOCATE = 0xa7e4, 0xac10
EQ_C2, AUDIO_PARAM_ADD = 0xc8d84, 0x11ec54
LINKABLE_C2, COMPONENT_D2, ATTRIBUTES_D2 = 0x82a48, 0x11a53c, 0x1228b0
DSP_SYNC, DSP_INFO = 0x82428, 0xb3db0
AUDIO_C2, AUDIO_D2 = 0x3d3c4, 0x3d300
FILTER_INIT = {
    "HP": (0xc90f8, 0x493e68, 0x172948, 0x3dae8),
    "LP": (0xc9294, 0x493e6c, 0x1728f4, 0x3d970),
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def native(original, controller_id, channel_id):
    contents = Path(original["elf_path"]).read_bytes()
    assert digest(contents) == original["elf"]
    elf = ELFFile(io.BytesIO(contents))
    section = elf.get_section(original["section"])
    offset = section["sh_offset"] + original["address"] - section["sh_addr"]
    assert section.name == original["section_name"]
    assert offset == original["file_offset"]
    assert original["address"] + original["size"] <= section["sh_addr"] + section["sh_size"]
    target = contents[offset:offset + original["size"]]
    assert digest(target) == original["range_sha256"]
    assert target.hex() == original["range_hex"]
    symbols = elf.get_section_by_name(".symtab")
    assert any(
        sym["st_value"] == original["address"] and sym["st_size"] == original["size"]
        and sym["st_shndx"] == original["section"]
        for sym in symbols.get_symbol_by_name(original["mangled"])
    )
    u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    u.mem_map(0x8000, 0x500000)
    for p in elf.iter_segments():
        if p["p_type"] == "PT_LOAD":
            u.mem_write(p["p_vaddr"], p.data())
    u.mem_map(OBJECT, 0x20000)
    trace = []
    observed = {}
    phase = "construct"
    kind = "HP" if "HPFilterComponent" in original["mangled"] else "LP"
    controller_ctor, guard, table, construct_entry = FILTER_INIT[kind]
    destroying = "D1Ev" in original["mangled"]
    object_live = False
    provider_live = False
    parameter_live = False

    def put(at, value):
        u.mem_write(at, struct.pack("<I", value & 0xffffffff))

    def word(at):
        return struct.unpack("<I", u.mem_read(at, 4))[0]

    def string(at):
        return bytes(u.mem_read(at, 64)).split(b"\0", 1)[0].decode() if at else None

    # Source-independent initialized descriptor input. The static XMen table
    # gives the tag/default, while the native filter list constructors give
    # input flags 2, and addFloat sets 0x20 before getParameterInfo clears it.
    # EQ base and CCL providers are boundary-modeled here.
    raw = bytes(u.mem_read(table, 84))
    ptype, tag = struct.unpack_from("<2I", raw)
    minimum, maximum, midpoint, default, delta, flags = struct.unpack_from("<6I", raw, 40)
    unit, curve, strings, title, short_title = map(string, struct.unpack_from("<5I", raw, 64))
    assert strings is None
    parameter_table = {
        "type": ptype, "tag": tag, "name": raw[8:40].split(b"\0")[0].decode(),
        "minimum": minimum, "maximum": maximum, "midpoint": midpoint,
        "default": default, "delta": delta, "flags": flags, "unit": unit,
        "curve": curve, "title": title, "short_title": short_title,
    }
    u.mem_write(NAME, b"filter-channel\0")
    put(guard, 1)
    put(HANDLER, HANDLER + 0x100)
    put(HANDLER + 0x108, HANDLER_RELEASE)
    put(PARAMETER, PARAMETER + 0x100)
    put(PARAMETER + 0xc, table)
    put(PARAMETER + 0x158, SET_PARAMETER)
    put(ARRAY, PARAMETER)
    put(DESCRIPTORS, DESCRIPTOR)
    put(DESCRIPTOR, tag)
    put(DESCRIPTOR + 0xc, 0x22)
    put(DESCRIPTOR + 0x14, default)

    def hook(cpu, address, _size, _data):
        nonlocal object_live, provider_live, parameter_live
        self, arg1, arg2, arg3 = (
            cpu.reg_read(reg) for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)
        )
        sp = cpu.reg_read(UC_ARM_REG_SP)
        if address == ALLOCATE:
            assert not provider_live
            provider_live = True
            trace.append(["operator-new", self])
            cpu.reg_write(UC_ARM_REG_R0, CONTROLLER)
        elif address == controller_ctor:
            assert self == CONTROLLER and arg1 == controller_id & 0xffffffff
            trace.append(["filter-controller-ctor", arg1])
            return
        elif address == EQ_C2:
            assert self == CONTROLLER and arg1 == 1 and arg2 == controller_id & 0xffffffff
            trace.append(["eq-controller-ctor-boundary", arg1, arg2, arg3])
            put(CONTROLLER + 8, 0xffffffff)
            put(CONTROLLER + 0xc, arg3)
            put(CONTROLLER + 0x18, arg2)
            put(CONTROLLER + 0x28, PROCESS)
            put(arg3 + 4, DESCRIPTORS)
            put(arg3 + 8, 1)
        elif address == AUDIO_C2:
            assert (self, arg1, arg2, arg3, word(sp)) == (
                OBJECT, NAME, CONTROLLER, HANDLER, channel_id & 0xffffffff)
            trace.append(["audio-ctor", string(arg1), word(sp)])
            return
        elif address == LINKABLE_C2:
            assert self == OBJECT and arg1 == NAME
            object_live = True
            trace.append(["linkable-ctor-boundary"])
        elif address == AUDIO_PARAM_ADD:
            assert (self, arg1, arg2, arg3) == (OBJECT + 0x28, table, 1, 0)
            assert object_live and not parameter_live
            parameter_live = True
            put(OBJECT + 0x34, ARRAY)
            put(OBJECT + 0x38, 1)
            trace.append(["ccl-param-add-boundary", table, arg2, arg3])
        elif address == DSP_SYNC:
            assert self == OBJECT and arg1 == 1
            trace.append(["dsp-sync", arg1])
            return
        elif address == SET_PARAMETER:
            assert self == PARAMETER and arg2 == 0
            trace.append(["ccl-param-set-boundary", arg1, arg2])
            observed["value"] = arg1
        elif address == DSP_INFO:
            assert self == CONTROLLER and arg2 == 0
            trace.append(["controller-param-info", arg2])
            observed["native_info_address"] = arg1
            return
        elif address == AUDIO_D2:
            assert self == OBJECT and phase == "destroy"
            trace.append(["audio-dtor"])
            return
        elif address == HANDLER_RELEASE:
            assert self == HANDLER and provider_live and parameter_live
            trace.append(["handler-release"])
        elif address == DEALLOCATE:
            assert self == CONTROLLER and provider_live
            provider_live = False
            trace.append(["controller-deallocation"])
        elif address == ATTRIBUTES_D2:
            assert self == OBJECT + 0x90
            trace.append(["ccl-attributes-dtor-boundary"])
        elif address == COMPONENT_D2:
            assert self == OBJECT and object_live and parameter_live
            assert not provider_live
            parameter_live = False
            object_live = False
            trace.append(["ccl-component-dtor-boundary"])
        else:
            return
        cpu.reg_write(UC_ARM_REG_PC, cpu.reg_read(UC_ARM_REG_LR))

    def run(at, arguments):
        for reg, val in zip((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3), arguments):
            u.reg_write(reg, val & 0xffffffff)
        put(STACK, channel_id)
        u.reg_write(UC_ARM_REG_SP, STACK)
        u.reg_write(UC_ARM_REG_LR, EXIT)
        u.emu_start(at, EXIT, count=20000)
        assert u.reg_read(UC_ARM_REG_PC) == EXIT

    u.hook_add(UC_HOOK_CODE, hook)
    run(construct_entry if destroying else original["address"], (OBJECT, NAME, HANDLER, controller_id))
    assert u.reg_read(UC_ARM_REG_R0) == OBJECT
    assert word(CONTROLLER + 4) == channel_id & 0xffffffff
    assert word(CONTROLLER + 0x14) == HANDLER
    assert observed["value"] == word(PROCESS + 4)
    observed.update({
        "controller_id": controller_id, "channel_id": channel_id,
        "table": parameter_table, "count": word(OBJECT + 0x38),
        "readouts": word(OBJECT + 0xb8),
        "descriptor_flags": word(observed.pop("native_info_address") + 0xc),
        "band_type": word(PROCESS),
        "band_enabled": u.mem_read(CONTROLLER + 0xa30, 1)[0],
        "band_dirty": u.mem_read(PROCESS + 0x139, 1)[0],
        "band_active": u.mem_read(PROCESS + 0x13a, 1)[0],
        "provider_pending": u.mem_read(CONTROLLER + 0x1c, 1)[0],
        "vptr_words": [word(OBJECT), word(OBJECT + 4)],
    })
    assert observed["readouts"] == 0 and observed["count"] == 1
    phase = "destroy"
    trace.append(["begin-destroy"])
    destroy_entry = original["address"] if destroying else (0x3e0e0 if kind == "HP" else 0x3e078)
    run(destroy_entry, (OBJECT,))
    assert not provider_live and not parameter_live and not object_live
    assert word(OBJECT + 0xb0) == 0
    assert list(t[0] for t in trace[trace.index(["begin-destroy"]) + 1:]) == [
        "audio-dtor", "handler-release", "controller-deallocation",
        "ccl-attributes-dtor-boundary", "ccl-component-dtor-boundary",
    ]
    return {"observed": observed, "trace": trace}, offset


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("packet")
    parser.add_argument("fixture")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    manifest = json.loads((PACKETS / args.packet / "CONTEXT.json").read_text())
    rows = []
    for row in manifest["originals"]:
        original = row["original"]
        cases = []
        for controller_id, channel_id in ((3, 27), (4660, -8), (-21, 65535)):
            case, offset = native(original, controller_id, channel_id)
            cases.append(case)
        rows.append({
            "original": original, "offset": offset, "cases": cases,
            "literal_pool_size": 4 if "D1Ev" in original["mangled"] else 12,
        })
    fixture = Path(args.fixture)
    payload = json.dumps(rows, indent=2, sort_keys=True) + "\n"
    if args.write:
        fixture.write_text(payload)
    else:
        assert fixture.read_text() == payload
    print(f"{args.packet} {sum(len(item['cases']) for item in rows)} native cases")


if __name__ == "__main__":
    main()
