#!/usr/bin/env python3
"""Format/build/replay LED state and emitted app-call contracts against ARM."""
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
    relative = Path('validation/panel-led-state') / ('replay-01' if args.platform == 'linux' else 'mac-01')
    out = library / relative
    out.mkdir(parents=True, exist_ok=False)
    reference = library / 'validation/panel-led-state'
    oracle = json.loads((reference / 'arm-oracle.json').read_text())
    fixture = reference / 'arm-vectors.txt'
    assert sha(fixture) == oracle['vectors_sha256']
    cpp = ['include/presonus/surface_panel/LEDState.hpp', 'src/surface_panel/LEDState.cpp', 'tests/panel_led_state_tests.cpp']
    inputs = cpp + ['tools/panel_led_state_oracle.py', 'tools/panel_led_state_validate.py']
    scratch = root / 'temp/panel-led-state'
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
    obj, binary = out / 'LEDState.o', out / 'panel_led_state_tests'
    run('compile', [compiler, *flags, '-c', 'src/surface_panel/LEDState.cpp', '-o', obj])
    run('link', [compiler, *flags, 'tests/panel_led_state_tests.cpp', obj, '-o', binary])
    result = run('test', [binary, fixture])
    assert f'PASS: {oracle["total_cases"]} original ARM LEDControl state/dispatch cases' in result
    nm = run('symbols', ['nm', '-g', '--defined-only', obj] if args.platform == 'linux' else ['/usr/bin/nm', '-gU', obj])
    names = {line.split()[-1][1:] if args.platform == 'mac' else line.split()[-1] for line in nm.splitlines() if line.split()}
    functions = [dict(s, role=role, original_elf_sha256=record['sha256']) for role, record in oracle['originals'].items() for s in record['functions']]
    expected = {s['mangled'] for s in functions}
    assert expected <= names, expected - names
    # No Core namespace function body is supplied or linked by this product object.
    assert not any(name.startswith(('_ZN4Core', '_ZNK4Core')) for name in names)
    if args.platform == 'linux':
        sanitized = out / 'panel_led_state_sanitized'
        run('sanitizer-build', [compiler, *flags, '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                                'src/surface_panel/LEDState.cpp', 'tests/panel_led_state_tests.cpp', '-o', sanitized])
        run('sanitizer-test', [sanitized, fixture])
    proof = dict(scope='Presonus::Panel::LEDControl local state and emitted app-dispatch contract', platform=args.platform,
                 functions=functions, mangled_names=sorted(expected), compiled_mangled_names_matched=True,
                 cpp_differential_passed=True, portable_ready=True, total_cases=oracle['total_cases'], counts=oracle['counts'],
                 sources={name: sha(library / name) for name in inputs}, formatter=formatter_version, format_check_passed=True,
                 formatting_configuration_sha256=sha(root / '.clang-format'), compiler=run('compiler-version', [compiler, '--version']).splitlines()[0],
                 domain=oracle['domain'], dependency_model=oracle['dependency_model'],
                 downstream_callback_behavior_verified=False, original_call_boundaries_verified=True,
                 no_core_function_definitions=True, fixture_reference='validation/panel-led-state/arm-vectors.txt', fixture_sha256=sha(fixture),
                 oracle_metadata_reference='validation/panel-led-state/arm-oracle.json', oracle_metadata_sha256=sha(reference / 'arm-oracle.json'),
                 object_sha256=sha(obj), executable_sha256=sha(binary), sanitizer_replay_passed=args.platform == 'linux',
                 original_full_verification=False, original_arm_object_layout_compatible=False, hardware_verified=False,
                 declaration_uncertainties=[
                     'Original return spellings unencoded: setters/broadcast and abstract callback boundaries use void, with original R0 ignored. Original full prototypes are not claimed.',
                     'Original global RGBLedColors and nested BlinkMode identities retained, with portable fixed-int declarations; original enumerators/underlying declaration unknown.',
                     'No historical base/layout/vtable ABI/constructor/default state/timer/transmit/paramChanged/parameter implementation or device behavior is recovered.',
                     'Core::Portable::Parameter is an opaque forward declaration only, required by an original app callback signature; no Core class definition or implementation exists here.',
                     'Only record-only callbacks preserving app state are covered. Downstream callback effects, foreign broadcast overrides, reentrancy and concurrency are excluded.',
                     'Dirty storage is represented as byte, preserving arbitrary seeded byte values where original does not write; historical field names/type declaration are uncertain.'])
    path = out / 'reconstruction.json'
    path.write_text(json.dumps(proof, indent=2) + '\n')
    fragment = {'functions': [dict(mangled=s['mangled'], original_elf_sha256=s['original_elf_sha256'], original_address=s['address'],
                                  validation=(relative / 'reconstruction.json').as_posix(), validation_sha256=sha(path), sources=proof['sources'],
                                  portable_ready=True, domain=oracle['domain'], original_full_verification=False, hardware_verified=False) for s in functions]}
    (out / 'readiness-records.json').write_text(json.dumps(fragment, indent=2) + '\n')
    print(json.dumps(dict(platform=args.platform, differential_cases=oracle['total_cases'], exact_mangled_names=len(expected), original_entries=len(functions),
                         proof_sha256=sha(path), fragment_sha256=sha(out / 'readiness-records.json')), indent=2), flush=True)


if __name__ == '__main__':
    main()
