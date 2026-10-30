#!/usr/bin/env python3
"""Separate selected state-body status from unverified callbacks and seal proof."""
import gzip
import json
from pathlib import Path
import shutil
import sys
sys.dont_write_bytecode = True
from panel_led_state_validate import sha

root = Path(sys.argv[1]).resolve()
library = root / 'uc-library'
validation = library / 'validation/panel-led-state'
proof_path = validation / 'replay-01/reconstruction.json'
mac_path = validation / 'mac-01/reconstruction.json'
proof = json.loads(proof_path.read_text())
mac = json.loads(mac_path.read_text())
assert proof['sources'] == mac['sources']
assert all(sha(library / name) == value for name, value in proof['sources'].items())
assert proof['cpp_differential_passed'] and mac['cpp_differential_passed']
assert proof['downstream_callback_behavior_verified'] is False
oracle = json.loads((validation / 'arm-oracle.json').read_text())
lines = ['# LEDControl symbol status\n\n',
         'Selected bodies: verified byte ranges, original scopes/mangles and bounded\n'
         'local state/emitted dispatch contract. Parent/global integration pending.\n'
         'Callback bodies/downstream behavior, full original behavior, ARM ABI and hardware unverified.\n\n',
         '| Role/version | ELF SHA-256 | Original mangled identity | Address | Bytes | Status |\n',
         '|---|---|---|---|---|---|\n']
for s in proof['functions']:
    lines.append(f'| {s["role"]}/{"13840" if s["role"] == "client" else "13731"} | `{s["original_elf_sha256"]}` | `{s["mangled"]}` | `0x{s["address"]:x}` | {s["size"]} | scoped C++/mangles/local state+dispatch passed; downstream/hardware pending |\n')
lines.extend(['\n## Intercepted callback bodies — NOT ready\n\n',
              '| Role | Original mangled identity | Entry | Bytes | Status |\n', '|---|---|---|---|---|\n'])
for role, record in oracle['originals'].items():
    for s in record['intercepted_callbacks'].values():
        lines.append(f'| {role} | `{s["mangled"]}` | `0x{s["address"]:x}` | {s["size"]} | entry intercepted; body not executed/recovered; NOT ready |\n')
lines.append('\n[Linux proof](replay-01/reconstruction.json), [Mac proof](mac-01/reconstruction.json), '
             '[actual ARM/vtable metadata](arm-oracle.json). No Core implementation supplied.\n')
(validation / 'SYMBOLS.md').write_text(''.join(lines))
destination = root / 'evidence/recovery/2026-10-27/panel-led-state/batch-01'
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
for name in sorted(set(proof['sources']) | {'tools/panel_led_state_seal.py'}):
    out = destination / 'sources' / name
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(library / name, out)
for role, record in oracle['originals'].items():
    catalog = library / 'recovered-all' / role
    for symbol in [*record['functions'], *record['intercepted_callbacks'].values(), record['actual_vtable_symbol']]:
        category = 'entry-intercepted-body-unverified' if symbol['mangled'] in {s['mangled'] for s in record['intercepted_callbacks'].values()} else 'selected-and-vtable-inputs'
        out = destination / 'original-bytes' / category / role / Path(symbol['export_path']).name
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(catalog / symbol['export_path'], out)
for name in ('oracle.log', 'validation.log'):
    shutil.copy2(root / 'temp/panel-led-state' / name, destination / name)
manifest = dict(kind='LEDControl local state and emitted dispatch contract evidence', linux_proof_sha256=sha(proof_path),
                mac_proof_sha256=sha(mac_path), readiness_fragment_sha256=sha(validation / 'replay-01/readiness-records.json'),
                fixture_uncompressed_sha256=sha(validation / 'arm-vectors.txt'), differential_cases=proof['total_cases'],
                original_entries=len(proof['functions']), callback_dispatches=sum(r['callback_dispatches'] for r in oracle['originals'].values()),
                intercepted_callback_bodies_ready=False, downstream_callback_behavior_verified=False, no_core_function_definitions=True,
                original_full_verification=False, original_arm_abi_compatible=False, hardware_verified=False,
                files={str(p.relative_to(destination)): sha(p) for p in destination.rglob('*') if p.is_file()})
(destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
sums = {str(p.relative_to(destination)): sha(p) for p in destination.rglob('*') if p.is_file()}
(destination / 'SHA256SUMS').write_text(''.join(f'{value}  {name}\n' for name, value in sorted(sums.items())))
print(json.dumps(dict(manifest_sha256=sha(destination / 'manifest.json'), sealed_files=len(sums), destination=str(destination)), indent=2))
