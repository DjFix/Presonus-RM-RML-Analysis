"""Fresh native replay and actual separate-role archive closure; no GC fallback."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

R = Path(__file__).resolve().parents[4]
T = Path(__file__).resolve().parent
O = R / 'temp/recovery-work/avb_manager_stream_control/role-successor-01/build'
O.mkdir(parents=True, exist_ok=True)
BUILD = Path('/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01')
AUTHORIZATION = 'temp/recovery-work/avb-role-architecture-extension-sol61/AUTHORIZATION.json'
COMMON = ['uc-library/src/Presonus/AVB/' + n + '.cpp' for n in
          ['AvbManagerStreams', 'AvbManagerTransmit', 'AvbManagerMac']]
ADAPTERS = {'client': 'uc-library/src/Presonus/AVB/DiceManagerTransport.cpp',
            'server': 'uc-library/src/Presonus/AVB/NoaaManagerTransport.cpp'}
READONLY = ['uc-library/src/Presonus/AVB/' + n + '.cpp' for n in
            ['Protocol', 'AvbManagerLookup', 'AvbManagerReceive', 'Streams']]
HEADERS = ['uc-library/include/presonus/avb/' + n + '.hpp' for n in
           ['protocol', 'manager_transport', 'dice_manager_transport', 'noaa_manager_transport']]
OWNED = HEADERS + COMMON + list(ADAPTERS.values()) + [str((T / 'Replay.cpp').relative_to(R))]
SOURCES = COMMON + list(ADAPTERS.values()) + READONLY
FLAGS = ['/usr/bin/c++', '-std=c++17', '-O0', '-Wno-multichar',
         '-Iuc-library/include', '-Ithird_party/ccl-framework']
ROLE_NAMES = {'client': 'cs18', 'server': 'rm'}
COMMANDS = []
ARCHIVE_EXPECTED = {'/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling-c001-20261124/workspaces/sqlite-pan-meter-successor01/temp/recovery-work/avb_manager_stream_control/role-successor-01/build/inputs/libpresonus_cs18_components.a': '198e05e7bff6f997d8aff4442fcebe756d7025cc1a7c71832f4e8973b69634e6', '/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling-c001-20261124/workspaces/sqlite-pan-meter-successor01/temp/recovery-work/avb_manager_stream_control/role-successor-01/build/inputs/libpresonus_rm_components.a': '342886127bf7f11ef5c031b510b6e11f7cb019355b34d082ce9a7a000bec55a0', '/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libcorelib.a': '5a2c8bbb20d8d194ff4f5047118696afa918a046b01739c4257416044e83f5f3', '/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_core_allocator.a': '69892fbcec9a50a140462982073c686a67ca4763dfb5dfa190534d022b78a40d', '/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_png.a': '99514af041c29b5aa782c14718794453b13841f99b7de584db3f3f89bf68ecc1', '/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/root-integration-01/upstream-core/sdk/lib/libpresonus_zlib.a': '9095c54154b7617d8f283d7858ae45218cad1ba92e54e04f983dc0a7151c6c93', '/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling-c001-20261124/workspaces/sqlite-pan-meter-successor01/temp/recovery-work/avb_manager_stream_control/role-successor-01/build/inputs/libpresonus_private_glibc29.a': 'e14acfad9b5246950768780a5bd372e58cc208be6dd290c29a11e9949356ab20'}
SYSTEM_INPUT_EXPECTED = {'/usr/lib/x86_64-linux-gnu/libssl.so': 'a40e7b67489bbd257e432c700ff8f6a1ad796425b5eccecdc2930127fdd86624', '/usr/lib/x86_64-linux-gnu/libcrypto.so': '6866ed711dab8927e1bf82bf1cd30e828bdfc34f3cc1e83b1c9eb01ce6c37d9a', '/home/rs/projects/opencs/ai-line-analysis/temp/core-upstream/external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so': '28b67af5dddb8eef17b77280db249c50344554c82226705733b1912a30c114a5'}
LOCAL_OUTPUT_EXPECTED = {'AvbManagerLookup.cpp.o': 'f81750db9ab0fb35e36f7a5c61fc9de7ff1f4317d7dffb4cd4df9ac406924d07', 'AvbManagerMac.cpp.o': 'c462e2644e41e39744f9f6c4b1faee67ab48f0ae4af18068d2ae95faade41bc4', 'AvbManagerReceive.cpp.o': '0c5556fc812cd66001d47173a54693e7521fd728b8566d68043fe0be02325812', 'AvbManagerStreams.cpp.o': 'aa8dec4cb4b4949771537885985e6f48cd1dd0e43ed01e01a0f295315d4595bc', 'AvbManagerTransmit.cpp.o': '605d88960c91750f620371da39ae8e937a98ad9151c70db868a0e704d96999b5', 'DiceManagerTransport.cpp.o': '09eeec4a718adc791f2331668bc30239a1316b0ce4f47a0e8c954634b1eeadef', 'NoaaManagerTransport.cpp.o': '2da3e312f94b7654ba8b56dda012b0896871c0a041ed89c0ef00ad64422cc486', 'Protocol.cpp.o': 'f078631e27b27e3f26b1c12ff211e3e4dd8375514bf9a5ea6893dc8014ffe899', 'Replay-cs18.o': '8121aab6ed97641d76a06a2be434e4ee132e79fce81a6ee935c7858cc5e28d0b', 'Replay-rm.o': 'c004a865fb016252c2ba22bfea683943a5c31d709709db8c8ad7978d4705f781', 'Streams.cpp.o': 'e1783e9eceeb547685ca3418247123f3d1dbf172981c8da51f02e818d2ee1b72', 'libpresonus_cs18_components.a': 'e316a588132251e5d708dd715e7ecbe769a38ca97198708eaf78623016745623', 'libpresonus_rm_components.a': 'b629088712dfd8eff0caaee6e7cd944f424322c7781bcfcbd9422f83cb7e5bd6', 'provider.so': '8cd494710ee0a68e79af8580165f6af62671a058dfa7e9992ce2f880ece1bb83', 'replay-cs18': 'aeb83e4cd0a9784f6a6a1ba301e615d6c5aaf63d0bebeadda3b54b5cbc9c5c33', 'replay-rm': 'a78f727a794891d6ba24761def247725090002bc73c8a7478f36263ea0965ee8'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(argv, **kwargs):
    argv = list(map(str, argv))
    print(json.dumps(argv), flush=True)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    before = time.monotonic()
    result = subprocess.run(argv, cwd=R, capture_output=True,
                            env={**os.environ, 'TMPDIR': str(O)}, **kwargs)
    COMMANDS.append(dict(argv=argv, started_utc=started,
                         seconds=time.monotonic() - before, returncode=result.returncode))
    if result.returncode:
        print(result.stdout.decode(), result.stderr.decode())
        result.check_returncode()
    return result.stdout.decode()


def obj(source):
    return O / (Path(source).name + '.o')


def role_archive(role):
    return O / ('libpresonus_' + ROLE_NAMES[role] + '_components.a')


def role_executable(role):
    return O / ('replay-' + ROLE_NAMES[role])


def core_archives():
    return [BUILD / 'upstream-core/sdk/lib' / n for n in
            ['libcorelib.a', 'libpresonus_core_allocator.a',
             'libpresonus_png.a', 'libpresonus_zlib.a']] + [
                 O / 'inputs/libpresonus_private_glibc29.a']


def system_libraries():
    return ['/usr/lib/x86_64-linux-gnu/libssl.so',
            '/usr/lib/x86_64-linux-gnu/libcrypto.so',
            str(BUILD.parent / 'external-dev/usr/lib/x86_64-linux-gnu/libdns_sd.so')]


def compile_source(source, target=None, definitions=()):
    target = target or obj(source)
    run([*FLAGS, *['-D' + d for d in definitions], '-MMD', '-MF', str(target) + '.d',
         '-c', source, '-o', target])


def compile_all():
    for source in SOURCES:
        compile_source(source)
    input_manifest = json.loads((O / 'ARCHIVE_INPUTS.json').read_text())
    for role, role_name in ROLE_NAMES.items():
        baseline = O / 'inputs' / ('libpresonus_' + role_name + '_components.a')
        binding = next(x for x in input_manifest['archives']
                       if Path(x['frozen_path']).name == baseline.name)
        assert sha(baseline) == binding['sha256']
        members = run(['/usr/bin/ar', 't', baseline]).splitlines()
        for source in READONLY:
            assert members.count(obj(source).name) == 1, ('ambiguous replacement', source)
        for source in COMMON + list(ADAPTERS.values()):
            assert obj(source).name not in members, ('unclean role baseline', source)
        archive = role_archive(role)
        shutil.copyfile(baseline, archive)
        # Exactly common units plus this role's exclusive concrete adapter.
        run(['/usr/bin/ar', 'rcs', archive,
             *[obj(s) for s in COMMON + READONLY + [ADAPTERS[role]]]])
        replay_obj = O / ('Replay-' + role_name + '.o')
        compile_source(str(T / 'Replay.cpp'), replay_obj,
                       ['AVB_REPLAY_CS18' if role == 'client' else 'AVB_REPLAY_RM'])
        argv = ['/usr/bin/c++', replay_obj, '-Wl,--wrap=_ZdlPv', '-Wl,--wrap=_ZdlPvm',
                '-Wl,-Map,' + str(O / ('link-' + role_name + '.map')),
                '-Wl,-rpath,' + str(BUILD.parent / 'external-dev/usr/lib/x86_64-linux-gnu'),
                archive, *core_archives()[:4], *system_libraries(),
                '-ldl', core_archives()[4], '-lm', '-lpthread', '-o', role_executable(role)]
        assert not any('gc-sections' in str(x) or 'libpresonus_uc.a' in str(x) for x in argv)
        assert not any(('libpresonus_' + ('rm' if role == 'client' else 'cs18') + '_components.a')
                       in str(x) for x in argv)
        run(argv)
    run([*FLAGS, '-DAVB_PROVIDER_BRIDGE', '-fPIC', '-shared', T / 'Replay.cpp',
         '-o', O / 'provider.so'])


def provider_family(symbols, role):
    patterns = ([r'Presonus4DICE13SysexReceiver', r'Presonus4DICE9Dice3Uart',
                 r'Presonus4DICE11SysexPacketC[12]EPKhh', r'DiceManagerTransport']
                if role == 'client' else
                [r'Presonus4NOAA13SysexReceiver', r'Presonus4NOAA8TCardSPI',
                 r'Presonus4NOAA11SysexPacketC[12]EPKhh', r'NoaaManagerTransport'])
    return sorted(set(line.split()[-1] for line in symbols.splitlines()
                      if line.split() and any(re.search(p, line) for p in patterns)))


def audit_roles(executables, archives, canonical=False):
    audits = {'common_unit_imports': {}}
    if not canonical:
        for source in COMMON + READONLY:
            undefined = run(['nm', '-u', obj(source)])
            assert not provider_family(undefined, 'client'), ('common imports DICE transport', source)
            assert not provider_family(undefined, 'server'), ('common imports NOAA transport', source)
            audits['common_unit_imports'][source] = dict(object_sha256=sha(obj(source)), undefined_symbols=undefined.splitlines(), forbidden_transport_imports=[])
    for role in executables:
        other = 'server' if role == 'client' else 'client'
        archive = archives[role]
        members = run(['/usr/bin/ar', 't', archive]).splitlines()
        assert members.count(obj(ADAPTERS[role]).name) == 1
        assert obj(ADAPTERS[other]).name not in members
        for source in COMMON:
            assert members.count(obj(source).name) == 1
        archive_symbols = run(['nm', '-g', '--defined-only', archive])
        assert provider_family(archive_symbols, role), ('missing own real provider', role)
        assert not provider_family(archive_symbols, other), ('opposite transport defined in facade', role)
        executable_symbols = run(['nm', '-g', executables[role]])
        assert provider_family(executable_symbols, role)
        assert not provider_family(executable_symbols, other), ('opposite provider in executable', role)
        if not canonical:
            adapter_imports = run(['nm', '-u', obj(ADAPTERS[role])])
            assert provider_family(adapter_imports, role)
            assert not provider_family(adapter_imports, other)
        audits[role] = dict(archive_symbols_sha256=hashlib.sha256(archive_symbols.encode()).hexdigest(), executable_symbols_sha256=hashlib.sha256(executable_symbols.encode()).hexdigest(), adapter_undefined_symbols=adapter_imports.splitlines() if not canonical else None, archive=str(archive), archive_sha256=sha(archive),
                            executable=str(executables[role]), executable_sha256=sha(executables[role]),
                            members=members, own_provider_symbols=provider_family(executable_symbols, role),
                            forbidden_opposite_symbols=[], linking='standalone matching-role facade; no aggregate app archive; no GC')
    return audits


def replay_cases(executable, cases):
    if not cases:
        return
    lines = []
    for case in cases:
        x = case['input']; args = x['args']
        status = args[2] if x['op'] == 'sendAvbSysex' else 1
        parts = [x['op'], case['role'], str(x['processing']), str(status),
                 json.dumps(x.get('text', '')), str(len(args)), *map(str, args),
                 str(len(x['listeners']))]
        for stream in x['listeners']:
            parts.extend(map(str, stream))
        parts.append(str(len(x['talkers'])))
        for stream in x['talkers']:
            parts.extend(map(str, stream))
        payload = x.get('payload', [])
        parts.extend([str(len(payload)), *map(str, payload)])
        lines.append(' '.join(parts))
    output = run([executable], input=('\n'.join(lines) + '\n').encode()).splitlines()
    actual = [json.loads(line) for line in output if line.startswith('{')]
    assert len(actual) == len(cases), (len(actual), len(cases), output[-10:])
    for case, observed in zip(cases, actual):
        expected = dict(case['output'])
        if case['input']['op'] != 'sendAvbSysex':
            expected['packets'] = [[0xf0, p[0], *[n for b in p[1] for n in [b >> 4, b & 15]], 0xf7]
                                   for p in expected['packets']]
        assert observed == expected, (case, observed, expected)
    run([executable, '--preconditions'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['format', 'compile', 'symbols', 'native', 'replay', 'proof', 'role-closure'])
    parser.add_argument('--task'); parser.add_argument('--exe'); parser.add_argument('--role', choices=['client', 'server'])
    parser.add_argument('--cs18-exe'); parser.add_argument('--rm-exe'); parser.add_argument('--runtime-provider')
    parser.add_argument('--archive-bindings'); parser.add_argument('--archive-bindings-sha256'); parser.add_argument('--out')
    args = parser.parse_args()
    if args.mode == 'format':
        run(['uc-library/.venv/bin/clang-format', '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror', *OWNED])
        return
    canonical = bool(args.exe or args.cs18_exe or args.rm_exe)
    bindings = ARCHIVE_EXPECTED
    if args.archive_bindings:
        assert canonical and args.runtime_provider and args.archive_bindings_sha256
        assert sha(args.archive_bindings) == args.archive_bindings_sha256
        bindings = json.loads(Path(args.archive_bindings).read_text())
        assert {Path(p).name for p in bindings} == {Path(p).name for p in ARCHIVE_EXPECTED}
    elif canonical:
        raise ValueError('Canonical executable(s) require explicit SHA-bound own-role archive/provider bindings')
    for path, expected in bindings.items():
        assert sha(path) == expected, ('linked input changed', path)
    for path, expected in SYSTEM_INPUT_EXPECTED.items():
        assert sha(path) == expected, ('system link input changed', path)
    import native
    if args.mode == 'compile' and args.task:
        identities = [o for task, o in native.catalog() if task == args.task]; assert identities
        name = identities[0]['mangled']
        source = COMMON[2] if 'macAddress' in name else COMMON[0] if any(n in name for n in
                  ['addListener', 'removeListener', 'removeAllListeners', 'addTalker', 'removeTalker']) else COMMON[1]
        compile_source(source, O / (args.task + '.o'))
        return
    if args.mode == 'compile':
        compile_all()
        return
    if not canonical:
        for name, expected in LOCAL_OUTPUT_EXPECTED.items():
            assert sha(O / name) == expected, ('frozen local output changed', name)
    if args.mode == 'symbols':
        paths = [O / (args.task + '.o')] if args.task else [obj(source) for source in COMMON]
        symbols = '\n'.join(run(['nm', '--defined-only', p]) for p in paths)
        names = {line.split()[-1] for line in symbols.splitlines() if line.split()}
        assert all(o['mangled'] in names for task, o in native.catalog() if not args.task or task == args.task)
        print('Exact original mangling matches; no additional identity credit')
        return
    runtime = Path(args.runtime_provider) if args.runtime_provider else O / 'provider.so'
    fixture = json.loads((T / 'fixtures.json').read_text())
    fresh = native.generate(runtime, args.task)
    expected_fixture = dict(fixture)
    if args.task:
        expected_fixture['ranges'] = [r for r in fixture['ranges'] if r['task_id'] == args.task]
        expected_fixture['cases'] = [c for c in fixture['cases'] if c['task_id'] == args.task]
    assert fresh == expected_fixture, 'Fresh independent native observations changed'
    if args.mode == 'native':
        print(len(fresh['cases']), 'fresh original observations')
        return
    cases = [c for c in fresh['cases'] if not args.role or c['role'] == args.role]
    executable_map = {'client': Path(args.cs18_exe) if args.cs18_exe else role_executable('client'),
                      'server': Path(args.rm_exe) if args.rm_exe else role_executable('server')}
    if args.exe:
        assert args.role and not args.cs18_exe and not args.rm_exe
        executable_map = {args.role: Path(args.exe)}
    elif args.role:
        executable_map = {args.role: executable_map[args.role]}
    archive_map = ({role: Path(next(p for p in bindings if Path(p).name ==
                    'libpresonus_' + ROLE_NAMES[role] + '_components.a')) for role in executable_map}
                   if canonical else {role: role_archive(role) for role in executable_map})
    audits = audit_roles(executable_map, archive_map, canonical)
    for role, executable in executable_map.items():
        replay_cases(executable, [c for c in cases if c['role'] == role])
    print(len(cases), 'native/portable cases passed through separate no-GC own-role executables')
    if args.mode != 'proof':
        return
    assert args.out
    run(['uc-library/.venv/bin/clang-format', '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror', *OWNED])
    symbols = '\n'.join(run(['nm', '--defined-only', obj(s)]) for s in COMMON)
    names = {line.split()[-1] for line in symbols.splitlines() if line.split()}
    assert all(o['mangled'] in names for task, o in native.catalog() if not args.task or task == args.task)
    sources = set(OWNED + SOURCES + [str((T / n).relative_to(R)) for n in ['native.py', 'check.py', 'fixtures.json']])
    for dep in O.glob('*.o.d'):
        sources.update(p for p in dep.read_text().replace('\\\n', ' ').split(':', 1)[1].split() if (R / p).is_file())
    context = json.loads((R / json.loads(native.DISPATCH.read_text())['workers'][0]['packets'][0]).read_text())
    sources.update(context['read_files']); sources.add(AUTHORIZATION)
    proof = dict(version=1, task_id=args.task or 'avb_manager_stream_control',
                 successor='role-architecture-01; same17 methods/33 identities; zero new credit',
                 session_id='/root/sqlite_avb_stream_control_sol61',
                 validation_end=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 command_records=COMMANDS, compiled_symbols=symbols,
                 native_behavior_verified=True, fresh_native_execution=True, cpp_compiled=True,
                 compiled=True, cpp_differential_passed=True, mangling_namespace_checked=True,
                 compiled_mangled_names_matched=True, formatting_verified=True,
                 original_declaration_verified=False, original_arm_abi_verified=False,
                 hardware_verified=False, portable_ready=False, canonical_binding_pending=True,
                 case_count=len(cases), shared_case_count=len(fixture['cases']),
                 ranges=fresh['ranges'], domain=(args.task or 'shared') + '; ' + str(len(cases)) +
                 ' bounded exact native cases versus actual typed role providers, receiver post/wait/assembly, CCL services and offline IO. Each standalone executable links only its own actual role facade without GC. Native cases counted once across task subsets.',
                 limitations=fresh['limitations'] + [
                     'Original full lifecycle/thread/global dispatcher excluded; original ordinary return declarations remain pending. Static MAC helper register use established; parser upper16 bits excluded.',
                     'Original start guard/ACK contradiction preserved and investigated separately. No pre-wait state jump or ACK success hook.',
                     'Canonical Root full Linux/installed-role/compile-once/admission gates remain pending. Role facades here are bounded source overlays over hash-bound actual clean incumbent role archives; opposite application facade/provider is never linked.'],
                 sources={p.removeprefix('uc-library/'): sha(R / p) for p in sorted(sources) if p.startswith('uc-library/')},
                 repository_sources={p: sha(R / p) for p in sorted(sources) if p.startswith('third_party/')},
                 source_sha256={p: sha(R / p) for p in sorted(sources)},
                 fixture_sha256=sha(T / 'fixtures.json'),
                 formatter_version=run(['uc-library/.venv/bin/clang-format', '--version']).strip(),
                 compiler_version=run(['/usr/bin/c++', '--version']).splitlines()[0],
                 native_provider_bridge=dict(path=str(runtime), sha256=sha(runtime)),
                 role_archive_audit=audits, archive_inputs_manifest=dict(path=str((O / 'ARCHIVE_INPUTS.json').relative_to(R)), sha256=sha(O / 'ARCHIVE_INPUTS.json')),
                 archives={p: sha(p) for p in bindings}, system_link_inputs=SYSTEM_INPUT_EXPECTED,
                 archive_bindings=dict(path=args.archive_bindings, sha256=args.archive_bindings_sha256) if args.archive_bindings else None)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(proof, indent=2) + '\n')


if __name__ == '__main__':
    main()
