"""Compile and compare the typed Linux constructor with the observed ARM boundary."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from native import generate, PAGE, TARGET

PYTHON = 'uc-library/.venv/bin/python'
FORMAT = 'uc-library/.venv/bin/clang-format'
HEADER = 'uc-library/include/presonus/surface/StartPageComponent.hpp'
SOURCE = 'uc-library/src/Presonus/Surface/StartPageComponent.cpp'
PAGE_SOURCE = 'uc-library/src/Presonus/PageComponent.cpp'
FLAGS = ['/usr/bin/c++', '-std=c++20', '-fno-rtti', '-fno-lto', '-Wno-multichar',
         '-ffunction-sections', '-fdata-sections', '-Iuc-library/include',
         '-Ithird_party/ccl-framework']
BUILD = Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01')
CCL = BUILD / 'upstream-core/sdk/lib'
ARCHIVES = [BUILD / 'libpresonus_cs18_components.a',
            *(CCL / ('lib' + name + '.a') for name in
              ('corelib', 'presonus_core_allocator', 'presonus_png', 'presonus_zlib'))]


def run(argv, **kwargs):
    argv = list(map(str, argv))
    print(json.dumps(argv), flush=True)
    return subprocess.check_output(argv, text=True, **kwargs)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main(variant, directory):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('generate', 'format', 'compile', 'symbols', 'replay'))
    parser.add_argument('--exe', type=Path)
    parser.add_argument('--object', type=Path)
    parser.add_argument('--fixtures', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--integration', type=Path)
    args = parser.parse_args()
    base = Path(directory).resolve().relative_to(Path.cwd())
    task = base.name
    scratch = Path('temp/recovery-work') / task
    scratch.mkdir(parents=True, exist_ok=True)
    fixture = args.fixtures or base / 'fixtures.json'
    obj = args.object or scratch / 'start-page.o'
    exe = args.exe or scratch / 'replay'
    if args.mode == 'generate':
        fixture.write_text(json.dumps(generate(variant), indent=2) + '\n')
        return
    if args.mode == 'format':
        run([FORMAT, '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror',
             HEADER, SOURCE, base / 'Replay.cpp'])
        return
    if args.mode == 'compile':
        env = {**os.environ, 'TMPDIR': str(scratch.resolve())}
        page_object = scratch / 'page.o'
        run([*FLAGS, '-O3', '-c', SOURCE, '-o', obj], env=env)
        run([*FLAGS, '-O3', '-c', PAGE_SOURCE, '-o', page_object], env=env)
        archives = {str(a): sha(a) for a in ARCHIVES}
        test_object = scratch / 'test.o'
        run([*FLAGS, '-O0', '-c', base / 'Replay.cpp', '-o', test_object], env=env)
        run([*FLAGS, test_object, obj, page_object, '-Wl,--gc-sections',
             *ARCHIVES, '-lssl', '-lcrypto', '-ldl', '-lm', '-pthread', '-o', exe], env=env)
        assert archives == {str(a): sha(a) for a in ARCHIVES}
        (scratch / 'linked-archives.json').write_text(json.dumps(archives, indent=2) + '\n')
        return
    names = {line.split()[-1] for line in run(['nm', '--defined-only', obj]).splitlines() if line}
    assert {TARGET.format('C1'), TARGET.format('C2')} <= names
    undefined = run(['nm', '--undefined-only', obj])
    assert PAGE in undefined
    if args.mode == 'symbols':
        test_undefined = run(['nm', '--undefined-only', scratch / 'test.o'])
        assert TARGET.format(variant) in test_undefined
        return
    native = generate(variant)
    assert native == json.loads(fixture.read_text())
    original = native['original']
    assert original['mangled'] == TARGET.format(variant)
    expected_rows = []
    for row in native['rows']:
        assert row['extra'] == [0] * 5
        assert (row['min'], row['max'], row['mid'], row['default'], row['delta']) == (0,) * 5
        flags = row['flags']
        expected_rows.append(' '.join(map(str, (
            row['type'], row['tag'], row['name'], 0, int(not flags & 4),
            int(bool(flags & 2)), int(bool(flags & 8)), int(bool(flags & 16)),
            int(bool(flags & 32)), int(bool(flags & 64)), int(bool(flags & 128)), 0,
        ))))
    observations = []
    for case in native['cases']:
        result = run([exe.resolve(), case['name'], case['form'], case['tag']]).splitlines()
        assert result == [case['name'], case['form'][:31], str(case['tag']),
                          *expected_rows, '0 0', '1 0', '0 1'], result
        observations.append(result)
    run([exe.resolve()])
    dependencies = [
        'third_party/ccl-framework/core/portable/' + file for file in
        ('corecomponent.h', 'corecomponent.cpp', 'coreparams.h', 'coreparams.cpp', 'coreparaminfo.h')
    ] + ['third_party/ccl-framework/core/public/corestringbuffer.h']
    sources = {str(Path(p).relative_to('uc-library')): sha(p) for p in [
        HEADER, SOURCE, 'uc-library/include/presonus/PageComponent.hpp', PAGE_SOURCE,
    ]}
    providers = {p: sha(p) for p in dependencies}
    domain = ('Offline StartPage and Page C2 ARM execution, native alias descriptor bytes, '
              'three valid name/form/tag tuples with default CCL aliases, two alias bindings, '
              'and one legacy caller-supplied pair on Linux.')
    limits = ('Native CCL component, form-copy and ParamList routines are observed at call '
              'boundaries. Linux uses the pinned CCL objects and real canonical PageComponent. '
              'Alias routing tests cover local provider behavior. Original layouts, hardware, '
              'destruction, mapping, and exceptional unwinding are outside the claim.')
    entry = dict(mangled=original['mangled'], original_elf_sha256=native['elf_sha256'],
                 sources=sources, repository_sources=providers, domain=domain,
                 portable_ready=True, cpp_compiled=True, mangling_namespace_checked=True)
    input_paths = [fixture, Path(__file__).resolve().relative_to(Path.cwd()),
                   base / 'check.py', base / 'Replay.cpp',
                   Path(__file__).with_name('native.py').resolve().relative_to(Path.cwd())]
    if args.integration and args.integration.is_file():
        assert json.loads(args.integration.read_text())['platform'] == 'linux'
        input_paths.append(args.integration)
    elif args.integration:
        assert args.integration.name == 'integration.json', args.integration
    shared = Path(__file__).with_name('Replay.cpp').resolve().relative_to(Path.cwd())
    input_paths.append(shared)
    output = args.out or scratch / 'local-proof.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    proof = dict(
        version=1, task_id=task, all_checks_passed=True, validation_domain=domain,
        domain=domain, limitations=limits, cpp_compiled=True,
        mangling_namespace_checked=True, compiled_mangled_names_matched=True,
        arm_differential_passed=True, native_cases=len(observations),
        separate_native_ranges={k: native[k] for k in ('original', 'page', 'descriptor')},
        original_elf_sha256=native['elf_sha256'], observations=observations,
        formatter_version=run([FORMAT, '--version']).strip(),
        compiler_version=run(['/usr/bin/c++', '--version']).splitlines()[0],
        unicorn_version=__import__('unicorn').__version__,
        artifact_sha256={str(p): sha(p) for p in {*input_paths, exe, obj}},
        source_sha256=sources, provider_sources=providers, functions=[entry],
        linked_archives=(json.loads((scratch / 'linked-archives.json').read_text())
                         if not args.exe else {}),
        proposed_readiness=dict(canonical_binding_pending=True, ready=[entry], pending=[]),
    )
    if args.integration and args.integration.is_file():
        proof['integration'] = {'path': str(args.integration), 'sha256': sha(args.integration)}
        proof['proposed_readiness']['canonical_binding_pending'] = False
    output.write_text(json.dumps(proof, indent=2, sort_keys=True) + '\n')
    print(len(observations), 'native and Linux constructor cases')


if __name__ == '__main__':
    main('C1', Path(__file__).parent)
