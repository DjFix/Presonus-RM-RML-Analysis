"""Check exact DawFxPage constructor variants, preserving the production compiler flags."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess

from native import PACKET, ROOT, TASK, observe, sha

TEST = Path('uc-library/tests/recovery') / TASK
CANDIDATE = Path('uc-library/candidates') / TASK
PROOF = CANDIDATE / 'worker-proof.json'
HEADER_SOURCE = Path('uc-library/include/presonus/surface/DawFxPageComponent.hpp')
FIXTURES = TEST / 'fixtures.json'
REPLAY = TEST / 'Replay.cpp'
SCRATCH = Path('temp/recovery-work') / TASK
HEADER = HEADER_SOURCE
SOURCE = Path('uc-library/src/Presonus/Surface/DawFxPageComponent.cpp')
MAPPING = SOURCE.with_name('DawFxPageMapping.cpp')
BUILD = ROOT / 'temp/core-upstream/root-integration-01'
SDK = BUILD / 'upstream-core/sdk'
COMPILATION_DB = BUILD / 'compile_commands.json'
OBJECTS = [SCRATCH / path.with_suffix('.o').name for path in (SOURCE, MAPPING)]
EXE = SCRATCH / 'Replay'
FORMATTER = 'uc-library/.venv/bin/clang-format'
FORMAT = [FORMATTER, '--style=file', '--fallback-style=LLVM', '--dry-run',
          '--Werror', *map(str, (HEADER, SOURCE, MAPPING, REPLAY))]
ARCHIVES = [BUILD / 'libpresonus_cs18_components.a',
            *(SDK / 'lib' / n for n in ('libcorelib.a', 'libpresonus_core_allocator.a',
                                        'libpresonus_png.a', 'libpresonus_zlib.a')),
            BUILD / 'private-glibc29-provider/libpresonus_private_glibc29.a']


def dump(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def compile_from_canonical():
    entries = json.loads(COMPILATION_DB.read_text())
    commands = []
    for source, obj in zip((SOURCE, MAPPING), OBJECTS):
        entry, = [e for e in entries if Path(e['file']) == ROOT / source]
        argv = shlex.split(entry['command'])
        assert argv[-3] == entry['output'] and argv[-2:] == ['-c', str(ROOT / source)]
        argv[argv.index('-I' + str(ROOT / 'uc-library/include'))] = '-Iuc-library/include'
        argv[-3], argv[-1] = str(obj), str(source)
        commands.append(argv)
    replay_flags = commands[-1][:-4]
    link = [*replay_flags, '-fno-devirtualize', '-fno-devirtualize-speculatively',
            '-Wl,--wrap=_ZdlPv', '-Wl,--wrap=_ZdlPvm', str(REPLAY), *map(str, OBJECTS),
            *map(str, ARCHIVES), '-lssl', '-lcrypto', '-lm', '-ldl', '-pthread', '-o', str(EXE)]
    return commands + [link]


VARIANT = 'base' if '_base_' in TASK else 'complete'
PYTHON = 'uc-library/.venv/bin/python'
DOMAIN = ('Two form/tag cases for the exact constructor variant, all 41 actual CCL '
          'descriptors, concrete parameter types, ownership, unattached state and mode '
          'cache, followed by original/portable D1 and D0 cleanup regression.')
LIMITS = [
    'Portable PageComponent and real pinned CCL source; ARM layout and additional native '
    'observer base interfaces remain unresolved. MainLCD and production updateList are outside scope.',
    'Native ELF loaders model only environmental lookup, TLS and brk around the actual allocator. '
    'The firmware and host allocator APIs differ (ARM unsized, host compiler-selected sized).',
    'Existing destructor variants are regression checks and receive zero reconstruction credit.',
]


def symbols(fixture):
    matched = {}
    definitions = [fixture['original'], *fixture['destructor_ranges'].values()]
    for original in definitions:
        name = original['mangled']
        obj = OBJECTS[0 if name == fixture['original']['mangled'] else 1]
        argv = ['/usr/bin/nm', '--defined-only', str(obj)]
        line, = [line for line in subprocess.check_output(argv, text=True).splitlines()
                 if line.split()[-1:] == [name]]
        assert line.split()[1] == 'T'
        matched[name] = dict(argv=argv, match=line)
    return matched


def replay(fixture, exe):
    argv = [str(exe), VARIANT]
    lines = iter(subprocess.check_output(argv, text=True).splitlines())
    observations = []
    for case in fixture['cases']:
        name, form, tag, mode = next(lines).split()
        assert [name, form, int(tag)] == case['base'] and int(mode) == case['modes_bound']
        assert list(map(int, next(lines).split())) == case['state']
        count = int(next(lines))
        assert count == len(case['descriptors']) == 41
        for expected in case['descriptors']:
            fields = next(lines).split()
            actual = [int(fields[0]), int(fields[1]), fields[2],
                      *map(float, fields[3:8]), *map(int, fields[8:])]
            assert actual == expected, (actual, expected)
        receiver, child, parameter, allocator = next(lines).split()
        disposition = [int(receiver), int(child), int(parameter)]
        assert disposition == case['disposition']
        assert allocator in (('sized', 'unsized') if receiver == '1' else ('none',))
        observations.append(dict(descriptors=count, disposition=disposition,
                                 host_allocator_overload=allocator,
                                 destructor_variant=case['destructor']))
    assert next(lines, None) is None
    print(f'{TASK}: 2 portable constructor and destructor cases matched')
    return observations


def seal(fixture, exe, fixture_path):
    packet = json.loads(PACKET.read_text())
    original = fixture['original']
    packet_row, = packet['originals']
    assert packet_row['original']['mangled'] == original['mangled']
    subprocess.run(FORMAT, check=True)
    assert fixture == observe()
    observed = replay(fixture, exe)
    matched = symbols(fixture)
    providers = {p['path']: p['sha256'] for p in packet['task']['review']['providers']}
    for path, digest in providers.items():
        assert sha(Path(path)) == digest
    sources = {str(path.relative_to('uc-library')): sha(path) for path in (SOURCE, HEADER)}
    formatted = {str(path.relative_to('uc-library')): sha(path)
                 for path in (SOURCE, HEADER, MAPPING, REPLAY)}
    pending = dict(original_elf_sha256=original['elf_sha256'], mangled=original['mangled'],
                   cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
                   sources=sources, repository_sources=providers,
                   validation_domain=DOMAIN, declaration_uncertainties=LIMITS)
    dump(PROOF, dict(task_id=TASK, originals=[original], native=fixture, portable=observed,
                     exe_sha256=sha(exe), fixture_sha256=sha(fixture_path),
                     object_sha256={str(path): sha(path) for path in OBJECTS},
                     link_input_hashes={str(path): sha(path) for path in ARCHIVES},
                     commands=compile_from_canonical(), symbols=matched,
                     compiled_mangled_names_matched=True, mangled_names=[original['mangled']],
                     cpp_differential_passed=True, portable_ready=False,
                     format_check_passed=True, format_argv=FORMAT, formatted_files=formatted,
                     formatter_version=subprocess.check_output([FORMATTER, '--version'],
                                                               text=True).strip(),
                     producer_inputs={str(path): sha(path) for path in
                                      (TEST/'native.py', TEST/'check.py', REPLAY)},
                     destructor_regression_credit=0,
                     proposed_readiness={'ready': [], 'pending': [pending]}))
    artifacts = {SOURCE: 'source', HEADER: 'source', REPLAY: 'test',
                 fixture_path: 'fixture', TEST/'check.py': 'replay',
                 TEST/'native.py': 'producer', PROOF: 'proof', PACKET: 'packet'}
    artifacts.update({Path(path): 'dependency' for path in providers})
    artifacts.update({Path(entry['path']): 'evidence' for entry in packet['task']['review']['evidence']})
    checks = [PYTHON, '-B', str(TEST/'check.py')]
    dump(CANDIDATE/'HANDOFF.json', dict(version=1, task_id=TASK,
        namespace=packet['task']['namespace'], packet_manifest=str(PACKET), originals=[original],
        artifacts=[dict(kind=kind,path=str(path),sha256=sha(path))
                   for path,kind in artifacts.items()],
        checks=[dict(kind=kind,argv=[*checks,kind],timeout_seconds=120)
                for kind in ('format','compile','symbols','native','replay')],
        validation_domain=DOMAIN, limitations=LIMITS,
        build_integration=dict(partition='CS18 (existing DawFxPageComponent.cpp and DawFxPageMapping.cpp)',
            public_headers=[str(HEADER)], test_target=TASK, test_sources=[str(REPLAY)],
            test_compile_options=['-fno-devirtualize', '-fno-devirtualize-speculatively'],
            test_link_options=['-Wl,--wrap=_ZdlPv', '-Wl,--wrap=_ZdlPvm'],
            link_dependencies=['presonus_cs18_components'],
            ctest_argv=[*checks,'replay','--exe',f'$<TARGET_FILE:{TASK}>','--fixtures',str(fixture_path)])))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('capture','format','compile','symbols',
                                          'native','replay','seal'))
    parser.add_argument('--exe', type=Path, default=EXE)
    parser.add_argument('--fixtures', type=Path, default=FIXTURES)
    args = parser.parse_args()
    if args.mode == 'capture':
        dump(args.fixtures, observe())
    elif args.mode == 'format':
        subprocess.run(FORMAT, check=True)
    elif args.mode == 'compile':
        SCRATCH.mkdir(parents=True, exist_ok=True)
        for cmd in compile_from_canonical():
            print(shlex.join(cmd), flush=True)
            subprocess.run(cmd, check=True)
    else:
        fixture = json.loads(args.fixtures.read_text())
        if args.mode == 'native':
            assert fixture == observe()
            print(f'{TASK}: independently reproduced ARM constructor and destructor dispositions')
        elif args.mode == 'symbols':
            print(json.dumps(symbols(fixture)))
        elif args.mode == 'replay':
            replay(fixture, args.exe)
        else:
            seal(fixture, args.exe, args.fixtures)


if __name__ == '__main__':
    main()
