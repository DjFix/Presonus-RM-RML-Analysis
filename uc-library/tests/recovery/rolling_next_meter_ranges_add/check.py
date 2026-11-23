"""Rebuild locally and compare the portable range registry with offline ARM observations."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).parent
TASK = HERE.name
METHOD = TASK.rsplit('_', 1)[1]
SCRATCH = Path('temp/recovery-work/meter-ranges-current01') / METHOD
PROVIDER = SCRATCH.parent / 'provider'
LIBRARY = Path('uc-library')
HEADER = LIBRARY / 'include/presonus/MeterScaleControl.hpp'
SOURCE = LIBRARY / 'src/Presonus/MeterScaleControl.cpp'
REPLAY = HERE / 'Replay.cpp'
CORE = Path('third_party/ccl-framework/core/public')
CHECKED = [
    '_ZN8Presonus17MeterScaleControl6Ranges8addRangeEPKciPKi',
    '_ZN8Presonus17MeterScaleControl6Ranges8getRangeEPKc',
]
CLANG_FORMAT = LIBRARY / '.venv/bin/clang-format'
DOMAIN = {
    'add': 'Offline ordered records; negative, zero and positive counts; null, empty and long names including 127/128 bytes; duplicate keys; borrowed payload and capacity growth. Separate scripted ARM resize-failure and portable allocation-failure observations.',
    'get': 'Offline first-match pointer identity and no mutation through empty and nonempty registries, duplicate and case-sensitive keys, null/empty lookup, 127/128-byte boundary probes and borrowed payload.',
}
UNCERTAINTY = {
    'add': ['Original ordinary return declaration and native field types/layout are unresolved. Portable declaration uses void.'],
    'get': ['Original pointer pointee type/const qualification, ordinary return declaration and native record field layout are unresolved. Portable declaration uses a pointer to the nested portable record.'],
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv):
    print(json.dumps([str(x) for x in argv]), flush=True)
    subprocess.run(argv, check=True, env={**os.environ, 'TMPDIR': str(SCRATCH.resolve())})


def local_compile(executable, obj):
    flags = [
        '-std=c++20', '-fno-rtti', '-O2', '-ffunction-sections',
        '-fdata-sections', '-pthread', '-Ulinux', '-DCORE_USE_OPENSSL=1',
        '-DPRESONUS_HAS_UPSTREAM_CORE=1', '-Iuc-library/include',
        '-Ithird_party/ccl-framework',
    ]
    run(['/usr/bin/c++', *flags, '-c', SOURCE, '-o', obj])
    libs = [PROVIDER / name for name in [
        'libpresonus_cs18_components.a', 'libpresonus_uc.a', 'libcorelib.a',
        'libpresonus_core_allocator.a',
    ]]
    run(['/usr/bin/c++', *flags, REPLAY, obj, '-Wl,--gc-sections',
         '-Wl,--start-group', *libs, '-Wl,--end-group', '-l:libpng16.so.16',
         '-lz', '-lssl', '-lcrypto', PROVIDER / 'libdns_sd.so', '-ldl', '-lm',
         '-o', executable])


def symbols(obj):
    argv = ['/usr/bin/nm', '--defined-only', obj]
    print(json.dumps([str(x) for x in argv]), flush=True)
    names = {line.split()[-1] for line in subprocess.check_output(argv, text=True).splitlines()}
    assert all(name in names for name in CHECKED), CHECKED
    return CHECKED


def replay(executable, fixture):
    total = 0
    for case in fixture['cases']:
        if METHOD == 'add':
            if case['resize_failure']:
                assert case['result_count'] == case['initial']
                assert case['allocated_record_retained_on_failure']
                continue
            args = [case['name'] if case['name'] is not None else '@NULL',
                    str(case['count']), str(case['initial'])]
            expected = [str(case['result_count']), case['stored_name'], str(case['count'])]
        else:
            args = [str(case['count']), case['key'] if case['key'] is not None else '@NULL']
            expected = [str(case['index'])]
        output = subprocess.check_output([executable, *args], text=True)
        assert output.splitlines() == expected, (case, output)
        total += 1
    if METHOD == 'add':
        run([executable, 'failures'])
    print(f'{total} native/portable comparisons passed')
    return total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('gate', choices=['format', 'compile', 'symbols', 'native', 'proof'])
    parser.add_argument('--exe', type=Path, default=SCRATCH / 'replay')
    parser.add_argument('--object', type=Path, default=SCRATCH / 'ranges.o')
    parser.add_argument('--fixture', type=Path, default=HERE / 'fixtures.json')
    parser.add_argument('--elf', type=Path)
    parser.add_argument('--integration', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()

    if args.gate == 'format':
        run([CLANG_FORMAT, '--version'])
        run([CLANG_FORMAT, '--style=file', '--fallback-style=LLVM', '--dry-run',
             '--Werror', HEADER, SOURCE, REPLAY])
        return
    SCRATCH.mkdir(parents=True, exist_ok=True)
    if args.gate == 'compile':
        local_compile(args.exe, args.object)
        return
    if args.gate == 'symbols':
        symbols(args.object)
        return
    if args.gate == 'native':
        assert args.elf
        output = SCRATCH / 'native.json'
        run([sys.executable, '-B', HERE / 'native.py', '--elf', args.elf, '--out', output])
        assert digest(output) == digest(args.fixture), 'fresh ARM observation changed'
        return

    fixture = json.loads(args.fixture.read_text())
    assert fixture['producer_sha256'] == digest(HERE / 'native.py')
    assert args.integration and args.out
    matched = symbols(args.object)
    assert fixture['mangled'] in matched
    portable_cases = replay(args.exe, fixture)
    sources = {str(p.relative_to(LIBRARY)): digest(p) for p in (SOURCE, HEADER)}
    repository_sources = {
        str(p): digest(p) for p in (CORE / 'corevector.h', CORE / 'corestringbuffer.h')
    }
    row = {
        'original_elf_sha256': fixture['elf_sha256'],
        'mangled': fixture['mangled'],
        'domain': DOMAIN[METHOD],
        'cpp_compiled': True,
        'mangling_namespace_checked': True,
        'portable_ready': False,
        'declaration_uncertainties': UNCERTAINTY[METHOD],
        'sources': sources,
        'repository_sources': repository_sources,
    }
    result = {
        'success': True,
        'cpp_differential_passed': True,
        'compiled_mangled_names_matched': True,
        'mangled_names': [fixture['mangled']],
        'integration_sha256': digest(args.integration),
        'integration_reference': str(args.integration),
        'executable_sha256': digest(args.exe),
        'object_sha256': digest(args.object),
        'fixture_sha256': digest(args.fixture),
        'native_case_count': len(fixture['cases']),
        'portable_case_count': portable_cases,
        'original_range': {
            k: fixture[k] for k in ['elf_sha256', 'mangled', 'address', 'size', 'section',
                                    'file_offset', 'range_sha256', 'producer_sha256',
                                    'unicorn', 'boundaries']
        },
        'format_validation': {
            'files': sources,
            'version': subprocess.check_output([CLANG_FORMAT, '--version'], text=True).strip(),
        },
        'proposed_readiness': {'ready': [], 'pending': [row]},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
