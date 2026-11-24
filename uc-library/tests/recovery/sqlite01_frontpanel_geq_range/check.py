"""Build and replay the portable default hook against the measured ARM cases."""
import argparse
import datetime
import json
import os
import pathlib
import shlex
import subprocess
import time

import capstone
import elftools
import unicorn

from native import PACKET, PROJECT, TASK, digest, observe

SOURCE = 'uc-library/src/Presonus/Panel/FrontPanelComponent.cpp'
HEADER = 'uc-library/include/presonus/panel/FrontPanelComponent.hpp'
TEST = f'uc-library/tests/recovery/{TASK}'
CANDIDATE = f'uc-library/candidates/{TASK}'
PYTHON = 'uc-library/.venv/bin/python'
FORMATTER = 'uc-library/.venv/bin/clang-format'
APP_SOURCES = [
    'uc-library/src/Presonus/Panel/FrontPanelLifecycle.cpp',
    'uc-library/src/Presonus/Panel/PanelComponentLifecycle.cpp',
    'uc-library/src/Presonus/Panel/PanelComponent.cpp',
    'uc-library/src/Presonus/DelayTimer.cpp',
]
PEER_INPUTS = [
    'uc-library/include/presonus/panel/BeastFrontPanelComponent.hpp',
    'uc-library/include/presonus/panel/RogueFrontPanelComponent.hpp',
    'uc-library/src/Presonus/Panel/FrontPanelRouting.cpp',
]
CORE_LIB = PROJECT / 'temp/core-upstream/root-integration-01/upstream-core/sdk/lib'
ARCHIVES = [CORE_LIB / name for name in ('libcorelib.a', 'libpresonus_core_allocator.a')]
FLAGS = ['c++', '-std=c++17', '-O2', '-fno-lto', '-fno-rtti',
         '-ffunction-sections', '-fdata-sections', '-Iuc-library/include',
         '-Ithird_party/ccl-framework', '-Wno-multichar', '-Ulinux']
DOMAIN = (
    'Two exact ARM32 executions with different synthetic receiver seeds, preserving '
    'the receiver and stack canaries, returning r0=0 and making only frame accesses. '
    'Two typed Linux executions use an existing FrontPanelComponent constructor and '
    'actual CCL integer parameters at 0 and 30. Observed false, intact receiver, '
    'port state and CCL parameter bytes, plus zero dependency calls. The original '
    'base and peer vtable entries and two original call-site windows were checked.'
)
LIMITATIONS = [
    'Original vtable relationships establish virtual membership; the original exact '
    'return spelling remains unresolved. bool is the portable predicate declaration.',
    'ARM32 layout, full native construction and caller execution, and hardware behavior '
    'are outside the validated domain. Native receivers were safely seeded for this '
    'routine; no receiver field was read or written. No external execution stubs.',
]


def sha(path):
    return digest(pathlib.Path(path).read_bytes())


