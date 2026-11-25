"""Compile the portable DAW component and compare individual ARM and Linux cases."""

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

from native import digest, observe, packet_path

HERE = Path(__file__).resolve().parent.relative_to(Path.cwd())
SOURCE = 'uc-library/src/Presonus/DAWClientComponent.cpp'
HEADER = 'uc-library/include/presonus/DAWClientComponent.hpp'
REPLAY = str(HERE / 'Replay.cpp')
PYTHON = 'uc-library/.venv/bin/python'
FORMATTER = 'uc-library/.venv/bin/clang-format'
PROJECT = Path('/home/rs/projects/opencs/ai-line-analysis')
CORE_BUILD = PROJECT / 'temp/core-upstream/root-integration-01'
ARCHIVES = [CORE_BUILD / 'upstream-core/sdk/lib' / library
            for library in ('libcorelib.a', 'libpresonus_core_allocator.a')]
LOCAL_PROVIDERS = ['uc-library/src/Presonus/' + unit + '.cpp' for unit in (
    'UC/ClientComponent', 'UC/ClientRootComponent', 'Surface/CapturePageComponent',
    'IDAWTimeInfo', 'DAWChannel', 'DAWChannelGroup', 'DAWDeviceFolder', 'DAWDeviceSlot',
)]
FLAGS = ['c++', '-std=c++17', '-O2', '-fno-lto', '-fno-rtti', '-ffunction-sections',
         '-fdata-sections', '-Iuc-library/include', '-Ithird_party/ccl-framework',
         '-Wno-multichar', '-Ulinux']
WRAP = '-Wl,--wrap=_ZN4Core17FormatterRegistry8optimizeEPPKc'
MODES = ('format', 'compile', 'symbols', 'replay')
TARGET = 'DawClientComponentSqliteReplay'


def sha(path):
    return digest(Path(path).read_bytes())


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class Replay:
    def __init__(self, work):
        self.work = work
        work.mkdir(parents=True, exist_ok=True)
        self.executable = work / 'replay'
        self.units = [SOURCE, REPLAY, *LOCAL_PROVIDERS]
        self.objects = [work / f'{index}.o' for index in range(len(self.units))]
        self.checks = []

    def run(self, *argv):
        argv = list(map(str, argv))
        start = time.monotonic()
        result = subprocess.run(argv, capture_output=True, text=True,
                                env={**os.environ, 'TMPDIR': str(self.work.resolve())})
        self.checks.append(dict(argv=argv, returncode=result.returncode,
                                seconds=time.monotonic()-start, stdout=result.stdout,
                                stderr=result.stderr))
        if result.returncode:
            raise RuntimeError(f'{shlex.join(argv)}\n{result.stdout}{result.stderr}')
        return result.stdout

    def format(self):
        self.run(FORMATTER, '--style=file', '--fallback-style=LLVM', '--dry-run',
                 '--Werror', HEADER, SOURCE, REPLAY)

    def compile(self):
        for source, obj in zip(self.units, self.objects, strict=True):
            self.run(*FLAGS, '-MMD', '-c', source, '-o', obj)
        self.run('c++', *self.objects, WRAP, '-Wl,--gc-sections', '-Wl,--start-group',
                 *ARCHIVES, '-Wl,--end-group', '-lm', '-pthread', '-o', self.executable)

    def symbols(self, packet):
        output = self.run('nm', '--defined-only', self.objects[0])
        symbols = []
        for original in packet['task']['originals']:
            name = original['mangled']
            matches = [line for line in output.splitlines() if line.split()[-1] == name]
            assert len(matches) == 1 and matches[0].split()[-2] == 'T', matches
            symbols.append(matches[0])
        print(symbols[0])
        return symbols

    def compare(self, task, fixture, executable=None):
        recorded = json.loads(fixture.read_text())
        raw = self.run(PYTHON, str(HERE / 'native.py'), task)
        generated = json.loads(raw)
        assert recorded == generated, 'The original ELF observations changed'
        entry = self.checks[-1]
        entry['stdout_sha256'] = digest(raw.encode())
        entry['stdout'] = f'Native replay exactly matches {fixture}'
        outputs = []
        for observation in generated['observations']:
            original = observation['original']
            for case in observation['cases']:
                result = self.run(executable or self.executable, generated['method'],
                                  *case['inputs']).splitlines()
                assert result == case['comparable_output'], (original['role'], generated['method'],
                                                             case, result)
                outputs.append(dict(role=original['role'], inputs=case['inputs'],
                                    portable_result=result))
        print(f'{task} matched {len(outputs)} ARM/portable cases across both roles', flush=True)
        return generated, outputs

    def dependencies(self):
        dependencies = set()
        for obj in self.objects:
            make_dep = obj.with_suffix('.d').read_text().replace('\\\n', ' ')
            dependencies.update(shlex.split(make_dep.split(':', 1)[1]))
        return sorted(dependencies)


