#!/usr/bin/env python3
"""Format/build/replay offline InputPin contracts; preserve return-declaration pending."""
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
    p.add_argument('--platform', choices=('linux', 'mac'), default='linux')
    args = p.parse_args()
    root = args.repository.resolve()
    library = root / ('uc-library' if args.platform == 'linux' else 'temp/recovery-package/uc-library')
    relative = Path('validation/panel-input-pin') / ('replay-01' if args.platform == 'linux' else 'mac-01')
    out = library / relative
    out.mkdir(parents=True, exist_ok=False)
    reference = library / 'validation/panel-input-pin'
    oracle = json.loads((reference / 'arm-oracle.json').read_text())
    fixture = reference / 'arm-vectors.txt'
    assert sha(fixture) == oracle['vectors_sha256']
    cpp = ['include/presonus/surface_panel/InputPin.hpp', 'src/surface_panel/InputPin.cpp', 'tests/panel_input_pin_tests.cpp']
    inputs = cpp + ['tools/panel_input_pin_oracle.py', 'tools/panel_input_pin_validate.py']
    scratch = root / 'temp/panel-input-pin'
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

    if args.platform == 'linux':
        formatter = library / '.venv/bin/clang-format'
        formatter_version = run('formatter-version', [formatter, '--version']).strip()
        run('format', [formatter, '--style=file', '--fallback-style=LLVM', '-i', *cpp])
        run('format-check', [formatter, '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror', *cpp])
    else:
        linux = json.loads((reference / 'replay-01/reconstruction.json').read_text())
        assert all(sha(library / name) == value for name, value in linux['sources'].items())
        assert linux['format_check_passed']
        formatter_version = linux['formatter']
    compiler = 'g++' if args.platform == 'linux' else '/usr/bin/clang++'
    flags = ['-std=c++17', '-O2', '-Wall', '-Wextra', '-Wpedantic', '-Iinclude']
    obj, binary = out / 'InputPin.o', out / 'panel_input_pin_tests'
    run('compile', [compiler, *flags, '-c', 'src/surface_panel/InputPin.cpp', '-o', obj])
    run('link', [compiler, *flags, 'tests/panel_input_pin_tests.cpp', obj, '-o', binary])
    result = run('test', [binary, fixture])
    assert f'PASS: {oracle["total_cases"]} original ARM InputPin state/IO contract cases' in result
    nm = run('symbols', ['nm', '-g', '--defined-only', obj] if args.platform == 'linux' else ['/usr/bin/nm', '-gU', obj])
    defined = {line.split()[-1][1:] if args.platform == 'mac' else line.split()[-1] for line in nm.splitlines() if line.split()}
    functions = [dict(s, role=role, original_elf_sha256=record['sha256']) for role, record in oracle['originals'].items() for s in record['functions']]
    names = {s['mangled'] for s in functions}
    assert names <= defined, names - defined
    assert not any(name.startswith(('_ZN4Core', '_ZNK4Core')) for name in defined)
    if args.platform == 'linux':
        sanitized = out / 'panel_input_pin_sanitized'
        run('sanitizer-build', [compiler, *flags, '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                                'src/surface_panel/InputPin.cpp', 'tests/panel_input_pin_tests.cpp', '-o', sanitized])
        run('sanitizer-test', [sanitized, fixture])
    proof = dict(scope='Presonus::Panel::InputPin offline state and emitted file/observer/log contracts', platform=args.platform,
                 functions=functions, mangled_names=sorted(names), compiled_mangled_names_matched=True, mangling_namespace_checked=True,
                 cpp_compiled=True, cpp_differential_passed=True, portable_ready=False,
                 total_cases=oracle['total_cases'], counts=oracle['counts'], method_invocations=oracle['method_invocations'],
                 sources={name: sha(library / name) for name in inputs}, formatter=formatter_version, format_check_passed=True,
                 formatting_configuration_sha256=sha(root / '.clang-format'), compiler=run('compiler-version', [compiler, '--version']).splitlines()[0],
                 domain=oracle['domain'], dependency_model=oracle['dependency_model'],
                 setup_r0_compared=True, setup_r0_values=[0, 4294967295], poll_r0_ignored=True,
                 original_return_declarations_verified=False, downstream_dependency_behavior_verified=False,
                 no_core_function_definitions=True, no_hardware_or_sysfs_access=True,
                 fixture_reference='validation/panel-input-pin/arm-vectors.txt', fixture_sha256=sha(fixture),
                 oracle_metadata_reference='validation/panel-input-pin/arm-oracle.json', oracle_metadata_sha256=sha(reference / 'arm-oracle.json'),
                 object_sha256=sha(obj), executable_sha256=sha(binary), sanitizer_replay_passed=args.platform == 'linux',
                 original_full_verification=False, original_arm_object_layout_compatible=False, hardware_verified=False,
                 declaration_uncertainties=[
                     'setup uses portable int and compares original explicit R0=0/-1 on all branches; original C++ return declaration spelling is unencoded/unproved.',
                     'read/read_debounce use portable void and ignore original fgetc/callback-dependent R0. These methods remain compiled/declaration-pending.',
                     'No PinStateObserver class/API body is invented: only an opaque original type identity and first-slot argument contract exist; independent IO gateway provides notifications.',
                     'Core::DebugPrintf entry is intercepted as a log request; no Core implementation, definition or body executes. Real logging/file/observer effects are unverified.',
                     'Historical base/vtable ABI, constructor/destructor/lifecycle and complete layout are not recovered; native FILE/observer pointers are opaque injected handles.',
                     'Formatting uses a bounded independent gateway for the constant safe path patterns; old sprintf/libc implementation equivalence outside these bounded arguments is unverified.'])
    path = out / 'reconstruction.json'
    path.write_text(json.dumps(proof, indent=2) + '\n')
    records = {'functions': [dict(mangled=s['mangled'], original_elf_sha256=s['original_elf_sha256'], original_address=s['address'],
                                 validation=(relative / 'reconstruction.json').as_posix(), validation_sha256=sha(path), sources=proof['sources'],
                                 cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
                                 domain=oracle['domain'], declaration_uncertainties=proof['declaration_uncertainties'],
                                 original_full_verification=False, hardware_verified=False) for s in functions]}
    (out / 'compiled-records.json').write_text(json.dumps(records, indent=2) + '\n')
    print(json.dumps(dict(platform=args.platform, differential_cases=oracle['total_cases'], exact_mangled_names=len(names),
                         compiled_pending_original_entries=len(functions), proof_sha256=sha(path),
                         fragment_sha256=sha(out / 'compiled-records.json')), indent=2), flush=True)


if __name__ == '__main__':
    main()
