#!/usr/bin/env python3
"""Replay MeterControl original ARM fixtures against a strict-float source port."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('repository', type=Path)
    p.add_argument('--platform', choices=('linux', 'mac'), default='linux')
    args = p.parse_args()
    root = args.repository.resolve()
    library = root / ('uc-library' if args.platform == 'linux' else 'temp/recovery-package/uc-library')
    rel = Path('validation/panel-meter-control') / ('replay-01' if args.platform == 'linux' else 'mac-01')
    out = library / rel
    out.mkdir(parents=True, exist_ok=False)
    oracle_dir = library / 'validation/panel-meter-control'
    oracle = json.loads((oracle_dir / 'arm-oracle.json').read_text())
    fixture = oracle_dir / 'arm-vectors.txt'
    assert sha(fixture) == oracle['vectors_sha256']
    db_proof_path = library / 'validation/panel-db-table/replay-01/reconstruction.json'
    db_proof = json.loads(db_proof_path.read_text())
    assert all(sha(library / name) == value for name, value in db_proof['sources'].items())
    new_cpp = ['include/presonus/surface_panel/MeterControl.hpp', 'src/surface_panel/MeterControl.cpp', 'tests/panel_meter_control_tests.cpp']
    inputs = new_cpp + ['include/presonus/surface_panel/DbTable.hpp', 'src/surface_panel/DbTable.cpp',
                        'tools/panel_db_table_oracle.py', 'tools/panel_meter_control_oracle.py', 'tools/panel_meter_control_validate.py']
    env = dict(os.environ, TMPDIR=str(root / 'temp/panel-meter-control'))
    (root / 'temp/panel-meter-control').mkdir(parents=True, exist_ok=True)
    commands = {}

    def run(name, command):
        commands[name] = list(map(str, command))
        (out / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        result = subprocess.run(commands[name], cwd=library, env=env, capture_output=True, text=True)
        (out / (name + '.log')).write_text(result.stdout + result.stderr)
        if result.returncode:
            print(result.stdout + result.stderr, flush=True)
            raise SystemExit(result.returncode)
        return result.stdout

    if args.platform == 'linux':
        formatter = library / '.venv/bin/clang-format'
        formatter_version = run('formatter-version', [formatter, '--version']).strip()
        run('format', [formatter, '--style=file', '--fallback-style=LLVM', '-i', *new_cpp])
        run('format-check', [formatter, '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror', *new_cpp])
    else:
        linux_path = library / 'validation/panel-meter-control/replay-01/reconstruction.json'
        linux = json.loads(linux_path.read_text())
        assert all(sha(library / name) == value for name, value in linux['sources'].items())
        assert linux['format_check_passed']
        formatter_version = linux['formatter']
    compiler = 'g++' if args.platform == 'linux' else '/usr/bin/clang++'
    flags = ['-std=c++17', '-O2', '-Wall', '-Wextra', '-Wpedantic', '-ffp-contract=off', '-fno-fast-math', '-fno-builtin-powf', '-Iinclude']
    obj, db_obj, binary = out / 'MeterControl.o', out / 'DbTable.o', out / 'panel_meter_control_tests'
    run('compile', [compiler, *flags, '-c', 'src/surface_panel/MeterControl.cpp', '-o', obj])
    run('compile-db', [compiler, *flags, '-c', 'src/surface_panel/DbTable.cpp', '-o', db_obj])
    run('link', [compiler, *flags, 'tests/panel_meter_control_tests.cpp', obj, db_obj,
                 *(['-lm'] if args.platform == 'linux' else []), '-o', binary])
    result = run('test', [binary, fixture])
    assert f'PASS: {oracle["total_cases"]} original ARM MeterControl differential cases' in result
    nm = run('symbols', ['nm', '-g', '--defined-only', obj] if args.platform == 'linux' else ['/usr/bin/nm', '-gU', obj])
    names = {line.split()[-1][1:] if args.platform == 'mac' else line.split()[-1] for line in nm.splitlines() if line.split()}
    functions = [dict(s, role=role, original_elf_sha256=record['sha256'])
                 for role, record in oracle['originals'].items() for s in record['functions']]
    expected = {s['mangled'] for s in functions}
    data = {s['mangled'] for record in oracle['originals'].values() for s in record['data_symbols'].values()}
    assert expected | data <= names, (expected | data) - names
    if args.platform == 'linux':
        sanitized = out / 'panel_meter_control_sanitized'
        run('sanitizer-build', [compiler, *flags, '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                                'src/surface_panel/MeterControl.cpp', 'src/surface_panel/DbTable.cpp', 'tests/panel_meter_control_tests.cpp', '-lm', '-o', sanitized])
        run('sanitizer-test', [sanitized, fixture])
    proof = dict(scope='Presonus::Panel::MeterControl partial state/configuration source port', platform=args.platform,
                 functions=functions, mangled_names=sorted(expected), compiled_mangled_names_matched=True,
                 compiled_data_mangled_names_matched=sorted(data), cpp_differential_passed=True, portable_ready=True,
                 counts=oracle['counts'], total_cases=oracle['total_cases'], domain=oracle['domain'], dependency_model=oracle['dependency_model'],
                 sources={name: sha(library / name) for name in inputs}, formatter=formatter_version, format_check_passed=True,
                 formatting_configuration_sha256=sha(root / '.clang-format'), compiler=run('compiler-version', [compiler, '--version']).splitlines()[0],
                 fixture_reference='validation/panel-meter-control/arm-vectors.txt', fixture_sha256=sha(fixture),
                 oracle_metadata_reference='validation/panel-meter-control/arm-oracle.json', oracle_metadata_sha256=sha(oracle_dir / 'arm-oracle.json'),
                 actual_dbtable_proof_reference='validation/panel-db-table/replay-01/reconstruction.json', actual_dbtable_proof_sha256=sha(db_proof_path),
                 object_sha256=sha(obj), db_object_sha256=sha(db_obj), executable_sha256=sha(binary),
                 sanitizer_replay_passed=args.platform == 'linux', original_full_verification=False, original_arm_object_layout_compatible=False, hardware_verified=False,
                 declaration_uncertainties=[
                     'Static setDbRange/setMeterSteps proven by original ARM argument use; setter return spelling unencoded and chosen void. Getter int preserves R0. bool is ignored.',
                     'BusDirection keeps original nested identity with portable fixed-int declaration; historical enumerators/underlying declaration unknown.',
                     'Original pointer at +0x20 is only proved to be nullable and point to a first signed32 count, so portable pointer-to-int is an explicit representation choice, not recovered historical pointee type.',
                     'Historical base class, full layout, vtable, constructors and process startup/static initialization are not recovered. Two DbTable objects provide portable storage; initial raw numMeterSteps bytes are16/16 in both ELFs.',
                     'Negative fallback indices, tables larger than16, overlapping/invalid arrays and concurrent global mutation are outside the validated domain. Negative setBusDirection values are preserved.',
                     'Only imported powf is modeled; historical ARM libm remains unverified. No Core implementation is used or recovered.'])
    path = out / 'reconstruction.json'
    path.write_text(json.dumps(proof, indent=2) + '\n')
    records = {'functions': [dict(mangled=s['mangled'], original_elf_sha256=s['original_elf_sha256'], original_address=s['address'],
                                 validation=(rel / 'reconstruction.json').as_posix(), validation_sha256=sha(path), sources=proof['sources'],
                                 portable_ready=True, domain=oracle['domain'], original_full_verification=False, hardware_verified=False) for s in functions]}
    (out / 'readiness-records.json').write_text(json.dumps(records, indent=2) + '\n')
    print(json.dumps(dict(platform=args.platform, differential_cases=oracle['total_cases'], original_entries=len(functions),
                         exact_mangled_names=len(expected), exact_data_names=len(data), proof_sha256=sha(path),
                         fragment_sha256=sha(out / 'readiness-records.json')), indent=2), flush=True)


if __name__ == '__main__':
    main()
