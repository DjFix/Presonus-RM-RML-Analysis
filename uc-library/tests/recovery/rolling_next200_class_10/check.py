"""Compile or replay the bounded direct NetworkSetupComponent callback on VM101."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shlex
import subprocess
import sys

from native import ELF_SHA256, MANGLED, digest

CANONICAL = Path('/home/rs/projects/opencs/ai-line-analysis')
BUILD = CANONICAL / 'temp/core-upstream/root-integration-01'
SCRATCH = Path('temp/recovery-work/rolling_next200_class_10-local')
TEST = Path('uc-library/tests/recovery/rolling_next200_class_10')
HEADER = Path('uc-library/include/presonus/surface/NetworkSetupComponent.hpp')
SOURCE = Path('uc-library/src/Presonus/Surface/NetworkSetupComponent.cpp')
DRIVER = TEST / 'Replay.cpp'
FORMATTER = 'uc-library/.venv/bin/clang-format'
FORMAT = [FORMATTER, '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror',
          *map(str, (HEADER, SOURCE, DRIVER))]
CORE_PIN = 'e8cbdea4a4a20e15111f5a690798a259c0374b31'
CORE = Path('third_party/ccl-framework')
DOMAIN = ('Four direct ARM and portable executions crossing null/live item pointer with '
          'empty/populated receiver state. Native restores frame and entry arguments, '
          'writes only its stack frame and returns directly. Portable callback preserves '
          'receiver, configured state and item, and invokes no instrumented boundaries.')
UNCERTAINTIES = ['Portable void is provisional. Native return declaration, original base dispatch '
                 'and thunk/receiver layout, ARM ABI and hardware remain unverified.']


def utc():
    return datetime.now(timezone.utc).isoformat()


def run(argv, **kwargs):
    return subprocess.run(list(map(str, argv)), check=True, text=True, **kwargs)


def capture(argv, **kwargs):
    return run(argv, stdout=subprocess.PIPE, **kwargs).stdout


def sha(path):
    return digest(Path(path).read_bytes())


def compile_entry(build, suffix):
    metadata = json.loads((build / 'compile_commands.json').read_text())
    entry, = (row for row in metadata if row['file'].endswith('/' + suffix))
    args = shlex.split(entry['command'])
    output_at = args.index('-o')
    output = Path(entry['directory']) / args[output_at + 1]
    return args[:output_at], output, Path(entry['directory'])


def compile_local(options):
    root = Path.cwd()
    git_root = Path(capture(['git', 'rev-parse', '--show-toplevel']).strip())
    if options.workspace is None or root != options.workspace or root != git_root:
        raise ValueError('Local build requires the explicit assigned physical repository')
    SCRATCH.mkdir(parents=True, exist_ok=True)
    start = utc()
    obj = options.object.resolve()
    exe = options.exe.resolve()
    driver_object = (SCRATCH / 'Replay.cpp.o').resolve()
    if any(not target.is_relative_to(SCRATCH.resolve()) for target in (obj, exe)):
        raise ValueError('Local build outputs must stay in assigned scratch')
    production, _, _ = compile_entry(BUILD, SOURCE.relative_to('uc-library').as_posix())
    test_flags, _, _ = compile_entry(BUILD, 'tests/recovery/NetworkSetupViewReplay.cpp')

    def worker_flags(flags):
        return [arg.replace(str(CANONICAL / 'uc-library/include'),
                            str(root / 'uc-library/include')) for arg in flags]

    src_compile = [*worker_flags(production), '-o', obj, '-c', SOURCE]
    test_compile = [*worker_flags(test_flags), '-fno-rtti', '-o', driver_object, '-c', DRIVER]
    link = shlex.split((BUILD / 'CMakeFiles/NetworkSetupViewReplay.dir/link.txt').read_text())
    library_at = link.index('libpresonus_cs18_components.a')
    link = [link[0], '-o', exe, driver_object, obj,
            *(arg for arg in link[:library_at] if arg.startswith('-Wl,-rpath,')),
            *link[library_at:]]
    for argv, cwd in ((src_compile, root), (test_compile, root), (link, BUILD)):
        run(argv, cwd=cwd)
    metadata = {'started_utc': start, 'finished_utc': utc(),
                'commands': [{'argv': list(map(str, argv)), 'cwd': str(cwd)}
                             for argv, cwd in ((src_compile, root), (test_compile, root),
                                               (link, BUILD))]}
    (SCRATCH / 'compile.json').write_text(json.dumps(metadata, indent=2) + '\n')


def check_symbol(obj, exe=None):
    rows = {}
    for file in (obj, exe):
        if file:
            symbols = capture(['nm', '--defined-only', file])
            match, = (line for line in symbols.splitlines() if line.split()[-1:] == [MANGLED])
            rows[str(file)] = match
    return rows


def dependencies(options):
    root = Path.cwd()
    provider = CANONICAL / CORE
    pin = capture(['git', '-C', provider, 'rev-list', '--max-parents=0', 'HEAD']).strip()
    head = capture(['git', '-C', provider, 'rev-parse', 'HEAD']).strip()
    if (pin, head) != (CORE_PIN, CORE_PIN):
        raise ValueError('Canonical provider checkout differs from pinned source')
    build = options.exe.absolute().parent
    if options.local:
        metadata = json.loads((SCRATCH / 'compile.json').read_text())
        scans = [(item['argv'][:-4] + ['-M', '-MT', 'bound', item['argv'][-1]], item['cwd'])
                 for item in metadata['commands'][:2]]
    else:
        scans = []
        for source, expected in ((SOURCE, options.object), (DRIVER, None)):
            flags, obj, cwd = compile_entry(build, source.relative_to('uc-library').as_posix())
            if expected is not None and obj.resolve() != expected.resolve():
                raise ValueError('Canonical object differs from build compile database')
            scans.append(([*flags, '-M', '-MT', 'bound', root / source], cwd))
        metadata = {'compile_commands_sha256': sha(build / 'compile_commands.json')}
    src = {str(p.relative_to('uc-library')): sha(p) for p in (HEADER, SOURCE, DRIVER)}
    core = {}
    sdk = BUILD / 'upstream-core/sdk/include/presonus-core-5'
    for argv, cwd in scans:
        tokens = shlex.split(capture(argv, cwd=cwd).replace('\\\n', ' '))
        for token in tokens[1:]:
            dep = (Path(cwd) / token).resolve()
            if dep.is_relative_to(root / 'uc-library/include'):
                src[str(dep.relative_to(root / 'uc-library'))] = sha(dep)
            elif dep.is_relative_to(sdk / 'core'):
                source = CORE / dep.relative_to(sdk)
                core[str(source)] = sha(dep)
    for path in ('portable/corecomponent.cpp', 'malloc/coremalloc.cpp'):
        source = CORE / 'core' / path
        core[str(source)] = sha(CANONICAL / source)
    if not core or any(sha(CANONICAL / path) != value or sha(path) != value
                       for path, value in core.items()):
        raise ValueError('Pinned provider, worker and SDK dependency bytes differ')
    return src, core, metadata


def replay(options):
    started = utc()
    fixture_sha256 = sha(options.fixtures)
    if fixture_sha256 != options.fixture_sha256:
        raise ValueError('Unexpected native fixture hash')
    fixture = json.loads(options.fixtures.read_text())
    if (fixture['elf_sha256'], fixture['mangled']) != (ELF_SHA256, MANGLED):
        raise ValueError('Wrong native fixture identity')
    cases = fixture['cases']
    if [row['input'] for row in cases] != [[0, 0], [1, 0], [0, 1], [1, 1]]:
        raise ValueError('Incomplete case domain')
    values = ''.join('{} {}\n'.format(*row['input']) for row in cases)
    if not options.exe.is_file():
        raise ValueError('Replay executable missing')
    argv = [options.exe.resolve()]
    actual = [list(map(int, line.split())) for line in capture(argv, input=values).splitlines()]
    if actual != [row['output'] for row in cases]:
        raise ValueError(f'Portable outputs differ from native fixture: {actual}')
    symbols = check_symbol(options.object, options.exe)
    run(FORMAT)
    src, core, metadata = dependencies(options)
    pending = {'original_elf_sha256': ELF_SHA256, 'mangled': MANGLED,
               'original_address': fixture['address'], 'role': 'client',
               'domain': DOMAIN, 'cpp_compiled': True, 'mangling_namespace_checked': True,
               'cpp_differential_passed': True, 'portable_ready': False,
               'sources': src, 'repository_sources': core,
               'declaration_uncertainties': UNCERTAINTIES}
    result = {
        'task_id': 'rolling_next200_class_10', 'cpp_differential_passed': True,
        'compiled_mangled_names_matched': True, 'functions': [pending],
        'proposed_readiness': {'ready': [], 'pending': [pending]},
        'native': fixture, 'native_producer_sha256': sha(TEST / 'native.py'),
        'fixture_sha256': sha(options.fixtures), 'producer_sha256': sha(__file__),
        'case_count': len(cases), 'outputs': actual, 'symbols': symbols,
        'compiler_version': capture(['c++', '--version']).splitlines()[0],
        'format': {'argv': FORMAT, 'version': capture([FORMATTER, '--version']).strip(),
                   'files': {str(path): sha(path) for path in (HEADER, SOURCE, DRIVER)}},
        'compilation': metadata, 'object_sha256': sha(options.object),
        'executable_sha256': sha(options.exe), 'provider_pin': CORE_PIN,
        'replay_argv': sys.argv, 'started_utc': started, 'finished_utc': utc(),
    }
    if options.integration != '-':
        path = Path(options.integration)
        if json.loads(path.read_text()).get('ctest_passed') is not True:
            raise ValueError('Canonical integration proof does not record passing CTest')
        result['integration_sha256'] = sha(path)
    receipt = json.dumps(result, indent=2) + '\n'
    if options.out == '-':
        print(receipt, end='')
    else:
        Path(options.out).write_text(receipt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('compile', 'symbols', 'replay'))
    parser.add_argument('--workspace', type=Path)
    parser.add_argument('--local', action='store_true')
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--object', type=Path, required=True)
    parser.add_argument('--fixtures', type=Path, default=TEST / 'fixtures.json')
    parser.add_argument('--fixture-sha256')
    parser.add_argument('--integration', default='-')
    parser.add_argument('--out', default='-')
    options = parser.parse_args()
    if options.mode == 'compile':
        compile_local(options)
    elif options.mode == 'symbols':
        print(json.dumps(check_symbol(options.object, options.exe)))
    else:
        replay(options)


if __name__ == '__main__':
    main()
