"""Build and replay the portable CompController against original ARM observations."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
SCRATCH = Path('temp/recovery-work/comp-validation')
BUILD = Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01')
SOURCE = Path('uc-library/src/Presonus/Dsp/CompController.cpp')
HEADER = Path('uc-library/include/presonus/dsp/CompController.hpp')
FORMATTER = Path('uc-library/.venv/bin/clang-format')
SOURCES = (SOURCE, HEADER, HERE / 'Replay.cpp')
FIXTURE = HERE / 'fixtures.json'
EXECUTABLE = SCRATCH / 'replay'
OBJECT = SCRATCH / 'CompController.o'
VECTOR = SCRATCH / 'provider'
LIBRARIES = tuple(BUILD / p for p in (
    'libpresonus_uc.a',
    'upstream-core/sdk/lib/libcorelib.a',
    'upstream-core/sdk/lib/libpresonus_core_allocator.a',
    'upstream-core/sdk/lib/libpresonus_png.a',
    'upstream-core/sdk/lib/libpresonus_zlib.a',
    'private-glibc29-provider/libpresonus_private_glibc29.a',
))
WRAPS = ('-Wl,--wrap=_ZdlPv', '-Wl,--wrap=_ZdlPvm')
FLAGS = (
    '-std=c++20', '-O2', '-fno-sized-deallocation', '-Ulinux',
    '-DCORE_USE_OPENSSL=1', '-DPRESONUS_HAS_UPSTREAM_CORE=1',
    '-Iuc-library/include', '-Ithird_party/ccl-framework',
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(*argv, **kwargs):
    command = list(map(str, argv))
    print(json.dumps(command), flush=True)
    return subprocess.run(command, check=True, text=True, **kwargs)


def format_check():
    run(FORMATTER, '--version')
    run(FORMATTER, '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror', *SOURCES)


def compile_checks(executable):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    run('/usr/bin/c++', *FLAGS, '-c', SOURCE, '-o', OBJECT)
    run('/usr/bin/c++', *FLAGS, HERE / 'Replay.cpp', OBJECT, *WRAPS,
        *LIBRARIES, '-lssl', '-lcrypto', '-ldl', '-lm', '-o', executable)
    run('/usr/bin/c++', *FLAGS, '-DCOMP_VECTOR_BOUNDARY',
        HERE / 'Replay.cpp', *LIBRARIES, '-lssl', '-lcrypto', '-ldl', '-lm', '-o', VECTOR)


def check_symbols(fixture, object_path):
    nm = run('/usr/bin/nm', '--defined-only', object_path, capture_output=True).stdout
    found = {line.split()[-1] for line in nm.splitlines() if line.split()}
    originals = [name for name in fixture['native_ranges'] if '14CompController' in name]
    assert len(originals) == 7
    for name in originals:
        assert name in found, name
        print(name)


def compare(case, observed):
    kind = case['kind']
    expected = case['expected']
    if kind in ('construct', 'set', 'get'):
        assert observed == [' '.join(map(str, expected))], (case, observed)
    else:
        assert observed == [*expected, 'end'], (case, observed)


def replay(fixture, executable, mangled):
    assert fixture['producer_sha256'] == sha(HERE / 'native.py')
    count = 0
    for case in fixture['cases']:
        if mangled and case['name'] != mangled:
            continue
        kind = case['kind']
        inputs = case['inputs']
        if kind == 'get_raw':
            continue
        if kind == 'construct':
            inputs = [*inputs, int(case['name'][-3])]
        elif kind == 'destroy':
            inputs = [*inputs, int(case['name'].endswith('D0Ev'))]
        text = ' '.join(map(str, [kind, *inputs])) + '\n'
        # Keep paired constructor calls in a single process, so each variant
        # exercises both first initialization and singleton reuse.
        if kind == 'construct' and inputs[0] < 0:
            first = (case, text)
            continue
        if kind == 'construct':
            first_case, first_text = first
            assert first_case['name'] == case['name']
            result = subprocess.run([executable], input=first_text + text,
                                    capture_output=True, text=True, check=True)
            lhs, rhs = result.stdout.splitlines()
            compare(first_case, [lhs])
            compare(case, [rhs])
            count += 2
        else:
            result = subprocess.run([executable], input=text, capture_output=True,
                                    text=True, check=True)
            compare(case, result.stdout.splitlines())
            count += 1
    assert count > 0
    print(f'{count} portable/native observations matched for {mangled or "all targets"}')
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('gate', choices=('format', 'compile', 'symbols', 'native', 'replay'))
    parser.add_argument('--fixtures', type=Path, default=FIXTURE)
    parser.add_argument('--executable', type=Path, default=EXECUTABLE)
    parser.add_argument('--object', type=Path, default=OBJECT)
    parser.add_argument('--mangled')
    args = parser.parse_args()

    if args.gate == 'format':
        format_check()
    elif args.gate == 'compile':
        compile_checks(args.executable)
    elif args.gate == 'native':
        run(sys.executable, HERE / 'native.py', '--provider', VECTOR,
            '--out', SCRATCH / 'native-replay.json')
        assert (SCRATCH / 'native-replay.json').read_bytes() == args.fixtures.read_bytes()
        print(f'Original observations reproduced exactly: {sha(args.fixtures)}')
    else:
        fixture = json.loads(args.fixtures.read_text())
        if args.gate == 'symbols':
            check_symbols(fixture, args.object)
        else:
            replay(fixture, args.executable, args.mangled)


if __name__ == '__main__':
    main()
