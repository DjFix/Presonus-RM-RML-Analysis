#!/usr/bin/env python3
"""Verify AlertManager application ranges and RTTI data, without Core code."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct

from elftools.elf.elffile import ELFFile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository', type=Path)
    args = parser.parse_args()
    repo = args.repository.resolve()
    library = repo / 'uc-library'
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    output = repo / 'evidence/recovery/2026-10-27/panel-alert-metadata' / stamp
    output.mkdir(parents=True, exist_ok=False)
    roles = {}
    for role in ('client', 'server'):
        scope = library / 'recovered-all' / role
        manifest = json.loads((scope / 'manifest.json').read_text())
        path = (repo / manifest['path']).resolve(strict=True)
        assert path.is_relative_to(repo) and sha(path) == manifest['sha256']
        symbols = json.loads((scope / 'symbols.json').read_text())
        by_name = {row['mangled']: row for row in symbols}
        by_address = {}
        for row in symbols:
            by_address.setdefault(row['address'], []).append(row['mangled'])
        records = {}
        with path.open('rb') as stream:
            elf = ELFFile(stream)
            def read(name):
                row = by_name[name]
                section = elf.get_section(row['section'])
                assert section['sh_type'] != 'SHT_NOBITS'
                offset = section['sh_offset'] + row['address'] - section['sh_addr']
                assert section['sh_addr'] <= row['address']
                assert row['address'] + row['size'] <= section['sh_addr'] + section['sh_size']
                stream.seek(offset)
                raw = stream.read(row['size'])
                assert offset == row['file_offset']
                assert raw == (scope / row['export_path']).read_bytes()
                assert hashlib.sha256(raw).hexdigest() == row['sha256']
                records[name] = dict(row)
                if row['kind'] == 'STT_OBJECT' and len(raw) % 4 == 0:
                    records[name]['words'] = list(struct.unpack('<' + 'I' * (len(raw) // 4), raw))
                return raw
            methods = [row for row in symbols if row['kind'] == 'STT_FUNC'
                       and row.get('size', 0) and row['mangled'].startswith('_ZN8Presonus5Panel12AlertManager')]
            for row in methods:
                read(row['mangled'])
            alert = '_ZTIN8Presonus5Panel12AlertManagerE'
            singleton = '_ZTIN4Core8Portable9SingletonIN8Presonus5Panel12AlertManagerEEE'
            read(alert)
            read(singleton)
            assert records[alert]['size'] == 12 and records[singleton]['size'] == 12
            assert records[alert]['words'][2] == by_name[singleton]['address']
            parent = records[singleton]['words'][2]
            parent_names = by_address[parent]
            assert '_ZTIN4Core8Portable9DeletableE' in parent_names
            table = '_ZTVN8Presonus5Panel12AlertManagerE'
            read(table)
            assert records[table]['words'] == [
                0, by_name[alert]['address'],
                by_name['_ZN8Presonus5Panel12AlertManagerD1Ev']['address'],
                by_name['_ZN8Presonus5Panel12AlertManagerD0Ev']['address']]
        roles[role] = dict(elf_sha256=manifest['sha256'], verified_ranges=records,
                           singleton_parent_symbols=parent_names,
                           method_entries=len(methods), original_rtti_chain_verified=True,
                           original_vtable_destructor_slots_verified=True)
    header = repo / 'third_party/ccl-framework/core/portable/coresingleton.h'
    report = dict(roles=roles, core_bodies_decoded=False, original_code_executed=False,
                  ccl_source_header='third_party/ccl-framework/core/portable/coresingleton.h',
                  ccl_header_sha256=sha(header), tool_sha256=sha(Path(__file__)),
                  scope='Application byte identities and RTTI data only. C++ declarations, behavior, full layouts and original ARM ABI are not established by this inspection.')
    proof = output / 'validation.json'
    proof.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(proof=str(proof.relative_to(repo)), sha256=sha(proof),
                          method_entries={role: item['method_entries'] for role, item in roles.items()},
                          singleton_rtti_verified=True, destructor_slots_verified=True)))


if __name__ == '__main__':
    main()
