"""Build or replay one exact DAWChannel task on Linux."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess

import elftools
import unicorn
from native import FOLDERS, ID, PROVIDER_MACHINE, SELECTED, method, run

LIB = Path('uc-library')
CORE = Path('third_party/ccl-framework/core')
TEST = Path(__file__).resolve().parent.relative_to(Path.cwd())
HEADER = LIB / 'include/presonus/DAWChannel.hpp'
SOURCE = LIB / 'src/Presonus/DAWChannel.cpp'
PROVIDERS = (
    LIB / 'src/Presonus/UC/ClientComponent.cpp',
    LIB / 'src/Presonus/DAWDeviceFolder.cpp',
    LIB / 'src/Presonus/DAWDeviceSlot.cpp',
)
DRIVER = TEST / 'Replay.cpp'
FORMATTER = LIB / '.venv/bin/clang-format'
FORMAT = [FORMATTER, '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror',
          HEADER, SOURCE, DRIVER]
FLAGS = ['g++', '-std=c++17', '-O2', '-Ulinux', '-DNDEBUG=1', '-Wno-multichar',
         '-Iuc-library/include', '-Ithird_party/ccl-framework']
FOLDER_DOMAIN = ('Both firmware roles with absent child, genuine same-name foreign child, '
                 'genuine differently named Folder and a genuine same-name Folder. Compare '
                 'the original lookup literal, exact native cast target and receiver, and portable '
                 'identity/null using real CCL lookup and accepted DAWDeviceFolder.')
DOMAINS = {
    **{name: FOLDER_DOMAIN + f' Lookup name {literal!r}.' for name, literal in FOLDERS.items()},
    SELECTED: ('Both native roles with no selected cache and genuine NumericParam negative, '
               'negative zero, positive zero and positive float values. Compare exact native '
               'provider reads and boolean result with pinned CCL NumericParam in portable replay.'),
    ID: ('Both native roles with missing, empty, nonempty and overlength ID cache. Compare '
         'null, initialized and already-initialized shared-buffer paths, exact virtual formatter '
         'receiver and size, retained address across channel instances and truncation to 63 '
         'characters. Portable replay uses pinned CCL StringParam.'),
}
LIMITATIONS = [
    'Host replay uses a source port and genuine pinned Core object layout. Original ARM ABI, '
    'hardware interoperability and paths beyond the named fixture domain are unverified.',
    'Portable test subclasses supply cache state. No initialization or ownership claim is made '
    'for unrecovered production cache population.',
]
FOLDER_UNCERTAINTY = (
    'Native lookup and cast establish nullable Folder identity. Original return spelling '
    'and pointee qualification are unresolved. The portable declaration uses DAWDeviceFolder*.')
SELECTED_UNCERTAINTY = (
    'Native r0 is 0 or 1. The exact original boolean or integral return declaration is '
    'unresolved. The portable declaration uses bool.')
ID_UNCERTAINTY = ('Original pointer const qualification and ownership are unresolved. '
                  'Portable getID returns a const view into one shared 64-byte buffer.')
RETURN_DECLARATIONS = {
    **dict.fromkeys(FOLDERS, FOLDER_UNCERTAINTY),
    SELECTED: SELECTED_UNCERTAINTY,
    ID: ID_UNCERTAINTY,
}
DECLARATION_EVIDENCE_NEEDED = (
    'Resolve from an independently identified original declaration, such as matching '
    'source, DWARF or a verified typed interface contract.')
ID_BOUNDARY = ('The native ID oracle intercepts relocation-verified single-threaded C++ '
               'guard calls and the actual virtual string formatter call, enforcing the observed '
               'address and size. Pinned CCL StringParam performs real formatting on the host. '
               'Simultaneous buffer writes are outside scope.')


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
    variant = method(mangled)
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
            observed = invoke([args.exe.resolve(), *case['input']]).removesuffix('\n')
            assert observed == case['portable']
            case_count += 1
    invoke(FORMAT)
    sources = {HEADER, SOURCE, *PROVIDERS, DRIVER, args.fixture, TEST / 'check.py',
               TEST / 'native.py', PROVIDER_MACHINE}
    core = {CORE / 'portable/corecomponent.cpp', CORE / 'portable/coreparams.cpp',
            CORE / 'public/corestringtraits.h'}
    for unit in (SOURCE, *PROVIDERS, DRIVER):
        raw = invoke([*FLAGS, '-MM', unit]).replace(chr(92) + '\n', ' ')
        sources.update(Path(path) for path in raw.split()[1:] if path.startswith('uc-library/'))
        core.update(Path(path) for path in raw.split()[1:] if path.startswith('third_party/'))
    declaration = [RETURN_DECLARATIONS[variant], DECLARATION_EVIDENCE_NEEDED]
    limits = LIMITATIONS + declaration + ([ID_BOUNDARY] if variant == ID else [])
    records = []
    for row in originals:
        record = dict(original_elf_sha256=row['elf'], mangled=mangled,
                      original_address=row['address'], domain=DOMAINS[variant],
                      sources={str(p.relative_to(LIB)): digest(p) for p in sorted(sources)},
                      repository_sources={str(p): digest(p) for p in sorted(core)},
                      cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
                      declaration_uncertainties=declaration)
        records.append(record)
    proof = dict(
        version=1, task_id=packet['task']['id'], cpp_compiled=True, portable_ready=False,
        cpp_differential_passed=True, compiled_mangled_names_matched=True,
        original_arm_abi_verified=False, hardware_verified=False,
        validation_domain=DOMAINS[variant], limitations=limits, functions=records,
        proposed_readiness=dict(ready=[], pending=records),
        inputs=[binding(p) for p in (args.packet, args.fixture, TEST / 'native.py', TEST / 'check.py', PROVIDER_MACHINE)],
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
