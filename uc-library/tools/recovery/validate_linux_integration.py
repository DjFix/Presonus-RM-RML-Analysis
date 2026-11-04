#!/usr/bin/env python3
"""Run existing full Linux integration/role gates with fresh bound inputs.

This operator never admits or reclassifies reconstructed symbols. Proof production,
readiness admission and trackers remain separate required reconstruction stages.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import sys
import time

import integration_preflight as preflight


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=Path, required=True)
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--additional-list', type=Path, help='Optional extra inputs beyond automatic production/test/tool inventory')
    parser.add_argument('--expected-suites', type=int, required=True)
    parser.add_argument('--source-relocations', type=Path, help='Explicit verified project-trash move manifest for retired integration inputs')
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--install-prefix', type=Path, required=True,
                        help='New install destination under repository temp/')
    args = parser.parse_args()
    root, library, build, out = (p.resolve() for p in
        (args.repository, args.library, args.build, args.evidence))
    assert sys.platform.startswith('linux'), 'Linux is the canonical validation target'
    assert all(p.is_relative_to(root) for p in (library, build, out))
    assert args.jobs > 0 and args.expected_suites > 0
    prefix = args.install_prefix.resolve()
    assert prefix.is_relative_to(root/'temp'), 'Installed-role audit requires a project temp prefix'
    assert not prefix.exists(), 'Use a new isolated install prefix'
    out.mkdir(parents=True, exist_ok=True)
    assert not (out/'commands.json').exists(), 'Use a new evidence directory'
    scratch = out/'tmp'
    scratch.mkdir(exist_ok=True)
    commands = []
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    producer = {'path': str(Path(__file__).resolve().relative_to(root)),
                'sha256': digest(Path(__file__))}
    python = library/'.venv/bin/python'
    cmake = library/'.venv/bin/cmake'
    ctest = library/'.venv/bin/ctest'

    def run(label, argv):
        argv = list(map(str, argv))
        wall, cpu = time.monotonic(), time.process_time()
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        stamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with (out/(label+'.log')).open('x') as log:
            result = subprocess.run(argv, cwd=root,
                env=dict(os.environ, TMPDIR=str(scratch)), stdout=log,
                stderr=subprocess.STDOUT, check=False)
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        commands.append({'label': label, 'argv': argv, 'start_utc': stamp,
            'wall_seconds': time.monotonic()-wall,
            'coordinator_cpu_seconds': time.process_time()-cpu,
            'subprocess_tree_cpu_seconds': (after.ru_utime+after.ru_stime
                                           -before.ru_utime-before.ru_stime),
            'returncode': result.returncode})
        (out/'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
        assert result.returncode == 0, label+' failed; inspect preserved log'

    old = json.loads((library/'validation/integration.json').read_text())
    old_names = set(re.findall(r'Test\s+#\d+: (\S+)\s+\.{2,}',
                              (root/old['test_log']).read_text()))
    assert len(old_names) == old['test_suites'], 'Prior suite names must be observable'
    archived = []
    for name in ('integration.json', 'integration-linux.json'):
        path = library/'validation'/name
        if path.exists():
            destination = out/('prior-'+name)
            with destination.open('xb') as stream:
                stream.write(path.read_bytes())
            assert digest(destination) == digest(path)
            archived.append({'original': str(path.relative_to(root)),
                'archive': str(destination.relative_to(root)), 'sha256': digest(path)})
    (out/'PRIOR_PROVENANCE.json').write_text(json.dumps(archived, indent=2)+'\n')
    additional = json.loads(args.additional_list.read_text()) if args.additional_list else []
    assert isinstance(additional, list) and all(isinstance(p, str) for p in additional)
    frozen = preflight.snapshot(library)
    (out/'source-snapshot.json').write_text(json.dumps(frozen, indent=2)+'\n')
    run('configure', [cmake, '-S', library, '-B', build])
    report = preflight.inspect_configuration(library, build, frozen, additional)
    (out/'preflight.json').write_text(json.dumps(report, indent=2)+'\n')
    additional = sorted(set(report['additional_inputs'] + [
        str(Path(__file__).resolve().relative_to(library))]))
    (out/'additional-effective.json').write_text(json.dumps(additional, indent=2)+'\n')
    run('capture', [python, '-B', library/'tools/capture_integration_inputs.py',
        '--library', library, '--additional-list', out/'additional-effective.json',
        '--expected-suites', args.expected_suites, '--output', out/'inputs.json'] +
        (['--source-relocations', args.source_relocations.resolve()]
         if args.source_relocations else []))
    run('build', [cmake, '--build', build, '--parallel', args.jobs])
    run('inventory', [ctest, '--test-dir', build, '--show-only=json-v1'])
    inventory = json.loads((out/'inventory.log').read_text())
    names = {test['name'] for test in inventory['tests']}
    assert len(names) == len(inventory['tests']) == args.expected_suites
    assert old_names <= names, 'Existing validation suites must not disappear'
    run('tests', [ctest, '--test-dir', build, '--output-on-failure', '--parallel', args.jobs])
    preflight.verify_snapshot(library, frozen)
    run('seal', [python, '-B', library/'tools/seal_integration.py', '--library', library,
        '--repository', root, '--evidence', out, '--platform', 'linux',
        '--baseline', out/'inputs.json', '--output', library/'validation/integration.json'])
    shutil.copyfile(library/'validation/integration.json', library/'validation/integration-linux.json')
    run('install', [cmake, '--install', build, '--prefix', prefix])
    run('role-audit', [python, '-B', library/'tools/recovery/audit_role_build_basic_activity.py',
        root, '--build', build, '--prefix', prefix])
    run('installed-audit', [python, '-B', library/'tools/audit_install.py', '--library', library,
        '--prefix', prefix, '--nm', '/usr/bin/nm', '--output', out/'installed-audit.json',
        '--provider-sdk', build/'upstream-core/sdk'])
    preflight.verify_snapshot(library, frozen)
    assert digest(Path(__file__)) == producer['sha256'], 'Operator changed during validation'
    assert (library/'validation/integration.json').read_bytes() == (library/'validation/integration-linux.json').read_bytes()
    (out/'COMPLETED.json').write_text(json.dumps({'passed': True, 'platform': 'linux',
        'test_suites': args.expected_suites, 'previous_suites_preserved': len(old_names),
        'producer': producer, 'commands': commands, 'start_utc': started,
        'end_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'readiness_admitted': False, 'preflight': {'path': str((out/'preflight.json').relative_to(root)), 'sha256': digest(out/'preflight.json'), 'source_snapshot_sha256': digest(out/'source-snapshot.json')}, 'scope': 'Fresh full Linux build/tests/integration/installed-role and compile-once checks; no readiness admission or classification.'}, indent=2)+'\n')
    print(json.dumps({'passed': True, 'test_suites': args.expected_suites,
                      'readiness_admitted': False}))


if __name__ == '__main__':
    main()
