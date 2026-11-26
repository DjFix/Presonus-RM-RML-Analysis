"""Compile and compare ChannelNameFormatter against sealed ARM observations."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from native import PACKET, ROOT, TASK, observe

TEST = Path('uc-library/tests/recovery') / TASK
CANDIDATE = Path('uc-library/candidates') / TASK
SOURCE = Path('uc-library/src/Presonus/Mixer/PreDelayFormatterT9.cpp')
HEADER = Path('uc-library/include/presonus/mixer/PreDelayFormatterT9.hpp')
REPLAY = TEST / 'Replay.cpp'
FIXTURE = TEST / 'fixtures.json'
SCRATCH = Path('temp/recovery-work/sqlite14-formatter') / TASK
OBJECT = SCRATCH / 'PreDelayFormatterT9.o'
DEPFILE = SCRATCH / 'Formatter.d'
EXE = SCRATCH / 'Replay'
PYTHON = 'uc-library/.venv/bin/python'
FORMATTER = 'uc-library/.venv/bin/clang-format'
FORMAT = [FORMATTER, '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror',
          *map(str, (SOURCE, HEADER, REPLAY))]
SDK = Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk')
CXX = ['/usr/bin/c++', '-std=c++17', '-O0', '-ffunction-sections', '-fdata-sections',
       '-Ulinux', '-fno-rtti', '-fno-sized-deallocation', '-DPRESONUS_HAS_UPSTREAM_CORE=1',
       '-DCORE_USE_OPENSSL=1', '-DNDEBUG=1', '-Iuc-library/include',
       '-isystem', 'third_party/ccl-framework']
COMPILE = [*CXX, '-MD', '-MF', str(DEPFILE), '-c', str(SOURCE), '-o', str(OBJECT)]
BUILD = Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01')
ARCHIVES = [SDK / 'lib/libcorelib.a', SDK / 'lib/libpresonus_core_allocator.a']
CASE = '-DFORMATTER_LIFECYCLE_TEST=1'
WRAP = ['-Wl,--wrap=_ZdlPv']
LINK = [*CXX, '-MD', '-MF', str(SCRATCH / 'Replay.d'),
        '-Wl,--gc-sections', CASE, *WRAP, str(REPLAY), 'uc-library/src/Presonus/Mixer/PreDelayFormatter.cpp', str(OBJECT), *map(str, ARCHIVES),
        '-o', str(EXE)]
DOMAIN = 'Three initialized receivers per exact ELF range; D1 resets receiver vptr to genuine Core::Formatter with no deletion; D0 resets vptr and calls verified unsized operator delete once with same receiver. Emulator releases mapped allocation at actual call boundary. Portable exact emitted symbols use independent tagged setup with the actual RTTI-proven parent, genuine pinned Core provider teardown through RTTI-proven original parent and actual wrapped global unsized deallocation.'
LIMITS = ['Portable source-port only; original source declaration, construction and ARM layout unresolved; original parent now independently established by RTTI.', 'No new print/scan or original constructor recovered. Inherits canonical real parent print and current scan adaptation; original PreDelay scan remains outside teardown scope. Core native code is not executed.', 'O0 local observation retains provider vptr stores; optimized code may elide lifetime-ended stores. No ARM ABI, hardware, or full formatter readiness claim.']
EXTENSION = Path('temp/recovery-work/formatter-initializer-extension-sol61/CONTEXT.json')
SUPPLEMENT = Path('temp/recovery-work/sqlite-issued/packet-sol61/SUPPLEMENT-actual-parents01/SUPPLEMENT.json')
DEPENDENCIES = [
    'uc-library/include/presonus/mixer/PreDelayFormatter.hpp',
    'uc-library/src/Presonus/Mixer/PreDelayFormatter.cpp',
    'third_party/ccl-framework/core/public/coreformatter.h',
    'third_party/ccl-framework/core/public/coreformatter.cpp',
    'third_party/ccl-framework/core/public/corestringbuffer.h',
    'third_party/ccl-framework/core/public/corestringtraits.h',
]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def symbols(path, targets):
    argv = ['/usr/bin/nm', '--defined-only', str(path)]
    output = subprocess.check_output(argv, text=True).splitlines()
    names = {row['original']['mangled'] for row in targets}
    matched = [line for line in output if line.split()[-1:] and line.split()[-1] in names]
    assert len(matched) == len(names)
    return {'argv': argv, 'matched': matched, 'all_defined': output, 'emitted_destructor_variants': [line for line in output if line.split()[-1].endswith(('D0Ev', 'D1Ev', 'D2Ev'))]}


def replay(fixture, exe, optimized=False):
    observed = subprocess.check_output([str(exe)], text=True).splitlines()
    for target in fixture['targets']:
        expected = [str(case['output']) for case in target['cases']]
        if optimized: expected = [' '.join(value.split()[:2]) for value in expected]
        assert observed == expected, (observed, expected)
    print(f'{TASK}: {len(observed)} portable observations matched exact assigned native ranges')
    return observed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('format', 'compile', 'symbols', 'capture',
                                          'native', 'replay', 'optimized', 'seal'))
    parser.add_argument('--optimized', action='store_true')
    parser.add_argument('--exe', type=Path, default=EXE)
    parser.add_argument('--object', type=Path, default=OBJECT)
    parser.add_argument('--fixtures', type=Path, default=FIXTURE)
    args = parser.parse_args()
    if args.mode == 'format':
        subprocess.run(FORMAT, check=True)
        return
    if args.mode == 'compile':
        SCRATCH.mkdir(parents=True, exist_ok=True)
        print(json.dumps(COMPILE), flush=True)
        subprocess.run(COMPILE, check=True)
        link_hashes = {str(path): sha(path) for path in (OBJECT, *ARCHIVES)}
        print(json.dumps(LINK), flush=True)
        subprocess.run(LINK, check=True)
        assert link_hashes == {str(path): sha(path) for path in (OBJECT, *ARCHIVES)}
        dump(SCRATCH / 'link-inputs.json', link_hashes)
        return
    if args.mode == 'capture':
        dump(args.fixtures, observe())
        return
    fixture = json.loads(args.fixtures.read_text())
    if args.mode == 'native':
        assert fixture == observe()
        print(f'{TASK}: {sum(len(target["cases"]) for target in fixture["targets"])} native executions reproduced')
        return
    if args.mode == 'optimized':
        optimized_object = SCRATCH / 'optimized.o'
        optimized_exe = SCRATCH / 'optimized-replay'
        compile_argv = [x.replace('-O0', '-O2') for x in COMPILE]
        compile_argv[-1] = str(optimized_object)
        link_argv = [x.replace('-O0', '-O2') for x in LINK]
        link_argv = [str(optimized_object) if x == str(OBJECT) else x for x in link_argv]
        link_argv[-1] = str(optimized_exe)
        link_argv.insert(1, '-DFORMATTER_OPTIMIZED=1')
        subprocess.run(compile_argv, check=True)
        subprocess.run(link_argv, check=True)
        observations = replay(fixture, optimized_exe, True)
        dump(SCRATCH / 'optimized.json', dict(compile_argv=compile_argv, link_argv=link_argv, observations=observations, object_sha256=sha(optimized_object), exe_sha256=sha(optimized_exe), domain='O2 normal production teardown: same receiver and unsized deletion count only; physical dead-object vptr writes excluded'))
        return
    if args.mode == 'replay':
        replay(fixture, args.exe, args.optimized)
        return
    matched = symbols(args.object, fixture['targets'])
    print(json.dumps(matched))
    if args.mode == 'symbols':
        return
    observations = replay(fixture, args.exe)
    assert fixture == observe()
    subprocess.run(FORMAT, check=True)
    originals = [target['original'] for target in fixture['targets']]
    dependencies = {path: sha(path) for path in DEPENDENCIES}
    dependencies.update({path: sha(path) for path in json.loads(SUPPLEMENT.read_text())['files']})
    sources = {str(path.relative_to('uc-library')): sha(path) for path in (SOURCE, HEADER)}
    pending = [dict(original_elf_sha256=original['elf_sha256'], mangled=original['mangled'],
                    cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
                    sources=sources, repository_sources=dependencies,
                    validation_domain=DOMAIN, declaration_uncertainties=LIMITS)
               for original in originals]
    proof = CANDIDATE / 'worker-proof.json'
    sealed_log = SCRATCH / 'final-combined-validation-frozen01.log'
    dump(proof, dict(task_id=TASK, originals=originals, native=fixture,
                     active_extension=dict(path=str(EXTENSION), sha256=sha(EXTENSION)),
                     immutable_validation_log=dict(path=str(sealed_log), sha256=sha(sealed_log)),
                     fixture_sha256=sha(args.fixtures), portable=observations,
                     object_sha256=sha(args.object), exe_sha256=sha(args.exe),
                     depfiles={str(path): sha(path) for path in (DEPFILE, SCRATCH / 'Replay.d')},
                     compile_argv=COMPILE, link_argv=LINK,
                     link_input_hashes=json.loads((SCRATCH / 'link-inputs.json').read_text()),
                     optimized=json.loads((SCRATCH / 'optimized.json').read_text()),
                     producer_inputs={str(path): sha(path) for path in
                                      (TEST / 'check.py', TEST / 'native.py', REPLAY)},
                     compiled_symbol=matched, compiled_mangled_names_matched=True,
                     mangled_names=sorted({original['mangled'] for original in originals}),
                     cpp_differential_passed=True, format_check_passed=True,
                     portable_ready=False, format_argv=FORMAT,
                     formatted_files={str(path.relative_to('uc-library')): sha(path)
                                      for path in (SOURCE, HEADER, REPLAY)},
                     compiler_version=subprocess.check_output(['/usr/bin/c++', '--version'], text=True).splitlines()[0],
                     provider_boundary='Core::Formatter inline constructor/destructor/scan from pinned source header; no native Core execution',
                     formatter_version=subprocess.check_output([FORMATTER, '--version'],
                                                               text=True).strip(),
                     proposed_readiness={'ready': [], 'pending': pending}))
    artifacts = {SOURCE: 'source', HEADER: 'source', args.fixtures: 'fixture', REPLAY: 'test',
                 TEST / 'check.py': 'replay', TEST / 'native.py': 'producer',
                 proof: 'proof', sealed_log: 'proof', PACKET: 'packet', SUPPLEMENT: 'dependency', EXTENSION: 'dependency',
                 **{path: 'dependency' for path in dependencies}}
    argv = [PYTHON, '-B', str(TEST / 'check.py')]
    dump(CANDIDATE / 'HANDOFF.json', dict(version=1, task_id=TASK,
         namespace='Presonus::Mixer::PreDelayFormatterT9', packet_manifest=str(PACKET), originals=originals,
         artifacts=[dict(path=str(path), kind=kind, sha256=sha(path))
                    for path, kind in artifacts.items()],
         checks=[dict(kind=kind, argv=[*argv, kind], timeout_seconds=120)
                 for kind in ('format', 'compile', 'symbols', 'native', 'replay')] + [dict(kind='replay', argv=[*argv, 'optimized'], timeout_seconds=120)],
         validation_domain=DOMAIN, limitations=LIMITS,
         build_integration=dict(partition='common (new PreDelayFormatterT9.cpp)',
                                public_headers=[str(HEADER)], test_target=TASK,
                                link_dependencies=['presonus_uc'],
                                compile_definitions=['FORMATTER_OPTIMIZED=1'], compile_options=['-fno-rtti', '-fno-sized-deallocation'], link_options=WRAP,
                                ctest_argv=[*argv, 'replay', '--exe', f'$<TARGET_FILE:{TASK}>',
                                            '--fixtures', str(args.fixtures), '--optimized'])))


if __name__ == '__main__':
    main()
