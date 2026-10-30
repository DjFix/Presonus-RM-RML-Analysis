#!/usr/bin/env python3
"""Freeze the new Panel DbTable evidence for mirroring; no global ledger edits."""
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


root = Path(sys.argv[1]).resolve()
library = root / 'uc-library'
validation = library / 'validation/panel-db-table'
destination = root / 'evidence/recovery/2026-10-27/panel-db-table/batch-01'
destination.mkdir(parents=True, exist_ok=False)
proof = json.loads((validation / 'replay-01/reconstruction.json').read_text())
mac = json.loads((validation / 'mac-01/reconstruction.json').read_text())
assert all(sha(library / name) == value for name, value in proof['sources'].items())
assert mac['sources'] == proof['sources'] and mac['cpp_differential_passed']
assert mac['linux_proof_sha256'] == sha(validation / 'replay-01/reconstruction.json')
for path in validation.rglob('*'):
    if path.is_file() and path.name != 'arm-vectors.txt':
        out = destination / 'validation' / path.relative_to(validation)
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, out)
with (destination / 'arm-vectors.txt.gz').open('wb') as out:
    with gzip.GzipFile(filename='', mode='wb', fileobj=out, mtime=0) as compressed:
        with (validation / 'arm-vectors.txt').open('rb') as stream:
            shutil.copyfileobj(stream, compressed)
names = set(proof['sources']) | {'tools/panel_db_table_mac_validate.py', 'tools/panel_db_table_seal.py'}
for name in sorted(names):
    path = destination / 'sources' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(library / name, path)
for role in ('client', 'server'):
    catalog = library / 'recovered-all' / role
    oracle = json.loads((validation / 'arm-oracle.json').read_text())['originals'][role]
    for symbol in oracle['executed_function_ranges']:
        path = destination / 'original-machine-code' / role / Path(symbol['export_path']).name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(catalog / symbol['export_path'], path)
for name in ('oracle.log', 'validation.log'):
    shutil.copy2(root / 'temp/panel-db-table' / name, destination / name)
manifest = dict(kind='Panel DbTable bounded portable reconstruction evidence',
                linux_proof_sha256=sha(validation / 'replay-01/reconstruction.json'),
                mac_proof_sha256=sha(validation / 'mac-01/reconstruction.json'),
                readiness_fragment_sha256=sha(validation / 'replay-01/readiness-records.json'),
                differential_cases=proof['total_cases'], original_entries=len(proof['functions']),
                original_mangled_names=proof['mangled_names'], fixture_uncompressed_sha256=sha(validation / 'arm-vectors.txt'),
                original_full_verification=False, original_arm_abi_compatible=False, hardware_verified=False,
                files={str(p.relative_to(destination)): sha(p) for p in destination.rglob('*') if p.is_file()})
(destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
sums = {str(p.relative_to(destination)): sha(p) for p in destination.rglob('*') if p.is_file()}
(destination / 'SHA256SUMS').write_text(''.join(f'{value}  {name}\n' for name, value in sorted(sums.items())))
print(json.dumps(dict(manifest_sha256=sha(destination / 'manifest.json'), sealed_files=len(sums), destination=str(destination)), indent=2))
