#!/usr/bin/env python3
"""Freeze Linux-only OutputPin evidence without admitting return declarations."""
import gzip
import json
from pathlib import Path
import shutil
import sys
sys.dont_write_bytecode = True
from panel_output_pin_validate import sha

root = Path(sys.argv[1]).resolve()
library = root / 'uc-library'
validation = library / 'validation/panel-output-pin'
proof_path = validation / 'replay-01/reconstruction.json'
proof = json.loads(proof_path.read_text())
assert all(sha(library / name) == value for name, value in proof['sources'].items())
assert proof['cpp_differential_passed'] and proof['sanitizer_replay_passed']
assert proof['portable_ready'] is False and proof['mac_validation_performed'] is False
oracle = json.loads((validation / 'arm-oracle.json').read_text())
lines = ['# OutputPin compiled/declaration-pending symbol status\n\n',
         'Original ranges, namespace/mangles, bounded state/IO traces and Linux\n'
         'sanitizers pass. Return declarations remain pending: NOT ready.\n'
         'No Mac validation, Core body, sysfs access or hardware execution.\n\n',
         '| Role/version | ELF SHA-256 | Original mangled identity | Address | Bytes | Status |\n',
         '|---|---|---|---|---|---|\n']
for s in proof['functions']:
    lines.append(f'| {s["role"]}/{"13840" if s["role"] == "client" else "13731"} | `{s["original_elf_sha256"]}` | `{s["mangled"]}` | `0x{s["address"]:x}` | {s["size"]} | compiled+mangling+bounded Linux state/trace passed; declaration pending; NOT ready |\n')
lines.append('\n[Linux proof](replay-01/reconstruction.json), [ARM metadata](arm-oracle.json). '
             'setup R0=0/-1 compared; set R0 ignored. No downstream implementation/ABI proof.\n')
(validation / 'SYMBOLS.md').write_text(''.join(lines))
destination = root / 'evidence/recovery/2026-10-27/panel-output-pin/batch-01'
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
for name in sorted(set(proof['sources']) | {'tools/panel_output_pin_seal.py'}):
    out = destination / 'sources' / name
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(library / name, out)
for role, record in oracle['originals'].items():
    catalog = library / 'recovered-all' / role
    for symbol in record['functions']:
        out = destination / 'original-app-bytes' / role / Path(symbol['export_path']).name
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(catalog / symbol['export_path'], out)
for name in ('oracle.log', 'validation.log'):
    shutil.copy2(root / 'temp/panel-output-pin' / name, destination / name)
manifest = dict(kind='OutputPin Linux-only compiled-declaration-pending evidence', linux_proof_sha256=sha(proof_path),
                compiled_fragment_sha256=sha(validation / 'replay-01/compiled-records.json'),
                fixture_uncompressed_sha256=sha(validation / 'arm-vectors.txt'), differential_scenarios=proof['total_cases'],
                original_entries=len(proof['functions']), portable_ready=False, original_return_declarations_verified=False,
                mac_validation_performed=False, no_hardware_or_sysfs_access=True, original_full_verification=False,
                original_arm_abi_compatible=False, hardware_verified=False,
                files={str(p.relative_to(destination)): sha(p) for p in destination.rglob('*') if p.is_file()})
(destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
sums = {str(p.relative_to(destination)): sha(p) for p in destination.rglob('*') if p.is_file()}
(destination / 'SHA256SUMS').write_text(''.join(f'{value}  {name}\n' for name, value in sorted(sums.items())))
print(json.dumps(dict(manifest_sha256=sha(destination / 'manifest.json'), sealed_files=len(sums), destination=str(destination)), indent=2))
