"""Build and replay FX validity against an independently recorded ARM oracle."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from native import NAME, generate

ROOT = Path(__file__).resolve().parents[4]
TESTS = Path(__file__).resolve().parent.relative_to(ROOT)
SCRATCH = ROOT / 'temp/recovery-work/rolling_next_fx_validity'
PROVIDERS = ROOT / 'temp/provider-baseline08'
FORMAT = [
    'uc-library/include/presonus/mixer/FXComponent.hpp',
    'uc-library/src/Presonus/Mixer/FXComponent.cpp',
    str(TESTS / 'Replay.cpp'),
]
DOMAIN = (
    'All 13 original effect dispatch slots with each signed upper-bound '
    'transition and negative parameters, out-of-range effect types, int32 '
    'extrema and 512 deterministically generated pairs. Original observations '
    'return 0 or 1 with stack-only writes. The executable checks unchanged '
    'borrowed parameter state and rejects app callbacks.'
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(argv, **kwargs):
    argv = list(map(str, argv))
    print(json.dumps(argv), flush=True)
    process = subprocess.run(
        argv, cwd=ROOT, capture_output=True,
        env={**os.environ, 'TMPDIR': str(SCRATCH)}, **kwargs
    )
    if process.returncode:
        print(process.stdout.decode(), process.stderr.decode())
        process.check_returncode()
    return process.stdout.decode()


def compile_replay(executable, production):
    flags = [
        '/usr/bin/c++', '-std=c++17', '-fno-rtti', '-fno-lto', '-Wno-multichar',
        '-ffunction-sections', '-fdata-sections', '-UNDEBUG',
        '-Iuc-library/include', '-Ithird_party/ccl-framework',
    ]
    dsp = SCRATCH / 'dsp.o'
    driver = SCRATCH / 'driver.o'
    run([*flags, '-O3', '-c', FORMAT[1], '-o', production])
    run([*flags, '-O3', '-c', 'uc-library/src/Presonus/DspComponent.cpp', '-o', dsp])
    run([*flags, '-O0', '-c', FORMAT[2], '-o', driver])
    run([
        '/usr/bin/c++', production, dsp, driver, '-Wl,--gc-sections',
        PROVIDERS / 'libcorelib.a', PROVIDERS / 'libpresonus_core_allocator.a',
        '-lz', '-lpthread', '-ldl', '-lm', '-o', executable,
    ])


def check_symbol(production):
    symbols = run(['/usr/bin/nm', '--defined-only', production]).splitlines()
    if not any(line.split()[-1] == NAME for line in symbols if line.split()):
        raise ValueError(f'Missing original symbol {NAME}')
    print(NAME)


def check_replay(executable, fixtures):
    cases = fixtures['cases']
    payload = ''.join(f'{t} {p}\n' for t, p in (case['input'] for case in cases))
    values = run([executable], input=payload.encode()).splitlines()
    if len(values) != len(cases):
        raise ValueError(f'Expected {len(cases)} results, received {len(values)}')
    for case, value in zip(cases, values):
        if int(value) != case['expected']:
            raise ValueError(f'{case} returned {value}')
    print(f'{len(cases)} ARM differential cases passed')
    return len(cases)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['format', 'compile', 'symbols', 'native', 'replay', 'canonical'])
    parser.add_argument('--exe', type=Path, default=SCRATCH / 'replay')
    parser.add_argument('--object', type=Path, default=SCRATCH / 'production.o')
    parser.add_argument('--fixtures', type=Path, default=TESTS / 'fixtures.json')
    parser.add_argument('--integration', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    if args.mode == 'format':
        run(['uc-library/.venv/bin/clang-format', '--style=file',
             '--fallback-style=LLVM', '--dry-run', '--Werror', *FORMAT])
        return
    if args.mode == 'compile':
        compile_replay(args.exe, args.object)
        return
    if args.mode == 'symbols':
        check_symbol(args.object)
        return

    fixtures = json.loads(args.fixtures.read_text())
    if args.mode in ('native', 'canonical'):
        if generate() != fixtures:
            raise ValueError('Independent ARM execution differs from the sealed fixtures')
        print(f'{len(fixtures["cases"])} fresh original ARM observations matched')
        if args.mode == 'native':
            return
    count = check_replay(args.exe, fixtures)
    if args.mode == 'canonical':
        if args.integration is None or args.out is None:
            parser.error('canonical mode requires --integration and --out')
        integration = json.loads(args.integration.read_text())
        if not isinstance(integration, dict) or not integration:
            raise ValueError('Expected nonempty integration evidence object')
        check_symbol(args.object)
        receipt = {
            'behavior_validated': True,
            'domain': DOMAIN,
            'cases': count,
            'elf_sha256': fixtures['elf_sha256'],
            'ranges': fixtures['ranges'],
            'fixtures_sha256': digest(args.fixtures),
            'executable_sha256': digest(args.exe),
            'object_sha256': digest(args.object),
            'integration_sha256': digest(args.integration),
        }
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()
