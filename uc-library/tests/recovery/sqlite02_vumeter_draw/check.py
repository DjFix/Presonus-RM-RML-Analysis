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

from native import PACKET, PROJECT, TASK, digest, observe

TEST = Path('uc-library/tests/recovery') / TASK
CANDIDATE = Path('uc-library/candidates') / TASK
PYTHON = 'uc-library/.venv/bin/python'
FORMATTER = 'uc-library/.venv/bin/clang-format'
BUILD = PROJECT / 'temp/core-upstream/root-integration-01'
DEPS = PROJECT / 'temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu'
ROLE = 'cs18'
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
    provider = 'uc-library/src/Presonus/PotControl.cpp'
    objects = [work / name for name in ('owner.o', 'test.o', 'provider.o')]
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
        for src, obj in zip((source, replay, provider), objects):
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
            for bitmap, frame in ((True, 2), (False, -1)):
                dirty = bool(case['dirty'])
                result = list(map(int, run([exe, int(dirty), int(bitmap), frame]).split()))
                expected = [case['final_dirty'], 1, 2 if bitmap else 0, int(bitmap)]
                if bitmap:
                    expected += [1, 0, 0, 0, 20, 12, 30, int(dirty), 1]
                assert result == expected, (case, bitmap, expected, result)
                outputs.append(dict(dirty_seed=case['dirty'], bitmap=bitmap,
                                    initial_frame=frame, portable=result))
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
    domain = task['review']['oracle_plan']
    domain += (' Native execution records seeding with 0, 1, and 0xa5, exact callee '
               'entry and return addresses, unchanged event bytes and the subsequent '
               'receiver-byte clear. Linux compares virtual draw through real CCL View '
               'with a qualified PotControl draw reference on the same typed VU state. '
               'A real CCL bitmap renderer executes and observes the selected frame, '
               'bitmap identity and latch state inside rendering. The no-bitmap path '
               'also exercises lazy frame initialization from -1.')
    limitations = [*task['review']['limitations'],
                   'The native PotControl entry is a bounded return seam. Its full '
                   'ARM rendering body and native hardware were outside this replay.']
    target = TASK + '_replay'
    proof_path = CANDIDATE / 'worker-proof.json'
    proof = dict(version=1, task_id=TASK, originals=originals, packet_sha256=sha(PACKET),
                 source_hashes={path: sha(path) for path in kinds if path != str(PACKET)},
                 native_case_count=len(fixture['cases']), portable_results=outputs,
                 native_ranges=[fixture['original']], provider_range=fixture['provider'],
                 exact_compiled_symbol=symbols[0], validation_domain=domain,
                 limitations=limitations, canonical_binding_pending=True,
                 proposed_classification='compiled_declaration_pending',
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
            production_partition='common',
            production_sources=[source], public_headers=[header], new_production_sources=[],
            test_target=target, test_sources=[str(replay)],
            link_dependencies=[f'presonus_{ROLE}_components'],
            ctest_argv=[PYTHON, str(TEST / 'check.py'), 'replay', '--exe',
                        f'$<TARGET_FILE:{target}>', '--fixture', str(config.fixture)],
            ctest_working_directory='repository root')))


if __name__ == '__main__':
    main()
