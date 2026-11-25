#!/usr/bin/env python3
"""Compare the production EQ4 implementation with ARM observations."""
import argparse
import json
import os
from pathlib import Path
import struct
import subprocess

ROOT = Path.cwd()
WORK = ROOT / 'temp/recovery-work/eq4-local'
CANONICAL_BUILD = Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01')
DIRECTORY = Path('uc-library/tests/recovery/sqlite02_eq4controller_do_updates')
CPP = Path('uc-library/src/Presonus/Dsp/EQ4Controller.cpp')
PROVIDERS = ('Presonus/Dsp/EQController.cpp', 'Presonus/Dsp/EQControllerProcess.cpp',
             'Presonus/Dsp/Controller.cpp', 'Presonus/Dsp/ControllerInfo.cpp',
             'Presonus/Dsp/ControllerInterface.cpp', 'Presonus/Dsp/ControllerSetupProcess.cpp',
             'Presonus/Dsp/EqParameterLists.cpp', 'Presonus/Dsp/ParamDescriptorList.cpp',
             'Presonus/Dsp/EqSourceProviders.cpp', 'mixer_dsp/EQTypeConversions.cpp',
             'mixer_dsp/Formatters.cpp', 'mixer_dsp/AdditionalFormatters.cpp',
             'mixer_dsp/Power.cpp', 'mixer_dsp/Logarithm.cpp', 'mixer_dsp/Interpolators.cpp',
             'DSP/BiquadCalcConstructor.cpp', 'DSP/BiquadMethods.cpp',
             'DSP/BiquadIncremental.cpp', 'DSP/BiquadSine.cpp')
ARCHIVES = ('upstream-core/sdk/lib/libcorelib.a', 'upstream-core/build/libpresonus_core_allocator.a',
            'private-glibc29-provider/libpresonus_private_glibc29.a')


def invoke(argv, **kwargs):
    print('+', ' '.join(map(str, argv)), flush=True)
    return subprocess.run(argv, check=True, **kwargs)


def build(binary, work):
    work.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, 'TMPDIR': str(work)}
    flags = ('-std=c++20', '-isystem', 'third_party/ccl-framework', '-Iuc-library/include', '-Iuc-library/src/mixer_dsp', '-fno-fast-math', '-ffp-contract=off')
    invoke(['g++', *flags, '-Wall', '-Wextra', '-Werror', '-c', CPP,
            '-o', work / 'EQ4Controller.o'], env=env)
    sources = []
    for name in PROVIDERS:
        source = Path('uc-library/src') / name
        if source.stem in ('EqSourceProviders', 'Interpolators'):
            obj = work / (source.stem + '.o')
            invoke(['g++', *flags, '-fno-rtti', '-frounding-math', '-fno-builtin',
                    '-c', source, '-o', obj], env=env)
            sources.append(obj)
        else:
            sources.append(source)
    invoke(['g++', *flags, work / 'EQ4Controller.o', DIRECTORY / 'Replay.cpp',
            *sources, '-Wl,--start-group',
            *(CANONICAL_BUILD / name for name in ARCHIVES), '-Wl,--end-group',
            '-pthread', '-o', binary], env=env)


def double_bits(value):
    return struct.unpack('<Q', struct.pack('<d', value))[0]


def expected(task, case):
    if task.endswith('construct'):
        return [*case['scalars'], *(word for band in case['bands'] for word in band)]
    if task.endswith('destroy'):
        return [case['released'], int(case['deallocated']), 1]
    result = case['flush_result']
    return [(-1 if result is None else result), case['process_dirty'], *case['dirty'],
            len(case['payloads']), *(word for payload in case['payloads'] for word in payload),
            *(double_bits(value) for band in case['final_coefficients'] for value in band)]


def replay(task, fixture, binary):
    data = json.loads(fixture.read_text())
    cases = data['cases']
    assert cases
    inputs = [case['input'] if task == 'do_updates' else [case['id']] for case in cases]
    lines = [' '.join(map(str, row)) for row in inputs]
    output = invoke([binary.resolve(), task], input='\n'.join(lines) + '\n',
                    text=True, capture_output=True).stdout.splitlines()
    assert len(output) == len(cases)
    for index, (line, case) in enumerate(zip(output, cases)):
        actual, reference = list(map(int, line.split())), expected(task, case)
        if actual != reference:
            deltas = [(i, a, r) for i, (a, r) in enumerate(zip(actual, reference)) if a != r]
            raise AssertionError(f'{task} case {index} differences (index, portable, native): {deltas}')
    print(f'{task}: {len(cases)} native/portable cases passed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('compile', 'symbols', 'native', 'replay'))
    parser.add_argument('task')
    parser.add_argument('fixture', type=Path)
    parser.add_argument('--binary', type=Path)
    args = parser.parse_args()
    work = WORK / args.task
    binary = args.binary or work / 'Replay'
    if args.mode == 'compile':
        build(binary, work)
    elif args.mode == 'symbols':
        identity = json.loads(args.fixture.read_text())['original']['mangled']
        result = invoke(['nm', '--defined-only', work / 'EQ4Controller.o'],
                        text=True, capture_output=True)
        defined = {line.split()[-1] for line in result.stdout.splitlines() if line.split()}
        assert identity in defined, identity
        print(identity)
    elif args.mode == 'native':
        import native

        actual = json.dumps(native.run(args.task), indent=2) + '\n'
        assert actual == args.fixture.read_text(), 'ARM fixture regeneration differs'
        print(f'{args.task}: original ELF ranges and ARM observations verified')
    else:
        replay(args.task, args.fixture, binary)


if __name__ == '__main__':
    main()
