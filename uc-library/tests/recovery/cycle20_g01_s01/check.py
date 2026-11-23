"""Build or check the Linux replay and compare the native call sequence."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from native import generate

TASK = Path(__file__).resolve().parent.name
TEST = Path('uc-library/tests/recovery') / TASK
MAPPING = TASK[-2:] in ('01', '02', '03')
UNIT = 'MappingComponent' if MAPPING else 'SLMixerEncoder'
UNITS = ('MappingComponent', 'SLMixerEncoder') if MAPPING else (UNIT,)
HEADER = {'MappingComponent': 'MappingComponent.hpp', 'SLMixerEncoder': 'sl_mixer_encoder.hpp'}
SOURCES = [f'uc-library/{name}' for unit in UNITS
           for name in (f'src/Presonus/Surface/{unit}.cpp',
                        f'include/presonus/surface/{HEADER[unit]}')]
CASE = TEST / 'fixtures.json'
REPLAY = Path('uc-library/tests/recovery') / ('cycle20_g01_s01' if MAPPING else 'cycle20_g01_s04') / 'Replay.cpp'
WORK = Path('temp/recovery-work/cycle20_g01-local') / TASK
BUILD = Path('temp/core-upstream/root-integration-01')
OBJECT = WORK / f'{UNIT}.o'
EXE = WORK / 'Replay'
SDK = BUILD / 'upstream-core/sdk'
FORMATTER = 'uc-library/.venv/bin/clang-format'
WRAPS = ['_ZdlPv']
if MAPPING:
    WRAPS += ['_ZN8Presonus10DelayTimerD1Ev', '_ZN4Core8Portable10AttributesD2Ev',
              '_ZN4Core8Portable9ComponentD2Ev']
FLAGS = ['c++', '-std=c++20', '-O3', '-DNDEBUG', '-Wno-multichar', '-Ulinux',
         '-fno-fast-math', '-ffp-contract=off', '-fno-sized-deallocation', '-Iuc-library/include',
         f'-I{SDK}/include/presonus-core-5']
CORE_DEPS = [
    'portable/coretypeinfo.h',
    'portable/corecomponent.h', 'portable/corecomponent.cpp',
    'portable/coreattributes.h', 'portable/coreattributes.cpp',
] if MAPPING else ['portable/coretypeinfo.h']
DOMAIN = ('Exact destructor entry with a same-size concrete portable fixture, null or borrowed '
          'handler, reverse destruction of two distinct DelayTimers and three real CCL attribute '
          'lists, actual CCL Component cleanup, and release only for D0.'
          if MAPPING else
          'Exact deleting destructor entry with a same-size heap-backed concrete portable '
          'fixture and one real unsized free of the same receiver.')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(argv):
    command = list(map(str, argv))
    print('+', ' '.join(command), flush=True)
    subprocess.run(command, check=True)


def compile_local():
    WORK.mkdir(parents=True, exist_ok=True)
    for unit in UNITS:
        run([*FLAGS, '-fno-rtti' if unit == 'MappingComponent' else '-frtti',
             '-c', f'uc-library/src/Presonus/Surface/{unit}.cpp', '-o', WORK / f'{unit}.o'])
    archives = [BUILD / 'libpresonus_cs18_components.a', BUILD / 'libpresonus_uc.a',
                SDK / 'lib/libcorelib.a', SDK / 'lib/libpresonus_core_allocator.a',
                BUILD / 'private-glibc29-provider/libpresonus_private_glibc29.a']
    run([*FLAGS, '-fno-rtti' if MAPPING else '-frtti', REPLAY,
         *(WORK / f'{unit}.o' for unit in UNITS),
         *(f'-Wl,--wrap={symbol}' for symbol in WRAPS), '-Wl,--start-group',
         *archives, '-Wl,--end-group', '-lpthread', '-ldl', '-lrt', '-o', EXE])


def symbol_line(path, mangled):
    listing = subprocess.check_output(['nm', '--defined-only', path], text=True)
    matches = [line for line in listing.splitlines() if line.split()[-1:] == [mangled]]
    assert len(matches) == 1 and matches[0].split()[1] in ('T', 'W'), (path, mangled, matches)
    return matches[0]


def deallocation_relocation(path, mangled):
    if not mangled.endswith('D0Ev'):
        return None
    output = subprocess.check_output(
        ['objdump', '-dr', '--disassemble=' + mangled, path], text=True)
    # GNU objdump -dr can print prior section relocations under the first
    # instruction. Restrict the result to the exact nm address and byte extent.
    listing = subprocess.check_output(['nm', '-S', '--defined-only', path], text=True)
    row = next(line.split() for line in listing.splitlines() if line.split()[-1:] == [mangled])
    start, length = (int(field, 16) for field in row[:2])
    matches = []
    for line in output.splitlines():
        fields = line.split()
        if len(fields) < 3 or not fields[1].startswith('R_'):
            continue
        if start <= int(fields[0].rstrip(':'), 16) < start + length and '_ZdlPv' in fields[2]:
            matches.append(fields)
    assert len(matches) == 1 and matches[0][2] in ('_ZdlPv', '_ZdlPv-0x4'), (mangled, matches)
    return ' '.join(matches[0])


def observe(args, oracle):
    mangled = oracle['mangled']
    assert oracle['task_id'] == TASK
    native_roles = {0x120: 'timer:blink', 0x100: 'timer:hold', 0xE0: 'attributes:2',
                    0xC0: 'attributes:1', 0xA0: 'attributes:0'}
    execution = []
    variant = mangled[-4:-2] if MAPPING else (
        'MixerAssignmentHandler' if TASK.endswith('05') else 'AssignmentHandler')
    for case in oracle['cases']:
        assert case['handler_slot'] == 0
        assert case['vptr'] != 0x11111111
        expected = []
        for call in case['trace']:
            if call['name'] in ('timer', 'attributes'):
                expected.append(native_roles[call['offset']])
            else:
                expected.append(call['name'])
        argv = [str(args.exe), variant, 'bound' if case['bound'] else 'unbound']
        observed = subprocess.check_output(argv, text=True).splitlines()
        assert observed == expected, (argv, observed, expected)
        assert ('delete' in observed) == case['storage_unmapped_by_delete_boundary']
        execution.append(dict(argv=argv, native_events=expected, portable_events=observed))
    return execution


def replay(args):
    oracle = json.loads(args.fixtures.read_text())
    assert oracle == generate(), 'Fresh original ARM replay differs from sealed fixture'
    source_hashes = {name.removeprefix('uc-library/'): digest(name)
                     for name in SOURCES}
    repositories = {f'third_party/ccl-framework/core/{name}':
                    digest(f'third_party/ccl-framework/core/{name}') for name in CORE_DEPS}
    mangled = oracle['mangled']
    symbols = {str(path): symbol_line(path, mangled) for path in (args.object, args.exe)}
    relocation = deallocation_relocation(args.object, mangled)
    executions = observe(args, oracle)
    row = dict(original_elf_sha256=oracle['elf_sha256'], mangled=mangled,
               cpp_compiled=True, mangling_namespace_checked=True, portable_ready=True,
               domain=DOMAIN, sources=source_hashes, repository_sources=repositories)
    proof = dict(
        passed=True, cpp_differential_passed=True, compiled_mangled_names_matched=True,
        mangled_names=[mangled], functions=[row], portable_ready=True,
        proposed_readiness=dict(ready=[row], pending=[]),
        domain=DOMAIN, task=TASK, exact_native=oracle,
        replay_executions=executions, cases=len(executions), compiled_symbols=symbols,
        exact_d0_unsized_deallocation_relocation=relocation,
        artifacts={str(path): digest(path) for path in
                   (args.object, args.exe, args.fixtures, REPLAY, TEST / 'native.py', TEST / 'check.py')},
        formatter=subprocess.check_output([FORMATTER, '--version'], text=True).strip(),
        compiler=subprocess.check_output(['c++', '--version'], text=True).splitlines()[0],
        integration=dict(path=str(args.integration), sha256=digest(args.integration)),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + '\n')
    print(f'{TASK}: {len(executions)} exact original/reconstruction replay cases passed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['format', 'compile', 'symbols', 'replay'])
    parser.add_argument('--exe', type=Path, default=EXE)
    parser.add_argument('--object', type=Path, default=OBJECT)
    parser.add_argument('--fixtures', type=Path, default=CASE)
    parser.add_argument('--integration', type=Path, default=Path('uc-library/validation/integration.json'))
    parser.add_argument('--out', type=Path, default=WORK / 'local-replay.json')
    args = parser.parse_args()
    if args.mode == 'format':
        run([FORMATTER, '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror',
             *SOURCES, REPLAY])
    elif args.mode == 'compile':
        compile_local()
    elif args.mode == 'symbols':
        oracle = json.loads(args.fixtures.read_text())
        print(symbol_line(args.object, oracle['mangled']))
        relocation = deallocation_relocation(args.object, oracle['mangled'])
        if relocation:
            print(relocation)
    else:
        replay(args)


if __name__ == '__main__':
    main()
