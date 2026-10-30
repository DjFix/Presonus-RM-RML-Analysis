#!/usr/bin/env python3
"""Format/build/replay DbTable and seal a root-integration readiness fragment."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('repository', type=Path)
    p.add_argument('--output', default='validation/panel-db-table/replay-01', type=Path)
    args = p.parse_args()
    root = args.repository.resolve()
    library = root / 'uc-library'
    assert not args.output.is_absolute() and '..' not in args.output.parts
    output = library / args.output
    output.mkdir(parents=True, exist_ok=False)
    oracle_dir = library / 'validation/panel-db-table'
    oracle = json.loads((oracle_dir / 'arm-oracle.json').read_text())
    assert sha(oracle_dir / 'arm-vectors.txt') == oracle['vectors_sha256']
    sources = ['include/presonus/surface_panel/DbTable.hpp', 'src/surface_panel/DbTable.cpp',
               'tests/panel_db_table_tests.cpp']
    inputs = sources + ['tools/panel_db_table_oracle.py', 'tools/panel_db_table_validate.py']
    commands = {}
    env = dict(os.environ, TMPDIR=str(root / 'temp/panel-db-table'))

    def run(name, command):
        commands[name] = list(map(str, command))
        (output / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        result = subprocess.run(commands[name], cwd=library, env=env, capture_output=True, text=True)
        (output / (name + '.log')).write_text(result.stdout + result.stderr)
        if result.returncode:
            print(result.stdout + result.stderr, flush=True)
            raise SystemExit(result.returncode)
        return result.stdout

    formatter = library / '.venv/bin/clang-format'
    formatter_version = run('formatter-version', [formatter, '--version']).strip()
    run('format', [formatter, '--style=file', '--fallback-style=LLVM', '-i', *sources])
    run('format-check', [formatter, '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror', *sources])
    flags = ['-std=c++17', '-O2', '-Wall', '-Wextra', '-Wpedantic', '-ffp-contract=off', '-fno-fast-math', '-fno-builtin-powf', '-Iinclude']
    obj, binary = output / 'DbTable.o', output / 'panel_db_table_tests'
    run('compile', ['g++', *flags, '-c', 'src/surface_panel/DbTable.cpp', '-o', obj])
    run('link', ['g++', *flags, 'tests/panel_db_table_tests.cpp', obj, '-lm', '-o', binary])
    result = run('test', [binary, oracle_dir / 'arm-vectors.txt'])
    assert f'PASS: {oracle["total_cases"]} original ARM DbTable differential cases' in result
    nm = run('symbols', ['nm', '-g', '--defined-only', obj])
    defined = {line.split()[-1] for line in nm.splitlines() if line.split()}
    functions = [dict(symbol, role=role, original_elf_sha256=record['sha256'])
                 for role, record in oracle['originals'].items() for symbol in record['functions']]
    expected = {f['mangled'] for f in functions}
    assert expected <= defined, expected - defined
    # ASan/UBSan replay covers only the portable candidate's bounded domain.
    sanitized = output / 'panel_db_table_sanitized'
    run('sanitizer-build', ['g++', *flags, '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                            'src/surface_panel/DbTable.cpp', 'tests/panel_db_table_tests.cpp', '-lm', '-o', sanitized])
    run('sanitizer-test', [sanitized, oracle_dir / 'arm-vectors.txt'])
    hashes = {name: sha(library / name) for name in inputs}
    proof = dict(scope='Presonus::Panel::DbTable portable source reconstruction',
                 functions=functions, mangled_names=sorted(expected), compiled_mangled_names_matched=True,
                 cpp_differential_passed=True, portable_ready=True, counts=oracle['counts'],
                 total_cases=oracle['total_cases'], domain=oracle['domain'], dependency_model=oracle['dependency_model'],
                 sources=hashes, object_sha256=sha(obj), executable_sha256=sha(binary),
                 fixture_reference='validation/panel-db-table/arm-vectors.txt', fixture_sha256=oracle['vectors_sha256'],
                 oracle_metadata_reference='validation/panel-db-table/arm-oracle.json', oracle_metadata_sha256=sha(oracle_dir / 'arm-oracle.json'),
                 format_check_passed=True, formatter=formatter_version, formatting_configuration_sha256=sha(root / '.clang-format'),
                 compiler=run('compiler-version', ['g++', '--version']).splitlines()[0],
                 sanitizer_replay_passed=True, original_arm_object_layout_compatible=False,
                 original_full_verification=False, hardware_verified=False,
                 declaration_uncertainties=[
                     'Original nonconstructor return type spellings are unencoded: portable int query returns match R0; setters/setup use void and ignore original unspecified R0.',
                     'Observed 140-byte ARM field usage informs a standalone portable class; historical field names, full header and general ABI compatibility are not proved.',
                     'Positive setup count must not exceed 16; oversized/overlapping input domains and concurrent mutation are excluded, as is original historical powf behavior.',
                     'Only constructor-written and preserved object bytes are compared; unused array float values are not read by the recovered implementation.',
                     'Build with strict float evaluation, no fast-math or contraction; host powf modeling is explicit and not original Core or libm recovery.'])
    (output / 'reconstruction.json').write_text(json.dumps(proof, indent=2) + '\n')
    reference = (args.output / 'reconstruction.json').as_posix()
    fragment = {'functions': [dict(mangled=f['mangled'], original_elf_sha256=f['original_elf_sha256'],
                                   original_address=f['address'], validation=reference,
                                   validation_sha256=sha(output / 'reconstruction.json'), sources=hashes,
                                   portable_ready=True, domain=oracle['domain'], original_full_verification=False,
                                   hardware_verified=False) for f in functions]}
    (output / 'readiness-records.json').write_text(json.dumps(fragment, indent=2) + '\n')
    print(json.dumps(dict(differential_cases=oracle['total_cases'], exact_mangled_names=len(expected), original_entries=len(functions),
                         proof_sha256=sha(output / 'reconstruction.json'), fragment_sha256=sha(output / 'readiness-records.json')), indent=2), flush=True)


if __name__ == '__main__':
    main()
