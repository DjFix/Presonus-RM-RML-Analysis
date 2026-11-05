#!/usr/bin/env python3
"""Bounded replay checks; never mutate production, provider, packets or ledgers."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

BASE = Path('uc-library/candidates/rolling200_02_permissions_readonly')
WORK = Path('temp/recovery-work/permissions-readonly-local01')
EVIDENCE = Path('evidence/recovery/2026-11-05/permissions-readonly01')
SOURCES = ['uc-library/include/presonus/uc/ClientSubscription.hpp', 'uc-library/include/presonus/mixer/PermissionsComponent.hpp', 'uc-library/src/Presonus/Mixer/PermissionsComponent.cpp', 'uc-library/tests/recovery/PermissionsReadonlyReplay.cpp']
PACKETS = Path('temp/recovery-work/rolling200-02/implementation-plan01/packets-current-permissions-readonly04-01/packets')

def run(argv):
    print(json.dumps(argv), flush=True)
    subprocess.run(argv, check=True)

def compile_check(sanitize=False):
    WORK.mkdir(parents=True, exist_ok=True)
    suffix = '-sanitized' if sanitize else ''
    obj = str(WORK / ('PermissionsComponent' + suffix + '.o'))
    flags = ['g++', '-std=c++17', '-O1' if sanitize else '-O2', '-ffunction-sections', '-fdata-sections', '-Wno-multichar', '-Iuc-library/include', '-Ithird_party/ccl-framework']
    if sanitize:
        flags += ['-fsanitize=address,undefined', '-fno-sanitize=vptr', '-fno-omit-frame-pointer']
    run(flags + ['-c', SOURCES[2], '-o', obj])
    run(flags + [SOURCES[3], obj, '-Wl,--gc-sections', '-o', str(WORK / ('replay' + suffix))])


def symbols_check():
    output = subprocess.check_output(['nm', '--defined-only', str(WORK / 'PermissionsComponent.o')], text=True)
    symbols = {line.split()[-1] for line in output.splitlines() if line.split()}
    for packet in sorted(PACKETS.iterdir()):
        identity = json.loads((packet / 'request.json').read_text())['targets'][0]['mangled']
        assert identity in symbols, identity
        print(identity)
    print('ELF host symbol names match all four originals; no object-format prefix adjustment. Return declarations and ARM ABI remain unresolved.')


def native_check():
    out = WORK / 'native-replay'
    run(['uc-library/.venv/bin/python', str(BASE / 'native_oracle.py'), '--out', str(out)])
    for name in ['native-fixture.txt', 'native-traces.jsonl', 'native-proof.json']:
        assert (out / name).read_bytes() == (EVIDENCE / name).read_bytes(), name
    print('Exact original range, ELF and PC/write boundary verification reproduced; native fixture/traces identical.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('kind', choices=['format', 'compile', 'symbols', 'native', 'replay', 'sanitizers'])
    parser.add_argument('--executable', default=str(WORK / 'replay'))
    parser.add_argument('--fixture', default=str(EVIDENCE / 'native-fixture.txt'))
    args = parser.parse_args()
    if args.kind == 'format':
        run(['uc-library/.venv/bin/clang-format', '--version'])
        run(['uc-library/.venv/bin/clang-format', '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror'] + SOURCES)
    elif args.kind == 'compile':
        run(['g++', '--version'])
        compile_check()
    elif args.kind == 'symbols':
        symbols_check()
    elif args.kind == 'native':
        native_check()
    elif args.kind == 'replay':
        run([args.executable, args.fixture])
    elif args.kind == 'sanitizers':
        compile_check(True)
        run([str(WORK / 'replay-sanitized'), args.fixture])

if __name__ == '__main__':
    main()
