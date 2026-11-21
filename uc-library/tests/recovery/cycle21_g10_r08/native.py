"""Execute exact original lifecycle instructions using observed external boundaries.

Adapted from the admitted cycle21_g09_s01 native tool and scoped to this packet.
Native delete is observed at the actual PLT transfer and unmaps its live receiver.
"""
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
import struct
import sys

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_SP, UC_ARM_REG_R0,
    UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3,
)

ROOT = Path("/home/rs/projects/opencs/ai-line-analysis")
WAVE = Path("temp/recovery-work/reconstruction10x10-20261121/packeting/post32-next-batch02")
READ_MAP = ROOT / WAVE.parent / "READ_INPUTS-post32-next-batch02-cycle21_g10-post32-next39-scoped01-dispatch02.json"
ELF_ENTRY = "rootfs/RML16AI_Rack_13731/home/root/mixer"
ELF_PATH = Path(json.loads(READ_MAP.read_text())[ELF_ENTRY]["frozen_read_path"])
ELF_SHA = "9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
OBJ, CTRL, PROP, STACK, END = (0x1000000, 0x1001000, 0x1002000, 0x1003000, 0x1004000)
NAME, ALLOC = END + 0x100, END + 0x200
CTRL_TABLE = 3527424
CORE = {
    0x119E8C: "component_construct",
    0x121DBC: "allocator",
    0x121A68: "attributes_construct",
    0x1228B0: "attributes",
    0x11A53C: "component",
}
APP = {
    0x3D300: "audio_destruct",
    0x83130: "dsp_destruct",
    0x82FFC: "linkable_destruct",
    0xB2A10: "controller_release",
    0xB2B04: "controller_d0",
}


def read_word(u, address):
    return struct.unpack("<I", u.mem_read(address, 4))[0]


def write_word(u, address, value):
    u.mem_write(address, struct.pack("<I", value & 0xFFFFFFFF))


def execute(elf, address, has_controller, identifier):
    u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    u.mem_map(0x8000, 0x500000)
    for seg in elf.iter_segments():
        if seg["p_type"] == "PT_LOAD":
            u.mem_write(seg["p_vaddr"], seg.data())
    u.mem_map(OBJ, 0x5000)
    u.mem_write(OBJ, b"\xa5" * 512)
    u.mem_write(NAME, b"NativeLifecycle\0")
    write_word(u, CTRL, CTRL_TABLE)
    # The two receivers have distinct identities, both using the exact
    # Controller implementation of the Core property-handler protocol.
    write_word(u, PROP, CTRL_TABLE)
    write_word(u, OBJ + 0xB0, CTRL if has_controller else 0)
    write_word(u, OBJ + 0xE4, PROP)
    sp = STACK + 0x800
    write_word(u, sp, identifier)
    for reg, val in zip(
        (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR),
        (OBJ, NAME, CTRL, PROP, sp, END),
    ):
        u.reg_write(reg, val)

    events, writes, deallocated = [], [], set()

    def record(u, addr, size, _):
        r0 = u.reg_read(UC_ARM_REG_R0)
        r1 = u.reg_read(UC_ARM_REG_R1)
        if addr in APP:
            label = APP[addr]
            if addr == 0xB2A10 and r0 == PROP:
                label = "property_release"
            event = [label, addr, r0, r1]
            if addr == 0x82FFC:
                event.append(read_word(u, OBJ + 0xB0))
            events.append(event)
        if addr in CORE:
            events.append([CORE[addr], addr, r0, r1])
            if addr == 0x121DBC:
                u.reg_write(UC_ARM_REG_R0, ALLOC)
            if addr == 0x119E8C:
                assert bytes(u.mem_read(r1, 16)) == b"NativeLifecycle\0"
            u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))
        if addr == 0xAC10:
            allocation = {OBJ: "receiver_delete", CTRL: "controller_delete", PROP: "property_delete"}[r0]
            assert r0 not in deallocated
            events.append([allocation, addr, r0, r1])
            u.mem_unmap(r0, 0x1000)
            deallocated.add(r0)
            u.reg_write(UC_ARM_REG_PC, u.reg_read(UC_ARM_REG_LR))

    def write(u, access, addr, size, value, _):
        if (OBJ <= addr < OBJ + 512 or CTRL <= addr < CTRL + 128
                or PROP <= addr < PROP + 128):
            writes.append([addr, size, value])

    u.hook_add(UC_HOOK_CODE, record)
    u.hook_add(UC_HOOK_MEM_WRITE, write)
    u.emu_start(address, END, count=3000)
    assert u.reg_read(UC_ARM_REG_PC) == END
    assert u.reg_read(UC_ARM_REG_R0) == OBJ
    state = {}
    if OBJ not in deallocated:
        state["receiver"] = [read_word(u, OBJ + off) for off in (0, 4, 0xB0, 0xE4)]
    if CTRL not in deallocated:
        state["controller"] = [read_word(u, CTRL + off) for off in (4, 0x14)]
    for dead in deallocated:
        from unicorn import UcError
        try:
            u.mem_read(dead, 1)
        except UcError:
            pass
        else:
            raise AssertionError("Deallocated native mapping is still readable")
    return {"has_controller": has_controller, "id": identifier, "events": events,
            "writes": writes, "state": state, "deallocated": sorted(deallocated)}


