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

from native import LCD, PACKET, PROJECT, TASK, WHEEL, digest, observe

TEST = Path('uc-library/tests/recovery') / TASK
CANDIDATE = Path('uc-library/candidates') / TASK
SUCCESSOR = Path('temp/recovery-work/rolling-c001-20261124/integration/sqlite-cycle02/wave17-preflight01/guard-successors02/WHEEL-CONTEXT-CURRENT67.json')
PYTHON = 'uc-library/.venv/bin/python'
FORMATTER = 'uc-library/.venv/bin/clang-format'
BUILD = PROJECT / 'temp/core-upstream/root-integration-01'
DEPS = PROJECT / 'temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu'
ROLE = 'cs18' if WHEEL else 'rm'
ARCHIVES = [BUILD / f'libpresonus_{ROLE}_components.a',
            *[BUILD / 'upstream-core/sdk/lib' / name for name in
              ('libcorelib.a', 'libpresonus_core_allocator.a', 'libpresonus_png.a',
               'libpresonus_zlib.a')],
            BUILD / 'private-glibc29-provider/libpresonus_private_glibc29.a']
FLAGS = ['c++', '-std=c++17', '-O2', '-fno-lto', '-ffunction-sections',
         '-fdata-sections', '-Iuc-library/include', '-Ithird_party/ccl-framework',
         '-Wno-multichar', '-Ulinux']


def sha(path):
    return digest(Path(path).read_bytes())


def write_json(path, payload):
    Path(path).write_text(json.dumps(payload, indent=2) + '\n')


