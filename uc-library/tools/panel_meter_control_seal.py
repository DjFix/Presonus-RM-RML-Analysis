#!/usr/bin/env python3
"""Generate per-symbol status and seal the new MeterControl evidence locally/VM."""
import gzip
import json
from pathlib import Path
import shutil
import sys
from panel_meter_control_validate import sha

root = Path(sys.argv[1]).resolve()
library = root / 'uc-library'
validation = library / 'validation/panel-meter-control'
proof_path = validation / 'replay-01/reconstruction.json'
proof = json.loads(proof_path.read_text())
mac_path = validation / 'mac-01/reconstruction.json'
mac = json.loads(mac_path.read_text())
assert proof['sources'] == mac['sources']
assert all(sha(library / name) == value for name, value in proof['sources'].items())
assert proof['cpp_differential_passed'] and mac['cpp_differential_passed']
oracle = json.loads((validation / 'arm-oracle.json').read_text())
lines = ['# MeterControl symbol status\n',
         'Each function below is byte-range verified, compiled in its original scope,\n'
         'mangle checked and behaviorally validated in the bounded documented domain.\n'
         'Parent/global integration is pending; original ARM ABI/full behavior and hardware are unverified.\n',
         '| Role/version | Original ELF SHA-256 | Original mangled identity | Address | Bytes | Status |\n',
         '|---|---|---|---|---|---|\n']
for s in proof['functions']:
    lines.append(f'| {s["role"]}/{"13840" if s["role"] == "client" else "13731"} | `{s["original_elf_sha256"]}` | `{s["mangled"]}` | `0x{s["address"]:x}` | {s["size"]} | bounded C++/mangling/Linux+Mac differential passed; hardware pending |\n')
lines.extend(['\nFunction proofs: [Linux](replay-01/reconstruction.json), [macOS](mac-01/reconstruction.json); '
              'ARM sections, symbol sizes and raw byte hashes are retained in [oracle](arm-oracle.json).\n',
              '\n## Static data (not ready function entries)\n\n',
              '| Role | Original mangled identity | Address | Bytes | Raw storage | Current status |\n',
              '|---|---|---|---|---|---|\n'])
for role, record in oracle['originals'].items():
    for s in record['data_symbols'].values():
        storage = 'SHT_NOBITS, zero-initialized file storage' if 'storage' in s else 'file bytes16/16 verified'
        lines.append(f'| {role} | `{s["mangled"]}` | `0x{s["address"]:x}` | {s["size"]} | {storage} | compiled name checked; startup/layout/hardware unverified |\n')
(validation / 'SYMBOLS.md').write_text(''.join(lines))
destination = root / 'evidence/recovery/2026-10-27/panel-meter-control/batch-01'
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
for name in sorted(set(proof['sources']) | {'tools/panel_meter_control_seal.py'}):
    out = destination / 'sources' / name
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(library / name, out)
for role, record in oracle['originals'].items():
    catalog = library / 'recovered-all' / role
    for symbol in [*record['executed_function_ranges'], *record['data_symbols'].values()]:
        if 'export_path' not in symbol:
            continue
        path = destination / 'original-bytes' / role / Path(symbol['export_path']).name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(catalog / symbol['export_path'], path)
for name in ('oracle.log', 'validation.log'):
    shutil.copy2(root / 'temp/panel-meter-control' / name, destination / name)
manifest = dict(kind='Panel MeterControl state/configuration bounded evidence', linux_proof_sha256=sha(proof_path),
                mac_proof_sha256=sha(mac_path), readiness_fragment_sha256=sha(validation / 'replay-01/readiness-records.json'),
                fixture_uncompressed_sha256=sha(validation / 'arm-vectors.txt'), differential_cases=proof['total_cases'],
                original_entries=len(proof['functions']), original_full_verification=False, original_arm_abi_compatible=False, hardware_verified=False,
                actual_dbtable_dependency_proof_sha256=proof['actual_dbtable_proof_sha256'],
                files={str(p.relative_to(destination)): sha(p) for p in destination.rglob('*') if p.is_file()})
(destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
sums = {str(p.relative_to(destination)): sha(p) for p in destination.rglob('*') if p.is_file()}
(destination / 'SHA256SUMS').write_text(''.join(f'{value}  {name}\n' for name, value in sorted(sums.items())))
print(json.dumps(dict(manifest_sha256=sha(destination / 'manifest.json'), sealed_files=len(sums), destination=str(destination)), indent=2))
