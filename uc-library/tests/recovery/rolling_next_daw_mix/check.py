"""Replay offline original observations with the typed Mapping/CCL provider."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess

LIBRARY = Path('uc-library')
TESTS = LIBRARY / 'tests/recovery'
SCRATCH = Path('temp/recovery-work/daw-mapping-current01')
CLASS_HEADER = 'include/presonus/surface/DAWMixerHandler.hpp'
CLASS_SOURCE = 'src/Presonus/Surface/DAWMixerHandler.cpp'
ROUTES = 'src/Presonus/Surface/MappingRadioRoutes.cpp'
CCL = 'third_party/ccl-framework/core/portable/'
CCL_REVISION = 'e8cbdea4a4a20e15111f5a690798a259c0374b31'
CCL_SOURCES = [CCL + stem + suffix
               for stem in ('corecomponent', 'coreparams') for suffix in ('.h', '.cpp')]
SOURCES = [CLASS_HEADER, CLASS_SOURCE, ROUTES, 'include/presonus/PageComponent.hpp',
           'include/presonus/surface/MappingComponent.hpp',
           'include/presonus/surface/mapping_input_routes.hpp',
           'include/presonus/surface/sl_mixer_encoder.hpp']
FLAGS = ['/usr/bin/c++', '-std=c++17', '-O2', '-fno-rtti', '-fno-lto',
         '-fno-fast-math', '-ffp-contract=off', '-ffunction-sections',
         '-fdata-sections', '-UNDEBUG', '-Wno-multichar', '-pthread', '-Ulinux',
         '-DCORE_USE_OPENSSL=1', '-DPRESONUS_HAS_UPSTREAM_CORE=1',
         '-Iuc-library/include', '-Ithird_party/ccl-framework']
ARCHIVES = [SCRATCH / 'providers' / ('lib' + name + '.a')
            for name in ('presonus_uc', 'corelib', 'presonus_core_allocator')]
FORMATTER = LIBRARY / '.venv/bin/clang-format'
ELF = Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/'
           'control10x20-after-4fed70d11/packeting/panel-first02-batch02/snapshot/'
           'rootfs/CS18_v13840/home/root/surface')
UNCERTAINTY = ('Original ordinary return declaration remains unresolved. '
               'The portable int return models the observed 32-bit signed result.')
DOMAIN = ('Offline CS18 original ARM range with a null controller or one controlled '
          'virtual result. Compare signed results, exact virtual tag bounds and call '
          'counts, and native stack-only writes. Exercise the real typed MappingComponent '
          'route and CCL NumericParam list with zero parameters or populated masks, '
          'fractional positives in range and positive out-of-range tags. '
          'Portable checks compare preserved parameters and handler state.')


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def run(argv, **kwargs):
    argv = list(map(str, argv))
    print(json.dumps(argv), flush=True)
    env = dict(os.environ, TMPDIR=str(SCRATCH.resolve())) if SCRATCH.is_dir() else None
    return subprocess.run(argv, check=True, text=True, env=env, **kwargs)


def format_check():
    paths = [LIBRARY / CLASS_HEADER, LIBRARY / CLASS_SOURCE]
    paths += [TESTS / ('rolling_next_daw_' + name) / 'Replay.cpp'
              for name in ('mix', 'meter')]
    argv = [FORMATTER, '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror', *paths]
    run(argv)
    return list(map(str, argv))


def local_compile(task):
    target = SCRATCH / task
    target.mkdir(parents=True, exist_ok=True)
    entries = [('DAWMixerHandler.o', CLASS_SOURCE), ('MappingRadioRoutes.o', ROUTES)]
    for name, source in entries:
        retry = target / name
        run([*FLAGS, '-c', LIBRARY / source, '-o', retry])
    run([*FLAGS, TESTS / task / 'Replay.cpp', *[target / name for name, _ in entries],
         '-Wl,--gc-sections', '-Wl,--start-group', *ARCHIVES, '-Wl,--end-group',
         '-ldl', '-lrt', '-lz', '/usr/lib/x86_64-linux-gnu/libpng16.so.16',
         '-lssl', '-lcrypto', '-o', target / 'replay'])


def check_symbol(mangled, obj):
    command = ['/usr/bin/nm', '--defined-only', str(obj)]
    lines = run(command, capture_output=True).stdout.splitlines()
    matches = [line for line in lines if line.split()[-2:] == ['T', mangled]]
    if len(matches) != 1:
        raise ValueError(f'Expected one defined global symbol {mangled}, got {matches}')
    return command, matches[0]


def replay(executable, fixture, first, last):
    cases = fixture['cases']
    if len(cases) != 371:
        raise ValueError('Missing original fixture cases')
    expected = {value: row['expected'] for row in cases
                for present, value in [row['input']] if present}
    rows = []
    for case in cases:
        present, value = case['input']
        if case['trace'] != ([[first, last]] if present else []):
            raise ValueError(f'Unexpected original call arguments: {case}')
        rows.append(('O' if present else 'N', value, case['expected'], present))
    width = last - first + 1
    if width == 4:
        masks = list(range(1 << width))
    else:
        bits = [1 << bit for bit in range(width)]
        masks = [0, (1 << width) - 1, *bits]
        masks += [left | right for index, left in enumerate(bits) for right in bits[index + 1:]]
    for mask in masks:
        first_active = next((first + bit for bit in range(width) if mask & (1 << bit)), -1)
        rows.append(('R', mask, expected[first_active], 1))
    rows.append(('E', 0, expected[-1], 1))
    payload = ''.join(f'{mode} {value}\n' for mode, value, _, _ in rows)
    lines = run([executable.resolve()], input=payload, capture_output=True).stdout.splitlines()
    if len(lines) != len(rows):
        raise ValueError(f'Expected {len(rows)} results, got {len(lines)}')
    for row, line in zip(rows, lines):
        if tuple(map(int, line.split())) != row[2:]:
            raise ValueError(f'Portable replay mismatch for {row[:2]}: {line}; expected {row[2:]}')
    return len(cases), len(rows) - len(cases)


def main(task):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('exe', 'object', 'fixture', 'integration', 'out'):
        parser.add_argument('--' + name, type=Path)
    parser.add_argument('--local-compile', action='store_true')
    parser.add_argument('--format-only', action='store_true')
    parser.add_argument('--symbols-only', action='store_true')
    parser.add_argument('--native-only', action='store_true')
    args = parser.parse_args()
    folder = TESTS / task
    if args.format_only:
        format_check()
        return
    if args.local_compile:
        local_compile(task)
        return
    if args.native_only:
        import sys
        sys.path.insert(0, str(folder.resolve()))
        import native
        if native.generate() != json.loads(args.fixture.read_text()):
            raise ValueError('Fresh original ARM observations differ from the fixture')
        print('371 fresh original ARM observations verified')
        return
    if not all((args.object, args.fixture)):
        parser.error('--object and --fixture are required')
    started = utc()
    doc = json.loads(args.fixture.read_text())
    original, = doc['ranges']
    native_bytes = ELF.read_bytes()
    if sha256(native_bytes).hexdigest() != doc['elf_sha256']:
        raise ValueError('Original ELF hash changed')
    offset = original['file_offset']
    if sha256(native_bytes[offset:offset + original['size']]).hexdigest() != original['sha256']:
        raise ValueError('Original symbol byte range changed')
    nm, symbol = check_symbol(original['mangled'], args.object)
    if args.symbols_only:
        print(symbol)
        return
    if not all((args.exe, args.integration, args.out)):
        parser.error('--exe, --integration and --out are required')
    first, last = (13, 33) if task.endswith('_mix') else (34, 37)
    format_argv = format_check()
    original_cases, provider_cases = replay(args.exe, doc, first, last)
    row = dict(original_elf_sha256=doc['elf_sha256'], mangled=original['mangled'],
               cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
               declaration_uncertainties=[UNCERTAINTY], validation_domain=DOMAIN,
               sources={path: digest(LIBRARY / path) for path in SOURCES},
               repository_sources={path: digest(Path(path)) for path in CCL_SOURCES})
    proof = dict(replay_passed=True, task=task, validation_domain=DOMAIN,
                 proposed_readiness=dict(ready=[], pending=[row]),
                 original=original, elf_path=str(ELF), original_cases=original_cases,
                 provider_cases=provider_cases, pinned_ccl_revision=CCL_REVISION,
                 symbol_argv=nm, compile_symbol=symbol, formatter_argv=format_argv,
                 clang_format_version=run([FORMATTER, '--version'], capture_output=True).stdout.strip(),
                 fixture_sha256=digest(args.fixture), executable_sha256=digest(args.exe),
                 object_sha256=digest(args.object), checker_sha256=digest(folder / 'check.py'),
                 native_producer_sha256=digest(folder / 'native.py'),
                 shared_checker_sha256=digest(Path(__file__)),
                 started_utc=started, finished_utc=utc())
    if args.integration.is_file():
        proof.update(integration_path=str(args.integration),
                     integration_sha256=digest(args.integration))
    elif args.integration.name != 'local-no-integration.json':
        raise FileNotFoundError(args.integration)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + '\n')
    print(task, original_cases, 'original ARM cases and', provider_cases, 'live Mapping/CCL cases passed')


if __name__ == '__main__':
    main(Path(__file__).parent.name)