def seal(runner, task, reusable_checks, tools, archives, started):
    path = packet_path(task)
    packet = json.loads(path.read_text())
    details = packet['task']
    review = details['review']
    test = Path('uc-library/tests/recovery') / task
    candidate = Path('uc-library/candidates') / task
    fixture = test / 'fixtures.json'
    runner.checks = list(reusable_checks)
    write_json(fixture, observe(task))
    symbols = runner.symbols(packet)
    observed, outputs = runner.compare(task, fixture)
    kinds = {
        str(path): 'packet', SOURCE: 'source', HEADER: 'source', REPLAY: 'test',
        str(HERE / 'check.py'): 'replay', str(HERE / 'native.py'): 'oracle',
        str(fixture): 'fixture',
    }
    for dependency in runner.dependencies() + LOCAL_PROVIDERS:
        kinds.setdefault(dependency, 'dependency')
    for item in review['providers'] + review['evidence']:
        assert sha(item['path']) == item['sha256'], item
    for item in review['providers']:
        kinds.setdefault(item['path'], 'dependency')
    originals = [
        dict(elf_sha256=identity['elf'], **{key: identity[key] for key in
             ('firmware', 'role', 'mangled', 'address', 'size', 'section')})
        for identity in details['originals']
    ]
    domain = f"{review['domain']} {review['oracle_plan']} " \
             f"Matched {len(outputs)} executions across the exact CS18 and RM/RML ranges."
    limitations = [*review['limitations']]
    method = observed['method']
    if method.startswith('get') and method not in ('getFocusChannel', 'getTimeInfo'):
        limitations.append('Provider call arguments and the returned identity are observed at the '
                           'native seam. The Linux replay separately uses actual CCL provider behavior.')
    if method == 'castTo':
        limitations.append('Primary native vtable slot identifies this override of the typed-object '
                           'cast. Secondary casts, thunks and original type layout are outside scope.')
    if method == 'setTimeInfoFactory':
        limitations.append('Opaque aligned factory test tokens are never dereferenced. Native stores '
                           'to the linked role-specific .bss location; portable factory lifetime and '
                           'construction remain outside this method.')
    if method == 'optimize':
        limitations.append('Linux links through an observing wrapper and executes pinned CCL optimize. '
                           'Static versus instance membership is unresolved from the original body.')
    proof_path = candidate / 'worker-proof.json'
    write_json(proof_path, dict(
        version=1, task_id=task, originals=originals, packet_sha256=sha(path),
        source_hashes={dependency: sha(dependency) for dependency in kinds if dependency != str(path)},
        native_case_count=len(outputs), portable_results=outputs,
        native_ranges=[item['original'] for item in observed['observations']],
        provider_ranges=[item['provider'] for item in observed['observations'] if item['provider']],
        vtable_ranges=[item['vtable'] for item in observed['observations'] if item['vtable']],
        exact_compiled_symbol=symbols[0], validation_domain=domain, limitations=limitations,
        canonical_binding_pending=True,
        proposed_classification='ready' if method == 'castTo' else 'declaration-pending',
        compiler=tools['compiler'], formatter=tools['formatter'],
        versions=dict(unicorn=unicorn.__version__, pyelftools=elftools.__version__),
        checks=runner.checks, archives=archives, executable_sha256=sha(runner.executable),
        object_sha256=sha(runner.objects[0]),
        session=dict(provider_thread_id=os.getenv('CODEX_THREAD_ID'),
                     phase_start_utc=started, phase_end_utc=now()),
    ))
    kinds[str(proof_path)] = 'proof'
    write_json(candidate / 'HANDOFF.json', dict(
        version=1, task_id=task, namespace=details['namespace'], packet_manifest=str(path),
        originals=originals, validation_domain=domain, limitations=limitations,
        artifacts=[dict(kind=kind, path=artifact, sha256=sha(artifact))
                   for artifact, kind in kinds.items()],
        checks=[dict(kind=mode, argv=[PYTHON, str(HERE / 'check.py'), mode, task],
                     timeout_seconds=120) for mode in MODES],
        build_integration=dict(
            production_partition='common', production_sources=[SOURCE],
            new_production_sources=[SOURCE], public_headers=[HEADER], test_target=TARGET,
            test_sources=[REPLAY], test_compile_options=['-fno-rtti'],
            test_link_options=[WRAP], link_dependencies=['presonus_cs18_components'],
            ctest_name=task,
            ctest_argv=[PYTHON, str(HERE / 'check.py'), 'replay', task, '--exe',
                        f'$<TARGET_FILE:{TARGET}>', '--fixture', str(fixture)],
            ctest_working_directory='repository root'),
    ))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=(*MODES, 'all'))
    parser.add_argument('task', nargs='+')
    parser.add_argument('--exe', type=Path)
    parser.add_argument('--fixture', type=Path)
    args = parser.parse_args()
    if args.mode != 'all' and len(args.task) != 1:
        parser.error('Only all supports multiple assigned task IDs')
    if args.exe and args.mode != 'replay':
        parser.error('--exe requires replay')
    started = now()
    work = Path('temp/recovery-work/daw-client-replay') / (
        'batch' if len(args.task) > 1 else args.task[0])
    runner = Replay(work)
    task = args.task[0]
    if args.mode == 'all':
        runner.format()
        runner.compile()
        tools = dict(compiler=runner.run('c++', '--version').splitlines()[0],
                     formatter=runner.run(FORMATTER, '--version').strip())
        archives = {str(path): sha(path) for path in ARCHIVES}
        checks = list(runner.checks)
        for item in args.task:
            seal(runner, item, checks, tools, archives, started)
    elif args.mode == 'symbols':
        runner.symbols(json.loads(packet_path(task).read_text()))
    elif args.mode == 'replay':
        fixture = args.fixture or Path('uc-library/tests/recovery') / task / 'fixtures.json'
        runner.compare(task, fixture, args.exe)
    else:
        getattr(runner, args.mode)()


if __name__ == '__main__':
    main()
