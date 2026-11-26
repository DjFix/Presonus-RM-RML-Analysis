"""Format, compile, seal and replay local Mackie model reconstruction."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
import native

ROOT = Path(__file__).resolve().parents[4]
BASE = Path(__file__).resolve().parent.relative_to(ROOT)
PYTHON = 'uc-library/.venv/bin/python'
FORMAT = 'uc-library/.venv/bin/clang-format'
SRC = 'uc-library/src/Presonus/'
INC = 'uc-library/include/presonus/'
HEADERS = [INC + name + '.hpp' for name in
           ('MackieControlModel', 'IFaderPanel', 'MackieControlComponent')]
SOURCES = [SRC + name + '.cpp' for name in
           ('MackieControlModel', 'MackieControlModelMappings',
            'MackieControlComponent', 'IFaderPanel')]
CCL = 'third_party/ccl-framework'
CCL_FILES = [CCL + '/core/' + name for name in
             ('portable/corecomponent.h', 'portable/corecomponent.cpp',
              'portable/coreparams.h', 'portable/coreparams.cpp',
              'portable/coreparaminfo.h', 'public/corestringbuffer.h',
              'public/corestringtraits.h', 'public/corevector.h')]
DRIVER = str(BASE / 'Replay.cpp')
FLAGS = ['-std=c++20', '-fno-rtti', '-Wno-multichar', '-UNDEBUG',
         '-Iuc-library/include', '-I' + CCL]
LIMITS = [
    'Original return declarations are absent from ordinary mangling; unused return registers do not establish void. Portable declarations are provisional.',
    'Initialized local receiver only. No parser, incoming device data, connection, transport beyond a native null-sink guard, hardware, ARM layout or ABI claim.',
    'Portable IFaderPanel LocalUpdates is an optional source-port capability. Tracing subclass delegates all local panel calls to production MackieControlComponent and checks real pinned CCL readback.',
    'Native original target and listed app/helper code execute in Unicorn. Boundary vtable targets are traced and verified against the ELF; their CCL behavior is supplied by the pinned portable provider. Native display Core constructor is represented by source-defined zero initialization; libc strlen/strncat and qsort are emulated, with actual ARM comparator execution.',
]
RESET_CORRECTION = {
    'observation': 'Native reset calls onMessageFaderValue, then dispatches through the model vtable at +0x1c to touchFader. There is no updateTextDisplay call in this function.',
    'model_vtable_address_point': '0x1f06e8',
    'model_touch_slot_word_address': '0x1f0704',
    'model_touch_target': '0xc0624',
    'fader_helper': '0xc0398',
    'concrete_panel_vtable_address_point': '0x1eaaf4',
    'panel_fader_slot': '0x10',
    'panel_fader_thunk': '0xbf8b8',
    'panel_text_slot_excluded': '0x1c',
    'panel_text_thunk_excluded': '0xbf824',
}


def sha(path):
    return native.digest(Path(path).read_bytes())


def run(argv, **kwargs):
    argv = list(map(str, argv))
    print(json.dumps(argv), flush=True)
    proc = subprocess.run(argv, text=True, capture_output=True, check=False, **kwargs)
    if proc.returncode:
        print(proc.stdout, proc.stderr, file=sys.stderr)
        proc.check_returncode()
    return proc.stdout


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n')


def sdk():
    suffix = 'temp/core-upstream/root-integration-01/upstream-core/sdk/lib'
    for checkout in (ROOT, *ROOT.parents):
        candidate = checkout / suffix
        if (candidate / 'libcorelib.a').is_file():
            return candidate
    raise FileNotFoundError(suffix)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('kind', choices=native.SUFFIX)
    parser.add_argument('mode', choices=('format', 'compile', 'symbols', 'fixtures', 'native', 'replay', 'seal'))
    parser.add_argument('--exe', type=Path)
    parser.add_argument('--fixture', type=Path)
    args = parser.parse_args()
    os.chdir(ROOT)
    task = native.PREFIX + native.SUFFIX[args.kind]
    packet = native.packet(args.kind)
    manifest = json.loads(packet.read_text())
    target = native.select(manifest)
    work = Path('temp/recovery-work') / task
    work.mkdir(parents=True, exist_ok=True)
    executable = args.exe or work / 'replay'
    obj = work / 'MackieControlModel.o'
    fmt = [FORMAT, '--style=file', '--fallback-style=LLVM', '--dry-run',
           '--Werror', *HEADERS, SOURCES[0], DRIVER]
    fixture = args.fixture or Path('uc-library/tests/recovery') / task / 'fixtures.json'
    modes = ['format', 'compile', 'symbols', 'native', 'replay']
    archive = ['libcorelib.a', 'libpresonus_core_allocator.a']
    compile_object = ['/usr/bin/c++', *FLAGS, '-c', SOURCES[0], '-o', obj]
    symbol_cmd = ['/usr/bin/nm', '--defined-only', obj]
    if args.mode == 'format':
        run(fmt)
        return
    if args.mode == 'compile':
        archives = [sdk() / name for name in archive]
        run(compile_object)
        run(['/usr/bin/c++', *FLAGS, DRIVER, obj, *SOURCES[1:], *archives,
             '-lz', '-lpthread', '-ldl', '-o', executable])
        return
    if args.mode == 'symbols':
        results = {line.split()[-1] for line in run(symbol_cmd).splitlines() if line.split()}
        assert target['mangled'] in results
        print(target['mangled'])
        return
    if args.mode == 'fixtures':
        write_json(fixture, native.make(args.kind))
        return
    data = json.loads(fixture.read_text())
    if args.mode == 'native':
        assert native.make(args.kind) == data
        print(len(data['cases']), 'fresh native cases')
        return

    argv = [PYTHON, str(BASE / 'check.py'), args.kind]
    checks = [dict(kind=mode, argv=[*argv, mode], timeout_seconds=120) for mode in modes]
    if args.mode == 'replay':
        for case in data['cases']:
            output = run([str(executable.resolve())], input=case['input'])
            observed = [line.rstrip() for line in output.splitlines()]
            assert observed == case['expected'], (case['input'], observed, case['expected'])
        print(len(data['cases']), 'native-to-portable replay cases')
        return

    logs = work / 'seal'
    logs.mkdir(exist_ok=True)
    receipts = []
    for check in checks:
        log = logs / (check['kind'] + '.log')
        output = run(check['argv'])
        log.write_text(output)
        receipts.append(dict(**check, returncode=0, log=str(log), log_sha256=sha(log)))
    source_hashes = {p: sha(p) for p in [*HEADERS, *SOURCES]}
    provider_hashes = {p: sha(p) for p in CCL_FILES}
    provider_hashes[SOURCES[2]] = source_hashes[SOURCES[2]]
    provider_paths = set(manifest['task']['review']['required_provider_paths'])
    assert provider_paths <= provider_hashes.keys()
    for provider in manifest['task']['review']['providers']:
        assert provider['sha256'] == provider_hashes[provider['path']]
    declared = dict(original_elf_sha256=target['elf'], mangled=target['mangled'],
                    sources={str(Path(k).relative_to('uc-library')): v for k, v in source_hashes.items()},
                    repository_sources=provider_hashes, domain=data['scope'],
                    cpp_compiled=True, mangling_namespace_checked=True, portable_ready=False,
                    declaration_uncertainties=LIMITS[:1])
    files = {
        **{p: 'source' for p in source_hashes}, **{p: 'provider' for p in CCL_FILES},
        DRIVER: 'test', str(fixture): 'fixture',
        str(BASE / 'native.py'): 'oracle', str(BASE / 'check.py'): 'replay',
        str(packet): 'packet',
    }
    for evidence in manifest['task']['review']['evidence']:
        assert sha(evidence['path']) == evidence['sha256']
        files[evidence['path']] = 'evidence'
    artifacts = [dict(path=p, sha256=sha(p), kind=k) for p,k in files.items()]
    proof = dict(version=1, task_id=task, original_elf_sha256=target['elf'],
                 functions=[declared], source_sha256=source_hashes, provider_sources=provider_hashes,
                 active_source=True, compiled_mangled_names_matched=True, arm_differential_passed=True,
                 formatter_version=run([FORMAT, '--version']).strip(),
                 compiler_version=run(['/usr/bin/c++', '--version']).splitlines()[0],
                 unicorn_version=__import__('unicorn').__version__,
                 provider_commit=run(['/usr/bin/git', '-C', CCL, 'rev-parse', 'HEAD']).strip(),
                 provider_archives={name: sha(sdk()/name) for name in archive},
                 native_ranges=[data['target'], *data['supporting_ranges']],
                 executable_sha256=sha(executable), compiled_object_sha256=sha(obj),
                 native_cases=len(data['cases']), portable_cases=len(data['cases']),
                 validation_domain=data['scope'], limitations=LIMITS, checks=receipts,
                 producer_inputs={a['path']: a['sha256'] for a in artifacts},
                 proposed_readiness=dict(canonical_binding_pending=True, ready=[], pending=[declared]))
    if args.kind == 'reset':
        proof['packet_review_correction'] = RESET_CORRECTION
    output = Path('uc-library/candidates') / task
    proof_path = output / 'worker-proof.json'
    write_json(proof_path, proof)
    artifacts.append(dict(kind='proof', path=str(proof_path), sha256=sha(proof_path)))
    original = {key: target[key] for key in ('address', 'size', 'section', 'firmware', 'role', 'mangled')}
    original['elf_sha256'] = target['elf']
    handoff = dict(version=1, task_id=task, namespace=manifest['task']['namespace'],
                   packet_manifest=str(packet), originals=[original], artifacts=artifacts,
                   checks=checks, validation_domain=data['scope'], limitations=LIMITS,
                   build_integration=dict(production_partition='CS18 (existing objects; no new production CPP)',
                       public_headers=HEADERS, test_source=DRIVER, test_target='cs18_mackie_local_model_replay',
                       link_dependencies=['presonus_cs18_components', 'presonus_core'],
                       ctest_argv=[*argv, 'replay', '--exe', '$<TARGET_FILE:cs18_mackie_local_model_replay>',
                                   '--fixture', str(fixture)]))
    write_json(output/'HANDOFF.json', handoff)


if __name__ == '__main__':
    main()
