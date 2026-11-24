"""Replay a bounded surface callback against its sealed ARM observations."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

from native import ORIGINAL, FIELD_OFFSET, observe

TEST = Path(__file__).relative_to(Path.cwd()) if Path(__file__).is_absolute() else Path(__file__)
TASK = TEST.parent.name
OWNER = 'UCMidiInputAdapter'
SOURCE = Path(f'uc-library/src/Presonus/Surface/{OWNER}.cpp')
HEADER = Path(f'uc-library/include/presonus/surface/{OWNER}.hpp')
SCRATCH = Path('temp/recovery-work/lane10-local') / TASK
EXE = SCRATCH / 'Replay'
OBJECT = SCRATCH / f'{OWNER}.o'
CHECK_INPUTS = [SOURCE, HEADER, TEST.with_name('Replay.cpp')]
PROVIDER = Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01')
CORE_INCLUDE = PROVIDER / 'upstream-core/sdk/include/presonus-core-5'
FORMAT = ['uc-library/.venv/bin/clang-format', '--style=file', '--fallback-style=LLVM',
          '--dry-run', '--Werror', *map(str, CHECK_INPUTS)]
CXX = ['/usr/bin/c++', '-std=c++17', '-O2', '-ffunction-sections',
       '-fdata-sections', '-Ulinux', '-fno-rtti', '-fno-sized-deallocation',
       '-DPRESONUS_HAS_UPSTREAM_CORE=1', '-DCORE_USE_OPENSSL=1', '-DNDEBUG=1',
       '-Iuc-library/include', '-isystem', str(CORE_INCLUDE)]
LINK_DEPS = [
    str(PROVIDER / file) for file in (
        'libpresonus_cs18_components.a', 'upstream-core/sdk/lib/libcorelib.a',
        'upstream-core/sdk/lib/libpresonus_core_allocator.a',
        'upstream-core/sdk/lib/libpresonus_png.a',
        'upstream-core/sdk/lib/libpresonus_zlib.a',
        'private-glibc29-provider/libpresonus_private_glibc29.a',
    )
] + ['-lssl', '-lcrypto', '-ldl', '-lm', '-pthread']
COMPILE = [*CXX, '-c', str(SOURCE), '-o', str(OBJECT)]
LINK = [*CXX, '-Wl,--gc-sections', str(CHECK_INPUTS[-1]), str(OBJECT),
        *LINK_DEPS, '-o', str(EXE)]


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def symbols(path):
    argv = ['/usr/bin/nm', '--defined-only', str(path)]
    result = subprocess.check_output(argv, text=True)
    matched = [line for line in result.splitlines()
               if line.split() and line.split()[-1] == ORIGINAL['mangled']]
    if len(matched) != 1:
        raise ValueError('Expected one exact original symbol in compiled owner')
    return {'argv': argv, 'matched': matched[0]}


def validate(fixtures, exe):
    argv = [str(exe)]
    lines = subprocess.check_output(argv, text=True).splitlines()
    observations = [list(map(int, line.split())) for line in lines]
    expected = [[case[k] for k in ('input', 'before', 'after')]
                for case in fixtures['cases']]
    if observations != expected:
        raise ValueError(f'Portable observation differs from ARM: {observations!r} != {expected!r}')
    return {'argv': argv, 'observations': observations, 'case_count': len(observations)}


def proof(args, fixture):
    started = utc()
    if args.integration:
        # CTest runs before integration.json is refreshed. A fresh canonical
        # invocation supplies the current Linux integration receipt.
        integration = json.loads(args.integration.read_text())
        if integration.get('platform') != 'linux' or integration.get('ctest_passed') is not True:
            raise ValueError('Expected Linux integration receipt')
        integration_sha = sha(args.integration)
    else:
        integration_sha = None
    subprocess.run(FORMAT, check=True)
    compiler_symbol = symbols(args.object)
    portable = validate(fixture, args.exe)
    if FIELD_OFFSET is None:
        if any(case['memory_writes'] for case in fixture['cases']):
            raise ValueError('Original default hook has an external memory write')
        domain = ('Three original calls on a mapped sentinel object with no external writes or calls. '
                  'Portable replay checks observer and supplied argument storage are unchanged. '
                  'Argument observations cover the relevant null, non-null, boolean or enum inputs.')
    else:
        if any(case['memory_writes'] != [[0x3000 + FIELD_OFFSET, 4, case['r1']]]
               for case in fixture['cases']):
            raise ValueError('Unexpected original write footprint')
        domain = ('Four successive typed pointer bindings covering two distinct non-null values, '
                  'replacement, null clearing and rebind. ARM traces check object-memory writes. '
                  'Portable replay observes the borrowed pointer after each binding.')
        if OWNER == 'UCMidiInputAdapter':
            domain += ' Portable replay also checks no setter sink call and unchanged short MIDI forwarding.'
    uncertainty = ['Original C++ return declaration remains unresolved; void is a portable choice.',
                   'Original application object layout and ARM32 ABI are outside the portable replay.']
    if OWNER == 'CapturePageComponent':
        uncertainty.append('Word slots in the native callback table support virtual dispatch; the source class does not claim original table layout, enum declaration, or complete interface.')
    else:
        uncertainty.append('Native member-style write is observed; original virtual declaration and lifetime contract remain unresolved.')
    sources = {str(p.relative_to('uc-library')): sha(p) for p in (SOURCE, HEADER)}
    dependencies = {}
    for name in {
        'CapturePageComponent': ['portable/corecomponent.h', 'portable/coreparams.h',
                                 'portable/gui/coreview.h', 'public/corevector.h'],
        'MainScreenComponent': ['portable/corecomponent.h', 'public/corevector.h'],
        'UCMidiInputAdapter': [],
    }[OWNER]:
        path = Path('third_party/ccl-framework/core') / name
        dependencies[str(path)] = sha(path)
    row = {'original_elf_sha256': ORIGINAL['elf_sha256'], 'mangled': ORIGINAL['mangled'],
           'cpp_compiled': True, 'mangling_namespace_checked': True, 'portable_ready': False,
           'sources': sources, 'repository_sources': dependencies, 'validation_domain': domain,
           'declaration_uncertainties': uncertainty}
    proof_data = {'task_id': TASK, 'original': ORIGINAL, 'section_name': fixture['section_name'],
                  'cpp_differential_passed': True, 'compiled_mangled_names_matched': True,
                  'format_check_passed': True, 'portable_ready': False,
                  'mangled_names': [ORIGINAL['mangled']], 'format_argv': FORMAT,
                  'formatter_version': subprocess.check_output([FORMAT[0], '--version'], text=True).strip(),
                  'formatted_files': {str(p.relative_to('uc-library')): sha(p) for p in CHECK_INPUTS},
                  'native': {'case_count': len(fixture['cases']), 'unicorn_version': fixture['unicorn_version'],
                             'fixture_sha256': sha(args.fixtures), 'case_observations': fixture['cases']},
                  'portable': portable, 'compiled_symbol': compiler_symbol,
                  'object_sha256': sha(args.object), 'exe_sha256': sha(args.exe),
                  'integration_sha256': integration_sha, 'integration': str(args.integration) if args.integration else None,
                  'producer_inputs': {str(path): sha(path) for path in (TEST, TEST.with_name('native.py'))},
                  'proposed_readiness': {'ready': [], 'pending': [row]},
                  'started_utc': started, 'finished_utc': utc()}
    if not args.integration:
        proof_data.update(compile_argv=COMPILE, link_argv=LINK,
                          local_provider_archive_sha256=sha(PROVIDER / 'libpresonus_cs18_components.a'))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof_data, indent=2) + '\n')
    print(f'{TASK}: {portable["case_count"]} portable cases matched the sealed native observations')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['format', 'compile', 'symbols', 'capture', 'native', 'replay', 'proof'])
    parser.add_argument('--exe', type=Path, default=EXE)
    parser.add_argument('--object', type=Path, default=OBJECT)
    parser.add_argument('--fixtures', type=Path, default=TEST.with_name('fixtures.json'))
    parser.add_argument('--integration', type=Path)
    parser.add_argument('--out', type=Path, default=SCRATCH / 'proof.json')
    args = parser.parse_args()
    if args.mode == 'format':
        subprocess.run(FORMAT, check=True)
    elif args.mode == 'compile':
        SCRATCH.mkdir(parents=True, exist_ok=True)
        print(json.dumps({'compile': COMPILE, 'link': LINK}), flush=True)
        for argv in (COMPILE, LINK):
            subprocess.run(argv, check=True)
    elif args.mode == 'symbols':
        print(json.dumps(symbols(args.object)))
    elif args.mode == 'capture':
        args.fixtures.write_text(json.dumps(observe(), indent=2) + '\n')
    else:
        fixture = json.loads(args.fixtures.read_text())
        if fixture['original'] != ORIGINAL:
            raise ValueError('Fixture binds a different original')
        if args.mode == 'native':
            if fixture != observe():
                raise ValueError('Fresh ARM observations differ from the sealed fixture')
            print(f'{TASK}: {len(fixture["cases"])} ARM observations reproduced')
        else:
            proof(args, fixture)


if __name__ == '__main__':
    main()
