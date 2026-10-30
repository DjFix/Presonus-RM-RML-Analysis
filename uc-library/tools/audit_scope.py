#!/usr/bin/env python3
"""Independently audit full/DICE export coverage against the original ELF tables."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
from elftools.elf.elffile import ELFFile


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('repository',type=Path)
    p.add_argument('--recovery',type=Path,required=True)
    p.add_argument('--bytes-only',action='store_true')
    a=p.parse_args()
    root=a.repository/a.recovery
    report={'roles':{},'original_library_fully_ported':False,'hardware_interoperability_verified':False}
    for role in ('client','server'):
        directory=root/role
        manifest=json.loads((directory/'manifest.json').read_text())
        binary=a.repository/manifest['path']
        raw=binary.read_bytes()
        assert hashlib.sha256(raw).hexdigest()==manifest['sha256'], 'original ELF identity changed'
        symbols=json.loads((directory/'symbols.json').read_text())
        functions=[]
        byte_functions=byte_data=nobits=0
        with binary.open('rb') as stream:
            elf=ELFFile(stream)
            original={(s.name,int(s['st_value']),int(s['st_size']),s['st_shndx']) for s in elf.get_section_by_name('.symtab').iter_symbols()}
            for sym in symbols:
                assert (sym['mangled'],sym['address'],sym['size'],sym['section']) in original, 'invented or changed original symbol'
                if sym['kind']=='STT_FUNC' and sym['size'] and isinstance(sym['section'],int):
                    functions.append(sym)
                if not sym['size'] or not isinstance(sym['section'],int):
                    continue
                section=elf.get_section(sym['section'])
                address=sym['address']&~1 if sym['kind']=='STT_FUNC' else sym['address']
                assert int(section['sh_addr'])<=address and address+sym['size']<=int(section['sh_addr'])+int(section['sh_size']), 'symbol not within section'
                if section['sh_type']=='SHT_NOBITS':
                    assert 'NOBITS' in sym.get('storage',''), 'NOBITS source not recorded'
                    nobits+=1
                    continue
                assert 'export_path' in sym, 'file-backed symbol has no exported bytes'
                offset=int(section['sh_offset'])+address-int(section['sh_addr'])
                assert offset==sym['file_offset'], 'file offset mismatch'
                exported=(directory/sym['export_path']).read_bytes()
                assert raw[offset:offset+sym['size']]==exported, 'extracted byte mismatch'
                assert hashlib.sha256(exported).hexdigest()==sym['sha256'], 'extracted hash mismatch'
                if sym['kind']=='STT_FUNC': byte_functions+=1
                else: byte_data+=1
        state_file=directory/'decompilation.json'
        entries=json.loads(state_file.read_text()) if state_file.exists() else []
        expected_addresses={s['address'] for s in functions}
        if not a.bytes_only:
            assert {e['address'] for e in entries}==expected_addresses, 'decompilation workload incomplete'
            assert 'DONE' in (directory/'decompiler.log').read_text(), 'decompiler has not reached its terminal report'
        for entry in entries:
            assert entry['address'] in expected_addresses, 'decompiler address outside selected functions'
            if entry['status']=='exported':
                text=(directory/'pseudocode'/f'{entry["address"]:08x}.cpp.txt').read_text()
                assert text.startswith('// UNVALIDATED'), 'unlabelled pseudocode'
        statuses=collections.Counter(e['status'] for e in entries)
        report['roles'][role]=dict(source=str(binary),sha256=manifest['sha256'],
            function_entries=len(functions),unique_function_addresses=len(expected_addresses),
            verified_function_byte_exports=byte_functions,verified_data_byte_exports=byte_data,
            verified_nobits_symbols=nobits,decompiler_status=dict(statuses),
            decompilation_workload_complete={e['address'] for e in entries}==expected_addresses,
            pseudocode_validated=False)
    output=root/('byte-audit.json' if a.bytes_only else 'audit.json')
    output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__': main()
