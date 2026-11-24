"""Compile the scoped port and compare portable output to sealed ARM observations."""

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

import native

TASK = 'rolling_wheel_wifisetupcomponent'
PYTHON = 'uc-library/.venv/bin/python'
SOURCE = 'uc-library/src/Presonus/Surface/WifiSetupComponent.cpp'
HEADER = 'uc-library/include/presonus/surface/WifiSetupComponent.hpp'
TEST = f'uc-library/tests/recovery/{TASK}/Replay.cpp'
CHECKER = f'uc-library/tests/recovery/{TASK}/check.py'
FIXTURE = f'uc-library/tests/recovery/{TASK}/fixtures.json'
PRODUCER = f'uc-library/tests/recovery/{TASK}/native.py'
LOCAL = Path(f'temp/recovery-work/{TASK}')
BUILD = Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01')
DOMAIN = ('240 original ARM and portable cases covering four current offsets, five signed '
          'deltas including zero, three network list sizes, visible and hidden pages, both '
          'wheel axes, forwarded receiver and delta, clamping, and display update traces.')
LIMITS = ['Original return declaration and virtual inheritance/slot ownership remain '
          'unresolved. The portable member uses void and existing receiver lifecycle.',
          'Native CCL, page visibility and numeric conversion boundaries are modeled. '
          'The portable replay uses pinned CCL and a page binding fixture. No ARM object '
          'layout, hardware or binary interoperability claim.']
CORE = 'third_party/ccl-framework/core/portable/gui/coreview.h'
FLAGS = ['-std=c++17', '-O2', '-fno-rtti', '-fno-lto', '-fno-fast-math',
         '-ffp-contract=off', '-ffunction-sections', '-fdata-sections', '-DNDEBUG',
         '-Wno-multichar', '-pthread', '-Ulinux', '-DCORE_USE_OPENSSL=1',
         '-DPRESONUS_HAS_UPSTREAM_CORE=1', '-Iuc-library/include',
         '-Ithird_party/ccl-framework']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(args, **kwargs):
    args = [str(item) for item in args]
    print(json.dumps(args), flush=True)
    return subprocess.run(args, check=True, **kwargs)


def symbols(obj):
    listed = run(['/usr/bin/nm', '--defined-only', obj],
                 capture_output=True, text=True).stdout
    assert sum(line.split()[-1] == native.NAME for line in listed.splitlines()
               if line.split()) == 1
    print(native.NAME)


def format_check():
    formatter = 'uc-library/.venv/bin/clang-format'
    version = run([formatter, '--version'], capture_output=True, text=True).stdout.strip()
    run([formatter, '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror',
         HEADER, SOURCE, TEST])
    return version


def compile_local():
    sdk = BUILD / 'upstream-core/sdk/lib'
    LOCAL.mkdir(parents=True, exist_ok=True)
    tools_env = dict(os.environ, TMPDIR=str(LOCAL.resolve()))
    run(['/usr/bin/c++', *FLAGS, '-c', SOURCE, '-o', LOCAL / 'WifiSetupComponent.o'],
        env=tools_env)
    run(['/usr/bin/c++', *FLAGS, TEST, LOCAL / 'WifiSetupComponent.o', '-Wl,--gc-sections',
         '-Wl,--start-group', BUILD / 'libpresonus_cs18_components.a',
         sdk / 'libcorelib.a', sdk / 'libpresonus_core_allocator.a',
         sdk / 'libpresonus_png.a', sdk / 'libpresonus_zlib.a',
         BUILD / 'private-glibc29-provider/libpresonus_private_glibc29.a',
         '-Wl,--end-group', '-lpthread', '-ldl', '-lrt', '-lssl', '-lcrypto',
         '-o', LOCAL / 'Replay'], env=tools_env)


def proof(args):
    symbols(args.object)
    fixtures = json.loads(Path(args.fixture).read_text())
    rows = [' '.join(map(str, case['input'])) for case in fixtures['cases']]
    expected = [line for case in fixtures['cases'] for line in case['output']]
    result = run([Path(args.exe).resolve()], input='\n'.join(rows) + '\n',
                 capture_output=True, text=True).stdout.splitlines()
    if result != expected:
        import difflib
        raise AssertionError('\n'.join(difflib.unified_diff(expected, result)))
    version = format_check()
    sources = {name.removeprefix('uc-library/'): digest(name) for name in (SOURCE, HEADER)}
    row = dict(original_elf_sha256=native.SHA, elf_sha256=native.SHA, mangled=native.NAME,
               validation_domain=DOMAIN, domain=DOMAIN, sources=sources,
               cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
               declaration_uncertainties=LIMITS, repository_sources={CORE: digest(CORE)})
    report = dict(cpp_differential_passed=True, compiled_mangled_names_matched=True,
                  mangled_names=[native.NAME], cases=len(rows), validation_domain=DOMAIN,
                  limitations=LIMITS, original_ranges=fixtures['ranges'],
                  formatter=dict(version=version, files=sources),
                  executable_sha256=digest(args.exe), object_sha256=digest(args.object),
                  integration_sha256=digest(args.integration), fixture_sha256=digest(args.fixture),
                  oracle_sha256=digest(PRODUCER), checker_sha256=digest(CHECKER),
                  proposed_readiness=dict(ready=[], pending=[row]))
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(f'{len(rows)} portable ARM-oracle differential cases')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['format', 'compile', 'symbols', 'proof'])
    parser.add_argument('--exe', default=LOCAL / 'Replay')
    parser.add_argument('--object', default=LOCAL / 'WifiSetupComponent.o')
    parser.add_argument('--fixture', default=FIXTURE)
    parser.add_argument('--integration', default=BUILD / 'CMakeCache.txt')
    parser.add_argument('--out', default=LOCAL / 'proof.json')
    args = parser.parse_args()
    if args.mode == 'format':
        print(format_check())
    elif args.mode == 'compile':
        compile_local()
    elif args.mode == 'symbols':
        symbols(args.object)
    else:
        proof(args)


if __name__ == '__main__':
    main()
