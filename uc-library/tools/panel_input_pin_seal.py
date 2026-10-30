#!/usr/bin/env python3
"""Freeze offline InputPin state/call evidence without promoting declarations."""
import gzip
import json
from pathlib import Path
import shutil
import sys
sys.dont_write_bytecode = True
from panel_input_pin_validate import sha

root = Path(sys.argv[1]).resolve()
library = root / 'uc-library'
validation = library / 'validation/panel-input-pin'
proof_path = validation / 'replay-01/reconstruction.json'
mac_path = validation / 'mac-01/reconstruction.json'
proof = json.loads(proof_path.read_text())
mac = json.loads(mac_path.read_text())
assert proof['sources'] == mac['sources']
assert all(sha(library / name) == value for name, value in proof['sources'].items())
assert proof['cpp_differential_passed'] and mac['cpp_differential_passed']
assert proof['portable_ready'] is False and proof['original_return_declarations_verified'] is False
declarations = json.loads((validation / 'return-declarations.json').read_text())
assert declarations['original_return_declarations_verified'] is False
oracle = json.loads((validation / 'arm-oracle.json').read_text())
lines = ['# InputPin compiled/declaration-pending symbol status\n\n',
         'Original byte ranges, namespaces/mangles, bounded local state/I/O traces\n'
         'and Linux/macOS replay pass. All entries remain NOT ready: original C++\n'
         'return declarations are unproved. Original ABI/full behavior/hardware unverified.\n\n',
         '| Role/version | ELF SHA-256 | Original mangled identity | Address | Bytes | Status |\n',
         '|---|---|---|---|---|---|\n']
for s in proof['functions']:
    lines.append(f'| {s["role"]}/{"13840" if s["role"] == "client" else "13731"} | `{s["original_elf_sha256"]}` | `{s["mangled"]}` | `0x{s["address"]:x}` | {s["size"]} | compiled+mangling+bounded state/trace passed; declaration pending; NOT ready |\n')
lines.append('\n[Linux proof](replay-01/reconstruction.json), [macOS proof](mac-01/reconstruction.json), '
             '[return evidence](return-declarations.json), [original ARM metadata](arm-oracle.json).\n'
             'setup R0=0/-1 is compared; poll R0 ignored. No Core/logger/observer/libc body is recovered.\n')
(validation / 'SYMBOLS.md').write_text(''.join(lines))
destination = root / 'evidence/recovery/2026-10-27/panel-input-pin/batch-01'
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
for name in sorted(set(proof['sources']) | {'tools/panel_input_pin_seal.py', 'tools/panel_input_pin_declarations.py'}):
    out = destination / 'sources' / name
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(library / name, out)
for role, record in oracle['originals'].items():
    catalog = library / 'recovered-all' / role
    caller_ranges = [entry['caller'] for entry in declarations['records'][role]['setup_constructor_callers']]
    for symbol in [*record['functions'], *caller_ranges]:
        out = destination / 'original-app-bytes' / role / Path(symbol['export_path']).name
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(catalog / symbol['export_path'], out)
for name in ('oracle.log', 'validation.log', 'declarations.log'):
    shutil.copy2(root / 'temp/panel-input-pin' / name, destination / name)
manifest = dict(kind='InputPin offline state/call compiled-declaration-pending evidence', linux_proof_sha256=sha(proof_path),
                mac_proof_sha256=sha(mac_path), compiled_fragment_sha256=sha(validation / 'replay-01/compiled-records.json'),
                fixture_uncompressed_sha256=sha(validation / 'arm-vectors.txt'), differential_scenarios=proof['total_cases'],
                method_invocations=proof['method_invocations'], original_entries=len(proof['functions']),
                portable_ready=False, original_return_declarations_verified=False, no_hardware_or_sysfs_access=True,
                original_full_verification=False, original_arm_abi_compatible=False, hardware_verified=False,
                files={str(p.relative_to(destination)): sha(p) for p in destination.rglob('*') if p.is_file()})
(destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
sums = {str(p.relative_to(destination)): sha(p) for p in destination.rglob('*') if p.is_file()}
(destination / 'SHA256SUMS').write_text(''.join(f'{value}  {name}\n' for name, value in sorted(sums.items())))
print(json.dumps(dict(manifest_sha256=sha(destination / 'manifest.json'), sealed_files=len(sums), destination=str(destination)), indent=2))
