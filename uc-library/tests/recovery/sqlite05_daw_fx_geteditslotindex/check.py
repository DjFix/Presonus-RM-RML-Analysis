"""Compile and compare DawFxPageComponent against sealed ARM observations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from native import PACKET, ROOT, TASK, observe

TEST = Path('uc-library/tests/recovery') / TASK
CANDIDATE = Path('uc-library/candidates') / TASK
SOURCE = Path('uc-library/src/Presonus/Surface/DawFxPageComponent.cpp')
HEADER = Path('uc-library/include/presonus/surface/DawFxPageComponent.hpp')
REPLAY = TEST / 'Replay.cpp'
FIXTURE = TEST / 'fixtures.json'
SCRATCH = Path('temp/recovery-work/sqlite05-worker-daw-fx-page') / TASK
OBJECT = SCRATCH / 'DawFxPageComponent.o'
DEPFILE = SCRATCH / 'DawFxPageComponent.d'
EXE = SCRATCH / 'Replay'
PYTHON = 'uc-library/.venv/bin/python'
FORMATTER = 'uc-library/.venv/bin/clang-format'
FORMAT = [FORMATTER, '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror',
          *map(str, (SOURCE, HEADER, REPLAY))]
SDK = ROOT / 'temp/core-upstream/root-integration-01/upstream-core/sdk'
CXX = ['/usr/bin/c++', '-std=c++20', '-O2', '-ffunction-sections', '-fdata-sections',
       '-Ulinux', '-fno-rtti', '-fno-sized-deallocation', '-DPRESONUS_HAS_UPSTREAM_CORE=1',
       '-DCORE_USE_OPENSSL=1', '-DNDEBUG=1', '-Iuc-library/include',
       '-isystem', str(SDK / 'include/presonus-core-5')]
FOLDER = Path('uc-library/src/Presonus/DAWDeviceFolder.cpp')
SLOT = Path('uc-library/src/Presonus/DAWDeviceSlot.cpp')
OBJECTS = [OBJECT, SCRATCH / 'Folder.o', SCRATCH / 'Slot.o']
DEPFILES = [DEPFILE, SCRATCH / 'Folder.d', SCRATCH / 'Slot.d', SCRATCH / 'Replay.d']
COMPILE = [[*CXX, '-MD', '-MF', str(depfile), '-c', str(source), '-o', str(obj)]
           for source, obj, depfile in zip((SOURCE, FOLDER, SLOT), OBJECTS, DEPFILES)]
BUILD = ROOT / 'temp/core-upstream/root-integration-01'
ARCHIVES = [BUILD / 'libpresonus_cs18_components.a',
            *(SDK / 'lib' / name for name in ('libcorelib.a', 'libpresonus_core_allocator.a',
                                             'libpresonus_png.a', 'libpresonus_zlib.a')),
            BUILD / 'private-glibc29-provider/libpresonus_private_glibc29.a']
LINK = [*CXX, '-MD', '-MF', str(DEPFILES[-1]), '-Wl,--gc-sections',
        str(REPLAY), *map(str, OBJECTS), *map(str, ARCHIVES),
        '-lssl', '-lcrypto', '-ldl', '-lm', '-pthread', '-o', str(EXE)]
TASK_DATA = json.loads(PACKET.read_text())['task']
DOMAIN = TASK_DATA['review']['domain'] + ' ' + TASK_DATA['review']['oracle_plan']
LIMITS = [
    *TASK_DATA['review']['limitations'],
    'ARM replay executes the verified target and application dependencies, models strcmp '
    'and Core parameter dispatch at their entries, and checks target-side non-stack writes.',
    'Portable replay uses pinned CCL storage and NumericParam, compiles Folder and Slot '
    'from current source, and checks active offset, child order and edit parameters for mutation.',
]
DEPENDENCIES = [
    'third_party/ccl-framework/core/portable/corecomponent.h',
    'third_party/ccl-framework/core/portable/corecomponent.cpp',
    'third_party/ccl-framework/core/portable/coreparams.h',
    'third_party/ccl-framework/core/portable/coreparams.cpp',
    'third_party/ccl-framework/core/portable/gui/coreview.h',
    'uc-library/include/presonus/DAWDeviceFolder.hpp',
    'uc-library/include/presonus/DAWDeviceSlot.hpp',
    'uc-library/include/presonus/uc/ClientComponent.hpp',
    'uc-library/src/Presonus/Surface/DawFxPageMapping.cpp',
    str(FOLDER), str(SLOT),
]


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
    target, = fixture['targets']
    rows = []
    for case in target['cases']:
        inputs = case['inputs']
        slot = inputs['slot'] if inputs['slot'] is not None else -2
        rows.append(' '.join(map(str, (int(TASK.endswith('calcautoscroll')),
                                      int(inputs['folder']), inputs['name'], inputs['used'],
                                      slot, inputs['send'], *inputs['offsets'],
                                      len(inputs['values']), *inputs['values']))))
    observed = list(map(int, subprocess.check_output(
        [str(exe)], input='\n'.join(rows) + '\n', text=True).splitlines()))
    expected = [case['result'] for case in target['cases']]
    assert observed == expected, (observed, expected)
    print(f'{TASK}: {len(expected)} portable observations matched ARM')
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
        for command in (*COMPILE, LINK):
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
    dependencies = {path: sha(path) for path in DEPENDENCIES}
    sources = {str(path.relative_to('uc-library')): sha(path) for path in (SOURCE, HEADER)}
    pending = [dict(original_elf_sha256=original['elf_sha256'], mangled=original['mangled'],
                    cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
                    sources=sources, repository_sources=dependencies,
                    validation_domain=DOMAIN, declaration_uncertainties=LIMITS)
               for original in originals]
    proof = CANDIDATE / 'worker-proof.json'
    dump(proof, dict(task_id=TASK, originals=originals, native=fixture,
                     fixture_sha256=sha(args.fixtures), portable=observations,
                     object_sha256=sha(args.object), exe_sha256=sha(args.exe),
                     depfiles={str(path): sha(path) for path in DEPFILES},
                     compile_argv=COMPILE, link_argv=LINK,
                     link_input_hashes={str(path): sha(path) for path in (*OBJECTS, *ARCHIVES)},
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
                 proof: 'proof', PACKET: 'packet',
                 **{path: 'dependency' for path in dependencies}}
    argv = [PYTHON, '-B', str(TEST / 'check.py')]
    dump(CANDIDATE / 'HANDOFF.json', dict(version=1, task_id=TASK,
         namespace='Presonus::Surface::DawFxPageComponent', packet_manifest=str(PACKET), originals=originals,
         artifacts=[dict(path=str(path), kind=kind, sha256=sha(path))
                    for path, kind in artifacts.items()],
         checks=[dict(kind=kind, argv=[*argv, kind], timeout_seconds=120)
                 for kind in ('format', 'compile', 'symbols', 'native', 'replay')],
         validation_domain=DOMAIN, limitations=LIMITS,
         build_integration=dict(partition='CS18 (existing DawFxPageComponent.cpp)',
                                public_headers=[str(HEADER)], test_target=TASK,
                                link_dependencies=['presonus_cs18_components'],
                                ctest_argv=[*argv, 'replay', '--exe', f'$<TARGET_FILE:{TASK}>',
                                            '--fixtures', str(args.fixtures)], test_sources=[str(REPLAY)])))


if __name__ == '__main__':
    main()
