MODE = 'focus'
import json
from pathlib import Path
import subprocess
import sys

here = Path(__file__).resolve().parent
root = here.parents[3]
canonical = next(parent for parent in (root, *root.parents)
                 if (parent / 'rootfs/CS18_v13840/home/root/surface').is_file())
build = canonical / 'temp/core-upstream/root-integration-01'
sdk = build / 'upstream-core/sdk'
scratch = root / 'temp/recovery-work' / (here.name + '-check')
executable = scratch / 'replay'
obj = scratch / 'table.o'
owned_header = Path('presonus/surface/AssignmentHandlerTable.hpp')
overlay = scratch / 'owned-headers'
fixture = here / 'fixtures.json'
source = 'uc-library/src/Presonus/AssignmentHandlerTable.cpp'
symbols = json.loads(fixture.read_text())['original']['mangled']
common = ['/usr/bin/c++', '-std=gnu++20', '-O2', '-DNDEBUG=1',
          '-DPRESONUS_HAS_UPSTREAM_CORE=1', '-DCORE_USE_OPENSSL=1',
          '-pthread', '-Ulinux', '-I', str(overlay),
          '-I', str(canonical / 'uc-library/include'),
          '-isystem', str(sdk / 'include/presonus-core-5'),
          '-isystem', str(sdk / 'include/presonus-core-codecs')]
dependencies = [str(build / 'libpresonus_cs18_components.a'),
                *(str(sdk / 'lib' / name) for name in
                  ('libcorelib.a', 'libpresonus_core_allocator.a',
                   'libpresonus_png.a', 'libpresonus_zlib.a')),
                '-lssl', '-lcrypto',
                str(build.parent / 'external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so'),
                '-ldl',
                str(build / 'private-glibc29-provider/libpresonus_private_glibc29.a'),
                '-lm']

def run_command(argv):
    print(json.dumps(argv), flush=True)
    subprocess.run(argv, cwd=root, check=True)

def replay(exe, fixtures):
    observed = json.loads(fixtures.read_text())['cases']
    count = 0
    for case in observed:
        slots = case['slots']
        if MODE == 'count':
            for mode in range(3):
                expected = case['result']
                if mode == 2 and slots:
                    comparable = next(other for other in observed
                                      if other['slots'] == slots[:-1])
                    expected = comparable['result']
                actual = subprocess.check_output([exe, slots, str(mode)], text=True)
                assert int(actual) == expected, (case, mode, actual)
                count += 1
        else:
            expected = []
            for call, index, value in case['trace']:
                expected.append(f'{call} {index} {int(value)}')
            expected.append(f'result {case["result"]} {case["info"]}')
            for mode in range(2):
                actual = subprocess.check_output(
                    [exe, slots, str(int(case['parameter'])), str(mode)],
                    text=True).splitlines()
                assert actual == expected, (case, mode, actual)
                count += 1
    print(f'Portable {MODE}: {count} comparisons to {len(observed)} native cases')

if sys.argv[1] == 'compile':
    header = overlay / owned_header
    header.parent.mkdir(parents=True, exist_ok=True)
    header.write_bytes((root / 'uc-library/include' / owned_header).read_bytes())
    run_command([*common, '-c', source, '-o', str(obj)])
    run_command([*common, str(here / 'Replay.cpp'), str(obj), *dependencies,
                 '-o', str(executable)])
elif sys.argv[1] == 'symbols':
    output = subprocess.check_output(['nm', '--defined-only', str(obj)], text=True)
    line = next(line for line in output.splitlines() if line.split()[-1] == symbols)
    assert line.split()[1] == 'T'
    print(line)
elif sys.argv[1] == 'replay':
    replay(Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else executable,
           Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else fixture)
else:
    raise SystemExit('expected compile, symbols or replay')
