"""Compare portable offline Panel replay with independent ARM observations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

TASK = Path(__file__).parent.name
DOMAINS = {
    's11': 'Both roles and both exact const methods. Clean, ordinary nonzero, high-bit and all-bit dirty state, then transition back to clean. Direct and virtual host dispatch agree on one inherited state.',
    's19': 'Both roles and independent C1/C2 ranges. Valid short names, signed coordinates, initially empty pinned CCL string buffer and actual LCD delegate resolution with or without observing a pinned CCL parameter. Normal teardown removes that same observer.',
    's20': 'Both roles and independent C1/C2 ranges. Actual Field constructor and normal teardown with signed coordinates, valid short names and optional CCL observer. Text cursor starts at zero and local string is empty.',
}
CCL_PATHS = [
    'third_party/ccl-framework/core/portable/coreparams.cpp',
    'third_party/ccl-framework/core/portable/coreparams.h',
    'third_party/ccl-framework/core/portable/coresingleton.cpp',
    'third_party/ccl-framework/core/portable/coresingleton.h',
    'third_party/ccl-framework/core/public/corestringbuffer.h',
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv, **kwargs):
    return subprocess.run(argv, text=True, check=True, capture_output=True, **kwargs).stdout


def symbols(path):
    return {line.split()[-1] for line in run(['nm', '--defined-only', str(path)]).splitlines() if line.split()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--object', type=Path, required=True)
    parser.add_argument('--secondary-object', type=Path)
    parser.add_argument('--fixtures', type=Path, required=True)
    parser.add_argument('--integration', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    packet = TASK[-3:]
    pending = packet == 's11'
    domain = DOMAINS[packet]
    rows = json.loads(args.fixtures.read_text())['originals']
    primary_symbols = symbols(args.object)
    secondary_symbols = symbols(args.secondary_object) if args.secondary_object else set()
    for row in rows:
        selected = secondary_symbols if pending and '7Element' in row['mangled'] else primary_symbols
        assert row['mangled'] in selected, row['mangled']
    if packet == 's20':
        assert not primary_symbols.intersection({_ for _ in (
            '_ZN8Presonus5Panel16TextEntryElementD0Ev',
            '_ZN8Presonus5Panel16TextEntryElementD1Ev',
            '_ZN8Presonus5Panel16TextEntryElementD2Ev',
        )})
    cases = [(row, case) for row in rows for case in row['cases']]
    inputs = []
    for row, case in cases:
        variant = [] if pending else [int('C2EiiPKc' in row['mangled'])]
        inputs.append(' '.join(map(str, variant + case['input'])))
    actual = run([str(args.exe.resolve())], input='\n'.join(inputs) + '\n').splitlines()
    assert actual == [case['expected'] for _, case in cases]
    classes = ['Element', 'OffscreenElement', 'LCDManager', 'FieldElement']
    if packet == 's20':
        classes.append('TextEntryElement')
    source_names = [f'{directory}/{class_name}.{ext}' for class_name in classes for directory, ext in (
        ('include/presonus/panel', 'hpp'), ('src/Presonus/Panel', 'cpp'))]
    source_names.append('include/presonus/panel/MixerLCD.hpp')
    sources = {name: digest(Path('uc-library') / name) for name in source_names}
    repository_sources = {name: digest(Path(name)) for name in CCL_PATHS}
    proposed = []
    for row in rows:
        record = {k: row[k] for k in ('mangled', 'firmware', 'role', 'address', 'size', 'section')}
        record.update(original_elf_sha256=row['elf_sha256'], cpp_compiled=True,
                      mangling_namespace_checked=True, portable_ready=not pending,
                      domain=domain, sources=sources, repository_sources=repository_sources)
        if pending:
            record['declaration_uncertainties'] = ['Original return type is unencoded. Host bool exposes the observed zero-or-one result.']
        proposed.append(record)
    result = {'passed': True, 'domain': domain, 'case_count': len(cases), 'originals': rows,
              'object_sha256': digest(args.object), 'executable_sha256': digest(args.exe),
              'secondary_object_sha256': digest(args.secondary_object) if args.secondary_object else None,
              'fixtures_sha256': digest(args.fixtures),
              'integration_sha256': digest(args.integration) if args.integration.is_file() else None,
              'proposed_readiness': {'ready': [] if pending else proposed, 'pending': proposed if pending else []}}
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(f'{len(cases)} matching host cases across {len(rows)} original ranges')


if __name__ == '__main__':
    main()
