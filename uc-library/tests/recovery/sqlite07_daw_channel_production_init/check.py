"""Build or replay one exact DAWChannel task on Linux."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess

import elftools
import unicorn
from native import PROVIDER_MACHINE, SERVER_COPY, run

LIB = Path('uc-library')
CORE = Path('third_party/ccl-framework/core')
TEST = Path(__file__).resolve().parent.relative_to(Path.cwd())
HEADER = LIB / 'include/presonus/DAWChannel.hpp'
SOURCE = LIB / 'src/Presonus/DAWChannelInit.cpp'
PROVIDERS = (
    LIB / 'src/Presonus/DAWChannel.cpp',
    LIB / 'src/Presonus/UC/ClientComponent.cpp',
    LIB / 'src/Presonus/DAWDeviceFolder.cpp',
    LIB / 'src/Presonus/DAWDeviceSlot.cpp',
    LIB / 'src/mixer_dsp/Formatters.cpp',
    LIB / 'src/mixer_dsp/Power.cpp',
)
DRIVER = TEST / 'Replay.cpp'
FORMATTER = LIB / '.venv/bin/clang-format'
FORMAT = [FORMATTER, '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror',
          HEADER, SOURCE, DRIVER]
FLAGS = ['g++', '-std=c++17', '-O2', '-Ulinux', '-DNDEBUG=1', '-Wno-multichar',
         '-Iuc-library/include', '-Ithird_party/ccl-framework']
DOMAIN = (
    'Both exact firmware roles with both mode flags on full, partial and empty freshly '
    'assembled valid channel trees. Compare ordered detach/destruction, surviving tags, '
    'cache identity and clearing, feedback flags, actual gain formatter, range-set order '
    'for a NumericParam and clamping for a ListParam, all extension descriptors and ordered typed Folder/Slot init. '
    'Portable replay also checks getID/isSelected against the populated caches.')
DECLARATION = (
    'The portable declaration uses void. Original return spelling is unencoded and remains '
    'pending an independently identified original declaration or verified typed contract.')
LIMITATIONS = [
    DECLARATION,
    'Native replay executes actual CCL, channel, GainDBFormatter constructor and Folder/Slot '
    'entries. Uninstrumented application and Core intervals execute from the original image. '
    'The test supplies bounded heap allocation/deallocation, memcpy, C-string and '
    'single-threaded C++ guard/atexit shims. Neither allocator internals nor guard '
    'exception/contended lifetime paths are covered.',
    'Fresh valid single-owner CCL trees only. Repeated initialization, malformed tree state '
    'and hardware interoperability are outside scope.',
    'Portable provider source uses its own object layout. Original ARM ABI is unverified.',
]


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def binding(path):
    return dict(path=str(path), sha256=digest(path))


def emit(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('format', 'compile', 'symbols', 'replay'))
    parser.add_argument('--packet', type=Path, required=True)
    parser.add_argument('--fixture', type=Path)
    parser.add_argument('--object', type=Path)
    parser.add_argument('--exe', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--integration', type=Path)
    parser.add_argument('--archive', action='append', type=Path, default=[])
    args = parser.parse_args()
    commands = []

    def invoke(argv):
        argv = list(map(str, argv))
        start = datetime.now(timezone.utc)
        result = subprocess.run(argv, text=True, capture_output=True)
        commands.append(dict(argv=argv, exit_code=result.returncode,
                             start_utc=start.isoformat(),
                             end_utc=datetime.now(timezone.utc).isoformat(),
                             stdout=result.stdout, stderr=result.stderr))
        if result.returncode:
            print(result.stdout, result.stderr)
        result.check_returncode()
        return result.stdout

    packet = json.loads(args.packet.read_text())
    originals = [item['original'] for item in packet['originals']]
    mangled = originals[0]['mangled']
    assert mangled == '_ZN8Presonus10DAWChannel4initEb'
    if args.mode == 'format':
        invoke(FORMAT)
        return
    if args.mode == 'compile':
        args.object.parent.mkdir(parents=True, exist_ok=True)
        assert len(args.archive) == 2
        archives = [binding(path) for path in args.archive]
        units = []
        units_to_build = [
            (SOURCE, args.object, 'local_production'),
            (DRIVER, args.object.with_name('Replay.o'), 'local_replay'),
            *[(provider, args.object.with_name(provider.stem + '.o'), 'application_dependency')
              for provider in PROVIDERS],
        ]
        for source, obj, kind in units_to_build:
            invoke([*FLAGS, '-MMD', '-c', source, '-o', obj])
            units.append(dict(kind=kind, role='common', source=str(source), directory='.',
                              object=binding(obj), depfile=binding(obj.with_suffix('.d'))))
        invoke(['g++', *[unit['object']['path'] for unit in units], *args.archive,
                '-pthread', '-o', args.exe])
        assert archives == [binding(path) for path in args.archive]
        emit(args.out, dict(version=1, commands=commands, archives=archives,
                            units=units[:2], extra_units=units[2:],
                            executable=binding(args.exe)))
        return

    output = invoke(['nm', '--defined-only', args.object])
    assert mangled in {line.split()[-1] for line in output.splitlines() if line.split()}
    if args.mode == 'symbols':
        print(mangled)
        return
    original_start = datetime.now(timezone.utc)
    fixtures = json.loads(args.fixture.read_text())
    assert run(args.packet) == fixtures
    original_end = datetime.now(timezone.utc)
    case_count = 0
    for original in fixtures:
        for case in original['cases']:
            output = invoke([args.exe.resolve(), case['profile'], int(case['remove_controls'])])
            assert output.splitlines() == case['normalized'], (case['profile'], output)
            case_count += 1
    invoke(FORMAT)
    sources = {HEADER, SOURCE, *PROVIDERS, DRIVER, args.fixture, TEST / 'check.py',
               TEST / 'native.py', PROVIDER_MACHINE}
    core = {CORE / 'portable/corecomponent.cpp', CORE / 'portable/coreparams.cpp',
            CORE / 'public/coreformatter.cpp', CORE / 'public/corestringtraits.h'}
    for unit in (SOURCE, *PROVIDERS, DRIVER):
        raw = invoke([*FLAGS, '-MM', unit]).replace(chr(92) + '\n', ' ')
        sources.update(Path(path) for path in raw.split()[1:] if path.startswith('uc-library/'))
        core.update(Path(path) for path in raw.split()[1:] if path.startswith('third_party/'))
    elf_inputs = []
    for row in originals:
        requested = Path(row['elf_path'])
        actual = requested if requested.is_file() else Path(SERVER_COPY)
        assert digest(actual) == row['elf']
        elf_inputs.append(dict(requested=str(requested), **binding(actual)))
    records = []
    for row in originals:
        record = dict(original_elf_sha256=row['elf'], mangled=mangled,
                      original_address=row['address'], domain=DOMAIN,
                      sources={str(p.relative_to(LIB)): digest(p) for p in sorted(sources)},
                      repository_sources={str(p): digest(p) for p in sorted(core)},
                      cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
                      declaration_uncertainties=[DECLARATION])
        records.append(record)
    proof = dict(
        version=1, task_id=packet['task']['id'], cpp_compiled=True, portable_ready=False,
        cpp_differential_passed=True, compiled_mangled_names_matched=True,
        original_arm_abi_verified=False, hardware_verified=False,
        validation_domain=DOMAIN, limitations=LIMITATIONS, functions=records,
        proposed_readiness=dict(ready=[], pending=records),
        inputs=[binding(p) for p in (args.packet, args.fixture, TEST / 'native.py', TEST / 'check.py', PROVIDER_MACHINE)],
        native_execution=dict(start_utc=original_start.isoformat(), end_utc=original_end.isoformat(),
                              cases=case_count, elf_inputs=elf_inputs,
                              ranges=[{k: v for k, v in f.items() if k != 'cases'} for f in fixtures]),
        portable_execution=dict(cases=case_count, executable=binding(args.exe), object=binding(args.object)),
        provider_archives=[binding(p) for p in args.archive],
        tools=dict(formatter=invoke([FORMATTER, '--version']).strip(),
                   compiler=invoke(['g++', '--version']).splitlines()[0],
                   unicorn=unicorn.__version__, elf_parser=elftools.__version__),
        commands=commands)
    if args.integration:
        proof['integration'] = binding(args.integration)
    emit(args.out, proof)
    print(f'{mangled}: {case_count} native and {case_count} portable executions')


if __name__ == '__main__':
    main()
