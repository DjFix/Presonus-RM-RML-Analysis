#!/usr/bin/env python3
"""Linux-only OutputPin compile/state/IO verification; declarations remain pending."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('repository', type=Path)
    args = p.parse_args()
    assert platform.system() == 'Linux', 'Canonical build/test is Linux only'
    root = args.repository.resolve()
    library = root / 'uc-library'
    relative = Path('validation/panel-output-pin/replay-01')
    out = library / relative
    out.mkdir(parents=True, exist_ok=False)
    reference = library / 'validation/panel-output-pin'
    oracle = json.loads((reference / 'arm-oracle.json').read_text())
    fixture = reference / 'arm-vectors.txt'
    assert sha(fixture) == oracle['vectors_sha256']
    cpp = ['include/presonus/surface_panel/OutputPin.hpp', 'src/surface_panel/OutputPin.cpp', 'tests/panel_output_pin_tests.cpp']
    inputs = cpp + ['tools/panel_output_pin_oracle.py', 'tools/panel_output_pin_validate.py']
    scratch = root / 'temp/panel-output-pin'
    scratch.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, TMPDIR=str(scratch), PYTHONDONTWRITEBYTECODE='1')
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

    formatter = library / '.venv/bin/clang-format'
    formatter_version = run('formatter-version', [formatter, '--version']).strip()
    run('format', [formatter, '--style=file', '--fallback-style=LLVM', '-i', *cpp])
    run('format-check', [formatter, '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror', *cpp])
    flags = ['-std=c++17', '-O2', '-Wall', '-Wextra', '-Wpedantic', '-Iinclude']
    obj, binary = out / 'OutputPin.o', out / 'panel_output_pin_tests'
    run('compile', ['g++', *flags, '-c', 'src/surface_panel/OutputPin.cpp', '-o', obj])
    run('link', ['g++', *flags, 'tests/panel_output_pin_tests.cpp', obj, '-o', binary])
    result = run('test', [binary, fixture])
    assert f'PASS: {oracle["total_cases"]} original ARM OutputPin state/IO contract cases' in result
    nm = run('symbols', ['nm', '-g', '--defined-only', obj])
    names = {line.split()[-1] for line in nm.splitlines() if line.split()}
    functions = [dict(s, role=role, original_elf_sha256=record['sha256']) for role, record in oracle['originals'].items() for s in record['functions']]
    expected = {s['mangled'] for s in functions}
    assert expected <= names, expected - names
    assert not any(name.startswith(('_ZN4Core', '_ZNK4Core')) for name in names)
    sanitized = out / 'panel_output_pin_sanitized'
    run('sanitizer-build', ['g++', *flags, '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                            'src/surface_panel/OutputPin.cpp', 'tests/panel_output_pin_tests.cpp', '-o', sanitized])
    run('sanitizer-test', [sanitized, fixture])
    proof = dict(scope='Presonus::Panel::OutputPin offline local state and emitted file/errno/log contract',
                 platform='Linux', native_architecture=platform.machine(), mac_validation_performed=False,
                 functions=functions, mangled_names=sorted(expected), compiled_mangled_names_matched=True,
                 cpp_compiled=True, mangling_namespace_checked=True, cpp_differential_passed=True, portable_ready=False,
                 total_cases=oracle['total_cases'], counts=oracle['counts'], sources={name: sha(library / name) for name in inputs},
                 formatter=formatter_version, format_check_passed=True, formatting_configuration_sha256=sha(root / '.clang-format'),
                 compiler=run('compiler-version', ['g++', '--version']).splitlines()[0], domain=oracle['domain'], dependency_model=oracle['dependency_model'],
                 setup_r0_compared=True, setup_r0_values=[0, 4294967295], set_r0_ignored=True,
                 original_return_declarations_verified=False, downstream_dependency_behavior_verified=False,
                 no_core_function_definitions=True, no_hardware_or_sysfs_access=True,
                 fixture_reference='validation/panel-output-pin/arm-vectors.txt', fixture_sha256=sha(fixture),
                 oracle_metadata_reference='validation/panel-output-pin/arm-oracle.json', oracle_metadata_sha256=sha(reference / 'arm-oracle.json'),
                 object_sha256=sha(obj), executable_sha256=sha(binary), sanitizer_replay_passed=True,
                 original_full_verification=False, original_arm_object_layout_compatible=False, hardware_verified=False,
                 declaration_uncertainties=[
                     'setup portable int compares explicit original R0=0/-1; original C++ return declaration spelling remains unproved.',
                     'set portable void ignores original fputc/logger-dependent R0; return uncertainty stays compiled/declaration-pending.',
                     'No original constructor/destructor/full layout/vtable ABI, real libc/errno/log effects or physical GPIO behavior is recovered.',
                     'OutputPinIO is an independent injected gateway. Errno pointer-to-value normalization and bounded constant snprintf paths are explicit port adaptations.',
                     'Core DebugPrintf is intercepted at entry only; no Core body/definition exists. Reentrancy/concurrency/lifecycle and invalid real FILE pointers are excluded.'])
    path = out / 'reconstruction.json'
    path.write_text(json.dumps(proof, indent=2) + '\n')
    fragment = {'functions': [dict(mangled=s['mangled'], original_elf_sha256=s['original_elf_sha256'], original_address=s['address'],
                                  validation=(relative / 'reconstruction.json').as_posix(), validation_sha256=sha(path), sources=proof['sources'],
                                  cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False, domain=oracle['domain'],
                                  declaration_uncertainties=proof['declaration_uncertainties'], original_full_verification=False, hardware_verified=False) for s in functions]}
    (out / 'compiled-records.json').write_text(json.dumps(fragment, indent=2) + '\n')
    print(json.dumps(dict(differential_cases=oracle['total_cases'], exact_mangled_names=len(expected), compiled_pending_original_entries=len(functions),
                         proof_sha256=sha(path), fragment_sha256=sha(out / 'compiled-records.json'), mac_validation_performed=False), indent=2), flush=True)


if __name__ == '__main__':
    main()
