"""Compile and replay the bounded CascadeHandler::onNetworkItemReleased source port."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess

import elftools
import unicorn
from native import ELF, MANGLED, run as native_run

ROOT = Path(__file__).resolve().parents[4]
TEST = Path(__file__).resolve().parent.relative_to(ROOT)
SOURCE = Path('uc-library/src/Presonus/Surface/CascadeHandler.cpp')
HEADER = Path('uc-library/include/presonus/surface/CascadeHandler.hpp')
DRIVER = TEST / 'Replay.cpp'
FIXTURE = TEST / 'fixtures.json'
FORMAT = [str(ROOT / 'uc-library/.venv/bin/clang-format'), '--style=file',
          '--fallback-style=LLVM', '--dry-run', '--Werror', HEADER, SOURCE, DRIVER]
SCRATCH = Path('temp/recovery-work') / TEST.name
CANONICAL = Path('/home/rs/projects/opencs/ai-line-analysis')
FROZEN = CANONICAL / 'temp/recovery-work/rolling-c001-20261124/packeting/next59/snapshot'
FLAGS = ['g++', '-std=c++20', '-O2', '-fno-rtti', '-Wall', '-Wextra', '-Werror',
         '-Wno-multichar', '-Wno-unused-parameter']
PROVIDERS = [SCRATCH / 'providers' / name for name in (
    'libpresonus_cs18_components.a', 'libcorelib.a', 'libpresonus_core_allocator.a',
    'libpresonus_png.a', 'libpresonus_zlib.a', 'libpresonus_private_glibc29.a',
)]
DEPS = SCRATCH / 'rebound-compile.json'
ROOT_HEADER = Path('uc-library/include/presonus/surface_panel/ControlHelpers.hpp')
ROOT_SNAPSHOT = SCRATCH / 'bound/presonus/surface_panel/ControlHelpers.hpp'
ROOT_SNAPSHOT_SHA256 = '44ae12c6111db0103446836364ddafa60b706d3166f1d8b0392007e650527ab9'


def dependency_paths(makefile):
    return map(Path, makefile.replace(chr(92) + '\n', ' ').split()[1:])


DOMAIN = ('Two exact ARM body executions with different receivers and null or '
          'mapped argument values, restoration of stack and preserved registers, '
          'stack-only writes and no receiver or item memory effects; two direct '
          'portable calls with a root-backed live receiver and null or live '
          'NetworkItem input. The root binding, empty item vector and live '
          'item identity remain unchanged.')
LIMITS = [
    'The portable declaration is a direct nonvirtual void member. Original '
    'return and member/virtual declaration traits, vtable dispatch and thunk '
    'behavior remain unresolved.',
    'Original ARM layout, ABI, native lifecycle and hardware remain unresolved. '
    'The native body executes against sentinel memory and returns without '
    'accessing the receiver or callback argument.',
    'The portable receiver replay binds a canonical SurfaceRootComponent header snapshot and pinned '
    'CCL headers and links the real CS18 production provider. Canonical replay '
    'uses its current generated executable and object.',
]


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('format', 'compile', 'symbols', 'replay'))
    parser.add_argument('--elf', type=Path)
    parser.add_argument('--fixture', type=Path, default=FIXTURE)
    parser.add_argument('--exe', type=Path)
    parser.add_argument('--object', type=Path)
    parser.add_argument('--integration', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if Path.cwd().resolve() != ROOT:
        parser.error(f'expected repository root {ROOT}')
    commands = []

    def invoke(argv):
        argv = list(map(str, argv))
        start = datetime.now(timezone.utc)
        result = subprocess.run(argv, check=False, text=True, capture_output=True)
        commands.append({'argv': argv, 'exit_code': result.returncode,
                         'start_utc': start.isoformat(),
                         'end_utc': datetime.now(timezone.utc).isoformat(),
                         'stdout': result.stdout, 'stderr': result.stderr})
        if result.returncode:
            print(result.stderr, end='')
        result.check_returncode()
        return result.stdout

    if args.mode == 'format':
        invoke(FORMAT)
        return
    canonical_flags = [*FLAGS, '-Iuc-library/include', '-Ithird_party/ccl-framework']
    if args.mode == 'compile':
        assert digest(ROOT_SNAPSHOT) == ROOT_SNAPSHOT_SHA256
        includes = [f'-I{SCRATCH / "bound"}', f'-I{FROZEN / "uc-library/include"}',
                    f'-I{FROZEN / "third_party/ccl-framework"}']
        driver_object = SCRATCH / 'driver.o'
        depfiles = []
        for source, obj in [(SOURCE, args.object), (DRIVER, driver_object)]:
            dep = obj.with_suffix('.d')
            invoke([*FLAGS, *includes, '-MMD', '-MF', dep, '-c', source, '-o', obj])
            depfiles.append(dep)
        dependencies = {}
        for depfile in depfiles:
            for name in dependency_paths(depfile.read_text()):
                if name.is_relative_to(FROZEN):
                    relative = name.relative_to(FROZEN)
                    assert relative != HEADER, 'The compiler used the old CascadeHandler declaration'
                    key = str(relative)
                elif name == ROOT_SNAPSHOT:
                    key = str(ROOT_HEADER)
                else:
                    relative = name.resolve().relative_to(ROOT)
                    assert relative in (HEADER, SOURCE, DRIVER), name
                    key = str(relative)
                binding = {'read_path': str(name), 'sha256': digest(name)}
                if name.is_relative_to(FROZEN) or name == ROOT_SNAPSHOT:
                    binding['canonical_sha256_at_compile'] = digest(CANONICAL / key)
                    if binding['sha256'] != binding['canonical_sha256_at_compile']:
                        print(f'Canonical provider changed after snapshot: {key}')
                dependencies[key] = binding
        assert str(HEADER) in dependencies
        providers = {str(path): digest(path) for path in PROVIDERS}
        invoke(['g++', driver_object, args.object, *PROVIDERS, '-ldl', '-lm', '-o', args.exe])
        receipt = {'commands': commands, 'compiler_dependencies': dependencies,
                   'link_providers': providers, 'object': digest(args.object),
                   'executable': digest(args.exe)}
        DEPS.write_text(json.dumps(receipt, indent=2) + '\n')
        args.out.write_text(json.dumps(commands, indent=2) + '\n')
        return
    nm = invoke(['nm', '--defined-only', args.object])
    symbols = {line.split()[-1] for line in nm.splitlines() if line.split()}
    assert MANGLED in symbols
    if args.mode == 'symbols':
        return

    fixture = json.loads(args.fixture.read_text())
    native_start = datetime.now(timezone.utc)
    assert native_run(args.elf) == fixture
    native_end = datetime.now(timezone.utc)
    lines = invoke([args.exe.resolve()]).splitlines()
    expected = ['1' if case['nonstack_memory_unchanged'] else '0'
                for case in fixture['cases']]
    assert lines == expected
    invoke(FORMAT)
    deps = {HEADER, SOURCE, DRIVER, TEST / 'check.py', TEST / 'native.py',
            FIXTURE}
    core = set()
    if args.integration:
        for unit in (SOURCE, DRIVER):
            for path in dependency_paths(invoke([*canonical_flags, '-MM', unit])):
                if path.is_relative_to('uc-library'):
                    deps.add(path)
                if path.is_relative_to('third_party/ccl-framework/core'):
                    core.add(path)
        receipt = None
    else:
        receipt = json.loads(DEPS.read_text())
        assert receipt['object'] == digest(args.object)
        assert receipt['executable'] == digest(args.exe)
        for relative, binding in receipt['compiler_dependencies'].items():
            read_path = Path(binding['read_path'])
            assert digest(read_path) == binding['sha256']
            path = Path(relative)
            if path.is_relative_to('third_party/ccl-framework/core'):
                assert digest(path) == binding['sha256'], relative
                core.add(path)
        for provider, expected in receipt['link_providers'].items():
            assert digest(provider) == expected, provider
    entry = {
        'original_elf_sha256': ELF, 'mangled': MANGLED, 'domain': DOMAIN,
        'sources': {str(path.relative_to('uc-library')): digest(path)
                    for path in sorted(deps)},
        'repository_sources': {str(path): digest(path) for path in sorted(core)},
        'cpp_compiled': True, 'mangling_namespace_checked': True,
        'portable_ready': False, 'declaration_uncertainties': LIMITS,
    }
    proof = {
        'version': 1, 'task_id': TEST.name, 'created_utc': datetime.now(timezone.utc).isoformat(),
        'proposed_readiness': {'ready': [], 'pending': [entry]},
        'functions': [entry], 'cpp_differential_passed': True,
        'compiled_mangled_names_matched': True, 'cpp_compiled': True,
        'portable_ready': False, 'original_arm_abi_verified': False,
        'hardware_verified': False, 'validation_domain': DOMAIN,
        'elf_input': {'path': str(args.elf), 'sha256': ELF},
        'original_range': {key: value for key, value in fixture.items() if key != 'cases'},
        'native_execution': {'cases': len(fixture['cases']), 'start_utc': native_start.isoformat(),
                             'end_utc': native_end.isoformat(), 'executor': 'Unicorn ARM'},
        'native_fixture_sha256': digest(args.fixture), 'portable_execution': {'cases': len(lines)},
        'executable': {'path': str(args.exe), 'sha256': digest(args.exe)},
        'object': {'path': str(args.object), 'sha256': digest(args.object)},
        'tools': {'compiler': invoke(['g++', '--version']).splitlines()[0],
                  'formatter': invoke([FORMAT[0], '--version']).strip(),
                  'unicorn': unicorn.__version__, 'pyelftools': elftools.__version__},
        'commands': commands, 'limitations': LIMITS,
    }
    if receipt:
        proof['compile_receipt'] = receipt
    if args.integration:
        proof['integration'] = {'path': str(args.integration), 'sha256': digest(args.integration)}
    args.out.write_text(json.dumps(proof, indent=2) + '\n')
    print(f'{TEST.name}: {len(lines)} native and {len(lines)} portable observations passed')


if __name__ == '__main__':
    main()