def signed(value):
    return value if value < 2**31 else value - 2**32


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
    assert sha(SUCCESSOR) == 'c84353d8fcaaee89945c5c67005ebbae1e2201a3b713514acff55ecd61aa9dbb'
    successor = json.loads(SUCCESSOR.read_text())
    record, = [record for record in successor['records'] if record['task'] == TASK]
    target = packet['originals'][0]['original']
    assert all(record['original'][key] == target[key] for key in ('elf', 'mangled', 'anchor'))
    for path, expected in successor['current_provider_reads'].items():
        assert sha(path) == expected, path
    joint = successor['joint_owned_provider']
    assert sha(joint['path']) == joint['sha256']
    header, source, *_ = task['owned_files']
    replay = TEST / 'Replay.cpp'
    work = Path('temp/recovery-work') / TASK
    work.mkdir(parents=True, exist_ok=True)
    exe = config.exe or work / 'replay'
    objects = [work / 'owner.o', work / 'test.o']
    checks = []

    def run(argv):
        argv = [str(arg) for arg in argv]
        start = time.monotonic()
        result = subprocess.run(argv, text=True, capture_output=True,
                                env={**os.environ, 'TMPDIR': str(work.resolve())})
        checks.append(dict(argv=argv, cwd=str(Path.cwd()), returncode=result.returncode,
                           seconds=time.monotonic() - start,
                           stdout=result.stdout, stderr=result.stderr))
        if result.returncode:
            raise RuntimeError(f'{shlex.join(argv)}\n{result.stdout}{result.stderr}')
        return result.stdout

    if config.mode in ('format', 'all'):
        run([FORMATTER, '--style=file', '--fallback-style=LLVM', '--dry-run',
             '--Werror', header, source, replay])

    if config.mode in ('compile', 'all'):
        for src, obj in zip((source, replay), objects):
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
        for role in fixture:
            for index, case in enumerate(role['cases']):
                if WHEEL:
                    initial = (2, 4, 8, 0, 2)[index]
                    tentative = signed((initial + case['delta']) & 0xffffffff)
                    bounded = min(10, max(0, tentative))
                    if 'groupsedit' not in TASK:
                        bounded &= ~1
                    argv = [exe, case['delta'], initial, index % 2]
                    expected = [bounded, 1, 1]
                else:
                    native_last_level = signed(case['words'][1])
                    assert case['words'][2:6] == [0, 0, 0, 0]
                    argv = [exe, case['input_tag'], case['input_argument']]
                    expected = [case['tag'], native_last_level, 1, 1, 1, 1, 1]
                    if LCD:
                        expected += [1, 1, ord('b'), case['owned_value'] & 0xff, 0x34, 0x12]
                    else:
                        expected += [case['owned_value']]
                result = list(map(int, run(argv).split()))
                assert result == expected, (role['original']['mangled'], argv, expected, result)
                outputs.append(dict(elf_sha256=role['original']['elf'], case=index,
                                    portable=result))
        print(f'{len(outputs)} ARM/portable cases matched')

    if config.mode != 'all':
        return
    kinds = {str(PACKET): 'packet', str(SUCCESSOR): 'operator_context', source: 'source', header: 'source', str(replay): 'test',
             str(TEST / 'check.py'): 'replay', str(TEST / 'native.py'): 'oracle',
             str(config.fixture): 'fixture'}
    for obj in objects:
        make_dep = obj.with_suffix('.d').read_text().replace('\\\n', ' ')
        for dependency in shlex.split(make_dep.split(':', 1)[1]):
            kinds.setdefault(dependency, 'dependency')
    for provider in task['review']['providers']:
        kinds.setdefault(provider['path'], 'dependency')
    actual_reads = {path for path, kind in kinds.items() if kind == 'dependency'}
    allowed_reads = set(successor['current_provider_reads']) | {joint['path']}
    assert actual_reads <= allowed_reads, sorted(actual_reads - allowed_reads)
    peer = dict(joint, inclusion='source' if joint['path'] == header else 'joint_dependency')
    assert joint['path'] in kinds
    originals = [dict(elf_sha256=target['elf'],
                      **{key: target[key] for key in
                         ('firmware', 'role', 'mangled', 'address', 'size', 'section')})
                 for target in task['originals']]
    domain = task['review']['oracle_plan']
    if WHEEL:
        domain += (' Native execution stops at the verified same-class callee entry. '
                   'Portable execution calls the real list implementation with bounded '
                   'visible state observations, using a hidden page for GroupsPageComponent '
                   'and inactive assignment refresh for GroupsEditPageComponent.')
    else:
        domain += (' Native execution captures all receiver stores and independently '
                   'executes the regular Control C2 for the same signed tags in each ELF. '
                   'The native C1/C2 bodies are separately addressed and byte-identical '
                   'within a role. Host C2 is exercised via real derived construction.')
    limitations = task['review']['limitations']
    target = TASK + '_replay'
    proof_path = CANDIDATE / 'worker-proof.json'
    proof = dict(version=1, task_id=TASK, originals=originals, packet_sha256=sha(PACKET),
                 successor_context_sha256=sha(SUCCESSOR), assignment=record['original'],
                 joint_owned_provider=peer,
                 source_hashes={path: sha(path) for path in kinds if path != str(PACKET)},
                 native_case_count=len(outputs), portable_results=outputs,
                 native_ranges=[report['original'] for report in fixture],
                 exact_compiled_symbol=symbols[0], validation_domain=domain,
                 limitations=limitations, canonical_binding_pending=True,
                 proposed_classification='compiled_declaration_pending' if WHEEL else 'ready',
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
        successor_context=str(SUCCESSOR), successor_context_sha256=sha(SUCCESSOR),
        joint_owned_provider=peer,
        artifacts=[dict(kind=kind, path=path, sha256=sha(path)) for path, kind in kinds.items()],
        checks=[dict(kind=mode, argv=[PYTHON, str(TEST / 'check.py'), mode], timeout_seconds=120)
                for mode in ('format', 'compile', 'symbols', 'replay')],
        build_integration=dict(
            production_partition='cs18' if WHEEL else 'common',
            production_sources=[source], public_headers=[header], new_production_sources=[],
            test_target=target, test_sources=[str(replay)],
            link_dependencies=[f'presonus_{ROLE}_components'],
            ctest_argv=[PYTHON, str(TEST / 'check.py'), 'replay', '--exe',
                        f'$<TARGET_FILE:{target}>', '--fixture', str(config.fixture)],
            ctest_working_directory='repository root')))


if __name__ == '__main__':
    main()
