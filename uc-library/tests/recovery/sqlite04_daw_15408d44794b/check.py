"""Build the owned portable unit and replay exact DAWChannelGroup observations."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess

TEST = Path(__file__).parent
SOURCE = Path('uc-library/src/Presonus/DAWChannelGroup.cpp')
HEADER = Path('uc-library/include/presonus/DAWChannelGroup.hpp')
CLIENT = Path('uc-library/src/Presonus/UC/ClientComponent.cpp')
DRIVER = TEST / 'Replay.cpp'
FORMATTER = 'uc-library/.venv/bin/clang-format'
FORMAT = [FORMATTER, '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror',
          HEADER, SOURCE, DRIVER]
FLAGS = ['g++', '-std=c++17', '-O2', '-Wno-multichar', '-Iuc-library/include',
         '-Ithird_party/ccl-framework', '-ffunction-sections', '-fdata-sections']


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def invoke(argv, text_input=None):
    argv = list(map(str, argv))
    result = subprocess.run(argv, check=True, input=text_input, text=True, capture_output=True)
    return result.stdout


def compile_replay(work, archives):
    work.mkdir(parents=True, exist_ok=True)
    objects = []
    commands = []
    for source in (SOURCE, CLIENT, DRIVER):
        obj = work / (source.stem + '.o')
        commands.append([*FLAGS, '-MMD', '-c', source, '-o', obj])
        objects.append(obj)
    commands.append(['g++', *objects, *archives, '-Wl,--gc-sections',
                     '-Wl,--wrap=_ZdlPv', '-Wl,--wrap=_ZdlPvm', '-pthread',
                     '-o', work / 'Replay'])
    archive_hashes = {str(path): digest(path) for path in archives}
    for command in commands:
        invoke(command)
    assert archive_hashes == {str(path): digest(path) for path in archives}
    receipt = dict(commands=[list(map(str, command)) for command in commands],
                   archive_sha256=archive_hashes,
                   objects={str(obj): digest(obj) for obj in objects},
                   dependency_files={str(obj.with_suffix('.d')): digest(obj.with_suffix('.d'))
                                     for obj in objects},
                   executable_sha256=digest(work / 'Replay'))
    (work / 'compile.json').write_text(json.dumps(receipt, indent=2) + '\n')


def replay(exe, fixture):
    variant, = {target['variant'] for target in fixture}
    assert {target['original']['role'] for target in fixture} == {'client', 'server'}
    cases = [case for target in fixture for case in target['cases']]
    inputs = ''.join(f"{case['prefill']} {case['type_id']}\n" for case in cases)
    lines = invoke([exe.resolve(), variant], text_input=inputs).splitlines()
    assert lines == [case['expected'] for case in cases]
    print(f'{variant}: {len(cases)} portable observations matched both original roles')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('format', 'compile', 'symbols', 'replay'))
    parser.add_argument('--work', type=Path)
    parser.add_argument('--archive', action='append', type=Path, default=[])
    parser.add_argument('--fixture', type=Path)
    parser.add_argument('--packet', type=Path)
    parser.add_argument('--exe', type=Path)
    args = parser.parse_args()
    if args.mode == 'format':
        invoke(FORMAT)
    elif args.mode == 'compile':
        compile_replay(args.work, args.archive)
    elif args.mode == 'symbols':
        fixture = json.loads(args.fixture.read_text())
        mangled, = {target['original']['mangled'] for target in fixture}
        symbols = invoke(['nm', '--defined-only', args.work / 'DAWChannelGroup.o'])
        assert mangled in {line.split()[-1] for line in symbols.splitlines() if line}
        print(mangled)
    else:
        fixture = json.loads(args.fixture.read_text())
        if args.packet:
            from native import run
            assert run(args.packet) == fixture
            print('Re-executed both original ARM ranges and matched the fixture')
        replay(args.exe, fixture)


if __name__ == '__main__':
    main()
