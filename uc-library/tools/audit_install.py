#!/usr/bin/env python3
"""Check installed headers and original ready symbols against current records."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent / 'registry'))
from adapter import snapshot


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
    parser.add_argument('--registry-db', type=Path, help='Explicit SQLite registry; defaults to ACTIVE')
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
                              'lib/libpresonus_png.a', 'lib/libpresonus_zlib.a',
                              'share/presonus-core-5/upstream/libpng/LICENSE',
                              'share/presonus-core-5/upstream/zlib/README',
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
    # Separately pinned official curl SDK headers retain their own provenance.
    # Missing/extra/unpinned headers still fail the exact installed union below.
    curl_headers = {}
    curl_manifest = prefix / 'share/presonus_uc/providers/curl-8.5.0/PROVIDER.json'
    if curl_manifest.exists():
        assert sha(curl_manifest) == 'b19c64d7605dbf2bbea3cebb422a7bf137b84b01a07ea28ee15d93bf95352703'
        curl = json.loads(curl_manifest.read_text())
        assert curl['header_version'] == '8.5.0' and curl['runtime_version'] == '8.5.0'
        assert sha(Path(curl['runtime']['path'])) == curl['runtime']['sha256']
        for row in curl['headers']:
            origin = library.parent / row['path']
            relative = origin.relative_to(Path(curl['include_directory']))
            assert relative.parts[0] == 'curl' and len(relative.parts) == 2
            assert sha(origin) == row['sha256']
            name = 'include/presonus-curl-8.5.0/' + relative.as_posix()
            assert name not in curl_headers
            curl_headers[name] = row['sha256']
        assert len(curl_headers) == 12
        assert sha(curl_manifest.parent / 'copyright') == curl['license']['sha256']
        assert not set(curl_headers) & (set(expected) | set(provider_headers))
    installed = {str(path.relative_to(prefix)): sha(path)
                 for path in (prefix / 'include').rglob('*') if path.is_file()}
    if installed != {**expected, **provider_headers, **curl_headers}:
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
    with snapshot(library, args.registry_db) as registry:
        ready = registry.ready
        registry_source = registry.provenance()
    required = {item['mangled'] for item in ready['functions']}
    missing = sorted(required - symbols)
    if missing:
        raise SystemExit('Missing original ready symbols: ' + repr(missing))
    report = dict(registry_source=registry_source, public_header_hashes=expected, archive_sha256=sha(archive),
                  application_header_count=len(expected),
                  provider_header_count=len(provider_headers),
                  provider_header_hashes=provider_headers,
                  curl_provider_header_hashes=curl_headers,
                  curl_same_host_runtime_binding_only=bool(curl_headers),
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
