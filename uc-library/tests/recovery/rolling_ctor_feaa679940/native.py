"""Offline ARM constructor and destructor traces with explicit call boundaries."""
import argparse
import hashlib
import io
import json
from pathlib import Path

from elftools.elf.elffile import ELFFile
import unicorn as arm
import unicorn.arm_const as reg

OBJECT, FORM, STACK, STOP = 0x1000000, 0x1001000, 0x1100000, 0x1200000
PAGE_CTOR, COMPONENT_DTOR, DELETE_PLT = 0x6826c, 0x11b5e0, 0xad5c
ELF_SHA = "304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0"
PREFIX = "_ZN8Presonus7Surface20PreampsPageComponent"

def digest(data):
    return hashlib.sha256(data).hexdigest()

def trace(elf, raw, name, form=None, tag=0):
    rows = elf.get_section_by_name(".symtab").get_symbol_by_name(name)
    assert len(rows) == 1, name
    symbol = rows[0]
    address, size, index = (symbol[k] for k in ("st_value", "st_size", "st_shndx"))
    section = elf.get_section(index)
    assert section.name == ".text" and section["sh_type"] == "SHT_PROGBITS"
    relative = address - section["sh_addr"]
    assert 0 <= relative and relative + size <= section["sh_size"]
    offset = section["sh_offset"] + relative
    block = raw[offset:offset + size]
    assert len(block) == size and block == section.data()[relative:relative + size]

    u = arm.Uc(arm.UC_ARCH_ARM, arm.UC_MODE_ARM)
    pages = set()
    for segment in elf.iter_segments():
        if segment["p_type"] != "PT_LOAD":
            continue
        base, end = segment["p_vaddr"], segment["p_vaddr"] + segment["p_memsz"]
        for page in range(base & ~4095, (end + 4095) & ~4095, 4096):
            if page not in pages:
                u.mem_map(page, 4096)
                pages.add(page)
        u.mem_write(base, segment.data())
    assert bytes(u.mem_read(address, size)) == block
    u.mem_map(OBJECT, 8192)
    u.mem_map(STACK, 4096)
    u.mem_map(STOP, 4096)
    u.mem_write(OBJECT, bytes([0xa5]) * 256)
    if form is not None:
        u.mem_write(FORM, form.encode() + b"\0")
    u.reg_write(reg.UC_ARM_REG_R0, OBJECT)
    u.reg_write(reg.UC_ARM_REG_R1, FORM)
    u.reg_write(reg.UC_ARM_REG_R2, tag & 0xffffffff)
    u.reg_write(reg.UC_ARM_REG_SP, STACK + 4080)
    u.reg_write(reg.UC_ARM_REG_LR, STOP)
    calls, writes, instructions = [], [], []

    def cstring(pointer):
        return bytes(u.mem_read(pointer, 128)).split(b"\0", 1)[0].decode()

    def code(uc, pc, _, data):
        if pc in (PAGE_CTOR, COMPONENT_DTOR, DELETE_PLT):
            receiver = uc.reg_read(reg.UC_ARM_REG_R0)
            assert receiver == OBJECT
            call = {"target": pc, "receiver": receiver}
            if pc == PAGE_CTOR:
                descriptor = uc.reg_read(reg.UC_ARM_REG_R1)
                original_form = uc.reg_read(reg.UC_ARM_REG_R2)
                original_tag = uc.reg_read(reg.UC_ARM_REG_R3)
                assert original_form == FORM and original_tag == tag & 0xffffffff
                call.update(descriptor_address=descriptor, descriptor=cstring(descriptor),
                            form_address=original_form, form=cstring(original_form),
                            tag_u32=original_tag)
            calls.append(call)
            uc.reg_write(reg.UC_ARM_REG_PC, uc.reg_read(reg.UC_ARM_REG_LR))
        else:
            assert address <= pc < address + size, hex(pc)
            instructions.append(pc)

    def write(uc, access, addr, width, value, data):
        if OBJECT <= addr < OBJECT + 256:
            writes.append([addr - OBJECT, width, value])

    u.hook_add(arm.UC_HOOK_CODE, code)
    u.hook_add(arm.UC_HOOK_MEM_WRITE, write)
    u.emu_start(address, STOP, count=100)
    assert u.reg_read(reg.UC_ARM_REG_PC) == STOP
    assert [(offset, width) for offset, width, _ in writes] == [(4, 4), (132, 4), (0, 4)]
    expected = [PAGE_CTOR] if form is not None else [COMPONENT_DTOR]
    if name.endswith("D0Ev"):
        expected.append(DELETE_PLT)
    assert [call["target"] for call in calls] == expected
    return {"mangled": name, "address": address, "size": size, "section": section.name,
            "section_index": index, "file_offset": offset, "bytes_sha256": digest(block),
            "form": form, "tag": tag, "calls": calls, "writes": writes,
            "executed": instructions}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, required=True)
    result = parser.add_mutually_exclusive_group(required=True)
    result.add_argument("--verify", type=Path)
    result.add_argument("--out", type=Path)
    args = parser.parse_args()
    raw = args.elf.read_bytes()
    assert digest(raw) == ELF_SHA
    elf = ELFFile(io.BytesIO(raw))
    cases = [("", 0), ("sceneOne", -1), ("thirty-two-byte-form-name-0123456789", -2147483648),
             ("another form", 2147483647)]
    observations = {
        "elf_sha256": ELF_SHA,
        "constructors": [trace(elf, raw, PREFIX + variant + "EPKci", form, tag)
                         for variant in ("C1", "C2") for form, tag in cases],
        "destructors": [trace(elf, raw, PREFIX + variant + "Ev") for variant in ("D1", "D0")],
    }
    if args.verify:
        assert json.loads(args.verify.read_text()) == observations
    else:
        args.out.write_text(json.dumps(observations, indent=2) + "\n")
    print("8 ARM constructor traces and 2 ARM destructor traces verified")

if __name__ == "__main__":
    main()
