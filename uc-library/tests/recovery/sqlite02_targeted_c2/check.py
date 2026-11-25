"""Build and replay the exact packet against its observed native fixture."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shlex
import subprocess
import time

import elftools
import unicorn

from native import PACKET, PROJECT, TARGETED, TASK, digest, observe

TEST = Path('uc-library/tests/recovery') / TASK
CANDIDATE = Path('uc-library/candidates') / TASK
PYTHON = 'uc-library/.venv/bin/python'
FORMATTER = 'uc-library/.venv/bin/clang-format'
BUILD = PROJECT / 'temp/core-upstream/root-integration-01'
DEPS = PROJECT / 'temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu'
ROLE = 'rm' if TARGETED else 'cs18'
ARCHIVES = [BUILD / f'libpresonus_{ROLE}_components.a',
            *[BUILD / 'upstream-core/sdk/lib' / name for name in
              ('libcorelib.a', 'libpresonus_core_allocator.a', 'libpresonus_png.a',
               'libpresonus_zlib.a')],
            BUILD / 'private-glibc29-provider/libpresonus_private_glibc29.a']
FLAGS = ['c++', '-std=c++17', '-O2', '-fno-lto', '-fno-rtti', '-ffunction-sections',
         '-fdata-sections', '-Iuc-library/include', '-Ithird_party/ccl-framework',
         '-Wno-multichar', '-Ulinux']


def sha(path):
    return digest(Path(path).read_bytes())


def write_json(path, payload):
    Path(path).write_text(json.dumps(payload, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('all', 'format', 'compile', 'symbols', 'replay'))
    parser.add_argument('--exe', type=Path)
    parser.add_argument('--fixture', type=Path, default=TEST / 'fixtures.json')
    config = parser.parse_args()
    if config.exe and config.mode != 'replay':
        parser.error('--exe requires replay')
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    packet = json.loads(PACKET.read_text())
    task = packet['task']
    header, source, *_ = task['owned_files']
    replay = TEST / 'Replay.cpp'
    work = Path('temp/recovery-work') / TASK
    work.mkdir(parents=True, exist_ok=True)
    exe = config.exe or work / 'replay'
    sources = [source, replay]
    if TARGETED:
        sources.append('uc-library/src/Presonus/UC/ServerComponent.cpp')
    objects = [work / f'{index}.o' for index in range(len(sources))]
    checks = []

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

    if config.mode in ('format', 'all'):
        run([FORMATTER, '--style=file', '--fallback-style=LLVM', '--dry-run',
             '--Werror', header, source, replay])

    if config.mode in ('compile', 'all'):
        for src, obj in zip(sources, objects):
            run([*FLAGS, '-MMD', '-c', src, '-o', obj])
        run(['c++', *objects, '-Wl,--gc-sections', '-Wl,--start-group',
             *ARCHIVES, '-Wl,--end-group', DEPS / 'libdns_sd.so',
             f'-Wl,-rpath,{DEPS}', '-lssl', '-lcrypto', '-ldl', '-lm', '-pthread',
             '-o', exe])

    if config.mode in ('symbols', 'all'):
        output = run(['nm', '--defined-only', objects[0]])
        mangled = task['originals'][0]['mangled']
        symbols = [line for line in output.splitlines() if line.split()[-1] == mangled]
        assert len(symbols) == 1 and symbols[0].split()[-2] == 'T', symbols
        print(symbols[0])

    if config.mode in ('replay', 'all'):
        fixture = json.loads(config.fixture.read_text())
        assert fixture == observe(), 'The original ELF observations changed'
        outputs = []
        for case in fixture['cases']:
            observed = case['result']
            if TARGETED:
                phase = 2 if TASK.endswith('_c2') else 0
                expected = [1, observed['pending'], 0, 0, phase, 0, phase, 1, 0]
                argv = [exe, observed['name']]
            else:
                expected = [bool(observed['owner']), bool(observed['source']),
                            observed['count'] == 0, observed['capacity'], observed['count'],
                            observed['delta'], observed['delta'], 1, 1, 0, 1, 1]
                argv = [exe]
            result = list(map(int, run(argv).split()))
            assert result == expected, (case, expected, result)
            outputs.append(dict(native_receiver=case['receiver'], portable=result))
        print(f'{len(outputs)} ARM/portable cases matched')

    if config.mode != 'all':
        return
    kinds = {str(PACKET): 'packet', source: 'source', header: 'source', str(replay): 'test',
             str(TEST / 'check.py'): 'replay', str(TEST / 'native.py'): 'oracle',
             str(config.fixture): 'fixture'}
    for obj in objects:
        make_dep = obj.with_suffix('.d').read_text().replace('\\\n', ' ')
        for dependency in shlex.split(make_dep.split(':', 1)[1]):
            kinds.setdefault(dependency, 'dependency')
    for provider in task['review']['providers']:
        kinds.setdefault(provider['path'], 'dependency')
    originals = [dict(elf_sha256=target['elf'],
                      **{key: target[key] for key in
                         ('firmware', 'role', 'mangled', 'address', 'size', 'section')})
                 for target in task['originals']]
    if TARGETED:
        domain = ('Three exact native executions for empty, main, and space-bearing live names. '
                  'The real application ServerComponent base body executes and forwards the '
                  'same pointer to the verified original Core constructor entry, bounded at '
                  'that external Core seam. The subsequent dispatch selection and latch writes '
                  'are captured. Real CCL name and pending-state behavior are checked in Linux, '
                  'including the inherited base-subobject path for C2 and preserved tagged construction.')
        limitations = [*task['review']['limitations'],
                       'Native Core constructor body and ServerComponent side fields are outside '
                       'the portable comparison. The CCL name is read from the actual pinned '
                       'source-owned Component, with no replacement provider.']
    else:
        domain = ('Three exact ARM runs on distinct nonzero canaries for this separately addressed '
                  'constructor variant. Direct native resize receives the vector at +8 and '
                  'capacity zero; the verified native resize executes its empty-state return. '
                  'Real pinned CCL vector construction starts empty and grows to capacity five '
                  'at the first one-item request. Typed borrowed component survives clipboard '
                  'destruction; C2 uses real derived construction.')
        limitations = [*task['review']['limitations'],
                       'The packet labels +0x18 an independent mode. The original paste routine '
                       'constructs a stand-alone stack vector with the identical vptr/zero fields/'
                       'five sequence before the same resize, and pinned Vector declares delta '
                       'after capacity. The source port uses its real vector growth delta. '
                       'Native app init/copy store actual Component pointers at the two outer '
                       'words. Copy/paste operations themselves remain outside this proof.']
    target = TASK + '_replay'
    proof_path = CANDIDATE / 'worker-proof.json'
    proof = dict(version=1, task_id=TASK, originals=originals, packet_sha256=sha(PACKET),
                 source_hashes={path: sha(path) for path in kinds if path != str(PACKET)},
                 native_case_count=len(fixture['cases']), portable_results=outputs,
                 native_ranges=[fixture['original']], provider_range=fixture['provider'],
                 exact_compiled_symbol=symbols[0], validation_domain=domain,
                 limitations=limitations, canonical_binding_pending=True,
                 proposed_classification='ready',
                 compiler=run(['c++', '--version']).splitlines()[0],
                 formatter=run([FORMATTER, '--version']).strip(),
                 versions=dict(unicorn=unicorn.__version__, pyelftools=elftools.__version__),
                 checks=checks, archives={str(path): sha(path) for path in ARCHIVES},
                 executable_sha256=sha(exe), object_sha256=sha(objects[0]),
                 session=dict(provider_thread_id=os.getenv('CODEX_THREAD_ID'),
                              phase_start_utc=started,
                              phase_end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    write_json(proof_path, proof)
    kinds[str(proof_path)] = 'proof'
    write_json(CANDIDATE / 'HANDOFF.json', dict(
        version=1, task_id=TASK, namespace=task['namespace'], packet_manifest=str(PACKET),
        originals=originals, validation_domain=domain, limitations=limitations,
        artifacts=[dict(kind=kind, path=path, sha256=sha(path)) for path, kind in kinds.items()],
        checks=[dict(kind=mode, argv=[PYTHON, str(TEST / 'check.py'), mode], timeout_seconds=120)
                for mode in ('format', 'compile', 'symbols', 'replay')],
        build_integration=dict(
            production_partition=ROLE,
            production_sources=[source], public_headers=[header], new_production_sources=[],
            test_target=target, test_sources=[str(replay)],
            link_dependencies=[f'presonus_{ROLE}_components'],
            ctest_argv=[PYTHON, str(TEST / 'check.py'), 'replay', '--exe',
                        f'$<TARGET_FILE:{target}>', '--fixture', str(config.fixture)],
            ctest_working_directory='repository root')))


if __name__ == '__main__':
    main()
