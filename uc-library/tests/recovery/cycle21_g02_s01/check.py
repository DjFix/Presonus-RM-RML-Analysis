"""Compile the SurfaceRoot replay or compare it against recorded ARM observations."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import time

BASE = Path('uc-library/tests/recovery/cycle21_g02_s01')
SOURCE = Path('uc-library/src/Presonus/Surface/SurfaceRootComponent.cpp')
HEADER = Path('uc-library/include/presonus/surface_panel/ControlHelpers.hpp')
BUILD = Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01')
CORE = Path('third_party/ccl-framework/core')
PIN = 'e8cbdea4a4a20e15111f5a690798a259c0374b31'
FORMATTER = 'uc-library/.venv/bin/clang-format'
WRAPS = [
    '_ZNK4Core8Portable9Component17getParameterByTagEi',
    '_ZNK8Presonus7Surface14PanelRegistrar17getParameterByTagEi',
    '_ZN4Core8Portable9Parameter11addObserverEPNS0_14IParamObserverE',
    '_ZN4Core8Portable9Parameter14removeObserverEPNS0_14IParamObserverE',
    '_ZN8Presonus7Surface14PanelRegistrar7runTestENS1_8TestModeEb',
    '_ZN8Presonus7Surface14PanelRegistrar29requestUpdatedFaderParametersEv',
    '_ZN4Core11DebugPrintfEPKcz',
]
DOMAINS = {
    's01': 'Select main-screen tag 34 with edit and then attach the exact root observer.',
    's02': 'Both launch flags, tag 33 write and observer order, and two fader request messages through the canonical offline panel port.',
    's03': 'Both touchscreen-active values, termination observer effects, optional local state clearing and tag 2 page selection.',
    's04': 'Both launch flags, tag 32 and progress observer ordering, real CCL progress reset and exact offline calibration start bytes.',
    's05': 'Exact mapping name with absence, wrong-type child and correctly bound typed child. Native cast outcome modeled at the imported ABI boundary; portable tree and pointer matching execute independently.',
    'r06': 'Exact networksetup name with absence, wrong-type child and correctly bound typed child. Native cast outcome modeled at the imported ABI boundary; portable tree and pointer matching execute independently without network operations.',
    's07': 'Zero, signed fractions inside truncation-to-zero and signed values truncating away from zero; exact local termination and active state effects.',
    's08': 'Zero, signed fractions inside truncation-to-zero and signed values truncating away from zero; remove only the tag 33 observer on the zero branch.',
    's09': 'Signed zero-truncating and nonzero-truncating values with and without a registrar. Observe both observer removals and offline calibration stop messages.',
    's10': 'Signed finite values, 7, 7.75, 8 and 9. Exact tag 31 selection and ordered observer attachment only above the truncated threshold.',
}
DEPENDS = {
    's02': ['src/Presonus/Surface/PanelRegistrarFaderCommands.cpp'],
    's03': ['src/Presonus/Surface/PanelRegistrarTests.cpp'],
    's04': ['src/Presonus/Surface/PanelRegistrarTests.cpp'],
    's05': ['include/presonus/surface/MappingComponent.hpp',
            'src/Presonus/Surface/MappingComponent.cpp'],
    'r06': ['include/presonus/surface/NetworkSetupComponent.hpp',
            'src/Presonus/Surface/NetworkSetupComponent.cpp'],
    's07': ['src/Presonus/Surface/PanelRegistrarTests.cpp'],
    's09': ['src/Presonus/Surface/PanelRegistrarTests.cpp'],
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(argv):
    args = [str(arg) for arg in argv]
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    before = time.monotonic()
    result = subprocess.run(args, check=True, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return {'argv': args, 'started_utc': started, 'seconds': time.monotonic() - before,
            'returncode': result.returncode, 'stdout': result.stdout}


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n')


def compile_replay(args):
    database = BUILD / 'compile_commands.json'
    commands = json.loads(database.read_text())
    canonical = next(row for row in commands if row['file'].endswith('/' + str(SOURCE)))
    flags = shlex.split(canonical['command'])
    flags = flags[:flags.index('-o')]
    flags = [f'-I{SOURCE.parts[0]}/include' if option.endswith('/uc-library/include')
             else option for option in flags]
    args.object.parent.mkdir(parents=True, exist_ok=True)
    args.exe.parent.mkdir(parents=True, exist_ok=True)
    sdk = BUILD / 'upstream-core/sdk/lib'
    link = [*flags, '-std=c++20', '-fno-rtti', BASE / 'Replay.cpp', args.object,
            *[f'-Wl,--wrap={name}' for name in WRAPS],
            '-Wl,--start-group', BUILD / 'libpresonus_cs18_components.a',
            BUILD / 'libpresonus_uc.a', sdk / 'libcorelib.a',
            sdk / 'libpresonus_core_allocator.a', '-Wl,--end-group',
            BUILD / 'private-glibc29-provider/libpresonus_private_glibc29.a',
            '/usr/lib/x86_64-linux-gnu/libpng16.so.16', '-lz', '-lssl', '-lcrypto',
            BUILD.parent / 'external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so',
            '-ldl', '-o', args.exe]
    checks = [run([*flags, '-c', SOURCE, '-o', args.object]), run(link)]
    dump(args.out, {'compile_database_sha256': digest(database), 'checks': checks,
                    'object_sha256': digest(args.object), 'exe_sha256': digest(args.exe),
                    'link_inputs': {str(path): digest(path) for path in link
                                    if isinstance(path, Path) and path.suffix == '.a'}})


def symbols(obj, target):
    receipt = run(['nm', '--defined-only', obj])
    hits = [line for line in receipt['stdout'].splitlines()
            if line.split()[-1:] == [target]]
    if len(hits) != 1 or hits[0].split()[1] != 'T':
        raise ValueError(f'Expected one globally defined {target} in {obj}')
    receipt['stdout'] = hits[0]
    return receipt


def observed(exe, fixture, task):
    rows = []
    for case in fixture['rows']:
        value, registrar, mode = case['input']
        result = run([exe.resolve(), task, value, int(registrar), mode])
        lines = result['stdout'].splitlines()
        events = [line.removeprefix('EVENT ') for line in lines if line.startswith('EVENT ')]
        expected = case['outcome']
        # A modeled ARM ABI cast is compared to the host's actual typed result.
        expected_events = [event for event in expected['events'] if not event.startswith('cast:')]
        actual = {'events': events}
        if expected_events != events:
            raise ValueError(f'{case["input"]}: expected {expected_events}, got {events}')
        for label in ('found', 'active'):
            if label not in expected:
                continue
            prefix = label.upper() + ' '
            actual[label] = [line for line in lines if line.startswith(prefix)] == [prefix + '1']
            if [line for line in lines if line.startswith(prefix)] != [prefix + str(int(expected[label]))]:
                raise ValueError(f'{case["input"]}: wrong {label} result')
        rows.append({'input': case['input'], 'outcome': actual, 'command': result})
    return rows


def proof(args):
    fixture = json.loads(args.fixtures.read_text())
    task = fixture['task']
    if args.task != 'cycle21_g02_' + task:
        raise ValueError('Mismatched fixture task')
    fingerprints = {json.dumps(row['range'], sort_keys=True) for row in fixture['rows']}
    if len(fingerprints) != 1:
        raise ValueError('Fixture ranges do not identify one exact original')
    identity = fixture['rows'][0]['range']
    original = {'original_elf_sha256': fixture['elf_sha256'], 'mangled': identity['mangled']}
    format_result = run([FORMATTER, '--style=file', '--fallback-style=LLVM',
                         '--dry-run', '--Werror', SOURCE, HEADER, BASE / 'Replay.cpp'])
    fmt_version = run([FORMATTER, '--version'])['stdout'].strip()
    symbol_result = symbols(args.object, identity['mangled'])
    results = observed(args.exe, fixture, task)
    integration_sha256 = digest(args.integration)
    integration = json.loads(args.integration.read_text())
    if integration.get('ctest_passed') is not True:
        raise ValueError('Expected an existing integration context receipt')
    sources = dict((str(path.relative_to('uc-library')), digest(path))
                   for path in (SOURCE, HEADER))
    sources.update((path, digest(Path('uc-library') / path))
                   for path in DEPENDS.get(task, []))
    repository_sources = {str(path): digest(path) for path in (
        CORE / 'portable/corecomponent.h', CORE / 'portable/corecomponent.cpp',
        CORE / 'portable/coreparams.h', CORE / 'portable/coreparams.cpp',
    )}
    uncertainty = ('Original static return declaration and pointee const qualification remain unresolved.'
                   if task in ('s05', 'r06') else
                   'Portable void declaration; ordinary original return type is unresolved.')
    limitations = [uncertainty, 'Original class layout, ARM ABI and hardware behavior remain unverified.',
                   fixture['boundary']]
    if task in ('s02', 's04'):
        limitations.append('A live registrar is required on the launch path.')
    if task in ('s07', 's08', 's09', 's10'):
        limitations.append('The replay uses finite callback values within the signed conversion domain.')
    row = dict(original, cpp_compiled=True, mangling_namespace_checked=True,
               portable_ready=False, sources=sources, repository_sources=repository_sources,
               domain=DOMAINS[task], declaration_uncertainties=[uncertainty])
    dump(args.out, {
        'version': 1, 'task_id': args.task, 'behavior_verified': True,
        'cpp_differential_passed': True, 'compiled_original_mangled_names_matched': True,
        'mangling_namespace_checked': True, 'portable_ready': False,
        'hardware_verified': False, 'original_arm_abi_verified': False,
        'native_range': identity, 'validation_domain': DOMAINS[task],
        'native_execution_count': len(results), 'portable_execution_count': len(results),
        'ccl_pinned_commit': PIN, 'format_check_passed': True, 'format_version': fmt_version,
        'format': format_result, 'symbols': symbol_result,
        'original': original, 'functions': [row], 'mangled_names': [identity['mangled']],
        'proposed_readiness': {'ready': [], 'pending': [row]}, 'limitations': limitations,
        'fixtures': {'path': str(args.fixtures), 'sha256': digest(args.fixtures)},
        'oracle_producer': {'path': str(BASE / 'native.py'), 'sha256': digest(BASE / 'native.py'),
                            'unicorn': fixture['unicorn']},
        'checker': {'path': str(BASE / 'check.py'), 'sha256': digest(BASE / 'check.py')},
        'portable_producer': {'path': str(BASE / 'Replay.cpp'), 'sha256': digest(BASE / 'Replay.cpp')},
        'object': {'path': str(args.object), 'sha256': digest(args.object)},
        'executable': {'path': str(args.exe), 'sha256': digest(args.exe)},
        'integration': {'path': str(args.integration), 'sha256': integration_sha256,
                        'scope': 'Point-in-time integration context. Root owns full current integration.'},
        'observations': results,
    })
    print(f'{args.task}: {len(results)} native/portable cases passed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest='mode', required=True)
    build = modes.add_parser('compile')
    replay = modes.add_parser('proof')
    symbol_check = modes.add_parser('symbols')
    for command in (build, replay, symbol_check):
        command.add_argument('--object', type=Path, required=True)
    for command in (build, replay):
        command.add_argument('--exe', type=Path, required=True)
        command.add_argument('--out', type=Path, required=True)
    replay.add_argument('--integration', type=Path, required=True)
    replay.add_argument('--fixtures', type=Path, required=True)
    replay.add_argument('--task', required=True)
    symbol_check.add_argument('--mangled', required=True)
    args = parser.parse_args()
    try:
        if args.mode == 'compile':
            compile_replay(args)
        elif args.mode == 'symbols':
            print(symbols(args.object, args.mangled)['stdout'])
        else:
            proof(args)
    except subprocess.CalledProcessError as error:
        parser.exit(error.returncode, str(error) + '\n' + (error.stdout or ''))


if __name__ == '__main__':
    main()
