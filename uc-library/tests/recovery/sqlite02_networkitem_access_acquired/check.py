"""Compile and compare NetworkItem against both sealed original ranges."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from native import PACKET, ROOT, TASK, observe

TEST = Path('uc-library/tests/recovery') / TASK
CANDIDATE = Path('uc-library/candidates') / TASK
SOURCE = Path('uc-library/src/Presonus/UC/NetworkItem.cpp')
HEADER = Path('uc-library/include/presonus/uc/NetworkItem.hpp')
REPLAY = TEST / 'Replay.cpp'
FIXTURE = TEST / 'fixtures.json'
SCRATCH = Path('temp/recovery-work/sqlite02-worker05') / TASK
OBJECT = SCRATCH / 'NetworkItem.o'
DEPFILE = SCRATCH / 'NetworkItem.d'
EXE = SCRATCH / 'Replay'
PYTHON = 'uc-library/.venv/bin/python'
FORMATTER = 'uc-library/.venv/bin/clang-format'
FORMAT = [FORMATTER, '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror',
          *map(str, (SOURCE, HEADER, REPLAY))]
SDK = ROOT / 'temp/core-upstream/root-integration-01/upstream-core/sdk'
CXX = ['/usr/bin/c++', '-std=c++17', '-O2', '-Ulinux', '-Iuc-library/include',
       '-isystem', str(SDK / 'include/presonus-core-5')]
COMPILE = [*CXX, '-MD', '-MF', str(DEPFILE), '-c', str(SOURCE), '-o', str(OBJECT)]
LINK = [*CXX, '-MD', '-MF', str(SCRATCH / 'Replay.d'),
        str(REPLAY), str(OBJECT), '-o', str(EXE)]
DOMAIN = ('Both original predicates independently executed on zero, 1, high-bit only, '
          'all-bits set and cleared receiver words. No external writes or calls. '
          'Portable replay covers default, nonzero and clear operations, independent '
          'receiver state and unchanged borrowed component.')
LIMITS = ['Original return spelling, receiver field type and layout remain unresolved.',
          'Portable observation is an explicit caller input. Acquisition and release behavior, '
          'ARM binary interoperability and hardware are outside this replay.']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def symbols(path, targets):
    argv = ['/usr/bin/nm', '--defined-only', str(path)]
    output = subprocess.check_output(argv, text=True).splitlines()
    names = {row['original']['mangled'] for row in targets}
    matched = [line for line in output if line.split()[-1:] and line.split()[-1] in names]
    assert len(matched) == len(names)
    return {'argv': argv, 'matched': matched}


def replay(fixture, exe):
    observed = [list(map(int, line.split())) for line in
                subprocess.check_output([str(exe)], text=True).splitlines()]
    for target in fixture['targets']:
        expected = [[case['r0'], target['cases'][0]['r0']] for case in target['cases']]
        assert observed == expected, (observed, expected)
    print(f'{TASK}: {len(observed)} portable cases matched both ELF identities')
    return observed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('format', 'compile', 'symbols', 'capture',
                                          'native', 'replay', 'seal'))
    parser.add_argument('--exe', type=Path, default=EXE)
    parser.add_argument('--object', type=Path, default=OBJECT)
    parser.add_argument('--fixtures', type=Path, default=FIXTURE)
    args = parser.parse_args()
    if args.mode == 'format':
        subprocess.run(FORMAT, check=True)
        return
    if args.mode == 'compile':
        SCRATCH.mkdir(parents=True, exist_ok=True)
        for command in (COMPILE, LINK):
            print(json.dumps(command), flush=True)
            subprocess.run(command, check=True)
        return
    if args.mode == 'capture':
        dump(args.fixtures, observe())
        return
    fixture = json.loads(args.fixtures.read_text())
    if args.mode == 'native':
        assert fixture == observe()
        print(f'{TASK}: {sum(len(target["cases"]) for target in fixture["targets"])} native executions reproduced')
        return
    if args.mode == 'replay':
        replay(fixture, args.exe)
        return
    matched = symbols(args.object, fixture['targets'])
    print(json.dumps(matched))
    if args.mode == 'symbols':
        return
    observations = replay(fixture, args.exe)
    assert fixture == observe()
    subprocess.run(FORMAT, check=True)
    originals = [target['original'] for target in fixture['targets']]
    provider = Path('third_party/ccl-framework/core/public/corestringbuffer.h')
    sources = {str(path.relative_to('uc-library')): sha(path) for path in (SOURCE, HEADER)}
    pending = [dict(original_elf_sha256=original['elf_sha256'], mangled=original['mangled'],
                    cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
                    sources=sources, repository_sources={str(provider): sha(provider)},
                    validation_domain=DOMAIN, declaration_uncertainties=LIMITS)
               for original in originals]
    proof = CANDIDATE / 'worker-proof.json'
    dump(proof, dict(task_id=TASK, originals=originals, native=fixture,
                     fixture_sha256=sha(args.fixtures), portable=observations,
                     object_sha256=sha(args.object), exe_sha256=sha(args.exe),
                     depfiles={str(path): sha(path) for path in (DEPFILE, SCRATCH / 'Replay.d')},
                     compile_argv=COMPILE, link_argv=LINK,
                     link_input_hashes={str(args.object): sha(args.object)},
                     producer_inputs={str(path): sha(path) for path in
                                      (TEST / 'check.py', TEST / 'native.py', REPLAY)},
                     compiled_symbol=matched, compiled_mangled_names_matched=True,
                     mangled_names=sorted({original['mangled'] for original in originals}),
                     cpp_differential_passed=True, format_check_passed=True,
                     portable_ready=False, format_argv=FORMAT,
                     formatted_files={str(path.relative_to('uc-library')): sha(path)
                                      for path in (SOURCE, HEADER, REPLAY)},
                     formatter_version=subprocess.check_output([FORMATTER, '--version'],
                                                               text=True).strip(),
                     proposed_readiness={'ready': [], 'pending': pending}))
    artifacts = {SOURCE: 'source', HEADER: 'source', args.fixtures: 'fixture', REPLAY: 'test',
                 TEST / 'check.py': 'replay', TEST / 'native.py': 'producer',
                 provider: 'dependency', proof: 'proof', PACKET: 'packet'}
    argv = [PYTHON, '-B', str(TEST / 'check.py')]
    dump(CANDIDATE / 'HANDOFF.json', dict(version=1, task_id=TASK,
         namespace='Presonus::UC::NetworkItem', packet_manifest=str(PACKET), originals=originals,
         artifacts=[dict(path=str(path), kind=kind, sha256=sha(path))
                    for path, kind in artifacts.items()],
         checks=[dict(kind=kind, argv=[*argv, kind], timeout_seconds=120)
                 for kind in ('format', 'compile', 'symbols', 'native', 'replay')],
         validation_domain=DOMAIN, limitations=LIMITS,
         build_integration=dict(partition='common (existing NetworkItem.cpp)',
                                public_headers=[str(HEADER)], test_target=TASK,
                                link_dependencies=['presonus_uc'],
                                ctest_argv=[*argv, 'replay', '--exe', f'$<TARGET_FILE:{TASK}>',
                                            '--fixtures', str(args.fixtures)])))


if __name__ == '__main__':
    main()
