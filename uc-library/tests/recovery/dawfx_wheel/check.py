"""Local repeatable format, compile, exact-symbol and fixture replay gates."""
import argparse
import json
import os
import subprocess
from pathlib import Path

CANONICAL = Path('/home/rs/projects/opencs/ai-line-analysis')
BUILD = CANONICAL / 'temp/core-upstream/root-integration-01'
HERE = Path('uc-library/tests/recovery/dawfx_wheel')
SCRATCH = Path('temp/dawfx-wheel')
SOURCES = ['uc-library/include/presonus/surface/DawFxPageComponent.hpp', 'uc-library/src/Presonus/Surface/DawFxPageComponent.cpp', str(HERE / 'Replay.cpp')]
SYMBOL = '_ZN8Presonus7Surface18DawFxPageComponent12onWheelInputERKN4Core8Portable10WheelEventE'

def run(argv):
    print(json.dumps([str(x) for x in argv]), flush=True)
    subprocess.run([str(x) for x in argv], check=True, env={**os.environ, 'TMPDIR': str(SCRATCH.resolve())})

def main():
    p = argparse.ArgumentParser()
    p.add_argument('gate', choices=['format', 'compile', 'symbols', 'replay'])
    p.add_argument('--fixture', default='temp/dawfx-wheel/native.json')
    p.add_argument('--executable', default='temp/dawfx-wheel/replay')
    a = p.parse_args()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    if a.gate == 'format':
        run(['uc-library/.venv/bin/clang-format', '--version'])
        run(['uc-library/.venv/bin/clang-format', '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror', *SOURCES])
    if a.gate == 'compile':
        flags = ['-std=c++20', '-fno-rtti', '-O2', '-pthread', '-Ulinux', '-DCORE_USE_OPENSSL=1', '-DPRESONUS_HAS_UPSTREAM_CORE=1', '-Iuc-library/include', '-Ithird_party/ccl-framework', '-I'+str(BUILD/'upstream-core/sdk/include/presonus-core-5')]
        run(['/usr/bin/c++', *flags, '-c', SOURCES[1], '-o', SCRATCH/'wheel.o'])
        run(['/usr/bin/c++', *flags, str(HERE/'Replay.cpp'), SCRATCH/'wheel.o', 'uc-library/src/Presonus/Surface/DawFxPageMapping.cpp', BUILD/'libpresonus_cs18_components.a', BUILD/'upstream-core/sdk/lib/libcorelib.a', BUILD/'upstream-core/sdk/lib/libpresonus_core_allocator.a', '/usr/lib/x86_64-linux-gnu/libpng16.so.16', '-lz', '-lssl', '-lcrypto', CANONICAL/'temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so', '-ldl', BUILD/'private-glibc29-provider/libpresonus_private_glibc29.a', '-lm', '-o', a.executable])
    if a.gate == 'symbols':
        result = subprocess.check_output(['nm', '--defined-only', str(SCRATCH/'wheel.o')], text=True)
        assert any(line.split()[-1] == SYMBOL for line in result.splitlines())
        print(result)
    if a.gate == 'replay':
        fixture = json.loads(Path(a.fixture).read_text())
        assert fixture['mangled'] == SYMBOL and len(fixture['cases']) == 26
        total = 0
        for case in fixture['cases']:
            assert case['calls'][0]['delta'] == case['delta']
            result = subprocess.check_output([a.executable, str(case['calls'][0]['delta']), str(case['axis'])], text=True)
            assert result.strip() == '600 provider regressions passed', result
            total += 600
        print(f'{len(fixture["cases"])} ARM boundary cases; {total} CCL/existing-provider regressions passed')

if __name__ == '__main__':
    main()
