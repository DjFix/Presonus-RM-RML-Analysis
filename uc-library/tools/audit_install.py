#!/usr/bin/env python3
"""Check installed headers and original ready symbols against current records."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--nm', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--provider-sdk', type=Path,
                        help='Expected SDK from the current source provider build')
    args = parser.parse_args()
    library = args.library.resolve()
    prefix = args.prefix.resolve()
    inputs = json.loads((library / 'validation/integration.json').read_text())
    expected = {name: digest for name, digest in inputs['files'].items()
                if name.startswith('include/')}
    provider_files = {}
    if args.provider_sdk:
        sdk = args.provider_sdk.resolve(strict=True)
        provider_files = {str(path.relative_to(sdk)): sha(path)
                          for path in sdk.rglob('*') if path.is_file()}
        for required_file in ('lib/libcorelib.a', 'lib/libpresonus_core_allocator.a',
                              'share/presonus-core-5/provenance.json',
                              'share/presonus-core-5/upstream/license.md'):
            if required_file not in provider_files:
                raise SystemExit('Incomplete expected provider SDK: ' + required_file)
        if not any(name.startswith('include/presonus-core-5/') for name in provider_files):
            raise SystemExit('Expected provider SDK has no public headers')
        mismatched = [name for name, digest in provider_files.items()
                      if not (prefix / name).is_file() or sha(prefix / name) != digest]
        if mismatched:
            raise SystemExit('Installed provider SDK differs from source build: ' + repr(mismatched))
    provider_headers = {name: digest for name, digest in provider_files.items()
                        if name.startswith('include/')}
    if set(expected) & set(provider_headers):
        raise SystemExit('Application and provider header sets overlap')
    installed = {str(path.relative_to(prefix)): sha(path)
                 for path in (prefix / 'include').rglob('*') if path.is_file()}
    if installed != {**expected, **provider_headers}:
        raise SystemExit('Installed public headers differ from integrated header set')
    archive = prefix / 'lib/libpresonus_uc.a'
    output = subprocess.run([str(args.nm), '-g', str(archive)], check=True,
                            text=True, capture_output=True).stdout
    symbols = set()
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 3 or parts[-2] not in ('T', 'W', 'V', 'D', 'B', 'R', 'S'):
            continue
        symbol = parts[-1]
        if symbol.startswith('__Z'):
            symbol = symbol[1:]  # Mach-O object-format decoration.
        symbols.add(symbol)
    ready = json.loads((library / 'validation/ready-functions.json').read_text())
    required = {item['mangled'] for item in ready['functions']}
    missing = sorted(required - symbols)
    if missing:
        raise SystemExit('Missing original ready symbols: ' + repr(missing))
    report = dict(public_header_hashes=expected, archive_sha256=sha(archive),
                  application_header_count=len(expected),
                  provider_header_count=len(provider_headers),
                  provider_header_hashes=provider_headers,
                  provider_sdk_hashes=provider_files,
                  provider_sdk_matches=True,
                  ready_original_mangles=sorted(required),
                  header_set_matches=True, compiled_mangles_matched=True,
                  original_arm_abi_verified=False, hardware_verified=False)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(installed_headers=len(installed),
                          original_mangled_methods=len(required), passed=True)))


if __name__ == '__main__':
    main()
