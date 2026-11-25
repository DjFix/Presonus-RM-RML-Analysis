"""Local and canonical replay entry points for sealed NetworkItem observations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from native import PACKET, TASK, TITLE, observe

TEST = Path('uc-library/tests/recovery') / TASK
CANDIDATE = Path('uc-library/candidates') / TASK
SOURCE = Path('uc-library/src/Presonus/UC/NetworkItem.cpp')
HEADER = Path('uc-library/include/presonus/uc/NetworkItem.hpp')
SERVER_SOURCE = Path('uc-library/src/Presonus/UC/ServerDescription.cpp')
SERVER_HEADER = Path('uc-library/include/presonus/uc/server_description.hpp')
CORE = Path('third_party/ccl-framework/core/public/corestringbuffer.h')
REPLAY = TEST / 'Replay.cpp'
FIXTURE = TEST / 'fixtures.json'
SCRATCH = Path('temp/recovery-work/sqlite-network-item-metadata01') / TASK
OBJECT = SCRATCH / 'NetworkItem.o'
EXE = SCRATCH / 'Replay'
PYTHON = 'uc-library/.venv/bin/python'
FORMATTER = 'uc-library/.venv/bin/clang-format'
FORMAT = [FORMATTER, '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror',
          *map(str, (SOURCE, HEADER, REPLAY))]
CXX = ['/usr/bin/c++', '-std=c++17', '-O0', '-Ulinux', '-Iuc-library/include',
       '-isystem', 'third_party/ccl-framework']
COMPILE = [*CXX, '-c', str(SOURCE), '-o', str(OBJECT)]
LINK = [*CXX, *map(str, (REPLAY, OBJECT, SERVER_SOURCE)), '-o', str(EXE)]
TITLE_DOMAIN = ('Initialized CStringBuffer<128> output. Both original roles independently '
                'observed over empty/partial metadata, nonempty type-1 and non-type-1 '
                'metadata, exact fill and truncation within each relevant path. All 128 '
                'output bytes compared with the pinned CCL portable replay.')
CTOR_DOMAIN = ('The original typed constructor executes the actual native ServerDescription '
               'and null-input CString64 constructor bodies. Tests cover two firmware roles '
               'and five type words, poison initial storage, both cleared component/access '
               'words and four scalar and seven string defaults. The portable replay uses '
               'genuine ServerDescription and CCL buffers through this ABI constructor variant.')
LIMITS = [
    'Portable source reconstruction. Original ARM class layout, host/ARM ABI interoperability '
    'and hardware behavior remain outside this replay.',
    'Original Type enumerator names and underlying signedness are unresolved.',
]
if TITLE:
    LIMITS.extend([
        'Original getTitle return declaration is unresolved. Portable void exposes the bounded output effect.',
        'ARM PLT calls are serviced by host libc at checked call boundaries.',
    ])
else:
    LIMITS.append('Original C1 and C2 have separate addresses and bytes in each firmware. '
                  'The Linux compiler can emit them at one address.')
DOMAIN = TITLE_DOMAIN if TITLE else CTOR_DOMAIN


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
    if not TITLE:
        replay_symbols = ['/usr/bin/nm', '--defined-only', str(EXE)]
        all_names = subprocess.check_output(replay_symbols, text=True)
        if TASK.endswith('base_construct'):
            assert '_ZN11DerivedItemC1EN8Presonus2UC11NetworkItem4TypeE' in all_names
    return {'argv': argv, 'matched': matched}


def replay(fixture, exe):
    observed = []
    for target in fixture['targets']:
        for case in target['cases']:
            value = case['input']
            inputs = value if TITLE else [value]
            raw = subprocess.check_output([str(exe), *map(str, inputs)], text=True).splitlines()
            actual = raw[0] if TITLE else [*map(int, raw[:7]), *raw[7:]]
            assert actual == case['expected'], (target['original']['role'], value, actual, case['expected'])
            observed.append(actual)
    print(f'{TASK}: {len(observed)} portable comparisons matched independently executed ELF cases')
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
        assert fixture == json.loads(json.dumps(observe()))
        print(f'{TASK}: {sum(len(target["cases"]) for target in fixture["targets"])} original executions reproduced')
        return
    if args.mode == 'replay':
        replay(fixture, args.exe)
        return
    matched = symbols(args.object, fixture['targets'])
    print(json.dumps(matched))
    if args.mode == 'symbols':
        return
    observations = replay(fixture, args.exe)
    assert fixture == json.loads(json.dumps(observe()))
    subprocess.run(FORMAT, check=True)
    originals = [target['original'] for target in fixture['targets']]
    dependencies = [CORE, SERVER_SOURCE, SERVER_HEADER]
    sources = {str(path.relative_to('uc-library')): sha(path) for path in (SOURCE, HEADER)}
    proposed = [
        dict(original_elf_sha256=original['elf_sha256'], mangled=original['mangled'],
             cpp_compiled=True, mangling_namespace_checked=True, portable_ready=not TITLE,
             sources=sources, repository_sources={str(path): sha(path) for path in dependencies},
             validation_domain=DOMAIN, declaration_uncertainties=LIMITS)
        for original in originals
    ]
    proof = CANDIDATE / 'worker-proof.json'
    dump(proof, dict(task_id=TASK, originals=originals, native=fixture,
                     original_execution_count=len(observations),
                     fixture_sha256=sha(args.fixtures), portable=observations,
                     object_sha256=sha(args.object), exe_sha256=sha(args.exe),
                     compile_argv=COMPILE, link_argv=LINK,
                     compiler_version=subprocess.check_output([CXX[0], '--version'],
                                                              text=True).splitlines()[0],
                     link_input_hashes={str(path): sha(path) for path in (args.object, SERVER_SOURCE)},
                     producer_inputs={str(path): sha(path) for path in
                                      (TEST / 'check.py', TEST / 'native.py', REPLAY)},
                     compiled_symbol=matched, compiled_mangled_names_matched=True,
                     mangled_names=sorted({original['mangled'] for original in originals}),
                     cpp_differential_passed=True, format_check_passed=True,
                     portable_ready=not TITLE, format_argv=FORMAT,
                     formatted_files={str(path.relative_to('uc-library')): sha(path)
                                      for path in (SOURCE, HEADER, REPLAY)},
                     formatter_version=subprocess.check_output([FORMATTER, '--version'],
                                                               text=True).strip(),
                     proposed_readiness={'ready': [] if TITLE else proposed,
                                         'pending': proposed if TITLE else []}))
    direct = Path(json.loads(PACKET.read_text())['task']['review']['equivalence']['path'])
    artifacts = {SOURCE: 'source', HEADER: 'source', args.fixtures: 'fixture', REPLAY: 'test',
                 TEST / 'check.py': 'replay', TEST / 'native.py': 'producer',
                 proof: 'proof', PACKET: 'packet', direct: 'evidence',
                 **{path: 'dependency' for path in dependencies}}
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
                                test_source=str(REPLAY), link_dependencies=['presonus_uc'],
                                ctest_argv=[*argv, 'replay', '--exe', f'$<TARGET_FILE:{TASK}>',
                                            '--fixtures', str(args.fixtures)])))


if __name__ == '__main__':
    main()
