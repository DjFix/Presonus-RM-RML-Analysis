"""Replay sealed ARM instructions for the assigned offline Panel entry point."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UcError, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *


CYCLE = Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/control10x20-after-4fed70d11')
PACKET = CYCLE / 'packeting/actual04-next-batch01/packets' / Path(__file__).parent.name
MAP = CYCLE / 'packeting/READ_INPUTS-actual04-next-batch01-cycle20_g06-actual04-next20-scoped02.json'
ENTRY = re.compile(r'ELF `([a-f0-9]+)`; version `([^`]+)`; `([^`]+)`; original `([^`]+)`; address `(0x[0-9a-f]+)`; size (\d+); section (\S+); SHA256 `([a-f0-9]+)`\nOriginal ELF path: `([^`]+)`; file offset `(0x[0-9a-f]+)`')
RECEIVER, STACK, STOP = 0x50000000, 0x60000000, 0x70000000
COORDS = [(0, 0), (4, 7), (-1, 27), (2147483647, -2147483648)]
ACTIVATIONS = [(0, 0, 0), (0, 0, 7), (0, 1, 7), (1, 0, 0), (1, 1, 3), (2, -1, 0), (2, 2, 44)]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def observed(read_map, ending):
    key, = (key for key in read_map if key.endswith('/' + ending))
    entry = read_map[key]
    raw = Path(entry['frozen_read_path']).read_bytes()
    assert digest(raw) == entry['sha256']
    return json.loads(raw)


def field_replay(elf, address, mangled, role, read_map, sha):
    task = PACKET.name[-3:]
    if task in ('s12', 's13'):
        source = observed(read_map, 'FIELD_LOOKUP_NATIVE.json')['role_observations'][sha]
        kind = 'field-lookup' if task == 's12' else 'field-get'
        inputs = [item for item in source['cases'] if item['entry'] == kind]
    elif task == 's14':
        source, = (row for row in observed(read_map, 'TEXT_ENTRY_STRING_NATIVE.json')['original_exact_cases']
                   if row['elf_sha256'] == sha)
        inputs = source['cases']
    else:
        source, = (row for row in observed(read_map, 'FIELD_TEARDOWN_NATIVE.json')['original_variants']
                   if row['elf_sha256'] == sha and row['original_mangled'] == mangled)
        inputs = source['native_cases']
    results = []
    for case in inputs:
        uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        for segment in elf.iter_segments():
            if segment['p_type'] != 'PT_LOAD':
                continue
            va = segment['p_vaddr']
            for page in range(va & ~4095, (va + segment['p_memsz'] + 4095) & ~4095, 4096):
                try:
                    uc.mem_map(page, 4096)
                except UcError as error:
                    if error.errno != 11:
                        raise
            uc.mem_write(va, segment.data())
        extra, delegate, manager = 0x53000000, 0x54000000, 0x55000000
        old, replacement = 1476395264, 1476395520
        for page in (RECEIVER, STACK, STOP, extra, delegate, manager, old & ~4095):
            uc.mem_map(page, 4096)

        def write32(addr, value):
            uc.mem_write(addr, struct.pack('<I', value))

        def read32(addr):
            return struct.unpack('<I', uc.mem_read(addr, 4))[0]

        def c_string(addr):
            return bytes(uc.mem_read(addr, 80)).split(b'\0', 1)[0]

        def return_from(machine, value=None):
            if value is not None:
                machine.reg_write(UC_ARM_REG_R0, value)
            machine.reg_write(UC_ARM_REG_PC, machine.reg_read(UC_ARM_REG_LR))

        offset = 0xa1c
        events = []
        if task in ('s12', 's13'):
            initial = case['cache']
            target = case['resolved']
            write32(RECEIVER + 0x980, initial)
            write32(RECEIVER + 0x74, 7)
            uc.mem_write(RECEIVER + 0x61, bytes([case['refresh']]))
            uc.mem_write(RECEIVER + 0x18, b'panel/level\0')
            write32(source['global_LCD_manager_slot'], manager if case['manager_bound'] else 0)
            write32(manager + 4, delegate if case['manager_bound'] else 0)
            write32(delegate, delegate + 64)
            write32(delegate + 64, delegate + 128)
            bindings = {value['target_address']: name for name, value in source['providers'].items()
                        if name != 'LCDManager'}
            bindings[delegate + 128] = 'delegate'
            r1_initial = 0
        elif task == 's14':
            uc.mem_write(RECEIVER + offset, b'\xb7' * 36)
            text = case['input']
            if text is not None:
                uc.mem_write(extra, text.encode() + b'\0')
            r1_initial = extra if text is not None else 0
            bindings = {int(k): v for k, v in source['called_providers'].items()}
            bindings[delegate + 128] = 'fromString'
            write32(old, delegate + 64)
            write32(delegate + 64 + source['source_parameter_binding']['slot'], delegate + 128)
        else:
            write32(RECEIVER + 0x980, old if case['observer_present'] else 0)
            bindings = {value['target']: name for name, value in source['calls'].items()}
            r1_initial = 0

        def hook(machine, pc, size, _):
            name = bindings.get(pc)
            if name is None:
                return
            a, b, n = [machine.reg_read(reg) for reg in (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2)]
            if name == 'delegate':
                assert a == delegate and b == RECEIVER + 0x18
                events.append([name, c_string(b).decode()])
                return_from(machine, target)
            elif name in ('remove', 'add'):
                assert b == RECEIVER + 0x97c
                if task == 's18':
                    assert a == old and read32(RECEIVER) == source['field_point']
                    assert read32(RECEIVER + 0x97c) == source['observer_address_point']
                events.append([name, a])
                return_from(machine)
            elif name == 'new':
                assert a == 8
                events.append([name, a])
                return_from(machine, manager)
            elif name == 'register':
                assert a == manager and read32(manager + 4) == 0
                assert read32(manager) == source['lcd_vtable_address_point']
                events.append([name, a])
                return_from(machine)
            elif name == 'delete':
                assert a == RECEIVER and read32(a) == source['element_point']
                events.append([name, a])
                machine.mem_unmap(RECEIVER, 4096)
                return_from(machine)
            elif name == 'getParam':
                assert a == RECEIVER
                events.append([name])
                return_from(machine, old if case['typed_parameter'] else 0)
            elif name == 'fromString':
                assert a == old and b == r1_initial and n == 0
                events.append([name])
                return_from(machine)
            elif name == 'strlen':
                events.append([name])
                return_from(machine, len(c_string(a)))
            elif name == 'strncpy':
                assert a == RECEIVER + offset and b == r1_initial
                events.append([name])
                machine.mem_write(a, c_string(b)[:n])
                return_from(machine, a)
            else:
                raise AssertionError(f'Unexpected boundary {name}')

        uc.reg_write(UC_ARM_REG_R0, RECEIVER)
        uc.reg_write(UC_ARM_REG_R1, r1_initial)
        uc.reg_write(UC_ARM_REG_SP, STACK + 4096)
        uc.reg_write(UC_ARM_REG_LR, STOP)
        uc.hook_add(UC_HOOK_CODE, hook)
        uc.emu_start(address, STOP, count=280)
        assert uc.reg_read(UC_ARM_REG_PC) == STOP and uc.reg_read(UC_ARM_REG_SP) == STACK + 4096
        if task in ('s12', 's13'):
            actual = read32(RECEIVER + 0x980)
            dirty = read32(RECEIVER + 0x74)
            assert actual == target and dirty == case['dirty']
            if task == 's13':
                assert uc.reg_read(UC_ARM_REG_R0) == target
            assert [e[0] for e in events] == [e[0] for e in case['observed_events']]
            for name, value in events:
                if name == 'add':
                    assert value == target
                if name == 'remove':
                    assert value == initial
            id_for = {0: 0, old: 1, replacement: 2}
            inputs_host = [id_for[initial], case['refresh'], int(case['manager_bound']), id_for[target]]
            shape = ''.join(e[0][0] for e in events if e[0] in ('delegate', 'remove', 'add'))
            output = f'{id_for[actual]} {dirty} {shape or "-"}'
        elif task == 's14':
            dirty = read32(RECEIVER + 0x74)
            buffer = bytes(uc.mem_read(RECEIVER + offset, 36))
            assert buffer[32:] == b'\xb7' * 4
            assert [e[0] for e in events] == case['ordered_boundary_calls']
            binding = case['typed_parameter']
            local = buffer[:32] if binding else buffer[:32].split(b'\0', 1)[0]
            assert local.hex() == (('b7' * 32) if binding else case['local_buffer_before_nul'])
            token = '~' if case['input'] is None else case['input'].encode().hex() or '-'
            inputs_host = [int(binding), token]
            output = f'{dirty} {(local.hex() or "-")} {token if binding else "-"}'
        else:
            variant = int(mangled.split('D')[-1][0])
            deleting = variant == 0
            if deleting:
                try:
                    uc.mem_read(RECEIVER, 4)
                except UcError:
                    pass
                else:
                    raise AssertionError('D0 left its receiver mapped')
            else:
                assert read32(RECEIVER) == source['element_point']
            assert [e[0] for e in events] == case['ordered_actions']
            inputs_host = [variant, int(case['observer_present'])]
            output = f'{int(deleting)} {int(case["observer_present"])}'
        results.append({'input': inputs_host, 'expected': output, 'events': events})
    return results


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
                          'body_sha256': content, 'cases': field_replay(elf, address, mangled, role, read_map, sha)})
    assert originals
    result = json.loads(json.dumps({'originals': originals}))
    if args.check:
        assert result == json.loads(args.check.read_text())
    if args.write:
        args.write.write_text(json.dumps(result, indent=2) + '\n')
    print(f"{len(originals)} exact ELF ranges, {sum(len(row['cases']) for row in originals)} native executions")


if __name__ == '__main__':
    main()
