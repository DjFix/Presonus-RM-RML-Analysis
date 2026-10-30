#!/usr/bin/env python3
"""Verify the sealed, VM-formatted DbTable source port with actual Apple tools."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository', type=Path)
    args = parser.parse_args()
    root = args.repository.resolve()
    library = root / 'temp/recovery-package/uc-library'
    directory = library / 'validation/panel-db-table/mac-01'
    directory.mkdir(parents=True, exist_ok=False)
    linux_path = library / 'validation/panel-db-table/replay-01/reconstruction.json'
    linux = json.loads(linux_path.read_text())
    assert all(sha(library / name) == value for name, value in linux['sources'].items())
    assert linux['format_check_passed']
    fixture = library / linux['fixture_reference']
    assert sha(fixture) == linux['fixture_sha256']
    commands = {}
    env = dict(os.environ, TMPDIR=str(root / 'temp/panel-db-table'))

    def run(name, command):
        commands[name] = list(map(str, command))
        (directory / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        result = subprocess.run(commands[name], cwd=library, env=env, capture_output=True, text=True)
        (directory / (name + '.log')).write_text(result.stdout + result.stderr)
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout

    flags = ['-std=c++17', '-O2', '-Wall', '-Wextra', '-Wpedantic', '-ffp-contract=off', '-fno-fast-math', '-fno-builtin-powf', '-Iinclude']
    obj = directory / 'DbTable.o'
    binary = directory / 'panel_db_table_tests'
    run('compile', ['/usr/bin/clang++', *flags, '-c', 'src/surface_panel/DbTable.cpp', '-o', obj])
    run('link', ['/usr/bin/clang++', *flags, 'tests/panel_db_table_tests.cpp', obj, '-o', binary])
    result = run('test', [binary, fixture])
    assert f'PASS: {linux["total_cases"]} original ARM DbTable differential cases' in result
    nm = run('symbols', ['/usr/bin/nm', '-gU', obj])
    names = {line.split()[-1][1:] for line in nm.splitlines() if line.split() and line.split()[-1].startswith('_')}
    assert set(linux['mangled_names']) <= names
    proof = dict(scope=linux['scope'], platform='macOS native portable source port',
                 linux_proof_reference='validation/panel-db-table/replay-01/reconstruction.json', linux_proof_sha256=sha(linux_path),
                 sources=linux['sources'], tool_sha256=sha(Path(__file__)), cpp_differential_passed=True,
                 compiled_mangled_names_matched=True, mangled_names=linux['mangled_names'], total_cases=linux['total_cases'],
                 fixture_sha256=sha(fixture), object_sha256=sha(obj), executable_sha256=sha(binary),
                 compiler=run('compiler-version', ['/usr/bin/clang++', '--version']).splitlines()[0],
                 domain=linux['domain'], dependency_model=linux['dependency_model'],
                 original_full_verification=False, original_arm_abi_compatible=False, hardware_verified=False)
    path = directory / 'reconstruction.json'
    path.write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps(dict(mac_proof_sha256=sha(path), differential_cases=linux['total_cases'], exact_mangled_names=len(linux['mangled_names'])), indent=2))


if __name__ == '__main__':
    main()
