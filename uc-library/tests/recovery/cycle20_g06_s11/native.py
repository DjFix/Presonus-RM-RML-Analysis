"""Replay sealed ARM instructions for the assigned offline Panel entry point."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *


CYCLE = Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/control10x20-after-4fed70d11')
PACKET = CYCLE / 'packeting/actual06-first-capture01/packets' / Path(__file__).parent.name
MAP = CYCLE / 'packeting/READ_INPUTS-actual06-first-capture01-cycle20_g06-actual06-authorized42-scoped03.json'
ENTRY = re.compile(r'ELF `([a-f0-9]+)`; version `([^`]+)`; `([^`]+)`; original `([^`]+)`; address `(0x[0-9a-f]+)`; size (\d+); section (\S+); SHA256 `([a-f0-9]+)`\nOriginal ELF path: `([^`]+)`; file offset `(0x[0-9a-f]+)`')
RECEIVER, STACK, STOP = 0x50000000, 0x60000000, 0x70000000


def digest(data):
    return hashlib.sha256(data).hexdigest()


def frozen(read_map, basename):
    key, = (key for key in read_map if key.endswith('/' + basename))
    source = read_map[key]
    raw = Path(source['frozen_read_path']).read_bytes()
    assert digest(raw) == source['sha256']
    return json.loads(raw)


def map_memory(elf):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    mapped = set()
    for segment in elf.iter_segments():
        if segment['p_type'] != 'PT_LOAD':
            continue
        va = segment['p_vaddr']
        for page in range(va & ~4095, (va + segment['p_memsz'] + 4095) & ~4095, 4096):
            if page not in mapped:
                uc.mem_map(page, 4096)
                mapped.add(page)
        uc.mem_write(va, segment.data())
    for page in (RECEIVER, STACK, STOP, EXTRA, DELEGATE, MANAGER, PARAM & ~4095):
        uc.mem_map(page, 4096)
    return uc


EXTRA, DELEGATE, MANAGER, PARAM = 0x51000000, 0x52000000, 0x53000000, 1459618048


def u32(uc, address):
    return struct.unpack('<I', uc.mem_read(address, 4))[0]


def put_u32(uc, address, value):
    uc.mem_write(address, struct.pack('<I', value & 0xffffffff))


def c_string(uc, address):
    return bytes(uc.mem_read(address, 128)).split(b'\0', 1)[0]


def execute(uc, address, args):
    for register, value in zip((UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3), args):
        uc.reg_write(register, value & 0xffffffff)
    uc.reg_write(UC_ARM_REG_SP, STACK + 4096)
    uc.reg_write(UC_ARM_REG_LR, STOP)
    uc.emu_start(address, STOP, count=450)
    assert uc.reg_read(UC_ARM_REG_PC) == STOP and uc.reg_read(UC_ARM_REG_SP) == STACK + 4096
    return uc.reg_read(UC_ARM_REG_R0)


def run(elf, address, mangled, role, read_map, elf_sha):
    if PACKET.name.endswith('s11'):
        results = []
        for dirty in (0, 1, 2, 7, 0x80000000, 0xffffffff, 0):
            uc = map_memory(elf)
            uc.mem_write(RECEIVER, b'\xb7' * 128)
            put_u32(uc, RECEIVER + 0x74, dirty)
            before = bytes(uc.mem_read(RECEIVER, 128))
            observed = execute(uc, address, [RECEIVER])
            assert observed in (0, 1) and bytes(uc.mem_read(RECEIVER, 128)) == before
            method = int('FieldElement' in mangled)
            results.append({'input': [method, dirty], 'expected': str(observed), 'events': []})
        return results

    catalog = frozen(read_map, 'FIELD_TEXT_CONSTRUCTION_NATIVE.json')
    prior_pin = CYCLE / 'packeting/READ_INPUTS-actual04-next-batch01-cycle20_g06-actual04-next20-scoped02.json'
    prior_map = json.loads(prior_pin.read_text())
    lookup_key, = [key for key in prior_map if key.endswith('/FIELD_LOOKUP_NATIVE.json')]
    assert catalog['typed_lookup_provider']['sha256'] == prior_map[lookup_key]['sha256']
    lookup = frozen(prior_map, 'FIELD_LOOKUP_NATIVE.json')['role_observations'][elf_sha]
    variants = catalog['exact_constructor_roles']
    text = PACKET.name.endswith('s20')
    kind = 'text-int-construction' if text else 'field-int-construction'
    row, = [r for r in variants[kind] if (r['elf_sha256'], r['original_mangled']) == (elf_sha, mangled)]
    field = row
    if text:
        field, = [r for r in variants['field-int-construction'] if
                  (r['elf_sha256'], r['original_address']) == (elf_sha, row['calls']['base']['address'])]
    for body in (field, row):
        elf.stream.seek(body['file_offset'])
        assert digest(elf.stream.read(body['original_size'])) == body['content_sha256']
    calls = field['calls']
    result = []

    for case in row['cases']:
        x, y = case['xy']
        name = case['field_name'].encode()
        uc = map_memory(elf)
        uc.mem_write(RECEIVER, b'\xb7' * 0xb00)
        uc.mem_write(EXTRA, name + b'\0')
        put_u32(uc, lookup['global_LCD_manager_slot'], MANAGER)
        put_u32(uc, MANAGER + 4, DELEGATE)
        put_u32(uc, DELEGATE, DELEGATE + 64)
        put_u32(uc, DELEGATE + 64, DELEGATE + 128)
        trace, events = [], []
        modeled = {
            (0xaba0 if role == 'client' else 0xaa60): 'memset',
            calls['string']['address']: 'string',
            calls['copy']['address']: 'copy',
            DELEGATE + 128: 'resolved_delegate',
            lookup['providers']['add']['target_address']: 'observe',
        }
        actual = {calls['base']['address']: 'OffscreenC2',
                  calls['lookup']['address']: 'FieldLookup',
                  lookup['providers']['LCDManager']['target_address']: 'LCDLookup'}
        if text:
            actual[field['original_address']] = 'FieldC2'

        def hook(machine, pc, _, data):
            a, b, n, r3 = [machine.reg_read(reg) for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3)]
            if pc in actual:
                tag = actual[pc]
                trace.append(tag)
                if tag in ('OffscreenC2', 'FieldC2'):
                    assert (a, b, n) == (RECEIVER, x & 0xffffffff, y & 0xffffffff)
                if tag == 'FieldC2':
                    assert r3 == EXTRA
            event = modeled.get(pc)
            if event is None:
                return
            events.append(event)
            if event == 'memset':
                assert (a, b, n) == (RECEIVER + 4, 0, 96)
                machine.mem_write(a, bytes(n))
            elif event == 'string':
                assert (a, b) == (RECEIVER + 0x984, 0)
                machine.mem_write(a, b'\0')
            elif event == 'copy':
                assert (a, b) == (RECEIVER + 0x18, EXTRA) and c_string(machine, b) == name
                machine.mem_write(a, name + b'\0')
            elif event == 'resolved_delegate':
                assert (a, b) == (DELEGATE, RECEIVER + 0x18)
                assert c_string(machine, b) == name
                machine.reg_write(UC_ARM_REG_R0, PARAM if case['attached_parameter'] else 0)
            elif event == 'observe':
                assert (a, b) == (PARAM, RECEIVER + 0x97c)
            machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

        uc.hook_add(UC_HOOK_CODE, hook)
        assert execute(uc, address, [RECEIVER, x, y, EXTRA]) == RECEIVER
        assert events == case['observed_calls']
        assert trace == (['FieldC2'] if text else []) + ['OffscreenC2', 'FieldLookup', 'LCDLookup']
        values = {offset: u32(uc, RECEIVER + int(offset, 16)) for offset in case['expected_fields_verified']}
        assert values == case['expected_fields_verified']
        assert bytes(uc.mem_read(RECEIVER + 0xa24, 16)) == b'\xb7' * 16
        assert c_string(uc, RECEIVER + 0x18) == name and u32(uc, RECEIVER + 0x980) in (0, PARAM)
        assert bytes(uc.mem_read(RECEIVER + 0x984, 1)) == b'\0'
        if text:
            assert bytes(uc.mem_read(RECEIVER + 0xa1c, 1)) == b'\0'
        name_token = name.hex() or '-'
        expected = f'{x} {y} {values["0x74"]} {int(values["0x980"] != 0)} 1'
        if text:
            expected += ' 0 1'
        result.append({'input': [x, y, int(case['attached_parameter']), name_token],
                       'expected': expected, 'modeled_boundary_calls': events,
                       'native_application_calls': trace, 'native_words': values})
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', type=Path)
    parser.add_argument('--write', type=Path)
    args = parser.parse_args()
    read_map = json.loads(MAP.read_text())
    context = (PACKET / 'ELF_CONTEXT.md').read_text().split('## Typed relationships')[0]
    originals = []
    for match in ENTRY.finditer(context):
        sha, firmware, role, mangled, addr_hex, size_str, section, content, path, off_hex = match.groups()
        address, size, offset = int(addr_hex, 16), int(size_str), int(off_hex, 16)
        binding = read_map[path]
        data = Path(binding['frozen_read_path']).read_bytes()
        assert digest(data) == sha == binding['sha256']
        elf = ELFFile(io.BytesIO(data))
        text = elf.get_section_by_name(section)
        assert offset == text['sh_offset'] + address - text['sh_addr']
        assert address >= text['sh_addr'] and address + size <= text['sh_addr'] + text['sh_size']
        assert digest(data[offset:offset + size]) == content
        originals.append({'elf_sha256': sha, 'firmware': firmware, 'role': role, 'mangled': mangled,
                          'address': address, 'size': size, 'section': section, 'file_offset': offset,
                          'body_sha256': content, 'cases': run(elf, address, mangled, role, read_map, sha)})
    assert originals
    result = json.loads(json.dumps({'originals': originals}))
    if args.check:
        assert result == json.loads(args.check.read_text())
    if args.write:
        args.write.write_text(json.dumps(result, indent=2) + '\n')
    print(f"{len(originals)} exact ELF ranges, {sum(len(row['cases']) for row in originals)} native executions")


if __name__ == '__main__':
    main()
