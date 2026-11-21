"""Check the exact compiled symbol and replay native observations."""
import argparse
import hashlib
import datetime
import json
from pathlib import Path
import subprocess

TASK = Path(__file__).parent.name
LIB = Path('uc-library')
DFU = TASK.endswith('09')
PROVIDER = [
    'src/Presonus/Dsp/RuntimeGlobals.cpp',
    'include/presonus/dsp/RuntimeGlobals.hpp',
]
SOURCES = (
    ['src/utilities/DfuDiagnostic.cpp', 'include/presonus/utilities/dfu_diagnostic.hpp']
    if DFU else ['src/DSPManager.cpp', 'include/presonus/dsp/DSPManager.hpp']
)
REPO_SOURCES = []
DOMAIN = (
    'Every native lookup code 2000 through 2009, boundary and unknown values, signed '
    'extremes, and repeated portable pointers into stable string storage.'
    if DFU else
    'Exact native tail branch, original vtable member word, pinned input range for '
    'getDSPState, and full result words and address traces for absent and present links '
    'in injected guest memory. The actual admitted portable provider executes, with zero '
    'guest-memory writes and without any attached device.'
)
UNCERTAINTY = (
    'Original pointer return const qualification and exact declaration remain unresolved.'
    if DFU else
    'Original return declaration, native class layout, vtable ABI and physical device '
    'behavior remain unresolved. Portable uint32_t models the observed result word.'
)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def replay(executable, case):
    command = [str(executable.resolve()), *map(str, case['arguments'])]
    output = subprocess.check_output(command, text=True)
    if DFU:
        if len(output.splitlines()) != 1:
            raise ValueError(f'Expected one immutable diagnostic string: {output!r}')
        return output.rstrip('\n')
    actual = dict(reads=[], writes=[])
    for line in output.splitlines():
        kind, word = line.split()
        if kind == 'value' and 'value' not in actual:
            actual['value'] = int(word)
        elif kind in {'read', 'write'}:
            actual[kind + 's'].append(int(word))
        else:
            raise ValueError(f'Unexpected DSP replay output: {line!r}')
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
    if not DFU:
        import struct
        binding = document['binding']
        start = binding['provider_offset']
        observed = hashlib.sha256(native[start:start + binding['provider_size']]).hexdigest()
        if observed != binding['provider_sha256']:
            raise ValueError('Original provider range mismatch')
        slot_offset = binding['vtable_slot'] - 0x8000
        if struct.unpack_from('<I', native, slot_offset)[0] != document['address']:
            raise ValueError('Native vtable member mismatch')
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
    dependencies = {} if DFU else {s: digest(LIB / s) for s in PROVIDER}
    evidence = dict(
        task=TASK, replay_passed=True, case_count=len(results), validation_domain=DOMAIN,
        provider_source_sha256=dependencies, results=results, proposed_readiness=dict(ready=[], pending=[row]),
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
