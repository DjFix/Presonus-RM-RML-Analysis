"""Replay the bound original ARM target and primary vtable slot offline."""

import argparse
import hashlib
from pathlib import Path
import json
import struct

from elftools.elf.elffile import ELFFile
import unicorn as uc
from unicorn import arm_const as arm

SYMBOL = '_ZN8Presonus7Surface19MarkerPageComponent20setMappingControllerEPNS_18IMappingControllerE'
ADDRESS = 737032
SIZE = 16
BODY_HASH = '60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad'
SLOT = 2000992
TABLE_ADDRESS = 2000928
TABLE_SIZE = 184
TABLE_HASH = '2b865eb87a7b38cce2f7a2763e19fda8e0eb8de4a2b5e888949c730b449d42eb'
TABLE_SYMBOL = '_ZTVN8Presonus7Surface19MarkerPageComponentE'
ELF_HASH = '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
START = 0x30000000
STACK = 0x30001000
RETURN = 0x30002000


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_symbol(elf, name, address, size, section_name, expected_hash):
    symbols = elf.get_section_by_name('.symtab').get_symbol_by_name(name)
    matches = [entry for entry in symbols if entry['st_value'] == address and entry['st_size'] == size]
    require(len(matches) == 1, f'Unexpected exact ELF symbol matches for {name}')
    section_index = matches[0]['st_shndx']
    section = elf.get_section(section_index)
    require(section.name == section_name, f'Unexpected section for {name}')
    relative = address - section['sh_addr']
    require(0 <= relative <= section['sh_size'] - size, f'Invalid range for {name}')
    code = section.data()[relative: relative + size]
    require(hashlib.sha256(code).hexdigest() == expected_hash, f'Changed range for {name}')
    return code, {'mangled': name, 'address': address, 'size': size, 'section': section_name,
                  'section_index': section_index, 'offset': section['sh_offset'] + relative,
                  'sha256': expected_hash}


def run(body, table, via_slot, seed):
    engine = uc.Uc(uc.UC_ARCH_ARM, uc.UC_MODE_ARM)
    for start in {ADDRESS & ~0xfff, TABLE_ADDRESS & ~0xfff}:
        engine.mem_map(start, 0x1000)
    engine.mem_map(START, 0x3000)
    engine.mem_write(ADDRESS, body)
    engine.mem_write(TABLE_ADDRESS, table)
    state = bytearray(bytes([seed]) * 0x1000)
    struct.pack_into('<I', state, 0, TABLE_ADDRESS + 8)
    engine.mem_write(START, bytes(state))
    entry = ADDRESS
    if via_slot:
        vptr = struct.unpack('<I', engine.mem_read(START, 4))[0]
        require(SLOT >= vptr, 'Unrecognized address point')
        entry = struct.unpack('<I', engine.mem_read(vptr + (SLOT - vptr), 4))[0]
    require(entry == ADDRESS, 'Vtable resolved outside exact target')
    sentinel = {arm.UC_ARM_REG_R0: START, arm.UC_ARM_REG_R1: START + 0x200 if seed else 0,
                arm.UC_ARM_REG_R2: START + 0x400, arm.UC_ARM_REG_R3: 0x71325748,
                arm.UC_ARM_REG_SP: STACK + 0x800, arm.UC_ARM_REG_LR: RETURN,
                arm.UC_ARM_REG_R11: 0x11329738}
    for reg, val in sentinel.items():
        engine.reg_write(reg, val)
    trace = []
    access = []
    engine.hook_add(uc.UC_HOOK_CODE, lambda _, pc, size, data: trace.append(pc))
    engine.hook_add(uc.UC_HOOK_MEM_READ | uc.UC_HOOK_MEM_WRITE,
                    lambda _, kind, at, size, value, data: access.append([kind, at, size]))
    engine.emu_start(entry, RETURN, count=32)
    require(engine.reg_read(arm.UC_ARM_REG_PC) == RETURN, 'Did not reach return boundary')
    require(trace == list(range(ADDRESS, ADDRESS + SIZE, 4)), 'Unexpected instructions or calls')
    require(all(STACK + 0x7f0 <= at <= STACK + 0x800 - size for _, at, size in access),
            'Unexpected non-frame memory access')
    require(all(engine.reg_read(reg) == val for reg, val in sentinel.items()), 'Changed entry register')
    require(bytes(engine.mem_read(START, len(state))) == state, 'Changed receiver or argument memory')
    return {'seed': seed, 'dispatch': 'primary_vtable_word' if via_slot else 'direct',
            'entry': entry, 'instructions': trace, 'memory_accesses': access,
            'state_unchanged': True, 'entry_registers_preserved': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--elf', type=Path, required=True)
    parser.add_argument('--verify', type=Path)
    args = parser.parse_args()
    with args.elf.open('rb') as stream:
        require(hashlib.file_digest(stream, 'sha256').hexdigest() == ELF_HASH, 'Original ELF changed')
        stream.seek(0)
        elf = ELFFile(stream)
        body, target = read_symbol(elf, SYMBOL, ADDRESS, SIZE, '.text', BODY_HASH)
        table, vtable = read_symbol(elf, TABLE_SYMBOL, TABLE_ADDRESS, TABLE_SIZE, '.rodata', TABLE_HASH)
    rows = [run(body, table, via_slot, seed) for via_slot in (False, True) for seed in (0, 165)]
    result = {'elf_sha256': ELF_HASH, 'unicorn_version': uc.__version__,
              'original': target, 'vtable': vtable, 'slot_address': SLOT,
              'native_cases': rows}
    if args.verify:
        require(result == json.loads(args.verify.read_text()), 'Fresh native observations differ')
        print(f'Verified {len(rows)} independent ARM observations for {SYMBOL}')
    else:
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
