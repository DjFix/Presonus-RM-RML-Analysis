"""Compile, check symbols and compare against the original lifetime observations."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess

import elftools
import unicorn
from native import PACKET, run

TEST = Path(__file__).resolve().parent.relative_to(Path.cwd())
SOURCE = Path('uc-library/src/Presonus/Panel/SharedMemoryComm.cpp')
HEADER = Path('uc-library/include/presonus/panel/SharedMemoryComm.hpp')
DRIVER = TEST / 'Replay.cpp'
FIXTURE = TEST / 'fixtures.json'
CHECK_FORMAT = ['uc-library/.venv/bin/clang-format', '--style=file',
                '--fallback-style=LLVM', '--dry-run', '--Werror', HEADER, SOURCE, DRIVER]
FLAGS = ['g++', '-std=c++17', '-O2', '-Wno-multichar', '-Iuc-library/include',
         '-Ithird_party/ccl-framework', '-ffunction-sections', '-fdata-sections']
WRAPS = ('pthread_mutex_init', 'pthread_mutex_destroy', '_ZdlPv', '_ZdlPvm')
DOMAIN = ('Two original receiver sentinels in each of CS18 and RM. Observe exact target '
          'writes, Core lock member arguments and original D0 call to the relocation-bound '
          'delete import. The host uses the real pinned CCL mutex provider and real virtual '
          'deallocation for D0, and checks existing stateless operations and source copying.')
LIMITS = ['Original C1/C2 and D1/D2 ranges are separate native entries. The host compiler '
          'may alias variants. Vptr stores and native offsets are not host layout claims.',
          'Native Core calls terminate at separately identified provider boundaries. Host '
          'replay observes real pthread initialization and destruction from pinned CCL.',
          'Native D0 crosses the ELF-verified delete import and unmaps the live guest '
          'receiver. Native allocator internals, exception paths and hardware are outside scope.']


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('format', 'compile', 'symbols', 'replay'))
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
        objects = [args.object, args.object.with_name('Replay.o')]
        for source, obj in zip((SOURCE, DRIVER), objects):
            invoke([*FLAGS, '-MMD', '-c', source, '-o', obj])
        archive_hashes = {str(path): digest(path) for path in args.archive}
        invoke(['g++', '-Wl,--gc-sections', *objects, *args.archive,
                *['-Wl,--wrap=' + name for name in WRAPS], '-pthread', '-o', args.exe])
        assert archive_hashes == {str(path): digest(path) for path in args.archive}
        args.out.write_text(json.dumps(dict(cwd=str(Path.cwd()), commands=commands,
                                           archives=archive_hashes,
                                           objects={str(obj): digest(obj) for obj in objects},
                                           depfiles={str(obj.with_suffix('.d')): digest(obj.with_suffix('.d'))
                                                     for obj in objects}), indent=2) + '\n')
        return

    originals = [row['original'] for row in json.loads(PACKET.read_text())['originals']]
    mangled = originals[0]['mangled']
    nm = invoke(['nm', '--defined-only', args.object])
    assert mangled in {line.split()[-1] for line in nm.splitlines() if line.split()}
    if args.mode == 'symbols':
        return
    fixture = json.loads(FIXTURE.read_text())
    native_start = datetime.now(timezone.utc)
    assert run() == fixture
    native_end = datetime.now(timezone.utc)
    variant = mangled[-4:-2]
    lines = invoke([args.exe.resolve(), variant]).splitlines()
    assert lines == [' '.join(call[0] for call in case['calls'])
                     for target in fixture for case in target['cases']]
    invoke(CHECK_FORMAT)
    sources = {SOURCE, HEADER, DRIVER, FIXTURE, TEST / 'check.py', TEST / 'native.py'}
    core = set()
    for unit in (SOURCE, DRIVER):
        raw = invoke([*FLAGS, '-MM', unit]).replace(chr(92) + '\n', ' ')
        sources.update(Path(path) for path in raw.split()[1:] if path.startswith('uc-library/'))
        core.update(Path(path) for path in raw.split()[1:] if path.startswith('third_party/'))
    core.update(Path(path) for path in
                ('third_party/ccl-framework/core/system/corethread.h',
                 'third_party/ccl-framework/core/platform/shared/posix/corethread.posix.cpp',
                 'third_party/ccl-framework/core/platform/shared/posix/corethread.posix.h'))
    entries = [
        dict(original_elf_sha256=row['elf'], mangled=mangled, domain=DOMAIN,
             sources={str(path.relative_to('uc-library')): digest(path) for path in sorted(sources)},
             repository_sources={str(path): digest(path) for path in sorted(core)},
             cpp_compiled=True, mangling_namespace_checked=True, portable_ready=True)
        for row in originals
    ]
    ranges = [{key: value for key, value in target.items() if key != 'cases'} for target in fixture]
    proof = dict(version=1, task_id=TEST.name, proposed_readiness=dict(ready=entries, pending=[]),
                 functions=entries, cpp_differential_passed=True, compiled_mangled_names_matched=True,
                 cpp_compiled=True, portable_ready=True, original_arm_abi_verified=False,
                 hardware_verified=False, validation_domain=DOMAIN, limitations=LIMITS,
                 original_ranges=ranges,
                 native_execution=dict(cases=len(lines), executor='Unicorn ARM',
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
