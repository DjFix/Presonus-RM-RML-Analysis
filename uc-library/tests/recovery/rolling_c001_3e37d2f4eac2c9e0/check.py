"""Compile and replay the bounded SPIControlGroup::sort source port."""
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
SOURCE = Path('uc-library/src/Presonus/Panel/SPIControlGroup.cpp')
HEADER = Path('uc-library/include/presonus/panel/SPIControlGroup.hpp')
GROUP = Path('uc-library/src/surface_panel/ControlGroup.cpp')
FROZEN = Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling-c001-20261124/packeting/reserve01/snapshot')
FROZEN_GROUP = FROZEN / GROUP
GROUP_HASH = '56c99495885aeeecf35579bbdcd359345d38ca5063017a03ef159e88185cd612'
DRIVER = TEST / 'Replay.cpp'
FIXTURE = TEST / 'fixtures.json'
FORMAT = [str(ROOT / 'uc-library/.venv/bin/clang-format'), '--style=file',
          '--fallback-style=LLVM', '--dry-run', '--Werror', HEADER, SOURCE, DRIVER]
FLAGS = ['g++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
         '-Iuc-library/include', '-Ithird_party/ccl-framework', '-Wno-multichar', '-Wno-unused-parameter']
DOMAIN = ('Two ARM receiver/pointed-to sentinel pairs with register, frame, stack '
          'and write checks; direct portable calls on constructed ControlGroup-backed '
          'SPI receivers with both dirty states, one stored null slot, owned group '
          'storage, a captured transport and unchanged visible buffers and metadata.')
LIMITS = ['Original return declaration and member/virtual declaration traits remain '
          'unresolved. The portable declaration is a direct nonvirtual void member; '
          'the bound vtable word is evidence of a reference, without exercised dispatch.',
          'Original ARM layout and ABI, constructor/destructor equivalence, hardware '
          'and device transport remain unresolved. Native execution uses sentinel '
          'memory and executes only the four exact original sort instructions.']


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
    group = GROUP if args.integration else FROZEN_GROUP
    if args.mode in ('compile', 'replay'):
        assert digest(group) == GROUP_HASH, f'ControlGroup provider mismatch: {group}'
    if args.mode == 'compile':
        invoke([*FLAGS, '-c', SOURCE, '-o', args.object])
        # The exact provider also contains unrelated reset methods. Their
        # sections are outside this sort-only local link boundary.
        invoke([*FLAGS, '-ffunction-sections', '-fdata-sections', DRIVER,
                group, args.object, '-Wl,--gc-sections', '-o', args.exe])
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
    for unit in (SOURCE, group, DRIVER):
        raw = invoke([*FLAGS, '-MM', unit])
        for name in raw.replace('\\\n', ' ').split()[1:]:
            if Path(name) == group:
                continue
            if unit == group and name.startswith(('uc-library/', 'third_party/ccl-framework/')):
                frozen_header = FROZEN / name
                if frozen_header.is_file():
                    assert digest(name) == digest(frozen_header), f'Frozen dependency mismatch: {name}'
                elif name.startswith('uc-library/'):
                    raise RuntimeError(f'Missing frozen application header: {name}')
            if name.startswith('uc-library/'):
                deps.add(Path(name))
            if name.startswith('third_party/ccl-framework/core/'):
                core.add(Path(name))
    entry = {
        'original_elf_sha256': ELF, 'mangled': MANGLED, 'domain': DOMAIN,
        'sources': {str(path.relative_to('uc-library')): digest(path)
                    for path in sorted(deps)},
        'repository_sources': {str(path): digest(path) for path in sorted(core)},
        'cpp_compiled': True, 'mangling_namespace_checked': True,
        'portable_ready': False, 'declaration_uncertainties': LIMITS,
    }
    if args.integration:
        entry['sources'][str(GROUP.relative_to('uc-library'))] = GROUP_HASH
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
        'control_group_provider': {'source': str(group), 'canonical_path': str(GROUP),
                                   'sha256': GROUP_HASH,
                                   'local_link_mode': 'unrelated sections discarded'},
    }
    if args.integration:
        proof['integration'] = {'path': str(args.integration), 'sha256': digest(args.integration)}
    args.out.write_text(json.dumps(proof, indent=2) + '\n')
    print(f'{TEST.name}: {len(lines)} native and {len(lines)} portable observations passed')


if __name__ == '__main__':
    main()
