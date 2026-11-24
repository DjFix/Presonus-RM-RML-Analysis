"""Check exact host symbols and compare rebuilt C++ with original ARM observations."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

from native import MANGLED, METHOD, TASK, digest, observe

TEST = Path('uc-library/tests/recovery') / TASK
SOURCE = Path('uc-library/src/Presonus/ChannelGroupFilter.cpp')
HEADER = Path('uc-library/include/presonus/ChannelGroupFilter.hpp')
CORE = Path('third_party/ccl-framework/core/public/corevector.h')
FILES = (SOURCE, HEADER, TEST / 'Replay.cpp')
OUT = Path('temp/recovery-work/lane10-channel-filter') / TASK
SDK = Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk')
INCLUDE = SDK / 'include/presonus-core-5'
LIBS = [SDK / 'lib' / path for path in ('libcorelib.a', 'libpresonus_core_allocator.a')]
PIN = 'e8cbdea4a4a20e15111f5a690798a259c0374b31'
FORMATTER = 'uc-library/.venv/bin/clang-format'
FORMAT = [FORMATTER, '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror', *map(str, FILES)]
CXX = ['/usr/bin/c++', '-std=c++17', '-O2', '-Ulinux', '-fno-rtti', '-fno-sized-deallocation',
       '-Iuc-library/include', '-isystem', str(INCLUDE)]
DOMAINS = {
    'count': 'Empty, singleton, all-hidden, all-visible and mixed normalized visibility across both original ELF roles.',
    'visible': 'Normalized visibility and both CCL bool error states, negative, in-range and at/above-count indices across both original ELF roles.',
    'getChannelOffset': 'First and later visible ordinals, all-hidden and empty vectors, negative and out-of-range ordinals and capacity fallback, with logical size differing from capacity in both ELF roles.',
}
LIMITS = [
    'The original C++ return declaration, member/virtual declaration traits, inheritance and layout remain unresolved.',
    'Host replay uses the pinned CCL bool vector and typed bool state; raw malformed bool values and ARM binary interoperability are outside its domain.',
    'ARM executions use synthetic object, item and stack memory. No external calls or non-stack writes are permitted. Hardware behavior is untested.',
]


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return digest(path.read_bytes())


def symbols(path):
    argv = ['/usr/bin/nm', '--defined-only', str(path)]
    lines = subprocess.check_output(argv, text=True).splitlines()
    exact, = (line for line in lines if line.split() and line.split()[-1] == MANGLED)
    return {'argv': argv, 'matched': exact}


def compile_argv(object_path):
    return [*CXX, '-c', str(SOURCE), '-o', str(object_path)]


def link_argv(object_path, exe):
    return [*CXX, str(TEST / 'Replay.cpp'), str(object_path), *map(str, LIBS), '-o', str(exe)]


def proof(args, fixture):
    started = utc()
    sdk_vector = INCLUDE / 'core/public/corevector.h'
    assert sha(sdk_vector) == sha(CORE) == '49634ef286112cfa48357391a3cdddbee86e76cfe5e820b6b74c6ec913aeed32'
    integration_hash = None
    if args.integration is not None:
        integration = json.loads(args.integration.read_text())
        assert integration['platform'] == 'linux' and integration['ctest_passed'] is True
        integration_hash = sha(args.integration)
    subprocess.run(FORMAT, check=True)
    symbol = symbols(args.object)
    roles = fixture['observations']
    cases = [case for role in roles for case in role['cases']]
    case_lines = []
    for case in cases:
        items, index, error = case['input']
        case_lines.append(' '.join(map(str, [len(items), index, error, *items])) + '\n')
    argv = [str(args.exe)]
    output = subprocess.check_output(argv, input=''.join(case_lines), text=True)
    values = [list(map(int, line.split())) for line in output.splitlines()]
    assert values == [[case['result'], case['capacity']] for case in cases]
    assert all(case['external_calls'] == case['external_memory_writes'] == 0 for case in cases)
    sources = {str(path.relative_to('uc-library')): sha(path) for path in (SOURCE, HEADER)}
    rows = [
        dict(original_elf_sha256=role['original']['elf_sha256'], mangled=MANGLED, cpp_compiled=True,
             mangling_namespace_checked=True, portable_ready=False, sources=sources,
             repository_sources={str(CORE): sha(CORE)}, validation_domain=DOMAINS[METHOD],
             declaration_uncertainties=LIMITS[:1])
        for role in roles
    ]
    receipt = dict(
        task_id=TASK, cpp_differential_passed=True, compiled_mangled_names_matched=True,
        format_check_passed=True, portable_ready=False, mangled_names=[MANGLED], functions=rows,
        proposed_readiness={'ready': [], 'pending': rows}, validation_domain=DOMAINS[METHOD],
        formatter_version=subprocess.check_output([FORMATTER, '--version'], text=True).strip(),
        format_argv=FORMAT, formatted_files={str(path.relative_to('uc-library')): sha(path) for path in FILES},
        fixture_sha256=sha(args.fixtures), native=fixture,
        portable={'argv': argv, 'case_count': len(values), 'results': values},
        compiled_symbol=symbol, object_sha256=sha(args.object), exe_sha256=sha(args.exe),
        producer_inputs={str(TEST / name): sha(TEST / name) for name in ('check.py', 'native.py')},
        ccl_commit=PIN, ccl_sdk_header_sha256=sha(sdk_vector),
        integration=str(args.integration) if args.integration else None, integration_sha256=integration_hash,
        started_utc=started, finished_utc=utc(), limitations=LIMITS,
    )
    if not args.integration:
        receipt.update(compile_argv=compile_argv(args.object), link_argv=link_argv(args.object, args.exe),
                       compiler_version=subprocess.check_output([CXX[0], '--version'], text=True).splitlines()[0],
                       provider_archives={str(path): sha(path) for path in LIBS})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(receipt, indent=2) + '\n')
    print(f'{TASK}: {len(values)} portable results matched both original ELF roles')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('capture', 'native', 'format', 'compile', 'symbols', 'proof'))
    parser.add_argument('--exe', type=Path, default=OUT / 'Replay')
    parser.add_argument('--object', type=Path, default=OUT / 'ChannelGroupFilter.o')
    parser.add_argument('--fixtures', type=Path, default=TEST / 'fixtures.json')
    parser.add_argument('--integration', type=Path)
    parser.add_argument('--out', type=Path, default=OUT / 'proof.json')
    args = parser.parse_args()
    if args.mode == 'capture':
        args.fixtures.write_text(json.dumps(observe(), indent=2) + '\n')
    elif args.mode == 'native':
        assert json.loads(args.fixtures.read_text()) == observe()
        print(f'{TASK}: independent ARM replay reproduced the sealed fixture')
    elif args.mode == 'format':
        subprocess.run(FORMAT, check=True)
    elif args.mode == 'compile':
        OUT.mkdir(parents=True, exist_ok=True)
        for argv in (compile_argv(args.object), link_argv(args.object, args.exe)):
            print(json.dumps(argv), flush=True)
            subprocess.run(argv, check=True)
    elif args.mode == 'symbols':
        print(json.dumps(symbols(args.object)))
    else:
        fixture = json.loads(args.fixtures.read_text())
        assert fixture['method'] == METHOD
        proof(args, fixture)


if __name__ == '__main__':
    main()
