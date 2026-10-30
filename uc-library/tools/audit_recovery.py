#!/usr/bin/env python3
"""Independently compare exported bytes to input ELFs and audit export coverage."""
import argparse
import collections
import hashlib
import json
import subprocess
from pathlib import Path

from elftools.elf.elffile import ELFFile


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('repository',type=Path)
    a=p.parse_args()
    library=a.repository/'uc-library'
    result={'roles':{},'packed_comparison_artifacts':[]}
    catalogues={}
    for role in ('client','server'):
        root=library/'recovered'/role
        manifest=json.loads((root/'manifest.json').read_text())
        binary=a.repository/manifest['path']
        source=binary.read_bytes()
        assert hashlib.sha256(source).hexdigest()==manifest['sha256'], 'source ELF hash mismatch'
        symbols=json.loads((root/'symbols.json').read_text())
        catalogue={s['mangled']:s for s in symbols if s['kind']=='STT_FUNC' and 'file_offset' in s}
        catalogues[role]=catalogue
        checked=0
        with binary.open('rb') as stream:
            elf=ELFFile(stream)
            for sym in catalogue.values():
                section=elf.get_section(sym['section'])
                offset=int(section['sh_offset'])+(sym['address']&~1)-int(section['sh_addr'])
                assert offset==sym['file_offset'], 'file offset mismatch'
                original=source[offset:offset+sym['size']]
                exported=(root/'machine-code'/f'{sym["address"]&~1:08x}.bin').read_bytes()
                assert original==exported, 'exported machine code mismatch'
                assert hashlib.sha256(exported).hexdigest()==sym['sha256'], 'machine code hash mismatch'
                checked+=1
        entries=json.loads((root/'decompilation.json').read_text())
        status=collections.Counter(x['status'] for x in entries)
        assert {x['address'] for x in entries}=={s['address'] for s in catalogue.values()}, 'decompiler coverage mismatch'
        for entry in entries:
            if entry['status']=='exported':
                path=root/'pseudocode'/f'{entry["address"]:08x}.cpp.txt'
                assert path.is_file() and path.read_text().startswith('// UNVALIDATED'), 'missing export or warning'
        assert 'DONE' in (root/'decompiler.log').read_text(), 'decompiler has not completed'
        result['roles'][role]={'source':str(binary),'sha256':manifest['sha256'],
                               'symbols':len(symbols),'verified_function_byte_exports':checked,
                               'decompiler_status':dict(status),'pseudocode_validated':False}
    common=set(catalogues['client'])&set(catalogues['server'])
    result['shared_function_symbols']=len(common)
    result['shared_functions_with_identical_machine_bytes']=sum(catalogues['client'][name]['sha256']==catalogues['server'][name]['sha256'] for name in common)
    for binary in sorted((library/'artifacts/binaries').glob('*.elf')):
        with binary.open('rb') as stream:
            elf=ELFFile(stream)
            result['packed_comparison_artifacts'].append(dict(path=str(binary),size=binary.stat().st_size,
                sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),has_full_symtab=elf.get_section_by_name('.symtab') is not None))
    result['original_library_fully_ported']=False
    result['hardware_interoperability_verified']=False
    (library/'recovered/audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
