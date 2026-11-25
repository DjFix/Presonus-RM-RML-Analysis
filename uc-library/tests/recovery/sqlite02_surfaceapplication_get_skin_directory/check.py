"""Compile and replay the exact SurfaceApplication filename return."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shlex
import subprocess
import time

import capstone
import elftools
import unicorn

from native import PACKET, PROJECT, TASK, digest, observe

TEST = Path('uc-library/tests/recovery') / TASK
CANDIDATE = Path('uc-library/candidates') / TASK
WORK = Path('temp/recovery-work') / TASK
PYTHON = 'uc-library/.venv/bin/python'
FORMATTER = 'uc-library/.venv/bin/clang-format'
CORE = PROJECT / 'temp/core-upstream/root-integration-01/upstream-core/sdk/lib'
ARCHIVES = [CORE / name for name in ('libcorelib.a', 'libpresonus_core_allocator.a')]
FLAGS = ['c++', '-std=c++17', '-O2', '-fno-lto', '-fno-rtti', '-ffunction-sections',
         '-fdata-sections', '-Iuc-library/include', '-Ithird_party/ccl-framework',
         '-Ulinux']
DOMAIN = ('Two runs of the original ARM wrapper over independently seeded result and '
          'temporary physical storage. Original instructions forward the null and mapped '
          'literal to the exact CCL constructor entry and request a 256-byte copy through '
          'the actual memcpy PLT slot. Pinned Linux CCL returns independent FileName '
          'values across real current SurfaceApplication expressions, preserving both '
          'serial sentinels and separate result buffers across mutation.')
LIMITATIONS = [
    'Native CCL construction and dynamic memcpy are explicit bound seams. Linux uses '
    'the actual pinned CCL provider. Three verified caller windows use only the '
    'hidden return register, establishing static use in the observed firmware.',
    'Path value scope only. No file access, skin loading, progress command execution, '
    'runtime or hardware behavior, or ARM object layout claim.',
]


def sha(path):
    return digest(Path(path).read_bytes())


def write(path, payload):
    Path(path).write_text(json.dumps(payload, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('all', 'format', 'compile', 'symbols', 'replay'))
    parser.add_argument('--exe', type=Path)
    parser.add_argument('--fixture', type=Path, default=TEST / 'fixtures.json')
    options = parser.parse_args()
    if options.exe and options.mode != 'replay':
        parser.error('--exe requires replay')
    WORK.mkdir(parents=True, exist_ok=True)
    packet = json.loads(PACKET.read_text())
    task = packet['task']
    header, source, *_ = task['owned_files']
    replay = TEST / 'Replay.cpp'
    objects = [WORK / 'owner.o', WORK / 'test.o']
    exe = options.exe or WORK / 'replay'
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    checks = []

    def run(argv):
        argv = [str(arg) for arg in argv]
        start = time.monotonic()
        result = subprocess.run(argv, text=True, capture_output=True,
                                env={**os.environ, 'TMPDIR': str(WORK.resolve())})
        checks.append(dict(argv=argv, cwd=str(Path.cwd()), returncode=result.returncode,
                           seconds=time.monotonic() - start, stdout=result.stdout,
                           stderr=result.stderr))
        if result.returncode:
            raise RuntimeError(f'{shlex.join(argv)}\n{result.stdout}{result.stderr}')
        return result.stdout

    if options.mode in ('format', 'all'):
        run([FORMATTER, '--style=file', '--fallback-style=LLVM', '--dry-run',
             '--Werror', header, source, replay])
    if options.mode in ('compile', 'all'):
        for src, obj in zip((source, replay), objects):
            run([*FLAGS, '-MMD', '-c', src, '-o', obj])
        run(['c++', *objects, '-Wl,--gc-sections', '-Wl,--start-group', *ARCHIVES,
             '-Wl,--end-group', '-ldl', '-pthread', '-o', exe])
    if options.mode in ('symbols', 'all'):
        lines = run(['nm', '--defined-only', objects[0]]).splitlines()
        mangled = task['originals'][0]['mangled']
        symbols = [line for line in lines if line.split()[-1] == mangled]
        assert len(symbols) == 1 and symbols[0].split()[-2] == 'T', symbols
        print(symbols[0])
    if options.mode in ('replay', 'all'):
        fixture = json.loads(options.fixture.read_text())
        assert fixture == observe(), 'Native fixture changed'
        paths = [case['value'] for case in fixture['cases']]
        assert len(set(paths)) == 1 and len(paths) == 2
        path = paths[0]
        expected = [path, path, path[:1] + 'X' + path[2:], path, path, '1 1 1 1 1']
        outputs = run([exe]).splitlines()
        assert outputs == expected, (outputs, expected)
        print('Two native paths matched three independent portable FileName values')
    if options.mode != 'all':
        return

    kinds = {str(PACKET): 'packet', source: 'source', header: 'source', str(replay): 'test',
             str(TEST / 'check.py'): 'replay', str(TEST / 'native.py'): 'oracle',
             str(options.fixture): 'fixture'}
    for obj in objects:
        depfile = obj.with_suffix('.d').read_text().replace('\\\n', ' ')
        for dependency in shlex.split(depfile.split(':', 1)[1]):
            kinds.setdefault(dependency, 'dependency')
    for provider in task['review']['providers']:
        kinds.setdefault(provider['path'], 'dependency')
    originals = [dict(elf_sha256=target['elf'],
                      **{key: target[key] for key in
                         ('firmware', 'role', 'mangled', 'address', 'size', 'section')})
                 for target in task['originals']]
    proof_path = CANDIDATE / 'worker-proof.json'
    proof = dict(
        version=1, task_id=TASK, originals=originals, packet_sha256=sha(PACKET),
        source_hashes={path: sha(path) for path in kinds if path != str(PACKET)},
        native_case_count=len(paths), portable_results=outputs,
        original_range=fixture['original'], constructor_boundary=fixture['constructor_boundary'],
        copy_boundary=fixture['copy_boundary'], direct_callers=fixture['direct_callers'],
        mapped_literal=fixture['mapped_literal'], exact_compiled_symbol=symbols[0],
        validation_domain=DOMAIN, limitations=LIMITATIONS, canonical_binding_pending=True,
        proposed_classification='ready', compiler=run(['c++', '--version']).splitlines()[0],
        formatter=run([FORMATTER, '--version']).strip(),
        versions=dict(unicorn=unicorn.__version__, pyelftools=elftools.__version__,
                      capstone=capstone.__version__),
        checks=checks, archives={str(path): sha(path) for path in ARCHIVES},
        executable_sha256=sha(exe), object_sha256=sha(objects[0]),
        session=dict(provider_thread_id=os.getenv('CODEX_THREAD_ID'), phase_start_utc=started,
                     phase_end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()),
    )
    write(proof_path, proof)
    kinds[str(proof_path)] = 'proof'
    target = TASK + '_replay'
    write(CANDIDATE / 'HANDOFF.json', dict(
        version=1, task_id=TASK, namespace=task['namespace'], packet_manifest=str(PACKET),
        originals=originals, validation_domain=DOMAIN, limitations=LIMITATIONS,
        artifacts=[dict(kind=kind, path=path, sha256=sha(path)) for path, kind in kinds.items()],
        checks=[dict(kind=mode, argv=[PYTHON, str(TEST / 'check.py'), mode], timeout_seconds=120)
                for mode in ('format', 'compile', 'symbols', 'replay')],
        build_integration=dict(
            production_partition='cs18', production_sources=[source], new_production_sources=[source],
            public_headers=[header], test_target=target, test_sources=[str(replay)],
            link_dependencies=['presonus_cs18_components'],
            ctest_argv=[PYTHON, str(TEST / 'check.py'), 'replay', '--exe',
                        f'$<TARGET_FILE:{target}>', '--fixture', str(options.fixture)],
            ctest_working_directory='repository root'),
    ))


if __name__ == '__main__':
    main()
