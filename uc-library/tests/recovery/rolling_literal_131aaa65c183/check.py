"""Build and compare the portable registrar getter against fresh ARM observations."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

from native import digest, observations

TEST = Path(__file__).resolve().parent.relative_to(Path.cwd())
TASK = TEST.name
WORK = Path('temp/recovery-work/rolling-roguepanelregistrar') / TASK
HEADER = Path('uc-library/include/presonus/panel/RoguePanelRegistrar.hpp')
CPP = Path('uc-library/src/Presonus/Panel/RoguePanelRegistrar.cpp')
REPLAY = TEST / 'Replay.cpp'
FIXTURE = TEST / 'fixtures.json'
FORMAT = ['uc-library/.venv/bin/clang-format', '--style=file', '--fallback-style=LLVM']
DOMAIN = ('Three ARM calls per getter on different synthetic receiver addresses. Verify '
          'the full ELF range and read-only literal mapping, that each invocation returns '
          'the exact literal pointer word, and that the only memory accesses are to the '
          'literal pool and stack frame. Compare NUL-terminated text, non-null and stable '
          'pointer identity across calls and constructed portable receivers, readability '
          'after receiver scope exit, and stable tag lookup and parameter group sizes.')
UNCERTAINTIES = [
    'The portable declaration is a non-const member returning const char*. Original C++ '
    'return type, character const qualification and dispatch declaration remain unresolved.',
    'Synthetic ARM receiver memory and portable receiver lifecycle provide no original '
    'layout, hardware or binary interoperability evidence.',
]
COMMANDS = []


def sha(path):
    return digest(Path(path).read_bytes())


def utc():
    return datetime.now(timezone.utc).isoformat()


def run(*argv):
    argv = list(map(str, argv))
    started = utc()
    result = subprocess.run(argv, capture_output=True, text=True, check=False)
    COMMANDS.append(dict(argv=argv, start_utc=started, end_utc=utc(),
                         returncode=result.returncode, stdout=result.stdout, stderr=result.stderr))
    result.check_returncode()
    return result.stdout


def formatting():
    run(*FORMAT, '--dry-run', '--Werror', HEADER, CPP, REPLAY)
    return run(FORMAT[0], '--version').strip()


def compile_replay(exe, obj):
    exe.parent.mkdir(parents=True, exist_ok=True)
    obj.parent.mkdir(parents=True, exist_ok=True)
    flags = ['/usr/bin/c++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
             '-Iuc-library/include']
    run(*flags, '-c', CPP, '-o', obj)
    run(*flags, REPLAY, obj, '-o', exe)


def symbols(obj, original):
    listing = run('/usr/bin/nm', '--defined-only', obj)
    matches = [line for line in listing.splitlines()
               if line.split() and line.split()[-1] == original['mangled']]
    assert len(matches) == 1, matches
    return matches


def proof(args, original, timing):
    version = formatting()
    matched = symbols(args.object, original)
    cases = original['cases']
    actual = run(args.exe.resolve(), original['text']).splitlines()
    assert actual == [f'case {index}' for index in range(len(cases))], actual
    sources = {str(path.relative_to('uc-library')): sha(path) for path in (HEADER, CPP)}
    row = dict(original_elf_sha256=original['elf_sha256'], mangled=original['mangled'],
               demangled=run('/usr/bin/c++filt', original['mangled']).strip(),
               address=original['address'], size=original['size'], section=original['section'],
               firmware='RM/RML mixer 13731', role='server', cpp_compiled=True,
               mangling_namespace_checked=True, portable_ready=False,
               validation_domain=DOMAIN, declaration_uncertainties=UNCERTAINTIES,
               sources=sources, repository_sources={}, original_function_verified=False,
               hardware_verified=False)
    result = dict(task_id=TASK, worker_session='/root/rolling_next_roguepanelregistrar',
                  timestamp_utc=utc(), native=original, native_timing=timing,
                  native_invocations=len(cases), portable_case_count=len(actual),
                  compiled_symbols=matched, compiled_original_mangled_names_matched=True,
                  mangled_names=[original['mangled']], original_elf_sha256=original['elf_sha256'],
                  formatting=dict(version=version, passed=True, sources=sources),
                  cpp_differential_passed=True, portable_ready=False, sources=sources,
                  validation_domain=DOMAIN, limitations=UNCERTAINTIES,
                  proposed_readiness=dict(ready=[], pending=[row]), commands=COMMANDS,
                  fixture_sha256=sha(args.fixtures), producer_sha256=sha(__file__),
                  native_producer_sha256=sha(TEST / 'native.py'), test_sources={str(REPLAY): sha(REPLAY)},
                  binary_bindings={str(path): sha(path) for path in (args.exe, args.object)})
    if args.integration:
        result['integration'] = dict(path=str(args.integration), sha256=sha(args.integration))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(f'{len(actual)} native ARM observations matched portable replay')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['format', 'compile', 'symbols', 'native', 'proof', 'local-proof'])
    parser.add_argument('--exe', type=Path, default=WORK / 'replay')
    parser.add_argument('--object', type=Path, default=WORK / 'production.o')
    parser.add_argument('--fixtures', type=Path, default=FIXTURE)
    parser.add_argument('--integration', type=Path)
    parser.add_argument('--out', type=Path, default=WORK / 'proof.json')
    args = parser.parse_args()
    if args.mode == 'format':
        print(formatting())
        return
    if args.mode == 'compile':
        compile_replay(args.exe, args.object)
        print(json.dumps(COMMANDS, indent=2))
        return
    fixture = json.loads(args.fixtures.read_text())
    if args.mode == 'symbols':
        print(*symbols(args.object, fixture), sep='\n')
        return
    if args.mode == 'local-proof':
        compile_replay(args.exe, args.object)
    started = utc()
    original = observations()
    assert original == fixture, 'Fresh ARM observations differ from the sealed fixture'
    timing = dict(start_utc=started, end_utc=utc())
    if args.mode == 'native':
        print(json.dumps(dict(timing=timing, native_invocations=len(original['cases']))))
        return
    proof(args, original, timing)


if __name__ == '__main__':
    main()
