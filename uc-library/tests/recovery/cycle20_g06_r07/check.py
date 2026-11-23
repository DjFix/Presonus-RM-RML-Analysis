"""Compare host TextEntry's actual Field association with ARM observations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

MANGLED = '_ZN8Presonus5Panel16TextEntryElement16getInternalParamEv'
DOMAIN = ('Both firmware roles: same-receiver delegation using verified original Field getter instructions, '
          'null or populated cache misses, clean cached lookup bypass, refreshed borrowed pointer identity, '
          'and portable delegate call count. The separate legacy encoder binding remains independent.')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv, **kwargs):
    return subprocess.run(argv, text=True, capture_output=True, check=True, **kwargs).stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--object', type=Path, required=True)
    parser.add_argument('--fixtures', type=Path, required=True)
    parser.add_argument('--integration', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    symbols = run(['nm', '--defined-only', str(args.object)])
    exact = [line for line in symbols.splitlines() if line.split()[-1:] == [MANGLED]]
    assert len(exact) == 1
    fixture = json.loads(args.fixtures.read_text())
    rows = fixture['originals']
    assert len(rows) == 2 and all(row['mangled'] == MANGLED for row in rows)
    cases = [case for row in rows for case in row['cases']]
    stdin = ''.join(' '.join(map(str, case['input'])) + '\n' for case in cases)
    actual = run([str(args.exe.resolve())], input=stdin).splitlines()
    assert actual == [case['expected'] for case in cases], actual
    source_names = [f'{directory}/{name}.{ext}' for name in (
        'TextEntryElement', 'FieldElement', 'LCDManager', 'OffscreenElement', 'Element')
        for directory, ext in (('src/Presonus/Panel', 'cpp'), ('include/presonus/panel', 'hpp'))]
    source_names.append('include/presonus/panel/MixerLCD.hpp')
    sources = {name: digest(Path('uc-library') / name) for name in source_names}
    repository_sources = {
        path: digest(Path(path)) for path in (
            'third_party/ccl-framework/core/portable/coreparams.h',
            'third_party/ccl-framework/core/portable/coreparams.cpp',
            'third_party/ccl-framework/core/portable/coresingleton.h',
            'third_party/ccl-framework/core/portable/coresingleton.cpp',
        )
    }
    pending = []
    for row in rows:
        identity = {key: row[key] for key in ('mangled', 'firmware', 'role', 'address', 'size', 'section')}
        pending.append(dict(identity, original_elf_sha256=row['elf_sha256'], cpp_compiled=True,
                            mangling_namespace_checked=True, portable_ready=False, domain=DOMAIN,
                            sources=sources, repository_sources=repository_sources, declaration_uncertainties=[
                                'The original return declaration is unencoded. Portable forwarding exposes its typed borrowed CCL Parameter pointer.']))
    result = {'passed': True, 'domain': DOMAIN, 'case_count': len(cases), 'originals': rows,
              'compiled_symbol': exact[0], 'object_sha256': digest(args.object),
              'executable_sha256': digest(args.exe), 'fixtures_sha256': digest(args.fixtures),
              'integration_sha256': digest(args.integration) if args.integration.is_file() else None,
              'proposed_readiness': {'ready': [], 'pending': pending}}
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(f'{len(cases)} matching optimized host cases across {len(rows)} original ranges')


if __name__ == '__main__':
    main()
