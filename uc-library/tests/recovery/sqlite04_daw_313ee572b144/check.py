"""Build or replay one exact DAWChannel task on Linux."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess

import elftools
import unicorn
from native import run

LIB = Path('uc-library')
CORE = Path('third_party/ccl-framework/core')
TEST = Path(__file__).resolve().parent.relative_to(Path.cwd())
HEADER = LIB / 'include/presonus/DAWChannel.hpp'
SOURCE = LIB / 'src/Presonus/DAWChannel.cpp'
BASE = LIB / 'src/Presonus/UC/ClientComponent.cpp'
DRIVER = TEST / 'Replay.cpp'
FORMATTER = LIB / '.venv/bin/clang-format'
FORMAT = [FORMATTER, '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror',
          HEADER, SOURCE, DRIVER]
FLAGS = ['g++', '-std=c++17', '-O2', '-Ulinux', '-DNDEBUG=1', '-Wno-multichar',
         '-Iuc-library/include', '-Ithird_party/ccl-framework']
PREFIX = '_ZN8Presonus10DAWChannel'
DOMAINS = {
    'C1': 'Exact C1 of each firmware from two nonzero storage prefills. Match empty name, '
          'genuine component construction, concrete type identity and the three null caches.',
    'C2': 'Exact C2 of each firmware from two nonzero storage prefills. Match empty name, '
          'genuine component construction, concrete type identity and the three null caches.',
    'D0': 'Exact D0 of each firmware with distinct receivers and concrete initial virtual '
          'address points. Observe transition to the ClientComponent address points, Core '
          'destruction boundary and one relocation-verified unsized receiver delete. '
          'Pinned Core replay observes owned child and parameter destruction before real delete.',
    'D1': 'Exact D1 of each firmware with distinct receivers and concrete initial virtual '
          'address points. Observe transition to the ClientComponent address points, Core '
          'destruction boundary and retained receiver storage. Pinned Core replay observes '
          'owned child and parameter destruction while retaining receiver storage.',
    'cast': 'Both native roles and two receiver prefills at the three recognized IDs, their '
            'nearest integer neighbors, zero, negative one and signed extrema. Compare '
            'receiver identity or null.'
}
LIMITATIONS = [
    'Lifecycle native evidence records exact ARM address-point transitions. Host RTTI and '
    'construction checks use portable CCL layout and establish no original ARM ABI.',
    'Native UC ClientComponent construction executes real firmware instructions. Calls '
    'at native Core and allocator boundaries are identified and intercepted. Real '
    'provider construction and owner cleanup are exercised in the pinned host CCL.',
    'Native allocator internals, exceptional lifetimes, remaining virtual slots '
    'and device behavior are outside scope.',
    'Portable C1/C2 and D1/D2 can share compiled entry addresses; native assigned ranges '
    'are checked independently.'
]
CAST_UNCERTAINTY = 'Firmware yields pointer identity in r0. Exact original return spelling is unencoded.'


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
    suffix = mangled.removeprefix(PREFIX)
    variant = 'cast' if suffix == '6castToEi' else suffix[:2]
    if args.mode == 'format':
        invoke(FORMAT)
        return
    if args.mode == 'compile':
        args.object.parent.mkdir(parents=True, exist_ok=True)
        assert len(args.archive) == 2
        archives = [binding(path) for path in args.archive]
        units = []
        for source, obj, kind in (
            (SOURCE, args.object, 'local_production'),
            (BASE, args.object.with_name('ClientComponent.o'), 'provider_application_dependency'),
            (DRIVER, args.object.with_name('Replay.o'), 'local_replay'),
        ):
            invoke([*FLAGS, '-MMD', '-c', source, '-o', obj])
            units.append(dict(kind=kind, role='common', source=str(source), directory='.',
                              object=binding(obj), depfile=binding(obj.with_suffix('.d'))))
        invoke(['g++', *[unit['object']['path'] for unit in units], *args.archive,
                '-Wl,--wrap=_ZdlPv', '-Wl,--wrap=_ZdlPvm', '-pthread', '-o', args.exe])
        assert archives == [binding(path) for path in args.archive]
        emit(args.out, dict(version=1, commands=commands, archives=archives,
                            units=units[:1] + units[2:], extra_units=units[1:2],
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
            value = case['prefill'] if variant.startswith('C') else case['input_id']
            observed = invoke([args.exe.resolve(), variant, value]).strip()
            assert observed == case['portable']
            case_count += 1
    invoke(FORMAT)
    sources = {HEADER, SOURCE, BASE, DRIVER, args.fixture, TEST / 'check.py', TEST / 'native.py'}
    core = {CORE / 'portable/corecomponent.cpp', CORE / 'portable/coreparams.cpp'}
    for unit in (SOURCE, BASE, DRIVER):
        raw = invoke([*FLAGS, '-MM', unit]).replace(chr(92) + '\n', ' ')
        sources.update(Path(path) for path in raw.split()[1:] if path.startswith('uc-library/'))
        core.update(Path(path) for path in raw.split()[1:] if path.startswith('third_party/'))
    ready = variant != 'cast'
    limits = LIMITATIONS + ([] if ready else [CAST_UNCERTAINTY])
    records = []
    for row in originals:
        record = dict(original_elf_sha256=row['elf'], mangled=mangled,
                      original_address=row['address'], domain=DOMAINS[variant],
                      sources={str(p.relative_to(LIB)): digest(p) for p in sorted(sources)},
                      repository_sources={str(p): digest(p) for p in sorted(core)},
                      cpp_compiled=True, mangling_namespace_checked=True, portable_ready=ready)
        if not ready:
            record['declaration_uncertainties'] = [CAST_UNCERTAINTY]
        records.append(record)
    proof = dict(
        version=1, task_id=packet['task']['id'], cpp_compiled=True, portable_ready=ready,
        cpp_differential_passed=True, compiled_mangled_names_matched=True,
        original_arm_abi_verified=False, hardware_verified=False,
        validation_domain=DOMAINS[variant], limitations=limits, functions=records,
        proposed_readiness=dict(ready=records if ready else [], pending=[] if ready else records),
        inputs=[binding(p) for p in (args.packet, args.fixture, TEST / 'native.py', TEST / 'check.py')],
        native_execution=dict(start_utc=original_start.isoformat(), end_utc=original_end.isoformat(),
                              cases=case_count,
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
