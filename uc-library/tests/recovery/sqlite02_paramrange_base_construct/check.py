import hashlib
import json
from pathlib import Path
import subprocess
import sys

here = Path(__file__).resolve().parent
root = here.parents[3]
scratch = root / 'temp/recovery-work' / (here.name + '-check')
fixture = here / 'fixtures.json'
symbol = json.loads(fixture.read_text())['observations'][0]['original']['mangled']
sources = [Path('uc-library/src/Presonus/UC/ParamRange.cpp')]
sources.append((here / 'Replay.cpp').relative_to(root))
executable = scratch / 'replay'
common = ['/usr/bin/c++', '-std=gnu++20', '-O2', '-DNDEBUG=1',
          '-DPRESONUS_HAS_UPSTREAM_CORE=1', '-DCORE_USE_OPENSSL=1',
          '-pthread', '-Ulinux', '-Iuc-library/include',
          '-isystem', 'third_party/ccl-framework']
core_source = Path('third_party/ccl-framework/core/public/corestringbuffer.h')

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
    link = run([*common, *objects, '-o', executable])
    report = {'cwd': str(root), 'compile': commands, 'link': link,
              'executable': str(executable), 'executable_sha256': digest(executable),
              'providers': [{'path': str(core_source), 'sha256': digest(root / core_source),
                             'type': 'instantiated header templates'}]}
    (scratch / 'build.json').write_text(json.dumps(report, indent=2) + '\n')

def verify_symbols():
    obj = scratch / 'ParamRange.o'
    output = subprocess.check_output(['nm', '--defined-only', obj], text=True)
    line = next(line for line in output.splitlines() if line.split()[-1] == symbol)
    assert line.split()[1] == 'T'
    print(line)
    replay_symbols = subprocess.check_output(['nm', '-u', scratch / 'Replay.o'], text=True)
    assert any(line.split()[-1] == symbol for line in replay_symbols.splitlines()), replay_symbols

def replay(exe, fixtures):
    native = json.loads(fixtures.read_text())['observations']
    count = 0
    for binding in native:
        for case in binding['cases']:
            provider_calls = [event for event in case['constructor_calls']
                              if event[0] == 'cstring64_c1']
            assert all(event[2] == 0 for event in provider_calls)
            expected = [*case['scalar_values'], len(provider_calls)]
            actual = subprocess.check_output([exe, str(case['poison'])], text=True)
            assert list(map(int, actual.split())) == expected, (case, actual)
            count += 1
    print(f'Portable constructor replay: {count} native comparisons')

if sys.argv[1] == 'compile':
    compile_replay()
elif sys.argv[1] == 'symbols':
    verify_symbols()
elif sys.argv[1] == 'replay':
    replay(Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else executable,
           Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else fixture)
else:
    raise SystemExit('expected compile, symbols or replay')
