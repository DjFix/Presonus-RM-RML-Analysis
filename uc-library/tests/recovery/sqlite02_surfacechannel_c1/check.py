import hashlib
import json
from pathlib import Path
import subprocess
import sys

here = Path(__file__).resolve().parent
root = here.parents[3]
canonical = next(p for p in (root, *root.parents)
                 if (p / 'rootfs/CS18_v13840/home/root/surface').is_file())
build = canonical / 'temp/core-upstream/root-integration-01'
sdk = build / 'upstream-core/sdk'
scratch = root / 'temp/recovery-work' / (here.name + '-check')
fixture = here / 'fixtures.json'
symbol = json.loads(fixture.read_text())['original']['mangled']
sources = [Path(path) for path in ['uc-library/src/Presonus/Surface/SurfaceChannelComponent.cpp', 'uc-library/src/Presonus/UC/ServerComponent.cpp']]
sources.append((here / 'Replay.cpp').relative_to(root))
executable = scratch / 'replay'
common = ['/usr/bin/c++', '-std=gnu++20', '-O2', '-DNDEBUG=1',
          '-DPRESONUS_HAS_UPSTREAM_CORE=1', '-DCORE_USE_OPENSSL=1',
          '-pthread', '-Ulinux', '-Iuc-library/include',
          '-isystem', str(sdk / 'include/presonus-core-5'),
          '-isystem', str(sdk / 'include/presonus-core-codecs')]
providers = [sdk / 'lib' / name for name in
             ('libcorelib.a', 'libpresonus_core_allocator.a', 'libpresonus_png.a',
              'libpresonus_zlib.a')]
providers.append(build / 'private-glibc29-provider/libpresonus_private_glibc29.a')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run(argv):
    command = list(map(str, argv))
    print(json.dumps(command), flush=True)
    completed = subprocess.run(command, cwd=root, check=True)
    return {'argv': command, 'cwd': str(root), 'exit_code': completed.returncode}

def compile_replay():
    scratch.mkdir(parents=True, exist_ok=True)
    objects = []
    commands = []
    for source in sources:
        obj = scratch / (source.stem + '.o')
        depfile = obj.with_suffix('.d')
        invocation = run([*common, '-MD', '-MF', depfile, '-c', source, '-o', obj])
        commands.append({**invocation, 'source': str(source), 'source_sha256': digest(root / source),
                         'object': str(obj), 'object_sha256': digest(obj),
                         'depfile': str(depfile), 'depfile_sha256': digest(depfile)})
        objects.append(obj)
    link = run([*common, *objects, *providers, '-ldl', '-lm', '-o', executable])
    report = {'cwd': str(root), 'compile': commands, 'link': link,
              'executable': str(executable), 'executable_sha256': digest(executable),
              'providers': [{'path': str(path), 'sha256': digest(path)} for path in providers]}
    (scratch / 'build.json').write_text(json.dumps(report, indent=2) + '\n')

def verify_symbols():
    obj = scratch / 'SurfaceChannelComponent.o'
    output = subprocess.check_output(['nm', '--defined-only', obj], text=True)
    line = next(line for line in output.splitlines() if line.split()[-1] == symbol)
    assert line.split()[1] == 'T'
    print(line)
    replay_symbols = subprocess.check_output(['nm', '-u', scratch / 'Replay.o'], text=True)
    assert any(line.split()[-1] == symbol for line in replay_symbols.splitlines()), replay_symbols
    if False:
        down = subprocess.check_output(['nm', '-u', obj], text=True)
        assert '_ZN8Presonus7Surface23SurfaceChannelComponentC2Ei' in down

def replay(exe, fixtures):
    cases = json.loads(fixtures.read_text())['cases']
    for row in cases:
        argv = [exe, str(row['argument'])]
        actual = subprocess.check_output(argv, text=True)
        assert int(actual) == row['mode'], (row, actual)
    print(f'Portable constructor replay: {len(cases)} native comparisons')

if sys.argv[1] == 'compile':
    compile_replay()
elif sys.argv[1] == 'symbols':
    verify_symbols()
elif sys.argv[1] == 'replay':
    replay(Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else executable,
           Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else fixture)
else:
    raise SystemExit('expected compile, symbols or replay')
