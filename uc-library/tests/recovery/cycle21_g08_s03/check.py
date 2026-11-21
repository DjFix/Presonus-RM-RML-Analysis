"""Check the exact compiled symbol and replay native observations."""
import argparse
import hashlib
import datetime
import json
from pathlib import Path
import subprocess

TASK = Path(__file__).parent.name
LIB = Path('uc-library')
SOURCES = [
    'src/Presonus/Surface/SurfaceRootComponent.cpp',
    'include/presonus/surface_panel/ControlHelpers.hpp',
]
REPO_SOURCES = [
    'third_party/ccl-framework/core/portable/corecomponent.cpp',
    'third_party/ccl-framework/core/portable/corecomponent.h',
    'third_party/ccl-framework/core/portable/coreparams.cpp',
    'third_party/ccl-framework/core/portable/coreparams.h',
]
DOMAIN = ('Offline CS18 application entrypoint with the exact native instruction range, '
          'bounded integer/fractional branch states, and isolated native receiver hooks. '
          'Host compares CCL parameter values, observer counts, notifications, root '
          'touchscreen flag and ordered CCL/registrar call boundaries using pinned CCL '
          'and the actual registrar with an offline output sink.')
UNCERTAINTY = ('Original ordinary return declaration remains unresolved. '
               'Portable void models observed side effects. No original layout, '
               'ARM ABI or physical panel behavior is claimed.')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def replay(executable, case):
    command = [str(executable.resolve()), str(case['registrar']), str(case['argument']),
               str(case['base_value'])]
    for tag, value in case['tags'].items():
        command.extend([tag, str(value)])
    output = subprocess.check_output(command, text=True)
    actual = dict(values={}, observers={}, trace=[])
    for line in output.splitlines():
        if line.startswith('state '):
            _, touch, count = line.split()
            actual.update(touchscreen=int(touch), observer_notifications=int(count))
        elif line.startswith('param '):
            _, tag, value, count = line.split()
            actual['values'][tag] = float(value)
            actual['observers'][tag] = int(count)
        elif line.startswith('trace '):
            actual['trace'].append(line.removeprefix('trace '))
        else:
            raise ValueError(f'Unknown replay output: {line}')
    return actual

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('exe', 'object', 'fixture', 'integration', 'out'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--symbols-only', action='store_true')
    args = parser.parse_args()
    document = json.loads(args.fixture.read_text())
    original = document['mangled']
    native = Path(document['elf']).read_bytes()
    if hashlib.sha256(native).hexdigest() != document['elf_sha256']:
        raise ValueError('Original ELF hash mismatch')
    offset = document['file_offset']
    if hashlib.sha256(native[offset:offset+document['size']]).hexdigest() != document['range_sha256']:
        raise ValueError('Original symbol range hash mismatch')
    nm = ['nm', '--defined-only', str(args.object)]
    symbols = subprocess.check_output(nm, text=True)
    matches = [line for line in symbols.splitlines() if line.split()[-1:] == [original]
               and line.split()[-2] == 'T']
    if len(matches) != 1:
        raise ValueError(f'Expected one defined original symbol: {original}')
    if args.symbols_only:
        print(matches[0])
        return
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    results = []
    for case in document['cases']:
        actual = replay(args.exe, case)
        if actual != case['expected']:
            raise ValueError(f"Mismatch {TASK} case {len(results)}: {actual!r} vs {case['expected']!r}")
        results.append(actual)
    if not results:
        raise ValueError('No replay cases')
    formatter = LIB / '.venv/bin/clang-format'
    format_cmd = [str(formatter), '--style=file', '--fallback-style=LLVM',
                  '--dry-run', '--Werror', *[str(LIB / source) for source in SOURCES],
                  str(Path(__file__).with_name('Replay.cpp'))]
    subprocess.run(format_cmd, check=True)
    row = dict(
        original_elf_sha256=document['elf_sha256'], mangled=original,
        cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
        declaration_uncertainties=[UNCERTAINTY], validation_domain=DOMAIN,
        sources={s: digest(LIB / s) for s in SOURCES},
        repository_sources={s: digest(Path(s)) for s in REPO_SOURCES})
    evidence = dict(
        task=TASK, replay_passed=True, case_count=len(results), validation_domain=DOMAIN,
        results=results, proposed_readiness=dict(ready=[], pending=[row]),
        original={k: v for k, v in document.items() if k != 'cases'},
        compile_symbol=matches[0], symbol_argv=nm,
        executable_sha256=digest(args.exe), object_sha256=digest(args.object),
        checker_sha256=digest(Path(__file__)), fixture_sha256=digest(args.fixture),
        native_producer_sha256=digest(Path(__file__).with_name('native.py')),
        formatter_argv=format_cmd,
        clang_format_version=subprocess.check_output([str(formatter), '--version'], text=True).strip(),
        validation_started_utc=start,
        validation_finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    if args.integration.is_file():
        evidence.update(integration_path=str(args.integration),
                        integration_sha256=digest(args.integration))
    elif args.integration.name != 'local-no-integration.json':
        raise FileNotFoundError(args.integration)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(evidence, indent=2) + '\n')
    print(TASK, len(results), 'native/portable replay cases passed')

if __name__ == '__main__':
    main()
