"""Compile, check symbols and compare against the original lifetime observations."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess

import elftools
import unicorn
from native import ADD, COMPONENT, REMOVE, PACKET, run

TEST = Path(__file__).resolve().parent.relative_to(Path.cwd())
SOURCE = Path('uc-library/src/Presonus/Mixer/GEQLinkHandler.cpp')
HEADER = Path('uc-library/include/presonus/mixer/GEQLinkHandler.hpp')
DRIVER = TEST / 'Replay.cpp'
FIXTURE = TEST / 'fixtures.json'
CHECK_FORMAT = ['uc-library/.venv/bin/clang-format', '--style=file',
                '--fallback-style=LLVM', '--dry-run', '--Werror', HEADER, SOURCE, DRIVER]
FLAGS = ['g++', '-std=c++17', '-O2', '-Wno-multichar', '-Iuc-library/include',
         '-Ithird_party/ccl-framework', '-ffunction-sections', '-fdata-sections']
WRAPS = (COMPONENT, ADD, REMOVE)
DOMAIN = ('ARM normal constructor paths on two receivers with null, aliased, '
          'numeric and string parameter identities; callback messages and raw float '
          'words, ordered get/set/remove targets and edit flag. Host uses real pinned '
          'CCL component construction, observer registration and detach, parameter '
          'setValue, clamping and notifications against an independent CCL baseline.')
LIMITS = ['The host C1/C2 aliases share code while original ARM entries have separate ranges.',
          'Native foreign Component and Parameter calls terminate at named boundaries. '
          'Host forwarding wraps the real pinned providers. Native abstract virtual '
          'parameter calls use an isolated CPU probe and exact fixture float words.',
          'Limits include valid nonnull callback parameters where required, stable '
          'aliased values, and no original binary layout, exception or hardware claims.',
          'Ordinary callback return declaration remains unresolved. The CCL override '
          'uses void. The pre-existing destructor stays default; borrowed live sources '
          'must be detached before handler teardown. No destructor credit.']
PROTECTED_HEADERS = {'uc-library/include/presonus/mixer/MixerComponentBase.hpp',
                     'uc-library/include/presonus/mixer/OutputComponent.hpp'}


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('format', 'compile', 'symbols', 'replay'))
    parser.add_argument('--object', type=Path)
    parser.add_argument('--exe', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--integration', type=Path)
    parser.add_argument('--archive', action='append', type=Path, default=[])
    args = parser.parse_args()
    commands = []

    def invoke(argv):
        argv = list(map(str, argv))
        start = datetime.now(timezone.utc)
        result = subprocess.run(argv, text=True, capture_output=True)
        commands.append(dict(argv=argv, exit_code=result.returncode,
                             start_utc=start.isoformat(),
                             end_utc=datetime.now(timezone.utc).isoformat(),
                             stdout=result.stdout, stderr=result.stderr))
        if result.returncode:
            print(result.stderr, end='')
        result.check_returncode()
        return result.stdout

    if args.mode == 'format':
        invoke(CHECK_FORMAT)
        return
    if args.mode == 'compile':
        args.object.parent.mkdir(parents=True, exist_ok=True)
        objects = [args.object, args.object.with_name('Replay.o')]
        for source, obj in zip((SOURCE, DRIVER), objects):
            invoke([*FLAGS, *(['-fno-rtti', '-UNDEBUG'] if source == DRIVER else []),
                    '-MMD', '-c', source, '-o', obj])
            inputs = obj.with_suffix('.d').read_text().replace(chr(92) + '\n', ' ').split()[1:]
            assert PROTECTED_HEADERS.isdisjoint(inputs)
        archive_hashes = {str(path): digest(path) for path in args.archive}
        invoke(['g++', '-Wl,--gc-sections', *objects, *args.archive,
                *['-Wl,--wrap=' + name for name in WRAPS], '-pthread', '-o', args.exe])
        assert archive_hashes == {str(path): digest(path) for path in args.archive}
        args.out.write_text(json.dumps(dict(cwd=str(Path.cwd()), commands=commands,
                                           archives=archive_hashes,
                                           objects={str(obj): digest(obj) for obj in objects},
                                           depfiles={str(obj.with_suffix('.d')): digest(obj.with_suffix('.d'))
                                                     for obj in objects}), indent=2) + '\n')
        return

    original, = [item['original'] for item in json.loads(PACKET.read_text())['originals']]
    mangled = original['mangled']
    ctor = mangled.endswith('ES5_')
    nm = invoke(['nm', '--defined-only', args.object])
    values = {line.split()[-1]: line.split()[0] for line in nm.splitlines() if line.split()}
    assert mangled in values
    if ctor:
        c1 = mangled.replace('C2EPN', 'C1EPN')
        c2 = mangled.replace('C1EPN', 'C2EPN')
        assert values[c1] == values[c2]
    if args.mode == 'symbols':
        return
    fixture = json.loads(FIXTURE.read_text())
    native_start = datetime.now(timezone.utc)
    assert run() == fixture
    native_end = datetime.now(timezone.utc)
    mode = 'C1' if 'C1EPN' in mangled else 'C2' if ctor else 'callback'
    for case in fixture['cases']:
        inputs = case['input']
        argv = [args.exe.resolve(), mode, inputs['destination']]
        if ctor:
            argv += [inputs['source']]
        else:
            argv += [inputs['passed'], inputs['msg'], inputs['bits']]
        lines = invoke(argv).splitlines()
        assert lines == [' '.join(str(word) for word in call if word != '')
                         for call in case['calls']], (inputs, lines, case['calls'])
    count = len(fixture['cases'])
    invoke(CHECK_FORMAT)
    sources = {SOURCE, HEADER, DRIVER, FIXTURE, TEST / 'check.py', TEST / 'native.py'}
    core = set()
    for unit in (SOURCE, DRIVER):
        raw = invoke([*FLAGS, '-MM', unit]).replace(chr(92) + '\n', ' ')
        sources.update(Path(path) for path in raw.split()[1:] if path.startswith('uc-library/'))
        core.update(Path(path) for path in
                ('third_party/ccl-framework/core/portable/corecomponent.cpp',
                 'third_party/ccl-framework/core/portable/coreparams.cpp'))
    assert PROTECTED_HEADERS.isdisjoint(map(str, sources))
    entry = dict(original_elf_sha256=original['elf'], mangled=mangled, domain=DOMAIN,
                 sources={str(path.relative_to('uc-library')): digest(path) for path in sorted(sources)},
                 repository_sources={str(path): digest(path) for path in sorted(core)},
                 cpp_compiled=True, mangling_namespace_checked=True, portable_ready=ctor)
    if not ctor:
        entry['declaration_uncertainties'] = [LIMITS[-1]]
    ranges = {key: value for key, value in fixture.items() if key != 'cases'}
    proof = dict(version=1, task_id=TEST.name, proposed_readiness=dict(
                     ready=[entry] if ctor else [], pending=[] if ctor else [entry]),
                 functions=[entry], cpp_differential_passed=True, compiled_mangled_names_matched=True,
                 cpp_compiled=True, portable_ready=ctor, original_arm_abi_verified=False,
                 hardware_verified=False, validation_domain=DOMAIN, limitations=LIMITS,
                 original_ranges=ranges,
                 native_execution=dict(cases=count, executor='Unicorn ARM',
                                       start_utc=native_start.isoformat(), end_utc=native_end.isoformat()),
                 native_fixture_sha256=digest(FIXTURE), portable_execution=dict(cases=count),
                 executable=dict(path=str(args.exe), sha256=digest(args.exe)),
                 object=dict(path=str(args.object), sha256=digest(args.object)),
                 tools=dict(compiler=invoke(['g++', '--version']).splitlines()[0],
                            formatter=invoke([CHECK_FORMAT[0], '--version']).strip(),
                            unicorn=unicorn.__version__, pyelftools=elftools.__version__),
                 commands=commands)
    if args.integration:
        proof['integration'] = dict(path=str(args.integration), sha256=digest(args.integration))
    args.out.write_text(json.dumps(proof, indent=2) + '\n')
    print(f'{TEST.name}: {count} native and portable observations passed')


if __name__ == '__main__':
    main()
