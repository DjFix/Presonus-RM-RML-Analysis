"""Coordinate an immutable source-graph generation and its Docker projection."""
import argparse
import hashlib
import json
import pathlib
import shlex
import shutil
import sqlite3
import subprocess
import time

from containers import docker

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = ROOT / 'dependency-graph'
BUILD = ROOT / 'temp/core-upstream/root-integration-01'
TARGETS = {'_ZNK8Presonus5Panel16ControlRegistrar5countEv',
           '_ZNK8Presonus5Panel16ControlRegistrar2atEi'}


def sha(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()


def native(run):
    rows = json.loads((run / 'compile_commands.json').read_text())
    start = time.perf_counter()
    observations = []
    missing = []
    for row in rows:
        argv = row.get('arguments') or shlex.split(row['command'])
        obj = pathlib.Path(row['directory']) / argv[argv.index('-o') + 1]
        if not obj.exists():
            missing.append(str(obj))
            continue
        before = sha(obj)
        result = subprocess.run(['nm', '-u', '--format=posix', str(obj)],
                                text=True, capture_output=True, check=True)
        names = {line.split()[0] for line in result.stdout.splitlines() if line.split()}
        assert sha(obj) == before
        observations.append({'source': row['file'], 'object': str(obj),
                             'sha256': before, 'undefined': sorted(names),
                             'target_references': sorted(names & TARGETS)})
    result = {'objects_checked': len(observations), 'missing': missing,
              'target_referencing_units': [r for r in observations if r['target_references']],
              'all_objects': observations, 'seconds': time.perf_counter() - start,
              'scope': 'Undefined-symbol references in current host objects; independent incoming-reference check'}
    path = run / 'native-references.json'
    assert not path.exists()
    path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ('objects_checked', 'missing', 'seconds')}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('prepare', 'probe', 'analyze', 'native', 'ctest'))
    p.add_argument('--run', default='dependency-graph/runs/full-01')
    p.add_argument('--index', type=int, default=0)
    p.add_argument('--delayed-templates', action='store_true')
    p.add_argument('--ast-dir', default='ast')
    p.add_argument('--gcc-evidence-dir')
    p.add_argument('--commands')
    p.add_argument('--host-openssl', action='store_true')
    a = p.parse_args()
    run = (ROOT / a.run).resolve()
    assert run.is_relative_to(BASE / 'runs')
    if a.action == 'prepare':
        run.mkdir(parents=True, exist_ok=False)
        shutil.copy2(pathlib.Path(a.commands) if a.commands else BUILD / 'compile_commands.json', run / 'compile_commands.json')
        return
    if a.action == 'native':
        native(run)
        return
    if a.action == 'ctest':
        output = run / 'ctest-inventory.json'
        assert not output.exists()
        result = subprocess.check_output([str(ROOT / 'uc-library/.venv/bin/ctest'),
                                          '--test-dir', str(BUILD), '--show-only=json-v1'], text=True)
        output.write_text(result)
        return
    source = run / ('extractor-' + str(time.time_ns()) + '.py')
    shutil.copy2(BASE / 'full_source_graph.py', source)
    source.chmod(0o444)
    destination = run / (f'probe-{a.index}-{time.time_ns()}.json' if a.action == 'probe' else a.ast_dir)
    command = ['run', '--name', 'dependency-graph-source-' + str(time.time_ns()),
               '--network=none', '--cpus=2', '--memory=4g',
               '-e', 'DEPENDENCY_GRAPH_ROOT=' + str(ROOT),
               '-v', str(ROOT) + ':' + str(ROOT) + ':ro',
               '-v', str(run) + ':' + str(run) + ':rw',
               '--user', '1000:1000']
    if a.host_openssl:
        for header_dir in ('/usr/include/openssl', '/usr/include/x86_64-linux-gnu/openssl'):
            assert pathlib.Path(header_dir).is_dir()
            command += ['-v', header_dir + ':' + header_dir + ':ro']
    command += ['dependency-graph-analysis:01',
               str(source), '--commands', str(run / 'compile_commands.json'), '--out', str(destination)]
    if a.action == 'probe':
        command += ['--index', str(a.index)]
        if a.delayed_templates:
            command += ['--delayed-templates']
    if a.gcc_evidence_dir:
        command += ['--gcc-evidence-dir', str((ROOT / a.gcc_evidence_dir).resolve())]
    (source.with_suffix('.launch.json')).write_text(json.dumps({
        'argv': command, 'producer_sha256': sha(source),
        'commands_sha256': sha(run / 'compile_commands.json')}, indent=2) + '\n')
    docker(command)


if __name__ == '__main__':
    main()
