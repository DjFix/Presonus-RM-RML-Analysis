#!/usr/bin/env python3
"""Produce per-symbol status and freeze new pure bitmap recovery evidence."""
import gzip
import json
from pathlib import Path
import shutil
import struct
import sys
sys.dont_write_bytecode = True
from panel_bitmap_drawing_validate import sha

root = Path(sys.argv[1]).resolve()
library = root / 'uc-library'
validation = library / 'validation/panel-bitmap-drawing'
proof_path = validation / 'replay-01/reconstruction.json'
mac_path = validation / 'mac-01/reconstruction.json'
proof = json.loads(proof_path.read_text())
mac = json.loads(mac_path.read_text())
assert proof['sources'] == mac['sources']
assert all(sha(library / name) == value for name, value in proof['sources'].items())
assert proof['cpp_differential_passed'] and mac['cpp_differential_passed']
oracle = json.loads((validation / 'arm-oracle.json').read_text())
lines = ['# BitmapDisplay drawing/state symbol status\n\n',
         'Byte ranges verified; original scopes/mangles checked; bounded Linux/macOS\n'
         'ARM differential replay passed. Parent/global integration pending.\n'
         'Hardware, original full behavior and ARM ABI remain unverified.\n\n',
         '| Role/version | ELF SHA-256 | Original mangled identity | Address | Bytes | Status |\n',
         '|---|---|---|---|---|---|\n']
for s in proof['functions']:
    lines.append(f'| {s["role"]}/{"13840" if s["role"] == "client" else "13731"} | `{s["original_elf_sha256"]}` | `{s["mangled"]}` | `0x{s["address"]:x}` | {s["size"]} | scoped C++/mangling/differential passed; hardware pending |\n')
lines.append('\nProofs: [Linux](replay-01/reconstruction.json), [macOS](mac-01/reconstruction.json), '
             '[ARM ranges/vtable](arm-oracle.json). No function dependency modeled; foreign overrides excluded.\n')
(validation / 'SYMBOLS.md').write_text(''.join(lines))
destination = root / 'evidence/recovery/2026-10-27/panel-bitmap-drawing/batch-01'
destination.mkdir(parents=True, exist_ok=False)
for path in validation.rglob('*'):
    if path.is_file() and path.name != 'arm-vectors.txt':
        out = destination / 'validation' / path.relative_to(validation)
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, out)
with (destination / 'arm-vectors.txt.gz').open('wb') as out:
    with gzip.GzipFile(filename='', mode='wb', fileobj=out, mtime=0) as compressed:
        with (validation / 'arm-vectors.txt').open('rb') as stream:
            shutil.copyfileobj(stream, compressed)
for name in sorted(set(proof['sources']) | {'tools/panel_bitmap_drawing_seal.py'}):
    out = destination / 'sources' / name
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(library / name, out)
vtable_references = {}
for role, record in oracle['originals'].items():
    catalog = library / 'recovered-all' / role
    table = record['actual_vtable_symbol']
    raw_table = (catalog / table['export_path']).read_bytes()
    words = struct.unpack('<' + 'I' * (len(raw_table) // 4), raw_table)
    vtable_references[role] = {s['mangled']: [offset * 4 - 8 for offset, value in enumerate(words) if offset >= 2 and value == s['address']]
                               for s in record['functions']}
    for symbol in [*record['executed_function_ranges'], table]:
        out = destination / 'original-bytes' / role / Path(symbol['export_path']).name
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(catalog / symbol['export_path'], out)
for name in ('oracle.log', 'validation.log'):
    shutil.copy2(root / 'temp/panel-bitmap-drawing' / name, destination / name)
manifest = dict(kind='BitmapDisplay pure drawing/state bounded evidence', linux_proof_sha256=sha(proof_path),
                mac_proof_sha256=sha(mac_path), readiness_fragment_sha256=sha(validation / 'replay-01/readiness-records.json'),
                fixture_uncompressed_sha256=sha(validation / 'arm-vectors.txt'), differential_cases=proof['total_cases'],
                original_entries=len(proof['functions']), modeled_dependency_calls=0,
                virtual_dispatch_domain='Actual original BitmapDisplay vtables only; no foreign overrides',
                original_vtable_references=vtable_references, tested_fill_modes=[-2147483648, -1, 0, 1, 2, 3, 2147483647],
                original_full_verification=False, original_arm_abi_compatible=False, hardware_verified=False,
                files={str(p.relative_to(destination)): sha(p) for p in destination.rglob('*') if p.is_file()})
(destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
sums = {str(p.relative_to(destination)): sha(p) for p in destination.rglob('*') if p.is_file()}
(destination / 'SHA256SUMS').write_text(''.join(f'{value}  {name}\n' for name, value in sorted(sums.items())))
print(json.dumps(dict(manifest_sha256=sha(destination / 'manifest.json'), sealed_files=len(sums), destination=str(destination)), indent=2))