def range_receipt(elf, data, mangled):
    symbols = elf.get_section_by_name(".symtab").get_symbol_by_name(mangled)
    assert symbols and len(symbols) == 1
    symbol = symbols[0]
    index = symbol["st_shndx"]
    section = elf.get_section(index)
    address, size = symbol["st_value"], symbol["st_size"]
    assert index == 12 and section.name == ".text"
    assert section["sh_addr"] <= address
    assert address + size <= section["sh_addr"] + section["sh_size"]
    offset = address - section["sh_addr"] + section["sh_offset"]
    checked = data[offset:offset + size]
    assert len(checked) == size
    return dict(mangled=mangled, address=address, size=size,
                section=index, file_offset=offset, range_sha256=sha256(checked).hexdigest())


def generate(task):
    packet = WAVE / "packets" / task
    request = json.loads((packet / "request.json").read_text())
    target = request["targets"][0]
    context = (packet / "ELF_CONTEXT.md").read_text()
    match = re.search(r"section (\S+); SHA256 `([0-9a-f]{64})`", context)
    assert match
    data = ELF_PATH.read_bytes()
    assert sha256(data).hexdigest() == target["original_elf_sha256"] == ELF_SHA
    elf = ELFFile(BytesIO(data))
    original = range_receipt(elf, data, target["mangled"])
    assert all(target[k] == original[k] for k in ("address", "size", "section"))
    assert original["range_sha256"] == match[2]
    names = [
        "_ZN8Presonus5Mixer14AudioComponentD2Ev",
        "_ZN8Presonus12DspComponentD2Ev",
        "_ZN8Presonus17LinkableComponentD2Ev",
        "_ZN8Presonus3Dsp10Controller7releaseEv",
        "_ZN8Presonus3Dsp10ControllerD0Ev",
    ]
    dependencies = [range_receipt(elf, data, name) for name in names]
    case = execute(elf, target["address"], True, 0)
    expected_labels = ["property_release", "property_delete", "dsp_destruct",
                       "controller_release", "controller_delete", "linkable_destruct",
                       "attributes", "component"]
    if task != "cycle21_g10_s08":
        expected_labels.insert(0, "audio_destruct")
    if "D0Ev" in original["mangled"]:
        expected_labels.append("receiver_delete")
    observed = [event[0] for event in case["events"] if event[0] != "controller_d0"]
    assert observed == expected_labels, observed
    for label, addr, pointer, *_ in case["events"]:
        if label in {"audio_destruct", "dsp_destruct", "linkable_destruct", "receiver_delete"}:
            assert pointer == OBJ, (label, addr, pointer)
    assert case["deallocated"] == ([OBJ] if "D0Ev" in original["mangled"] else []) + [CTRL, PROP]
    return {"original": dict(original, elf_sha256=ELF_SHA, firmware=target["firmware"],
                             role=target["role"]),
            "dependency_ranges": dependencies,
            "elf_path": str(ELF_PATH), "cases": [case]}


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.name
    print(json.dumps(generate(task), indent=2))