def write_json(path, payload):
    pathlib.Path(path).write_text(json.dumps(payload, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('all', 'format', 'compile', 'symbols', 'replay'))
    parser.add_argument('--exe', type=pathlib.Path)
    parser.add_argument('--fixture', type=pathlib.Path, default=pathlib.Path(TEST) / 'fixtures.json')
    options = parser.parse_args()
    if options.exe and options.mode != 'replay':
        parser.error('--exe is supported only by replay')
    work = pathlib.Path('temp/recovery-work') / TASK
    work.mkdir(parents=True, exist_ok=True)
    objects = [work / f'{i}.o' for i in range(2 + len(APP_SOURCES))]
    exe = options.exe or work / 'replay'
    checks = []
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    task = json.loads(PACKET.read_text())['task']
    target = task['originals'][0]

    def run(argv):
        argv = [str(arg) for arg in argv]
        start = time.monotonic()
        result = subprocess.run(argv, text=True, capture_output=True,
                                env={**os.environ, 'TMPDIR': str(work.resolve())})
        checks.append(dict(argv=argv, returncode=result.returncode,
                           seconds=time.monotonic() - start,
                           stdout=result.stdout, stderr=result.stderr))
        if result.returncode:
            raise RuntimeError(f'{shlex.join(argv)}\n{result.stdout}{result.stderr}')
        return result.stdout

    if options.mode in ('all', 'format'):
        run([FORMATTER, '--style=file', '--fallback-style=LLVM', '--dry-run',
             '--Werror', SOURCE, HEADER, f'{TEST}/Replay.cpp'])

    if options.mode in ('all', 'compile'):
        for src, obj in zip([SOURCE, f'{TEST}/Replay.cpp', *APP_SOURCES], objects):
            run([*FLAGS, '-MMD', '-c', src, '-o', obj])
        run(['c++', *objects, '-Wl,--gc-sections', '-Wl,--start-group',
             *ARCHIVES, '-Wl,--end-group', '-lpthread', '-ldl', '-lz', '-o', exe])

    if options.mode in ('all', 'symbols'):
        output = run(['nm', '--defined-only', objects[0]])
        symbols = [line for line in output.splitlines() if line.split()[-1] == target['mangled']]
        assert len(symbols) == 1 and symbols[0].split()[-2] == 'T', symbols
        print(symbols[0])

    if options.mode in ('all', 'replay'):
        fixture = json.loads(options.fixture.read_text())
        assert fixture == observe(), 'The original ELF observations changed'
        outputs = []
        for case in fixture['cases']:
            assert case['receiver_preserved']
            output = run([exe, case['offset'], case['selected']]).strip()
            assert output == f"{case['result']} 1 1 1 0", output
            outputs.append(output)
        print(f'{len(outputs)} ARM/portable cases matched')

    if options.mode == 'all':
        cpp_inputs = set(PEER_INPUTS)
        for obj in objects:
            dep = obj.with_suffix('.d').read_text().replace('\\\n', ' ')
            cpp_inputs.update(shlex.split(dep.split(':', 1)[1]))
        producers = [f'{TEST}/{name}' for name in ('native.py', 'check.py', 'fixtures.json')]
        source_hashes = {path: sha(path) for path in sorted(cpp_inputs | set(producers))}
        originals = [{
            'elf_sha256': target['elf'],
            **{key: target[key] for key in ('firmware', 'role', 'mangled', 'address', 'size', 'section')},
        }]
        proof_path = f'{CANDIDATE}/worker-proof.json'
        proof = dict(
            version=1, task_id=TASK, originals=originals, source_hashes=source_hashes,
            original_range=fixture['original'], native_case_count=len(fixture['cases']),
            portable_results=outputs, exact_compiled_symbol=symbols[0],
            validation_domain=DOMAIN, limitations=LIMITATIONS,
            formatter=run([FORMATTER, '--version']).strip(),
            compiler=run(['c++', '--version']).splitlines()[0],
            versions=dict(unicorn=unicorn.__version__, capstone=capstone.__version__,
                          pyelftools=elftools.__version__),
            checks=checks, archives={str(path): sha(path) for path in ARCHIVES},
            executable_sha256=sha(exe), object_sha256=sha(objects[0]),
            proposed_classification='compiled_declaration_pending',
            canonical_binding_pending=True, packet_sha256=sha(PACKET),
            session=dict(provider_thread_id=os.getenv('CODEX_THREAD_ID'),
                         phase_start_utc=started,
                         phase_end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()),
        )
        write_json(proof_path, proof)
        kinds = {SOURCE: 'source', HEADER: 'source', f'{TEST}/Replay.cpp': 'test',
                 f'{TEST}/native.py': 'oracle', f'{TEST}/check.py': 'replay',
                 f'{TEST}/fixtures.json': 'fixture', proof_path: 'proof', str(PACKET): 'packet'}
        for path in source_hashes:
            kinds.setdefault(path, 'dependency')
        write_json(f'{CANDIDATE}/HANDOFF.json', dict(
            version=1, task_id=TASK, namespace=task['namespace'], packet_manifest=str(PACKET),
            originals=originals, validation_domain=DOMAIN, limitations=LIMITATIONS,
            artifacts=[dict(kind=kind, path=path, sha256=sha(path))
                       for path, kind in kinds.items()],
            checks=[dict(kind=mode, argv=[PYTHON, f'{TEST}/check.py', mode],
                         timeout_seconds=120) for mode in ('format', 'compile', 'symbols', 'replay')],
            build_integration=dict(
                production_partition='rm', production_sources=[SOURCE], public_headers=[HEADER],
                new_production_sources=[], test_target='FrontPanelGeqViewRangeReplay',
                test_sources=[f'{TEST}/Replay.cpp'], link_dependencies=['presonus_rm_components'],
                ctest_argv=[PYTHON, f'{TEST}/check.py', 'replay', '--exe',
                            '$<TARGET_FILE:FrontPanelGeqViewRangeReplay>',
                            '--fixture', f'{TEST}/fixtures.json'],
                ctest_working_directory='repository root',
            ),
        ))


if __name__ == '__main__':
    main()
