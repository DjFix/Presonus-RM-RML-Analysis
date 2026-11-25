"""Compile and compare the RM GEQ name-list port with independent ARM observations."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

import elftools
import unicorn

from native import PACKET, TASK, TEST, digest, run

SOURCE = Path('uc-library/src/Presonus/Panel/GeqUIComponent.cpp')
HEADER = Path('uc-library/include/presonus/panel/GeqUIComponent.hpp')
REPLAY = TEST / 'Replay.cpp'
FIXTURE = TEST / 'fixtures.json'
CORE = Path('third_party/ccl-framework/core')
OUT = Path('temp/recovery-work') / TASK
CANDIDATE = Path('uc-library/candidates') / TASK
FORMAT = ['uc-library/.venv/bin/clang-format', '--style=file',
          '--fallback-style=LLVM', '--dry-run', '--Werror', SOURCE, HEADER, REPLAY]
CXX = ['g++', '-std=c++17', '-O2', '-UNDEBUG', '-Wno-multichar', '-fno-rtti',
       '-ffunction-sections', '-fdata-sections', '-Iuc-library/include',
       '-Ithird_party/ccl-framework']
CANONICAL_BUILD = Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01')
ARCHIVES = [CANONICAL_BUILD / 'libpresonus_rm_components.a',
            *(CANONICAL_BUILD / 'upstream-core/sdk/lib' / filename
              for filename in ('libcorelib.a', 'libpresonus_core_allocator.a',
                               'libpresonus_zlib.a'))]
DOMAIN = ('Initialized tag-zero CCL ListParam and real GEQ components with numeric link '
          'tag 32. Compare exact ordered labels and per-GEQ reads for empty, main, '
          'auxiliary, linked and unlinked rosters, mixed links and the original indexed '
          'eight-bit mask boundary. Verify stale list removal, selection restore arguments '
          'with edit false, and resulting pinned-provider clamping for shortened rosters.')
LIMITS = [
    'Original return declaration is unresolved; void models the observed consumer contract.',
    'Native executes the original method at the verified ELF range. Intercepts named '
    'Core append/remove/format and virtual numeric boundaries, and supplies GEQ link '
    'results to the native link-query boundary. The portable replay uses actual CCL '
    'list and numeric provider bodies and actual source-port GEQ components.',
    'Initialized receiver, stable nonnegative roster counts, 0/1 GEQ link values and '
    'bounded integral selector values. Invalid selector guard is a portable choice.',
    'The original mixer constructor/roster wiring, observer callback changes, native '
    'CCL internal state, original object layout, ARM ABI and hardware are outside scope.',
]


def sha(path):
    return digest(Path(path).read_bytes())


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def save(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('format', 'compile', 'symbols', 'replay'))
    parser.add_argument('--object', type=Path, default=OUT / 'GeqUIComponent.o')
    parser.add_argument('--exe', type=Path, default=OUT / 'Replay')
    parser.add_argument('--fixture', type=Path, default=FIXTURE)
    parser.add_argument('--out', type=Path, default=OUT / 'replay-proof.json')
    args = parser.parse_args()
    commands = []

    def invoke(argv):
        start = timestamp()
        argv = list(map(str, argv))
        result = subprocess.run(argv, text=True, capture_output=True)
        commands.append(dict(argv=argv, start_utc=start, end_utc=timestamp(),
                             returncode=result.returncode, stdout=result.stdout,
                             stderr=result.stderr))
        if result.returncode:
            print(result.stderr)
        result.check_returncode()
        return result.stdout

    if args.mode == 'format':
        invoke(FORMAT)
        return
    if args.mode == 'compile':
        beginning = {str(path): sha(path) for path in ARCHIVES}
        args.object.parent.mkdir(parents=True, exist_ok=True)
        invoke([*CXX, '-c', SOURCE, '-o', args.object])
        invoke([*CXX, '-Wl,--gc-sections', REPLAY, args.object, *ARCHIVES, '-pthread',
                '-o', args.exe])
        assert beginning == {str(path): sha(path) for path in ARCHIVES}
        save(OUT / 'compile.json', dict(commands=commands, archives=beginning,
                                        object_sha256=sha(args.object),
                                        executable_sha256=sha(args.exe)))
        return

    original, = (row['original'] for row in json.loads(PACKET.read_text())['originals'])
    mangled = original['mangled']
    for binary in (args.object, args.exe):
        symbols = invoke(['nm', '--defined-only', binary])
        assert any(line.split()[-2:] == ['T', mangled] for line in symbols.splitlines())
    if args.mode == 'symbols':
        return
    invoke(FORMAT)
    native_start = timestamp()
    fixture = json.loads(args.fixture.read_text())
    assert run() == fixture
    native_end = timestamp()
    portable_start = timestamp()
    for case in fixture['cases']:
        expected = [f'link {index}' for index in case['link_indices']]
        expected.extend(f'label {label}' for label in case['labels'])
        selected, edit = case['restore']
        expected.append(f'restore {selected:g} {edit}')
        # Pinned ParamInfo clamps to the final range. An empty mutable list
        # allows the interval -1..0, so a nonnegative selection clamps to zero.
        expected.append(f'selected {min(selected, max(0, len(case["labels"]) - 1)):g}')
        actual = invoke([args.exe.resolve(), case['links'], case['selection']]).splitlines()
        assert actual == expected, (case['links'], case['selection'], actual, expected)
    portable_end = timestamp()

    paths = (SOURCE, HEADER, REPLAY, args.fixture, TEST / 'native.py', TEST / 'check.py',
             Path('uc-library/include/presonus/mixer/GEQComponent.hpp'),
             Path('uc-library/src/Presonus/Mixer/GEQComponent.cpp'),
             Path('uc-library/src/Presonus/Panel/GeqAssignedChannel.cpp'))
    core_paths = [CORE / 'portable' / path for path in
                  ('corecomponent.h', 'corecomponent.cpp', 'coreparams.h', 'coreparams.cpp',
                   'coreparaminfo.h')]
    core_paths.extend(CORE / 'public' / path for path in
                      ('corestringbuffer.h', 'corestringtraits.h'))
    entry = dict(original_elf_sha256=original['elf'], mangled=mangled,
                 original_address=original['address'], domain=DOMAIN,
                 cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
                 declaration_uncertainties=[LIMITS[0]],
                 sources={str(path.resolve().relative_to(Path('uc-library').resolve())): sha(path)
                          for path in paths},
                 repository_sources={str(path): sha(path) for path in core_paths})
    count = len(fixture['cases'])
    proof = dict(version=1, task_id=TASK, functions=[entry],
                 proposed_readiness=dict(ready=[], pending=[entry]),
                 validation_domain=DOMAIN, limitations=LIMITS,
                 cpp_compiled=True, compiled_mangled_names_matched=True,
                 cpp_differential_passed=True, portable_ready=False,
                 original_arm_abi_verified=False, hardware_verified=False,
                 original_ranges=[original], packet=dict(path=str(PACKET), sha256=sha(PACKET)),
                 fixture=dict(path=str(args.fixture), sha256=sha(args.fixture)),
                 direct_calls=fixture['direct_calls'],
                 native_execution=dict(cases=count, executor='Unicorn ARM',
                                       start_utc=native_start, end_utc=native_end),
                 portable_execution=dict(cases=count, start_utc=portable_start,
                                         end_utc=portable_end),
                 executable=dict(path=str(args.exe), sha256=sha(args.exe)),
                 object=dict(path=str(args.object), sha256=sha(args.object)),
                 tools=dict(compiler=invoke(['g++', '--version']).splitlines()[0],
                            formatter=invoke([FORMAT[0], '--version']).strip(),
                            unicorn=unicorn.__version__, pyelftools=elftools.__version__),
                 commands=commands)
    if args.object == OUT / 'GeqUIComponent.o':
        proof['compile'] = json.loads((OUT / 'compile.json').read_text())
    save(args.out, proof)
    print(f'{TASK}: {count} native and portable observations passed')


if __name__ == '__main__':
    main()
