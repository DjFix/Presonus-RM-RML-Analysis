#!/usr/bin/env python3
"""Recover symbol/byte evidence without pretending mangled names encode layouts."""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_THUMB, CS_MODE_LITTLE_ENDIAN
from elftools.elf.elffile import ELFFile


def inspect(path):
    with path.open('rb') as stream:
        elf = ELFFile(stream)
        symtab = elf.get_section_by_name('.symtab')
        return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    size=path.stat().st_size, machine=elf['e_machine'],
                    symbols=symtab.num_symbols() if symtab else 0,
                    dwarf_sections=[s.name for s in elf.iter_sections() if s.name.startswith('.debug')])


def recover(binary, output, scope='uc'):
    output.mkdir(parents=True, exist_ok=True)
    raw = binary.read_bytes()
    with binary.open('rb') as stream:
        elf = ELFFile(stream)
        tab = elf.get_section_by_name('.symtab')
        if tab is None:
            raise ValueError(f'{binary}: no full symbol table')
        symbols = [s for s in tab.iter_symbols() if s.name]
        names = subprocess.run(['c++filt'], input='\n'.join(s.name for s in symbols),
                               text=True, capture_output=True, check=True).stdout.splitlines()
        all_symbols = []
        selected = []
        for sym, name in zip(symbols, names):
            item = dict(mangled=sym.name, demangled=name, address=int(sym['st_value']),
                        size=int(sym['st_size']), kind=sym['st_info']['type'],
                        binding=sym['st_info']['bind'], section=sym['st_shndx'])
            all_symbols.append(item)
            if scope == 'uc' and 'Presonus::UC::' in name or scope == 'all' and item['kind'] in ('STT_FUNC', 'STT_OBJECT') or scope == 'dice' and re.search(r'Presonus::DICE::|::Dice[A-Z0-9]|::initDice|::Shelby|^dice[0-9_]|^tcat_|^shelby', name):
                selected.append(item)
        by_address = {s['address'] & ~1: s['demangled'] for s in all_symbols if s['address']}
        disasm = []
        calls = []
        machine_code = output / 'machine-code'
        machine_code.mkdir(exist_ok=True)
        data_directory = output / 'data'
        if scope != 'uc':
            data_directory.mkdir(exist_ok=True)
        for sym in selected:
            index = sym['section']
            if not isinstance(index, int) or not sym['size']:
                continue
            section = elf.get_section(index)
            address = sym['address'] & ~1 if sym['kind'] == 'STT_FUNC' else sym['address']
            offset = int(section['sh_offset']) + address - int(section['sh_addr'])
            if section['sh_type'] == 'SHT_NOBITS':
                sym['storage'] = 'zero-initialized NOBITS; no file bytes'
                continue
            if not (int(section['sh_addr']) <= address and address + sym['size'] <= int(section['sh_addr']) + int(section['sh_size'])):
                raise ValueError(f'Symbol outside section: {sym}')
            code = raw[offset:offset+sym['size']]
            sym['file_offset'] = offset
            sym['sha256'] = hashlib.sha256(code).hexdigest()
            if sym['kind'] != 'STT_FUNC':
                if scope != 'uc':
                    data_path = data_directory / f'{address:08x}-{sym["size"]:x}.bin'
                    data_path.write_bytes(code)
                    sym['export_path'] = str(data_path.relative_to(output))
                continue
            filename = f'{address:08x}.bin' if scope == 'uc' else f'{address:08x}-{sym["size"]:x}.bin'
            code_path = machine_code / filename
            code_path.write_bytes(code)
            sym['export_path'] = str(code_path.relative_to(output))
            decoder = Cs(CS_ARCH_ARM, (CS_MODE_THUMB if sym['address'] & 1 else CS_MODE_ARM) | CS_MODE_LITTLE_ENDIAN)
            disasm.append(f"\n// {sym['demangled']}\n// {sym['mangled']} size={sym['size']} file_offset=0x{offset:x}\n")
            for ins in decoder.disasm(code, address):
                suffix = ''
                if ins.mnemonic in ('bl', 'blx', 'b') and ins.op_str.startswith('#'):
                    try:
                        target = int(ins.op_str[1:], 0)
                        callee = by_address.get(target & ~1, '')
                        suffix = f' // {callee}'
                        calls.append(dict(caller=sym['mangled'], address=ins.address, target=target, callee=callee))
                    except ValueError:
                        pass
                disasm.append(f'{ins.address:08x}: {ins.bytes.hex():16s} {ins.mnemonic:8s} {ins.op_str}{suffix}\n')
        (output / 'symbols.json').write_text(json.dumps(selected, indent=2) + '\n')
        (output / 'all-symbols.json').write_text(json.dumps(all_symbols, indent=2) + '\n')
        (output / 'calls.json').write_text(json.dumps(calls, indent=2) + '\n')
        (output / f'{scope}.arm.asm').write_text(''.join(disasm))
        # This header is an address/signature catalogue, not an ABI invented from names.
        role = output.name
        if role not in ('client', 'server'):
            raise ValueError('output directory must identify client or server')
        namespace = f'presonus::uc::recovered::{role}' if scope == 'uc' else f'presonus::firmware::recovered::{scope}::{role}'
        header = [f'#pragma once\n#include <cstdint>\n#include <cstddef>\nnamespace {namespace} {{\n',
                  'struct Symbol { std::uint32_t address, size; const char *mangled, *demangled; };\n',
                  'inline constexpr Symbol symbols[] = {\n']
        for sym in selected:
            header.append(f'  {{0x{sym["address"]:08x}u, {sym["size"]}u, {json.dumps(sym["mangled"])}, {json.dumps(sym["demangled"])}}},\n')
        header.append('};\ninline constexpr std::size_t symbol_count = sizeof(symbols)/sizeof(symbols[0]);\n}\n')
        (output / 'symbols.hpp').write_text(''.join(header))
        manifest = inspect(binary)
        manifest.update(scope=scope, selected_symbols=len(selected), function_symbols=sum(s['kind']=='STT_FUNC' and isinstance(s['section'], int) and s['size']>0 for s in selected),
                        unique_function_addresses=len({s['address'] for s in selected if s['kind']=='STT_FUNC' and isinstance(s['section'], int) and s['size']>0}),
                        byte_exports=sum('export_path' in s for s in selected),
                        note='DWARF presence alone does not imply UC type information. Address catalogue is not a callable ABI.')
        if scope == 'uc':
            manifest.update(uc_symbols=len(selected), uc_functions=sum(s['kind']=='STT_FUNC' for s in selected))
        (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        print(json.dumps(manifest), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scope', choices=['uc', 'dice', 'all'], default='uc')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    inventory = []
    for name in ('surface', 'mixer'):
        for path in sorted((args.repository/'rootfs').glob(f'*/home/root/{name}')):
            item = inspect(path)
            item['version'] = int(re.findall(r'\d+', path.parents[2].name)[-1])
            item['role'] = 'client' if name == 'surface' else 'server'
            inventory.append(item)
        candidates = [x for x in inventory if x['role']==('client' if name=='surface' else 'server') and x['symbols']]
        latest = max(candidates, key=lambda x:(x['version'], 'RML16' in x['path']))
        recover(Path(latest['path']), args.output/latest['role'], args.scope)
    (args.output/'inventory.json').write_text(json.dumps(inventory, indent=2)+'\n')


if __name__ == '__main__':
    main()
