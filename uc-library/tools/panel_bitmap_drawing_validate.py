#!/usr/bin/env python3
"""Format/build/replay pure BitmapDisplay drawing against actual ARM fixtures."""
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository', type=Path)
    parser.add_argument('--platform', choices=('linux', 'mac'), default='linux')
    args = parser.parse_args()
    root = args.repository.resolve()
    library = root / ('uc-library' if args.platform == 'linux' else 'temp/recovery-package/uc-library')
    relative = Path('validation/panel-bitmap-drawing') / ('replay-01' if args.platform == 'linux' else 'mac-01')
    output = library / relative
    output.mkdir(parents=True, exist_ok=False)
    reference = library / 'validation/panel-bitmap-drawing'
    oracle = json.loads((reference / 'arm-oracle.json').read_text())
    fixture = reference / 'arm-vectors.txt'
    assert sha(fixture) == oracle['vectors_sha256']
    cpp = ['include/presonus/surface_panel/BitmapDrawing.hpp', 'src/surface_panel/BitmapDrawing.cpp', 'tests/panel_bitmap_drawing_tests.cpp']
    inputs = cpp + ['tools/panel_bitmap_drawing_oracle.py', 'tools/panel_bitmap_drawing_validate.py']
    commands = {}
    scratch = root / 'temp/panel-bitmap-drawing'
    scratch.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, TMPDIR=str(scratch))

    def run(name, command):
        commands[name] = list(map(str, command))
        (output / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        result = subprocess.run(commands[name], cwd=library, env=env, capture_output=True, text=True)
        (output / (name + '.log')).write_text(result.stdout + result.stderr)
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
    obj, binary = output / 'BitmapDrawing.o', output / 'panel_bitmap_drawing_tests'
    run('compile', [compiler, *flags, '-c', 'src/surface_panel/BitmapDrawing.cpp', '-o', obj])
    run('link', [compiler, *flags, 'tests/panel_bitmap_drawing_tests.cpp', obj, '-o', binary])
    result = run('test', [binary, fixture])
    assert f'PASS: {oracle["total_cases"]} original ARM BitmapDisplay differential cases' in result
    nm = run('symbols', ['nm', '-g', '--defined-only', obj] if args.platform == 'linux' else ['/usr/bin/nm', '-gU', obj])
    defined = {line.split()[-1][1:] if args.platform == 'mac' else line.split()[-1] for line in nm.splitlines() if line.split()}
    functions = [dict(s, role=role, original_elf_sha256=record['sha256'])
                 for role, record in oracle['originals'].items() for s in record['functions']]
    expected = {s['mangled'] for s in functions}
    assert expected <= defined, expected - defined
    if args.platform == 'linux':
        sanitized = output / 'panel_bitmap_drawing_sanitized'
        run('sanitizer-build', [compiler, *flags, '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                                'src/surface_panel/BitmapDrawing.cpp', 'tests/panel_bitmap_drawing_tests.cpp', '-o', sanitized])
        run('sanitizer-test', [sanitized, fixture])
    proof = dict(scope='Presonus::Panel::BitmapDisplay pure drawing and state source port', platform=args.platform,
                 functions=functions, mangled_names=sorted(expected), compiled_mangled_names_matched=True,
                 cpp_differential_passed=True, portable_ready=True, total_cases=oracle['total_cases'], counts=oracle['counts'],
                 sources={name: sha(library / name) for name in inputs}, formatter=formatter_version, format_check_passed=True,
                 formatting_configuration_sha256=sha(root / '.clang-format'), compiler=run('compiler-version', [compiler, '--version']).splitlines()[0],
                 domain=oracle['domain'], dependency_model=oracle['dependency_model'],
                 fixture_reference='validation/panel-bitmap-drawing/arm-vectors.txt', fixture_sha256=sha(fixture),
                 oracle_metadata_reference='validation/panel-bitmap-drawing/arm-oracle.json', oracle_metadata_sha256=sha(reference / 'arm-oracle.json'),
                 object_sha256=sha(obj), executable_sha256=sha(binary), sanitizer_replay_passed=args.platform == 'linux',
                 original_full_verification=False, original_arm_object_layout_compatible=False, hardware_verified=False,
                 declaration_uncertainties=[
                     'Original return type spellings unencoded; portable dimensions/previous-state returns use int, pixel getter uses bool and setters/draw use void, matching observed results.',
                     'Virtualness is established by the actual original vtable; the native class deliberately contains a partial portable vtable, not the historical base/layout/order/ABI.',
                     'Rectangle field names are portable choices for the four observed signed32 arguments; original complete declaration unknown.',
                     'No historical constructor/destructor/lifecycle/default state, mutex, clear, update, font, transport or hardware path is supplied.',
                     'Pixel bounds guards are not invented: only valid backing offsets or negative remainder exits are covered; rectangle overflow/invalid memory domains are excluded.',
                     'No function dependency is modeled; actual original vtable callees are executed. Native byte-for-byte frame comparison reconstructs the full expected image from exact initial frame plus oracle deltas.'])
    path = output / 'reconstruction.json'
    path.write_text(json.dumps(proof, indent=2) + '\n')
    records = {'functions': [dict(mangled=s['mangled'], original_elf_sha256=s['original_elf_sha256'], original_address=s['address'],
                                 validation=(relative / 'reconstruction.json').as_posix(), validation_sha256=sha(path), sources=proof['sources'],
                                 portable_ready=True, domain=oracle['domain'], original_full_verification=False, hardware_verified=False) for s in functions]}
    (output / 'readiness-records.json').write_text(json.dumps(records, indent=2) + '\n')
    print(json.dumps(dict(platform=args.platform, differential_cases=oracle['total_cases'], exact_mangled_names=len(expected), original_entries=len(functions),
                         proof_sha256=sha(path), fragment_sha256=sha(output / 'readiness-records.json')), indent=2), flush=True)


if __name__ == '__main__':
    main()
