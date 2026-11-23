"""Run the exact ARM TextEntry and delegated Field getter instructions offline."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile
from unicorn import UC_ARCH_ARM, UC_HOOK_CODE, UC_MODE_ARM, Uc
from unicorn.arm_const import (
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_SP,
)

ROOT = Path('/home/rs/projects/opencs/ai-line-analysis')
CYCLE = ROOT / 'temp/recovery-work/control10x20-after-4fed70d11'
READ_MAP = CYCLE / 'packeting/READ_INPUTS-actual07-authorized-wave01-capture02-cycle20_g06-actual07-authorized-wave01-scoped03.json'
PROVIDER_RECEIPT = 'TEXTENTRY_INTERNAL_NATIVE01.json'
ORIGINAL = '_ZN8Presonus5Panel16TextEntryElement16getInternalParamEv'
RECEIVER, STACK, STOP = 0x50100000, 0x60000000, 0x70000000
PARAM_IDS = {0: 0, 1158676480: 1, 1159725056: 2, 1160773632: 3}
ROLES = {
    'client': ('rootfs/CS18_v13840/home/root/surface', 'CS18AI surface 13840'),
    'server': ('rootfs/RML16AI_Rack_13731/home/root/mixer', 'RM/RML mixer 13731'),
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def frozen(item):
    raw = Path(item['frozen_read_path']).read_bytes()
    assert digest(raw) == item['sha256']
    return raw


def verify_range(elf, raw, row):
    text = elf.get_section_by_name(row['section'])
    address, size = row['address'], row['size']
    delta = address - text['sh_addr']
    assert 0 <= delta and delta + size <= text['sh_size']
    offset = text['sh_offset'] + delta
    assert offset == row['file_offset'] and digest(raw[offset:offset + size]) == row['range_sha256']


def run(elf, row, case):
    uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    mapped = set()
    for segment in elf.iter_segments():
        if segment['p_type'] != 'PT_LOAD':
            continue
        start = segment['p_vaddr']
        for page in range(start & ~4095, (start + segment['p_memsz'] + 4095) & ~4095, 4096):
            if page not in mapped:
                uc.mem_map(page, 4096)
                mapped.add(page)
        uc.mem_write(start, segment.data())
    for page in (RECEIVER, STACK, STOP):
        uc.mem_map(page, 4096)
    uc.mem_write(RECEIVER, b'\xb7' * 0xa00)
    uc.mem_write(RECEIVER + 0x61, bytes([int(case['dirty'])]))
    uc.mem_write(RECEIVER + 0x980, struct.pack('<I', case['initial']))
    before = bytes(uc.mem_read(RECEIVER, 0xa00))
    calls = []

    def hook(machine, pc, _, data):
        if pc in (row['actual_field_get']['address'], row['original_lookup']['address']):
            assert machine.reg_read(UC_ARM_REG_R0) == RECEIVER
        if pc == row['actual_field_get']['address']:
            calls.append('actual original FieldElement::getParam')
        if pc == row['original_lookup']['address']:
            calls.append('actual typed Field lookup boundary')
            machine.mem_write(RECEIVER + 0x980, struct.pack('<I', case['lookup_return']))
            machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

    uc.hook_add(UC_HOOK_CODE, hook)
    uc.reg_write(UC_ARM_REG_R0, RECEIVER)
    uc.reg_write(UC_ARM_REG_SP, STACK + 4096)
    uc.reg_write(UC_ARM_REG_LR, STOP)
    uc.emu_start(row['address'], STOP, count=100)
    assert uc.reg_read(UC_ARM_REG_PC) == STOP and uc.reg_read(UC_ARM_REG_SP) == STACK + 4096
    returned = uc.reg_read(UC_ARM_REG_R0)
    assert returned == case['returned'] and calls == case['calls']
    after = bytes(uc.mem_read(RECEIVER, 0xa00))
    assert after[:0x980] == before[:0x980] and after[0x984:] == before[0x984:]
    assert struct.unpack_from('<I', after, 0x980)[0] == returned
    return {
        'input': [PARAM_IDS[case['initial']], int(case['dirty']), PARAM_IDS[case['lookup_return']]],
        'expected': f'{PARAM_IDS[returned]} {int(len(calls) == 2)}',
        'native_same_receiver_calls': calls,
        'native_return_word': returned,
    }


def main():
    parser = argparse.ArgumentParser()
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--check', type=Path)
    choice.add_argument('--write', type=Path)
    args = parser.parse_args()
    read_map = json.loads(READ_MAP.read_text())
    item, = [item for key, item in read_map.items() if key.endswith('/' + PROVIDER_RECEIPT)]
    assert item['sha256'] == 'c0758957e28267b421beac4822da2092e6114f5673ac5b57cecc7cfadb22be8e'
    catalog = json.loads(frozen(item))['originals']
    rows = []
    for role, (path, firmware) in ROLES.items():
        raw = frozen(read_map[path])
        row, = [row for row in catalog.values() if row['elf_sha256'] == digest(raw)]
        assert row['original_mangled'] == ORIGINAL
        elf = ELFFile(io.BytesIO(raw))
        for evidence in (row, row['actual_field_get'], row['original_lookup']):
            verify_range(elf, raw, evidence)
        rows.append({
            'role': role, 'firmware': firmware, 'elf_sha256': row['elf_sha256'],
            'mangled': ORIGINAL, **{key: row[key] for key in ('address', 'size', 'section', 'file_offset', 'range_sha256')},
            'actual_field_get': row['actual_field_get'], 'modeled_field_lookup': row['original_lookup'],
            'cases': [run(elf, row, case) for case in row['cases']],
        })
    result = {'originals': rows, 'provider_receipt_sha256': item['sha256']}
    if args.write:
        args.write.write_text(json.dumps(result, indent=2) + '\n')
    else:
        assert result == json.loads(args.check.read_text())
    print('8 fresh native cases across 2 original TextEntry and 2 actual Field getter ranges')


if __name__ == '__main__':
    main()
