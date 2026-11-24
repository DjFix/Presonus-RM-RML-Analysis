"""Compile and differentially replay the recovered base meter hook."""
import argparse
import datetime
import hashlib
import json
import subprocess
from pathlib import Path

import native
import unicorn

ROOT = Path(__file__).resolve().parents[4]
BASE = Path(__file__).parent.relative_to(ROOT) if Path(__file__).is_absolute() else Path(__file__).parent
TASK = BASE.name
SCRATCH = Path('temp/recovery-work') / TASK
# CCL runtime is built and owned by the canonical Linux integration checkout.
PROVIDER_BUILD = Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01')
CPP = Path('uc-library/src/Presonus/MeterManagerBase.cpp')
HEADER = Path('uc-library/include/presonus/MeterManagerBase.hpp')
TEST = BASE / 'Replay.cpp'
FIXTURE = BASE / 'fixtures.json'
PYTHON = Path('uc-library/.venv/bin/python')
FORMAT = [Path('uc-library/.venv/bin/clang-format'), '--style=file',
          '--fallback-style=LLVM', '--dry-run', '--Werror', CPP, HEADER, TEST]
CORE_SOURCES = [Path('third_party/ccl-framework') / name for name in (
    'core/public/corevector.h', 'core/system/corethread.h',
    'core/platform/shared/posix/corethread.posix.cpp', 'core/platform/linux/corethread.linux.cpp')]
DOMAIN = (
    'Eight offline RM ARM calls cover both bool values and four receiver/stack '
    'sentinel patterns. The callee returns after four instructions, restores SP '
    'and FP, preserves receiver and bool registers, and accesses only its '
    '16-byte stack frame. Eight live CCL-backed C++ calls compare the receiver '
    'object representation across running, stop and client-vector states; '
    'test-only application services abort on unexpected calls.'
)
LIMITS = [
    'Original return type unresolved. The source-port virtual hook uses void '
    'with access chosen alongside processMeters; native table slot supports '
    'member dispatch, but original access and portable vtable position are unverified.',
    'Native receivers are synthetic mapped sentinels; original construction, '
    'destruction, real overrides, threading, layout, ARM ABI and hardware are outside scope.'
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('format', 'compile', 'symbols', 'native', 'replay'))
    parser.add_argument('--exe', type=Path, default=SCRATCH / 'replay')
    parser.add_argument('--object', type=Path, default=SCRATCH / 'MeterManagerBase.o')
    parser.add_argument('--fixtures', type=Path, default=FIXTURE)
    parser.add_argument('--integration', type=Path)
    parser.add_argument('--out', type=Path, default=SCRATCH / 'local-proof.json')
    args = parser.parse_args()
    assert Path.cwd() == ROOT
    commands = []

    def run(argv, **kwargs):
        command = list(map(str, argv))
        print(json.dumps(command), flush=True)
        result = subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE,
                                **kwargs)
        commands.append({'argv': command, 'exit_code': result.returncode})
        return result.stdout.strip()

    if args.mode == 'format':
        run(FORMAT)
        return
    if args.mode == 'compile':
        SCRATCH.mkdir(parents=True, exist_ok=True)
        flags = ['/usr/bin/c++', '-std=c++17', '-O2', '-fno-rtti', '-pthread',
                 '-Ulinux', '-DPRESONUS_HAS_UPSTREAM_CORE=1', '-DCORE_USE_OPENSSL=1',
                 '-Iuc-library/include', '-isystem', 'third_party/ccl-framework']
        lib = PROVIDER_BUILD / 'upstream-core/sdk/lib'
        dns = PROVIDER_BUILD.parent / 'external-dev/usr/lib/x86_64-linux-gnu'
        run([*flags, '-c', CPP, '-o', args.object])
        run([*flags, TEST, args.object, lib / 'libcorelib.a',
             lib / 'libpresonus_core_allocator.a', lib / 'libpresonus_png.a',
             lib / 'libpresonus_zlib.a', '-lssl', '-lcrypto', dns / 'libdns_sd.so',
             '-ldl', PROVIDER_BUILD / 'private-glibc29-provider/libpresonus_private_glibc29.a',
             '-lm', f'-Wl,-rpath,{dns}', '-o', args.exe])
        return
    if args.mode in ('symbols', 'replay'):
        defined = run(['/usr/bin/nm', '--defined-only', args.object])
        matches = [line for line in defined.splitlines() if line.split()[-1] == native.MANGLED]
        assert len(matches) == 1, matches
        if args.mode == 'symbols':
            return
    start = now()
    fresh = native.generate()
    native_finish = now()
    assert json.loads(args.fixtures.read_text()) == fresh
    cases = fresh['cases']
    if args.mode == 'native':
        print(f'{len(cases)} exact original executions passed')
        return
    inputs = ''.join(f"{case['state']} {case['flag']}\n" for case in cases)
    actual = run([args.exe], input=inputs).splitlines()
    assert actual == [str(int(case['receiver_unchanged'])) for case in cases]
    assert all(case['receiver_unchanged'] for case in cases)
    portable_finish = now()
    run(FORMAT)
    sources = {str(path.relative_to('uc-library')): sha(path) for path in (CPP, HEADER)}
    pinned = {str(path): sha(path) for path in CORE_SOURCES}
    row = dict(original_elf_sha256=native.ELF_SHA, mangled=native.MANGLED,
               sources=sources, repository_sources=pinned, domain=DOMAIN,
               portable_ready=False, declaration_uncertainties=LIMITS[:1],
               cpp_compiled=True, mangling_namespace_checked=True)
    proof = dict(version=1, task_id=TASK, session_id='/root/' + TASK, created=now(),
                 original_elf_path=str(native.ELF), ranges=[fresh['range']],
                 native_cases=len(cases), portable_cases=len(actual),
                 native_case_started_utc=start, native_case_finished_utc=native_finish,
                 portable_case_finished_utc=portable_finish,
                 arm_differential_passed=True, compiled_mangled_names_matched=True,
                 compiled_symbols=matches, validation_domain=DOMAIN, limitations=LIMITS,
                 formatter_version=run(['uc-library/.venv/bin/clang-format', '--version']),
                 compiler_version=run(['/usr/bin/c++', '--version']).splitlines()[0],
                 unicorn_version=unicorn.__version__, functions=[row],
                 proposed_readiness=dict(canonical_binding_pending=args.integration is None,
                                         ready=[], pending=[row]), commands=commands)
    proof['inputs'] = {str(path): sha(path) for path in (
        CPP, HEADER, TEST, args.fixtures, args.exe, args.object, BASE / 'native.py',
        BASE / 'check.py')}
    if args.integration:
        proof['integration'] = dict(path=str(args.integration), sha256=sha(args.integration))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + '\n')
    print(f'{len(cases)} ARM/C++ cases passed')


if __name__ == '__main__':
    main()
