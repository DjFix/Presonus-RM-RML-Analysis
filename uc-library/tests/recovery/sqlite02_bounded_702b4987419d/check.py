"""Compile, check symbols and compare against the original getter observations."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess

import elftools
import unicorn
from native import MANGLED, run

TEST = Path(__file__).resolve().parent.relative_to(Path.cwd())
SOURCE = Path('uc-library/src/Presonus/Mixer/SendOutputComponent.cpp')
HEADER = Path('uc-library/include/presonus/mixer/SendOutputComponent.hpp')
PROVIDER = SOURCE.with_name('OutputComponent.cpp')
DRIVER = TEST / 'Replay.cpp'
FIXTURE = TEST / 'fixtures.json'
CHECK_FORMAT = ['uc-library/.venv/bin/clang-format', '--style=file',
                '--fallback-style=LLVM', '--dry-run', '--Werror', HEADER, SOURCE, DRIVER]
FLAGS = ['g++', '-std=c++17', '-O2', '-Wno-multichar', '-Iuc-library/include',
         '-Ithird_party/ccl-framework', '-ffunction-sections', '-fdata-sections']
DOMAIN = ('Exact uint32 return bits for six raw words on each of two receivers, '
          'native full instruction and memory traces, host receiver isolation and '
          'one existing Output delegation regression using a real CCL parameter.')
LIMITS = ['The original signedness and ordinary return declaration remain unresolved. '
          'The portable member returns the observed word as uint32_t.',
          'The host state binding models the observed read. Object layout, ARM ABI '
          'and hardware behavior remain unverified.']


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('format', 'compile', 'symbols', 'replay'))
    parser.add_argument('--elf', type=Path)
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
            print(result.stderr, end='')
        result.check_returncode()
        return result.stdout

    if args.mode == 'format':
        invoke(CHECK_FORMAT)
        return
    if args.mode == 'compile':
        args.object.parent.mkdir(parents=True, exist_ok=True)
        objects = [args.object, args.object.with_name('OutputComponent.o'),
                   args.object.with_name('Replay.o')]
        for source, obj in zip((SOURCE, PROVIDER, DRIVER), objects):
            invoke([*FLAGS, '-MMD', '-c', source, '-o', obj])
        archive_hashes = {str(path): digest(path) for path in args.archive}
        invoke(['g++', '-Wl,--gc-sections', *objects, *args.archive,
                '-pthread', '-o', args.exe])
        assert archive_hashes == {str(path): digest(path) for path in args.archive}
        args.out.write_text(json.dumps(dict(cwd=str(Path.cwd()), commands=commands,
                                           archives=archive_hashes,
                                           objects={str(obj): digest(obj) for obj in objects},
                                           depfiles={str(obj.with_suffix('.d')): digest(obj.with_suffix('.d'))
                                                     for obj in objects}), indent=2) + '\n')
        return

    nm = invoke(['nm', '--defined-only', args.object])
    assert MANGLED in {line.split()[-1] for line in nm.splitlines() if line.split()}
    if args.mode == 'symbols':
        return
    fixture = json.loads(FIXTURE.read_text())
    native_start = datetime.now(timezone.utc)
    assert run(args.elf) == fixture
    native_end = datetime.now(timezone.utc)
    words = [str(case['word']) for case in fixture['cases']]
    lines = invoke([args.exe.resolve(), *words]).splitlines()
    assert lines == [str(case['r0']) for case in fixture['cases']]
    invoke(CHECK_FORMAT)
    sources = {SOURCE, HEADER, PROVIDER, DRIVER, FIXTURE, TEST / 'check.py', TEST / 'native.py'}
    core = set()
    for unit in (SOURCE, PROVIDER, DRIVER):
        raw = invoke([*FLAGS, '-MM', unit]).replace(chr(92) + '\n', ' ')
        sources.update(Path(path) for path in raw.split()[1:] if path.startswith('uc-library/'))
        core.update(Path(path) for path in raw.split()[1:] if path.startswith('third_party/'))
    core.add(Path('third_party/ccl-framework/core/portable/coreparams.cpp'))
    entry = dict(original_elf_sha256=fixture['elf_sha256'], mangled=MANGLED, domain=DOMAIN,
                 sources={str(path.relative_to('uc-library')): digest(path) for path in sorted(sources)},
                 repository_sources={str(path): digest(path) for path in sorted(core)},
                 cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
                 declaration_uncertainties=LIMITS)
    proof = dict(version=1, task_id=TEST.name, proposed_readiness=dict(ready=[], pending=[entry]),
                 functions=[entry], cpp_differential_passed=True, compiled_mangled_names_matched=True,
                 cpp_compiled=True, portable_ready=False, original_arm_abi_verified=False,
                 hardware_verified=False, validation_domain=DOMAIN, limitations=LIMITS,
                 elf_input=dict(path=str(args.elf), sha256=fixture['elf_sha256']),
                 original_range={key: value for key, value in fixture.items() if key != 'cases'},
                 native_execution=dict(cases=len(words), executor='Unicorn ARM',
                                       start_utc=native_start.isoformat(), end_utc=native_end.isoformat()),
                 native_fixture_sha256=digest(FIXTURE), portable_execution=dict(cases=len(lines)),
                 executable=dict(path=str(args.exe), sha256=digest(args.exe)),
                 object=dict(path=str(args.object), sha256=digest(args.object)),
                 tools=dict(compiler=invoke(['g++', '--version']).splitlines()[0],
                            formatter=invoke([CHECK_FORMAT[0], '--version']).strip(),
                            unicorn=unicorn.__version__, pyelftools=elftools.__version__),
                 commands=commands)
    if args.integration:
        proof['integration'] = dict(path=str(args.integration), sha256=digest(args.integration))
    args.out.write_text(json.dumps(proof, indent=2) + '\n')
    print(f'{TEST.name}: {len(lines)} native and portable observations passed')


if __name__ == '__main__':
    main()
