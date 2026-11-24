"""Compile and verify the AVB cascade server-change portable replay."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path.cwd()
HERE = Path(__file__).parent.relative_to(ROOT) if Path(__file__).is_absolute() else Path(__file__).parent
LIB = Path('uc-library')
SOURCE = Path('src/Presonus/Mixer/AVBCascadeManager.cpp')
HEADER = Path('include/presonus/mixer/AVBCascadeManager.hpp')
NETWORK = Path('include/presonus/uc/NetworkItem.hpp')
WORK = Path('temp/recovery-work/lane04-build')
FORMAT = [str(LIB / '.venv/bin/clang-format'), '--style=file', '--fallback-style=LLVM',
          '--dry-run', '--Werror', str(LIB / HEADER), str(LIB / SOURCE), str(HERE / 'Replay.cpp')]
COMPILER = ['g++', '-std=c++20', '-O2', '-ffunction-sections', '-fdata-sections',
            '-Iuc-library/include', '-Ithird_party/ccl-framework']
DOMAIN = ('Three direct calls with a valid portable manager and a null, selected, or distinct '
          'NetworkItem pointer. Verify no receiver/item/component change and no external call. '
          'Original ARM execution also verifies stack/frame restoration and no non-stack access.')
UNCERTAINTY = ('Original return declaration unresolved; void is the portable choice. Original '
               'inheritance, vtable dispatch, thunk behavior, ARM layout and ABI remain unresolved.')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv):
    return subprocess.check_output(argv, text=True)


def verify_symbols(obj, mangled):
    argv = ['nm', '--defined-only', str(obj)]
    matches = [row for row in run(argv).splitlines()
               if row.split()[-1:] == [mangled]]
    if len(matches) != 1 or matches[0].split()[-2] not in ('T', 'W'):
        raise ValueError(f'Expected one defined text symbol {mangled}: {matches}')
    return argv, matches[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=['format', 'compile', 'symbols', 'replay'], nargs='?',
                        default='replay')
    parser.add_argument('--exe', type=Path, default=WORK / 'replay')
    parser.add_argument('--object', type=Path, default=WORK / 'manager.o')
    parser.add_argument('--fixture', type=Path, default=HERE / 'fixtures.json')
    parser.add_argument('--integration', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if args.phase == 'format':
        run(FORMAT)
        return
    compile_argv = [
        [*COMPILER, '-c', str(LIB / SOURCE), '-o', str(args.object)],
        [*COMPILER, '-Wl,--gc-sections', str(HERE / 'Replay.cpp'),
         str(args.object), '-o', str(args.exe)],
    ]
    if args.phase == 'compile':
        for argv in compile_argv:
            run(argv)
        return

    native = json.loads(args.fixture.read_text())
    nm_argv, matched = verify_symbols(args.object, native['mangled'])
    if args.phase == 'symbols':
        print(matched)
        return
    exe_argv = [str(args.exe.resolve())]
    observed = run(exe_argv).splitlines()
    expected = [
        f"{case['argument']} {int(case['objects_unchanged'])} {case['external_calls']}"
        for case in native['cases']
    ]
    if len(expected) != 3 or observed != expected:
        raise ValueError(f'Replay differs from native fixture: {observed!r}')

    if args.out:
        run(FORMAT)
        core_deps = {
            Path(line).as_posix()
            for line in run([*COMPILER, '-MM', str(HERE / 'Replay.cpp')])
            .replace('\\\n', ' ').split()
            if line.startswith('third_party/ccl-framework/core/')
        }
        pending = dict(original_elf_sha256=native['elf_sha256'], mangled=native['mangled'],
                       original_address=native['address'], original_size=native['size'],
                       cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
                       domain=DOMAIN, declaration_uncertainties=[UNCERTAINTY],
                       sources={str(p): digest(LIB / p) for p in (SOURCE, HEADER, NETWORK)},
                       repository_sources={p: digest(Path(p)) for p in sorted(core_deps)})
        proof = dict(cpp_differential_passed=True, compiled_mangled_names_matched=True,
                     format_check_passed=True, validation_domain=DOMAIN,
                     proposed_readiness={'ready': [], 'pending': [pending]},
                     original_range={k: v for k, v in native.items() if k != 'cases'},
                     native_case_count=len(expected), cpp_case_count=len(observed),
                     compiled_symbol=matched, compiled_object_sha256=digest(args.object),
                     executable_sha256=digest(args.exe), fixture_sha256=digest(args.fixture),
                     formatter_version=run([FORMAT[0], '--version']).strip(),
                     commands={'format': FORMAT, 'nm': nm_argv, 'replay': exe_argv},
                     producer_sha256={str(p): digest(p) for p in
                                      (HERE / 'native.py', HERE / 'check.py', HERE / 'Replay.cpp')},
                     integration_sha256=digest(args.integration) if args.integration else None)
        if args.integration is None:
            proof['commands']['compile'] = compile_argv
            proof['compiler_version'] = run([COMPILER[0], '--version']).splitlines()[0]
        args.out.write_text(json.dumps(proof, indent=2) + '\n')
    print(f'Portable differential replay passed {len(observed)} cases')


if __name__ == '__main__':
    main()
