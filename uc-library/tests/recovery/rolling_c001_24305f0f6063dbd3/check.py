"""Build and compare a portable registrar call with a fresh ARM observation."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

from native import ARGUMENT_KINDS, digest, observations

TEST = Path(__file__).resolve().parent.relative_to(Path.cwd())
TASK = TEST.name
WORK = Path('temp/recovery-work') / TASK
CPP = Path('uc-library/src/Presonus/Surface/SurfaceRootComponent.cpp')
HEADER = Path('uc-library/include/presonus/surface_panel/ControlHelpers.hpp')
REPLAY = TEST / 'Replay.cpp'
FIXTURE = TEST / 'fixtures.json'
SOURCES = [HEADER, CPP]
CORE = [Path('third_party/ccl-framework/core') / name for name in (
    'portable/corecomponent.h', 'portable/coreparams.h',
    'public/corevector.h', 'system/corethread.h',
)]
FORMAT = ['uc-library/.venv/bin/clang-format', '--style=file',
          '--fallback-style=LLVM']
BUILD = Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01')
PROVIDERS = [BUILD / name for name in (
    'libpresonus_cs18_components.a', 'libpresonus_uc.a', 'upstream-core/sdk/lib/libcorelib.a',
    'upstream-core/sdk/lib/libpresonus_core_allocator.a',
    'private-glibc29-provider/libpresonus_private_glibc29.a',
)]
DOMAIN = (
    'Three calls of the exact original ARM entry with distinct receiver addresses, '
    'initialized argument/working registers, LR, SP and FP, and sentinel memory. '
    'Checks return PC, preserved registers and confinement of data accesses to its '
    '16-byte stack frame. Constructed portable receivers are called with the matching '
    'typed argument cases (ref, uchar, Payload); observe unchanged receiver and applicable '
    'referent bytes.'
)
LIMITATIONS = [
    'Portable non-static, nonvirtual void is a source-port choice. Original table words '
    'equal the verified function entry, but the original C++ return declaration, precise '
    'member/dispatch declaration and table layout remain unresolved.',
    'ARM receiver and pointed-to sentinel blocks are synthetic memory. Portable construction '
    'and teardown exercise only the current source-port lifecycle. Original object layout, '
    'native lifecycle, hardware effects and ARM binary interoperability remain unverified.',
]
COMMANDS = []


def sha(path):
    return digest(Path(path).read_bytes())


def utc():
    return datetime.now(timezone.utc).isoformat()


def run(argv, input_text=None):
    argv = list(map(str, argv))
    started = utc()
    result = subprocess.run(argv, capture_output=True, text=True, check=False, input=input_text)
    COMMANDS.append(dict(argv=argv, start_utc=started, end_utc=utc(),
                         returncode=result.returncode, stdout=result.stdout, stderr=result.stderr))
    result.check_returncode()
    return result.stdout


def formatting():
    run([*FORMAT, '--dry-run', '--Werror', *SOURCES, REPLAY])
    return run([FORMAT[0], '--version']).strip()


def compile_replay(exe, obj):
    exe.parent.mkdir(parents=True, exist_ok=True)
    obj.parent.mkdir(parents=True, exist_ok=True)
    flags = ['/usr/bin/c++', '-std=c++17', '-O2', '-fno-rtti', '-fno-lto',
             '-ffunction-sections', '-fdata-sections', '-Wno-multichar', '-Ulinux',
             '-Iuc-library/include']
    flags += ['-Ithird_party/ccl-framework']
    driver = obj.parent / 'driver.o'
    run([*flags, '-c', CPP, '-o', obj])
    run([*flags, '-c', REPLAY, '-o', driver])
    link = ['/usr/bin/c++', obj, driver, '-Wl,--gc-sections']
    link += ['-Wl,--start-group', *PROVIDERS, '-Wl,--end-group',
             '-pthread', '-ldl', '-lm', '-lz']
    run([*link, '-o', exe])


def symbols(obj, name):
    listing = run(['/usr/bin/nm', '--defined-only', obj])
    matches = [row for row in listing.splitlines() if row.split() and row.split()[-1] == name]
    assert len(matches) == 1, matches
    return matches


def native_check(path):
    start = utc()
    observed = observations()
    assert observed == json.loads(path.read_text()), 'Fresh ELF observations differ from fixture'
    return observed, dict(start_utc=start, end_utc=utc())


def compare(exe, original):
    expected = []
    for case in original['cases']:
        unchanged = {name: int(value['before'] == value['after'])
                     for name, value in case['sentinels'].items()}
        values = [unchanged['receiver']]
        if 'ref' in ARGUMENT_KINDS:
            values.append(unchanged['registrar'])
        if any(kind[0].isupper() for kind in ARGUMENT_KINDS):
            values.append(unchanged.get('pointed', 1))
        
        expected.append(' '.join(map(str, values)))
    inputs = ''.join(' '.join(map(str, case['inputs'])) + '\n'
                     for case in original['cases'])
    actual = run([exe.resolve()], input_text=inputs).splitlines()
    assert actual == expected, (actual, expected)
    return len(actual)


def proof(args, original, native_timing):
    version = formatting()
    name = original['mangled']
    matched = symbols(args.object, name)
    count = compare(args.exe, original)
    sources = {str(path.relative_to('uc-library')): sha(path) for path in SOURCES}
    dependencies = {str(path): sha(path) for path in CORE}
    row = dict(original_elf_sha256=original['elf_sha256'], mangled=name,
               demangled=run(['/usr/bin/c++filt', name]).strip(), firmware=original['firmware'],
               role=original['role'], address=original['address'], size=original['size'],
               section=original['section'], cpp_compiled=True, mangling_namespace_checked=True,
               portable_ready=False, validation_domain=DOMAIN, sources=sources,
               repository_sources=dependencies, declaration_uncertainties=LIMITATIONS,
               original_function_verified=False, hardware_verified=False)
    result = dict(task_id=TASK, worker_session='/root/rolling_c001_surface_control',
                  timestamp_utc=utc(), native=original, native_timing=native_timing,
                  native_invocations=len(original['cases']), portable_case_count=count,
                  cpp_differential_passed=True, compiled_original_mangled_names_matched=True,
                  compiled_symbols=matched, formatting=dict(version=version, passed=True, sources=sources),
                  validation_domain=DOMAIN, limitations=LIMITATIONS, sources=sources,
                  repository_sources=dependencies, proposed_readiness=dict(ready=[], pending=[row]),
                  commands=COMMANDS, fixture_sha256=sha(args.fixtures), producer_sha256=sha(__file__),
                  native_producer_sha256=sha(TEST / 'native.py'), test_sources={str(REPLAY): sha(REPLAY)},
                  binary_bindings={str(path): sha(path) for path in (args.exe, args.object)})
    if args.integration:
        result['integration'] = dict(path=str(args.integration), sha256=sha(args.integration))
    elif PROVIDERS:
        result['local_archive_bindings'] = {str(path): sha(path) for path in PROVIDERS}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(f'{count} original ARM observations matched portable {TASK} replay cases')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['format', 'compile', 'symbols', 'native', 'replay', 'proof', 'local-proof'])
    parser.add_argument('--exe', type=Path, default=WORK / 'replay')
    parser.add_argument('--object', type=Path, default=WORK / 'production.o')
    parser.add_argument('--fixtures', type=Path, default=FIXTURE)
    parser.add_argument('--integration', type=Path)
    parser.add_argument('--out', type=Path, default=WORK / 'proof.json')
    args = parser.parse_args()
    if args.mode == 'format':
        print(formatting())
    elif args.mode == 'compile':
        compile_replay(args.exe, args.object)
        print(json.dumps(COMMANDS, indent=2))
    elif args.mode == 'symbols':
        print(*symbols(args.object, json.loads(args.fixtures.read_text())['mangled']), sep='\n')
    else:
        if args.mode == 'local-proof':
            compile_replay(args.exe, args.object)
        original, timing = native_check(args.fixtures)
        if args.mode == 'native':
            print(f"{len(original['cases'])} original ARM observations reproduced")
        elif args.mode == 'replay':
            print(f'{compare(args.exe, original)} original and portable cases matched')
        else:
            proof(args, original, timing)


if __name__ == '__main__':
    main()
