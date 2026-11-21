"""Execute exact original application ranges with external Core calls intercepted."""
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
WAVE = Path("temp/recovery-work/reconstruction10x10-20261121/packeting/wave0509-batch01")
GROUP = "cycle21_g09"
ELF_PATH = ROOT / WAVE / "snapshot/rootfs/RML16AI_Rack_13731/home/root/mixer"
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
    0x82AFC: "dsp_construct",
    0x83130: "dsp_destruct",
    0x82FFC: "linkable_destruct",
    0xB2A10: "controller_release",
    0xB2B04: "controller_d0",
    0xB2764: "set_target",
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
            if addr == 0xB2764:
                event.extend((read_word(u, r0 + 4), read_word(u, OBJ + 0xE4)))
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
    return {"has_controller": has_controller, "id": identifier, "events": events,
            "writes": writes, "state": state}


def generate(task):
    packet = WAVE / "packets" / task
    request = json.loads((packet / "request.json").read_text())
    target = request["originals"][0]["original"]
    context = (packet / "ELF_CONTEXT.md").read_text()
    match = re.search(r"section (\S+); SHA256 `([0-9a-f]{64})`", context)
    assert match
    data = ELF_PATH.read_bytes()
    assert sha256(data).hexdigest() == target["elf"] == ELF_SHA
    elf = ELFFile(BytesIO(data))
    section = elf.get_section(int(target["section_json"]))
    assert section.name == match[1]
    offset = target["address"] - section["sh_addr"] + section["sh_offset"]
    checked = data[offset:offset + target["size"]]
    assert len(checked) == target["size"] and sha256(checked).hexdigest() == match[2]
    candidates = elf.get_section_by_name(".symtab").get_symbol_by_name(target["mangled"])
    assert any(s["st_value"] == target["address"] and s["st_size"] == target["size"]
               and s["st_shndx"] == int(target["section_json"]) for s in candidates)
    kind = int(task[-2:])
    domain = [(False, 0)] if kind <= 3 else [(False, 0), (True, 0)]
    if kind in (7, 8):
        domain = [(True, value) for value in (0, 314159, -7, -2147483648)]
    if kind in (9, 10):
        domain = [(True, 0)]
    return {"original": target, "file_offset": offset, "range_sha256": match[2],
            "section": section.name, "elf_path": str(ELF_PATH),
            "cases": [execute(elf, target["address"], present, ident) for present, ident in domain]}


if __name__ == "__main__":
    print(json.dumps(generate(sys.argv[1]), indent=2))
