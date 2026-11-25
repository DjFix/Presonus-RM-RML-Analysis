"""Compile and compare the portable FX recall against exact ARM observations."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

from native import digest, generate

TEST = Path('uc-library/tests/recovery/sqlite03_fx_preset_recall')
SRC = Path('uc-library/src/Presonus/Panel/FXPresetRecallComponent.cpp')
HEADER = Path('uc-library/include/presonus/panel/FXPresetRecallComponent.hpp')
PY = 'uc-library/.venv/bin/python'
CLANG = 'uc-library/.venv/bin/clang-format'
WORK = Path('temp/recovery-work/sqlite03-fx-recall-local')
EXE = WORK / 'replay'
FIXTURES = TEST / 'fixtures.json'
SYMBOL = '_ZN8Presonus5Panel23FXPresetRecallComponent14recallFxPresetEv'
ARCHIVE = '_ZN4Core8Portable12ArchiveUtils12loadFromFileERNS0_10AttributesEPKcNS0_8Archiver6FormatEPNS0_18FileStorageContextEib'
FORMAT = [CLANG, '--style=file', '--fallback-style=LLVM', '--dry-run',
          '--Werror', HEADER, SRC, TEST / 'Replay.cpp']
COMPILE_FLAGS = ['g++', '-std=c++17', '-O2', '-fno-rtti', '-Ulinux',
                 '-Wno-multichar', '-Iuc-library/include', '-Ithird_party/ccl-framework']


def run(argv, **kwargs):
    print(json.dumps(list(map(str, argv))), flush=True)
    return subprocess.run(argv, text=True, check=True, **kwargs)


def local_build():
    root = next(path for path in [Path.cwd(), *Path.cwd().parents]
                if (path / 'temp/core-upstream/root-integration-01/libpresonus_rm_components.a').is_file())
    build = root / 'temp/core-upstream/root-integration-01'
    dns = root / 'temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu'
    libs = [build / 'libpresonus_rm_components.a',
            *[build / 'upstream-core/sdk/lib' / (name + '.a') for name in (
                'libcorelib', 'libpresonus_core_allocator', 'libpresonus_png', 'libpresonus_zlib')],
            build / 'private-glibc29-provider/libpresonus_private_glibc29.a']
    WORK.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, 'TMPDIR': str(WORK.resolve())}
    source_object = WORK / 'recall.o'
    run([*COMPILE_FLAGS, '-c', SRC, '-o', source_object], env=env)
    run([*COMPILE_FLAGS, TEST / 'Replay.cpp', source_object, '-Wl,--start-group',
         *libs, '-Wl,--end-group', '-Wl,--wrap=' + ARCHIVE,
         '-Wl,-rpath,' + str(dns), dns / 'libdns_sd.so', '-lssl', '-lcrypto',
         '-ldl', '-lm', '-pthread', '-o', EXE], env=env)
    print(json.dumps({str(path): digest(path.read_bytes()) for path in libs}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('format', 'compile', 'symbols', 'replay'))
    parser.add_argument('--executable', type=Path, default=EXE)
    parser.add_argument('--fixtures', type=Path, default=FIXTURES)
    args = parser.parse_args()
    if args.mode == 'format':
        run(FORMAT)
    elif args.mode == 'compile':
        local_build()
    elif args.mode == 'symbols':
        output = run(['nm', '--defined-only', args.executable], capture_output=True).stdout
        symbols = [line for line in output.splitlines() if line.split()[-1:] == [SYMBOL]]
        assert len(symbols) == 1, symbols
        print(symbols[0])
    elif args.mode == 'replay':
        observed = json.loads(args.fixtures.read_text())
        assert observed == generate(), 'native evidence mismatch'
        WORK.mkdir(parents=True, exist_ok=True)
        for case in observed['cases']:
            with tempfile.TemporaryDirectory(dir=WORK) as folder:
                replay = run([args.executable.resolve(), *case['argv'], folder],
                             stdout=subprocess.PIPE)
            expected = [*case['trace'], f"result:{case['result']}",
                        f"loadedValue:{case['loaded']}"]
            lines = [line for line in replay.stdout.splitlines()
                     if line not in ('FXComponent::load start', 'FXComponent::load complete')
                     and not line.startswith('  loaded values: ')]
            assert lines == expected, (case['argv'], replay.stdout, expected)
        print(f"Passed {len(observed['cases'])} exact ARM and portable CCL/FX recall comparisons.")


if __name__ == '__main__':
    main()
