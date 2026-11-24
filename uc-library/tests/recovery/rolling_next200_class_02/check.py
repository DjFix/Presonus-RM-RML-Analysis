"""Build and replay the Messenger initialization comparison."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

from native import digest, observations

TASK = 'rolling_next200_class_02'
TEST = Path('uc-library/tests/recovery') / TASK
WORK = Path('temp/recovery-work') / TASK
CPP = Path('uc-library/src/Presonus/Link/Messenger.cpp')
HEADER = Path('uc-library/include/presonus/link/Messenger.hpp')
FIXTURE = TEST / 'fixtures.json'
SOURCES = [HEADER, CPP]
FORMAT = ['uc-library/.venv/bin/clang-format']
BUILD = Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01')
LIBS = [BUILD / name for name in (
    'upstream-core/sdk/lib/libcorelib.a',
    'upstream-core/sdk/lib/libpresonus_core_allocator.a',
    'private-glibc29-provider/libpresonus_private_glibc29.a',
)]
CORE = ['third_party/ccl-framework/core/' + name for name in (
    'portable/coresingleton.h', 'system/corethread.h', 'system/coredebug.h',
)]
DOMAIN = ('Two exact RM/RML mixer 13731 ARM calls with mapped receiver sentinels and distinct '
          'argument registers. Verify return PC, restored SP/FP, preserved R0–R3, unchanged '
          'receiver bytes and stack-frame-only data accesses. Compare two direct portable '
          'calls on independently constructed Messenger objects before and after release, '
          'including byte-for-byte unchanged object representations.')
LIMITS = [
    'Portable virtual void is an explicit choice. The original ordinary return declaration remains unresolved.',
    'Native synthetic receiver buffers are opaque and the portable class uses its existing real CCL lock. '
    'No layout, vtable slot/order, native singleton lifecycle, hardware or ARM ABI claim.',
    'The existing pinned CCL Singleton has no init hook, and its lifecycle remains unchanged. '
    'No fixture stubs are used.',
]
COMMANDS = []


def sha(path):
    return digest(Path(path).read_bytes())


def run(argv):
    argv = list(map(str, argv))
    start = datetime.now(timezone.utc).isoformat()
    result = subprocess.run(argv, check=True, capture_output=True, text=True)
    COMMANDS.append(dict(argv=argv, start_utc=start, end_utc=datetime.now(timezone.utc).isoformat(),
                         returncode=result.returncode, stdout=result.stdout, stderr=result.stderr))
    return result.stdout


def formatting():
    run(FORMAT + ['--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror',
                  *SOURCES, TEST / 'Replay.cpp'])
    return run(FORMAT + ['--version']).strip()


def compile_replay(exe, obj):
    exe.parent.mkdir(parents=True, exist_ok=True)
    obj.parent.mkdir(parents=True, exist_ok=True)
    flags = ['/usr/bin/c++', '-std=c++17', '-O2', '-fno-rtti', '-fno-lto', '-Wno-multichar',
             '-ffunction-sections', '-fdata-sections', '-Ulinux', '-pthread',
             '-Iuc-library/include', '-Ithird_party/ccl-framework']
    driver = WORK / 'driver.o'
    run(flags + ['-c', CPP, '-o', obj])
    run(flags + ['-c', TEST / 'Replay.cpp', '-o', driver])
    run(['/usr/bin/c++', obj, driver, '-Wl,--gc-sections', '-Wl,--start-group', *LIBS,
         '-Wl,--end-group', '-pthread', '-ldl', '-lm', '-lz', '-o', exe])


def symbols(obj, name):
    observed = run(['nm', '--defined-only', obj])
    rows = [line for line in observed.splitlines() if line.split() and line.split()[-1] == name]
    assert len(rows) == 1, rows
    return rows


def native_check(fixture):
    start = datetime.now(timezone.utc).isoformat()
    observed = observations()
    assert observed == json.loads(fixture.read_text())
    return observed, dict(start_utc=start, end_utc=datetime.now(timezone.utc).isoformat())


def compare(exe, original):
    expected = ['case {} {}'.format(case['portable_pre_released'], int(case['receiver_unchanged']))
                for case in original['cases']]
    observed = [line for line in run([exe.resolve()]).splitlines() if line.startswith('case ')]
    assert observed == expected, (observed, expected)
    return len(observed)


def proof(args, original, native_timing):
    version = formatting()
    name = original['mangled']
    matched = symbols(args.object, name)
    count = compare(args.exe, original)
    sources = {str(path.relative_to('uc-library')): sha(path) for path in SOURCES}
    dependencies = {path: sha(path) for path in CORE}
    row = dict(original_elf_sha256=original['elf_sha256'], mangled=name,
               demangled=run(['c++filt', name]).strip(), firmware='RM/RML mixer 13731',
               role='server', address=original['address'], size=original['size'],
               section=original['section'], cpp_compiled=True, mangling_namespace_checked=True,
               portable_ready=False, validation_domain=DOMAIN, sources=sources,
               repository_sources=dependencies, declaration_uncertainties=LIMITS,
               original_function_verified=False, hardware_verified=False)
    result = dict(task_id=TASK, worker_session='/root/rolling_next200_class_02',
                  timestamp_utc=datetime.now(timezone.utc).isoformat(), native=original,
                  native_timing=native_timing, native_invocations=len(original['cases']),
                  cpp_differential_passed=True, compiled_original_mangled_names_matched=True,
                  compiled_symbols=matched, portable_case_count=count,
                  formatting=dict(version=version, passed=True, sources=sources),
                  validation_domain=DOMAIN, limitations=LIMITS, sources=sources,
                  repository_sources=dependencies, proposed_readiness=dict(ready=[], pending=[row]),
                  commands=COMMANDS,
                  binary_bindings={str(path): sha(path) for path in (args.exe, args.object)},
                  fixture_sha256=sha(args.fixtures), producer_sha256=sha(__file__),
                  native_producer_sha256=sha(TEST / 'native.py'),
                  test_sources={str(TEST / 'Replay.cpp'): sha(TEST / 'Replay.cpp')})
    if args.integration:
        result['integration'] = {'path': str(args.integration), 'sha256': sha(args.integration)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(f'{count} original and portable cases matched')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['format', 'compile', 'symbols', 'native', 'replay', 'proof'])
    parser.add_argument('--exe', type=Path, default=WORK / 'replay')
    parser.add_argument('--object', type=Path, default=WORK / 'production.o')
    parser.add_argument('--fixtures', type=Path, default=FIXTURE)
    parser.add_argument('--integration', type=Path)
    parser.add_argument('--out', type=Path, default=WORK / 'proof.json')
    args = parser.parse_args()
    if args.mode == 'format':
        print(formatting())
    elif args.mode == 'compile':
        compile_replay(args.exe, args.object)
        print(json.dumps(COMMANDS, indent=2))
    elif args.mode == 'symbols':
        print(*symbols(args.object, json.loads(args.fixtures.read_text())['mangled']), sep='\n')
    else:
        original, native_timing = native_check(args.fixtures)
        if args.mode == 'native':
            print(f"{len(original['cases'])} exact original ARM observations reproduced")
        elif args.mode == 'replay':
            print(f'{compare(args.exe, original)} original and portable cases matched')
        else:
            proof(args, original, native_timing)


if __name__ == '__main__':
    main()
