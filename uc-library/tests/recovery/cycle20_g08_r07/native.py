"""Observe the exact offline model of each original deleting and complete destructor."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UcError, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP,
                               UC_ARM_REG_LR, UC_ARM_REG_PC)

CLASS = "EarlyRefFormatterT4"
ROLES = {'client': {'D0': {'actual_deallocator': 44380,
                   'address': 67328,
                   'file_offset': 34560,
                   'range_sha256': 'e5410697aab2c1629b044a73f10a1e60ed8320b8960714eb219d3ce21e855383',
                   'size': 44},
            'D1': {'actual_deallocator': None,
                   'address': 65084,
                   'file_offset': 32316,
                   'range_sha256': 'a00bd49c18ad3ba8320e3e5410c311b6b384f8f657987705e8e1f1e79b7fe91e',
                   'size': 28},
            'base': 1611184,
            'base_sha': '402699e98fa7cc3a503aad456658a2c1468b1ac770e700b74775eabb5bdec7c1',
            'elf': '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0',
            'firmware': 'CS18AI surface 13840',
            'registered': {'actual_print': 63484,
                           'actual_scan': 63880,
                           'name': 'earlyrefT4',
                           'vtable': 1613264,
                           'vtable_sha256': '9b12b2eb87bb434f0aa14dbb28098e86255ee46b27a06dca91f266b470b02261'}},
 'server': {'D0': {'actual_deallocator': 44048,
                   'address': 143976,
                   'file_offset': 111208,
                   'range_sha256': 'f67391fb49773e1b46fc197bfec4a3742845f6f5991aa59a84e1fa870d1dc020',
                   'size': 44},
            'D1': {'actual_deallocator': None,
                   'address': 141776,
                   'file_offset': 109008,
                   'range_sha256': 'dd48a7b21b6b862c03281fccbbc23f055aedd14ef213b61e98e4a3587e4a6926',
                   'size': 28},
            'base': 1431992,
            'base_sha': 'c568eb1430581285ac3c5ae3877f7b4127592b0211254d7f3fa7be3eb8238fbb',
            'elf': '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07',
            'firmware': 'RM/RML mixer 13731',
            'registered': {'actual_print': 140224,
                           'actual_scan': 140572,
                           'name': 'earlyrefT4',
                           'vtable': 1439888,
                           'vtable_sha256': 'e5cb931526e86ef3e6dd4a1b1e73015577f1c2c074359e82171ddc746cb406ad'}}}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def replay(address, body, delete, base_vtable, derived_vtable, seed):
    receiver, data, stack, stop = 0x22000000, 0x23000000, 0x24000000, 0x25000000
    cpu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    for page in {a & ~4095 for a in (address, address + len(body) - 1,
                                     delete or address, receiver, data, stack, stop)}:
        cpu.mem_map(page, 4096)
    cpu.mem_write(address, body)
    initial_data = bytes([seed]) * 32
    tail = initial_data[4:]
    cpu.mem_write(receiver, struct.pack("<I", derived_vtable + 8) + tail)
    cpu.mem_write(data, initial_data)
    events = []

    def hook(uc, pc, size, context):
        if address <= pc < address + len(body):
            return
        assert pc == delete and uc.reg_read(UC_ARM_REG_R0) == receiver
        assert uc.mem_read(receiver, 32) == struct.pack("<I", base_vtable + 8) + tail
        uc.mem_unmap(receiver, 4096)
        events.append("same_receiver_unmapped")
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    for reg, val in ((UC_ARM_REG_R0, receiver), (UC_ARM_REG_R1, data),
                     (UC_ARM_REG_SP, stack + 2048), (UC_ARM_REG_LR, stop)):
        cpu.reg_write(reg, val)
    cpu.hook_add(UC_HOOK_CODE, hook)
    cpu.emu_start(address, stop, count=40)
    assert cpu.reg_read(UC_ARM_REG_PC) == stop and cpu.reg_read(UC_ARM_REG_SP) == stack + 2048
    try:
        current = cpu.mem_read(receiver, 32)
    except UcError:
        disposed = True
    else:
        disposed = False
        assert current == struct.pack("<I", base_vtable + 8) + tail
    assert disposed == bool(delete)
    assert events == (["same_receiver_unmapped"] if delete else [])
    assert cpu.mem_read(data, 32) == initial_data
    return dict(seed=seed, receiver_disposed=disposed, data_unchanged=True, events=events)


def observe(rm, surface):
    originals, companions = [], []
    for path, role in ((rm, "server"), (surface, "client")):
        metadata = ROLES[role]
        elf_hash = sha(path.read_bytes())
        assert elf_hash == metadata["elf"]
        with path.open("rb") as stream:
            elf = ELFFile(stream)
            syms = elf.get_section_by_name(".symtab")

            def symbol(name):
                sym, = syms.get_symbol_by_name(name)
                address, length, index = sym["st_value"], sym["st_size"], sym["st_shndx"]
                sec = elf.get_section(index)
                offset = address - sec["sh_addr"]
                assert 0 <= offset < offset + length <= sec["sh_size"]
                return address, sec["sh_offset"] + offset, sec.data()[offset:offset + length], index

            stem = f"N8Presonus5Mixer{len(CLASS)}{CLASS}"
            base, base_offset, base_body, _ = symbol("_ZTVN4Core9FormatterE")
            derived, derived_offset, derived_body, _ = symbol(f"_ZTV{stem}E")
            assert base == metadata["base"] and sha(base_body) == metadata["base_sha"]
            reg = metadata["registered"]
            assert derived == reg["vtable"] and sha(derived_body) == reg["vtable_sha256"]
            assert struct.unpack_from("<II", derived_body, 16) == (reg["actual_print"], reg["actual_scan"])
            assert syms.get_symbol_by_name(f"_Z{stem}D2Ev") is None
            for variant, target in (("D0", originals), ("D1", companions)):
                name = f"_Z{stem}{variant}Ev"
                address, offset, body, section = symbol(name)
                expected = metadata[variant]
                assert (address, offset, len(body), sha(body)) == (
                    expected["address"], expected["file_offset"], expected["size"], expected["range_sha256"])
                slot = 12 if variant == "D0" else 8
                assert struct.unpack_from("<I", derived_body, slot)[0] == address
                assert struct.unpack_from("<I", body, len(body) - 4)[0] == base + 8
                delete = None
                if variant == "D0":
                    instruction, = struct.unpack_from("<I", body, 28)
                    assert instruction >> 24 == 0xEB
                    delta = (instruction & 0xFFFFFF) << 2
                    delete = address + 36 + delta - (1 << 26 if delta & (1 << 25) else 0)
                    assert delete == expected["actual_deallocator"]
                cases = [replay(address, body, delete, base, derived, seed) for seed in (1, 99, 255)]
                target.append(dict(elf_sha256=elf_hash, firmware=metadata["firmware"], role=role,
                                   mangled=name, address=address, size=len(body), section=section,
                                   file_offset=offset, range_sha256=sha(body), cases=cases,
                                   base_table=dict(offset=base_offset, sha256=sha(base_body)),
                                   derived_table=dict(offset=derived_offset, sha256=sha(derived_body)),
                                   registered_name=reg["name"], allocator_target=delete))
    return dict(originals=originals, related_companions=companions)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", required=True, type=Path)
    parser.add_argument("--surface", required=True, type=Path)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--out", type=Path)
    action.add_argument("--check", type=Path)
    args = parser.parse_args()
    result = observe(args.elf, args.surface)
    if args.check is not None:
        assert json.loads(args.check.read_text()) == result
    else:
        with args.out.open("x") as stream:
            stream.write(json.dumps(result, indent=2) + "\n")
    print(f"{CLASS}: 6 exact D0 and 6 exact D1 companion observations")
