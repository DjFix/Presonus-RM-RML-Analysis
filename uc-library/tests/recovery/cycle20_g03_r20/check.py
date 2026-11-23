"""Check exact DigitalPot D0 symbols, provider dependency closure and behavior."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

TASK = 'cycle20_g03_r20'
TEST = Path('uc-library/tests/recovery') / TASK
WORK = Path('temp/recovery-work/cycle20-g03-actual07')
SNAPSHOT = Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/control10x20-after-4fed70d11/packeting/actual07-authorized-wave01-capture02/snapshot')
HEADER = Path('uc-library/include/presonus/surface_panel/DigitalPotControl.hpp')
SOURCE = Path('uc-library/src/surface_panel/DigitalPotControl.cpp')
REPLAY = TEST / 'Replay.cpp'
SYMBOL = '_ZN8Presonus5Panel17DigitalPotControlD0Ev'
ARCHIVES = {
    'libcorelib.a': '3c4f0825acb529fda135587b7ff5cb92ca0100bb417a20c034d3fdef80a93e0c',
    'libpresonus_core_allocator.a': '69892fbcec9a50a140462982073c686a67ca4763dfb5dfa190534d022b78a40d',
}
PROVIDERS = ('Presonus/Panel/control.cpp', 'Presonus/Panel/param_edit_handler.cpp',
             'Presonus/DICE/PacketClockGateway.cpp')
DOMAIN = ('Exact offline CS18 and RM deleting destructor entries with actual Control D2; zero, one or three local parameter observers, empty timer roster and modeled unsized delete with same-receiver unmapping. '
          'Portable virtual delete through Control, actual pinned CCL observers, preserved legacy callback and a tested Linux unsized receiver unmap.')
LIMITATIONS = ['D1/D2 companion emission is recorded without credit. Native allocator and CCL observer boundary are modeled; ARM class ABI and hardware remain outside scope.']
FROZEN = {'PacketClockGateway': {'third_party/ccl-framework/core/platform/corefeatures.h': '0ab03cb55c5dd05e418d321b91be07ea0f8dd488358db70c2fc5d2903a9ff96d',
                        'third_party/ccl-framework/core/platform/shared/coreplatformtime.h': '919a7a83e5312182c613142e8a2d5ad26dfdcad0c09365b3caf658c2cbd113f2',
                        'third_party/ccl-framework/core/platform/shared/posix/coretime.posix.h': 'f58e058d5bcf234615fc2a7dad635bc6688fee34d253e419352f9cc5696c0555',
                        'third_party/ccl-framework/core/public/corebasicmacros.h': '9b879c0b7d7c02ba55e881c2cc768f04f60aa2e8d6d2834cf4afe43e6ca5d0ce',
                        'third_party/ccl-framework/core/public/coreclassmacros.h': 'f67174739f108e57b6fdf4fe0a64a7c9df2a38b69841a97bb6ad8b762652ac77',
                        'third_party/ccl-framework/core/public/coreclibrary.h': 'be34ea81e1ef1f42c0f66df7584757089e75f1e41df835db2075a21c629f26bc',
                        'third_party/ccl-framework/core/public/coremacros.h': 'd2827dfd0182e53757411849b4e582e5a2d4926814a0d21720472432a0ef7829',
                        'third_party/ccl-framework/core/public/coremalloc.h': '619ed30f6e89ed3bb27c9179819864a7069a123e9c96ad5b950f5494729f14ff',
                        'third_party/ccl-framework/core/public/coreplatform.h': 'c0c45a8fcce4d694ff6b440a64769c30dcf0a8592c5e24a27d48dc7ac5e854d1',
                        'third_party/ccl-framework/core/public/coretypes.h': '42caf0a821eb374df5fe0e8b14b3ea1fa368ce06c025710b47abb5a71f247a68',
                        'third_party/ccl-framework/core/system/coretime.h': '112daede39c5e3fdf85a2a813afa729fbfeef05eb07dd831fccb1c1e401ebea1',
                        'uc-library/include/presonus/dice/packet_services.hpp': 'cf3e9129780ef49c137ebb8d7e904ca1e3ab1d1aa0b45a1288622143c695b079',
                        'uc-library/src/Presonus/DICE/PacketClockGateway.cpp': 'a44a01a71a9ac8be0abf8d886a0075b57ca6eea6405dedb3982ad50606ec15a0'},
 'app': {'third_party/ccl-framework/core/portable/coreparaminfo.h': '5465baf63065883e6f63d446609ef2feeea513853246c1f04c887be1d25f30f0',
         'third_party/ccl-framework/core/portable/coreparams.h': '50784dfb1ff6f3a4ce7134560d8a042b850971f96ebac6476be16326ed2c93cd',
         'third_party/ccl-framework/core/portable/coretypeinfo.h': '2c5c4ac61b372f490ad071f6a610f5dbbfe9946b3ac38b25d210a97d637261dc',
         'third_party/ccl-framework/core/public/corebasicmacros.h': '9b879c0b7d7c02ba55e881c2cc768f04f60aa2e8d6d2834cf4afe43e6ca5d0ce',
         'third_party/ccl-framework/core/public/coreclassmacros.h': 'f67174739f108e57b6fdf4fe0a64a7c9df2a38b69841a97bb6ad8b762652ac77',
         'third_party/ccl-framework/core/public/coreclibrary.h': 'be34ea81e1ef1f42c0f66df7584757089e75f1e41df835db2075a21c629f26bc',
         'third_party/ccl-framework/core/public/corecontainer.h': 'e0c4482b13494aa0aa1d0a1713276bb42c7cdeb2609df7ab73b1a5be395e280a',
         'third_party/ccl-framework/core/public/coreformatter.h': 'cc9215eeea8262be411ed08b2dcda376a2bc2510d5b0cf49b123be82b583d023',
         'third_party/ccl-framework/core/public/coreinterpolator.h': 'df53a9ef512006a619b46831a7026380154a0589032290748737b8b2f030a202',
         'third_party/ccl-framework/core/public/coremacros.h': 'd2827dfd0182e53757411849b4e582e5a2d4926814a0d21720472432a0ef7829',
         'third_party/ccl-framework/core/public/coremalloc.h': '619ed30f6e89ed3bb27c9179819864a7069a123e9c96ad5b950f5494729f14ff',
         'third_party/ccl-framework/core/public/coreplatform.h': 'c0c45a8fcce4d694ff6b440a64769c30dcf0a8592c5e24a27d48dc7ac5e854d1',
         'third_party/ccl-framework/core/public/corestringbuffer.h': '46de7c2332457b082b9078b75b32ddb8ca35ce01d063fb9b330ffaa7e7acd55c',
         'third_party/ccl-framework/core/public/corestringtraits.h': '887b7de884ad52608e4fa3a74c45102b6fbcac863a8b9db4f54618bc2534275f',
         'third_party/ccl-framework/core/public/coretypes.h': '42caf0a821eb374df5fe0e8b14b3ea1fa368ce06c025710b47abb5a71f247a68',
         'third_party/ccl-framework/core/public/corevector.h': '49634ef286112cfa48357391a3cdddbee86e76cfe5e820b6b74c6ec913aeed32',
         'uc-library/include/presonus/panel/control.hpp': '99362bca17b334732614fac545a98157a10fe0e347c73a02493e3f0579f335d7'},
 'control': {'third_party/ccl-framework/core/portable/coreparaminfo.h': '5465baf63065883e6f63d446609ef2feeea513853246c1f04c887be1d25f30f0',
             'third_party/ccl-framework/core/portable/coreparams.h': '50784dfb1ff6f3a4ce7134560d8a042b850971f96ebac6476be16326ed2c93cd',
             'third_party/ccl-framework/core/portable/coretypeinfo.h': '2c5c4ac61b372f490ad071f6a610f5dbbfe9946b3ac38b25d210a97d637261dc',
             'third_party/ccl-framework/core/public/corebasicmacros.h': '9b879c0b7d7c02ba55e881c2cc768f04f60aa2e8d6d2834cf4afe43e6ca5d0ce',
             'third_party/ccl-framework/core/public/coreclassmacros.h': 'f67174739f108e57b6fdf4fe0a64a7c9df2a38b69841a97bb6ad8b762652ac77',
             'third_party/ccl-framework/core/public/coreclibrary.h': 'be34ea81e1ef1f42c0f66df7584757089e75f1e41df835db2075a21c629f26bc',
             'third_party/ccl-framework/core/public/corecontainer.h': 'e0c4482b13494aa0aa1d0a1713276bb42c7cdeb2609df7ab73b1a5be395e280a',
             'third_party/ccl-framework/core/public/coreformatter.h': 'cc9215eeea8262be411ed08b2dcda376a2bc2510d5b0cf49b123be82b583d023',
             'third_party/ccl-framework/core/public/coreinterpolator.h': 'df53a9ef512006a619b46831a7026380154a0589032290748737b8b2f030a202',
             'third_party/ccl-framework/core/public/coremacros.h': 'd2827dfd0182e53757411849b4e582e5a2d4926814a0d21720472432a0ef7829',
             'third_party/ccl-framework/core/public/coremalloc.h': '619ed30f6e89ed3bb27c9179819864a7069a123e9c96ad5b950f5494729f14ff',
             'third_party/ccl-framework/core/public/coreplatform.h': 'c0c45a8fcce4d694ff6b440a64769c30dcf0a8592c5e24a27d48dc7ac5e854d1',
             'third_party/ccl-framework/core/public/corestringbuffer.h': '46de7c2332457b082b9078b75b32ddb8ca35ce01d063fb9b330ffaa7e7acd55c',
             'third_party/ccl-framework/core/public/corestringtraits.h': '887b7de884ad52608e4fa3a74c45102b6fbcac863a8b9db4f54618bc2534275f',
             'third_party/ccl-framework/core/public/coretypes.h': '42caf0a821eb374df5fe0e8b14b3ea1fa368ce06c025710b47abb5a71f247a68',
             'third_party/ccl-framework/core/public/corevector.h': '49634ef286112cfa48357391a3cdddbee86e76cfe5e820b6b74c6ec913aeed32',
             'uc-library/include/presonus/dice/packet_services.hpp': 'cf3e9129780ef49c137ebb8d7e904ca1e3ab1d1aa0b45a1288622143c695b079',
             'uc-library/include/presonus/panel/control.hpp': '99362bca17b334732614fac545a98157a10fe0e347c73a02493e3f0579f335d7',
             'uc-library/include/presonus/panel/param_edit_handler.hpp': '9a0c578c791e2c9a3cdeed380702d26b7d8529a4f4ac6dd22e7efe3d0a801f7b',
             'uc-library/src/Presonus/Panel/control.cpp': '0d45529ff5274d159af31ad162be384beb2a53927127a3dec9edd1004b0dbf49'},
 'param_edit_handler': {'third_party/ccl-framework/core/platform/corefeatures.h': '0ab03cb55c5dd05e418d321b91be07ea0f8dd488358db70c2fc5d2903a9ff96d',
                        'third_party/ccl-framework/core/platform/shared/coreplatformtime.h': '919a7a83e5312182c613142e8a2d5ad26dfdcad0c09365b3caf658c2cbd113f2',
                        'third_party/ccl-framework/core/platform/shared/posix/coretime.posix.h': 'f58e058d5bcf234615fc2a7dad635bc6688fee34d253e419352f9cc5696c0555',
                        'third_party/ccl-framework/core/portable/coreparaminfo.h': '5465baf63065883e6f63d446609ef2feeea513853246c1f04c887be1d25f30f0',
                        'third_party/ccl-framework/core/portable/coreparams.h': '50784dfb1ff6f3a4ce7134560d8a042b850971f96ebac6476be16326ed2c93cd',
                        'third_party/ccl-framework/core/portable/coretypeinfo.h': '2c5c4ac61b372f490ad071f6a610f5dbbfe9946b3ac38b25d210a97d637261dc',
                        'third_party/ccl-framework/core/public/corebasicmacros.h': '9b879c0b7d7c02ba55e881c2cc768f04f60aa2e8d6d2834cf4afe43e6ca5d0ce',
                        'third_party/ccl-framework/core/public/coreclassmacros.h': 'f67174739f108e57b6fdf4fe0a64a7c9df2a38b69841a97bb6ad8b762652ac77',
                        'third_party/ccl-framework/core/public/coreclibrary.h': 'be34ea81e1ef1f42c0f66df7584757089e75f1e41df835db2075a21c629f26bc',
                        'third_party/ccl-framework/core/public/corecontainer.h': 'e0c4482b13494aa0aa1d0a1713276bb42c7cdeb2609df7ab73b1a5be395e280a',
                        'third_party/ccl-framework/core/public/coreformatter.h': 'cc9215eeea8262be411ed08b2dcda376a2bc2510d5b0cf49b123be82b583d023',
                        'third_party/ccl-framework/core/public/coreinterpolator.h': 'df53a9ef512006a619b46831a7026380154a0589032290748737b8b2f030a202',
                        'third_party/ccl-framework/core/public/coremacros.h': 'd2827dfd0182e53757411849b4e582e5a2d4926814a0d21720472432a0ef7829',
                        'third_party/ccl-framework/core/public/coremalloc.h': '619ed30f6e89ed3bb27c9179819864a7069a123e9c96ad5b950f5494729f14ff',
                        'third_party/ccl-framework/core/public/coreplatform.h': 'c0c45a8fcce4d694ff6b440a64769c30dcf0a8592c5e24a27d48dc7ac5e854d1',
                        'third_party/ccl-framework/core/public/corestringbuffer.h': '46de7c2332457b082b9078b75b32ddb8ca35ce01d063fb9b330ffaa7e7acd55c',
                        'third_party/ccl-framework/core/public/corestringtraits.h': '887b7de884ad52608e4fa3a74c45102b6fbcac863a8b9db4f54618bc2534275f',
                        'third_party/ccl-framework/core/public/coretypes.h': '42caf0a821eb374df5fe0e8b14b3ea1fa368ce06c025710b47abb5a71f247a68',
                        'third_party/ccl-framework/core/public/corevector.h': '49634ef286112cfa48357391a3cdddbee86e76cfe5e820b6b74c6ec913aeed32',
                        'third_party/ccl-framework/core/system/coretime.h': '112daede39c5e3fdf85a2a813afa729fbfeef05eb07dd831fccb1c1e401ebea1',
                        'uc-library/include/presonus/dice/packet_services.hpp': 'cf3e9129780ef49c137ebb8d7e904ca1e3ab1d1aa0b45a1288622143c695b079',
                        'uc-library/include/presonus/panel/param_edit_handler.hpp': '9a0c578c791e2c9a3cdeed380702d26b7d8529a4f4ac6dd22e7efe3d0a801f7b',
                        'uc-library/src/Presonus/Panel/param_edit_handler.cpp': '478b8a72edbff4d58377cee92602ddc4c0aef07086cbca63f3e35dc3c4d109f2'},
 'test': {'third_party/ccl-framework/core/portable/coreparaminfo.h': '5465baf63065883e6f63d446609ef2feeea513853246c1f04c887be1d25f30f0',
          'third_party/ccl-framework/core/portable/coreparams.h': '50784dfb1ff6f3a4ce7134560d8a042b850971f96ebac6476be16326ed2c93cd',
          'third_party/ccl-framework/core/portable/coretypeinfo.h': '2c5c4ac61b372f490ad071f6a610f5dbbfe9946b3ac38b25d210a97d637261dc',
          'third_party/ccl-framework/core/public/corebasicmacros.h': '9b879c0b7d7c02ba55e881c2cc768f04f60aa2e8d6d2834cf4afe43e6ca5d0ce',
          'third_party/ccl-framework/core/public/coreclassmacros.h': 'f67174739f108e57b6fdf4fe0a64a7c9df2a38b69841a97bb6ad8b762652ac77',
          'third_party/ccl-framework/core/public/coreclibrary.h': 'be34ea81e1ef1f42c0f66df7584757089e75f1e41df835db2075a21c629f26bc',
          'third_party/ccl-framework/core/public/corecontainer.h': 'e0c4482b13494aa0aa1d0a1713276bb42c7cdeb2609df7ab73b1a5be395e280a',
          'third_party/ccl-framework/core/public/coreformatter.h': 'cc9215eeea8262be411ed08b2dcda376a2bc2510d5b0cf49b123be82b583d023',
          'third_party/ccl-framework/core/public/coreinterpolator.h': 'df53a9ef512006a619b46831a7026380154a0589032290748737b8b2f030a202',
          'third_party/ccl-framework/core/public/coremacros.h': 'd2827dfd0182e53757411849b4e582e5a2d4926814a0d21720472432a0ef7829',
          'third_party/ccl-framework/core/public/coremalloc.h': '619ed30f6e89ed3bb27c9179819864a7069a123e9c96ad5b950f5494729f14ff',
          'third_party/ccl-framework/core/public/coreplatform.h': 'c0c45a8fcce4d694ff6b440a64769c30dcf0a8592c5e24a27d48dc7ac5e854d1',
          'third_party/ccl-framework/core/public/corestringbuffer.h': '46de7c2332457b082b9078b75b32ddb8ca35ce01d063fb9b330ffaa7e7acd55c',
          'third_party/ccl-framework/core/public/corestringtraits.h': '887b7de884ad52608e4fa3a74c45102b6fbcac863a8b9db4f54618bc2534275f',
          'third_party/ccl-framework/core/public/coretypes.h': '42caf0a821eb374df5fe0e8b14b3ea1fa368ce06c025710b47abb5a71f247a68',
          'third_party/ccl-framework/core/public/corevector.h': '49634ef286112cfa48357391a3cdddbee86e76cfe5e820b6b74c6ec913aeed32',
          'uc-library/include/presonus/panel/control.hpp': '99362bca17b334732614fac545a98157a10fe0e347c73a02493e3f0579f335d7'}}

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(argv):
    return subprocess.check_output(argv, text=True)


def checked_compile():
    overlay = WORK / 'include'
    own = overlay / HEADER.relative_to('uc-library/include')
    own.parent.mkdir(parents=True, exist_ok=True)
    if not own.is_symlink():
        own.symlink_to(HEADER.resolve())
    assert own.resolve() == HEADER.resolve()
    flags = ['c++', '-std=c++20', '-O3', '-DNDEBUG=1', '-DCORE_USE_OPENSSL=1',
             '-DPRESONUS_HAS_UPSTREAM_CORE=1', '-Wall', '-Wextra', '-pthread',
             '-Ulinux', '-fno-lto', '-fno-rtti', '-I', str(overlay), '-I',
             str(SNAPSHOT / 'uc-library/include'), '-isystem',
             str(SNAPSHOT / 'third_party/ccl-framework')]
    units = {'app': SOURCE, 'test': REPLAY}
    units.update((Path(p).stem, SNAPSHOT / 'uc-library/src' / p) for p in PROVIDERS)
    compiled, resolved, depfiles, commands = [], {}, {}, []
    for key, src in units.items():
        obj = WORK / f'{TASK}.{key}.o'
        depfile = WORK / f'{TASK}.{key}.d'
        argv = [*flags, *(['-fno-sized-deallocation'] if key == 'app' else []),
                '-MD', '-MF', str(depfile), '-c', str(src), '-o', str(obj)]
        commands.append(argv)
        run(argv)
        compiled.append(obj)
        text = depfile.read_text()
        depfiles[str(depfile)] = {'sha256': digest(depfile), 'contents': text}
        actual = {}
        for path in map(Path, shlex.split(text.replace('\\\n', ' '))[1:]):
            if path.resolve() in (SOURCE.resolve(), REPLAY.resolve(), HEADER.resolve()):
                continue
            for prefix in ('uc-library/include/', 'uc-library/src/', 'third_party/ccl-framework/'):
                at = str(path).find(prefix)
                if at >= 0:
                    rel = str(path)[at:]
                    assert (SNAPSHOT / rel).resolve() == path.resolve(), path
                    actual[rel] = digest(path)
                    break
            else:
                assert path.is_absolute() and str(path).startswith('/usr/'), path
        resolved[key] = actual
    assert resolved == FROZEN, 'Actual translation-unit dependency hashes differ from frozen seal'
    archives = [WORK / 'archives' / name for name in ARCHIVES]
    assert {p.name: digest(p) for p in archives} == ARCHIVES
    link = ['c++', '-pthread', *map(str, [*compiled, *archives]), '-lssl', '-lcrypto',
            '-ldl', '-o', str(WORK / f'{TASK}.replay')]
    run(link)
    commands.append(link)
    receipt = {'compiler': run(['c++', '--version']).splitlines()[0], 'commands': commands,
               'depfiles': depfiles, 'frozen': resolved, 'archives': ARCHIVES}
    (WORK / f'{TASK}.compile.json').write_text(json.dumps(receipt, indent=2) + '\n')


def checked_symbol(obj):
    symbols = run(['nm', '--defined-only', str(obj)]).splitlines()
    [match] = [line for line in symbols if line.split()[-1:] == [SYMBOL]]
    assert match.split()[1] in ('T', 'W')
    assembly = run(['objdump', '-dr', '--disassemble=' + SYMBOL, str(obj)])
    d0 = assembly[assembly.index('<' + SYMBOL + '>:'):]
    assert '_ZdlPv' in d0 and '_ZdlPvm' not in d0
    companions = [ln for ln in symbols if 'DigitalPotControlD1Ev' in ln or 'DigitalPotControlD2Ev' in ln]
    return {'original_symbol': match, 'compiler_companions': companions, 'portable_d0_assembly': d0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compile', action='store_true')
    parser.add_argument('--symbols-only', action='store_true')
    for option in ('exe', 'object', 'fixture', 'integration', 'out'):
        parser.add_argument('--' + option, type=Path)
    args = parser.parse_args()
    if args.compile:
        checked_compile()
        return
    symbols = checked_symbol(args.object)
    if args.symbols_only:
        print(symbols['original_symbol'])
        return
    fixture = json.loads(args.fixture.read_text())
    native = fixture['rows']
    assert len(native) == 2 and all(row['original']['mangled'] == SYMBOL for row in native)
    for row in native:
        assert [case['bound_count'] for case in row['native_cases']] == [0, 1, 3]
        assert all(case['receiver_unmapped'] for case in row['native_cases'])
    actual = run([str(args.exe.resolve())]).splitlines()
    assert actual == [f'{count} observers removed, receiver unmapped' for count in (0, 1, 3)]
    frozen = {p: sha for bindings in FROZEN.values() for p, sha in bindings.items()}
    core = {p: sha for p, sha in frozen.items() if p.startswith('third_party/ccl-framework/core/')}
    assert all(digest(p) == sha for p, sha in core.items())
    if args.integration is not None:
        assert all(digest(p) == sha for p, sha in frozen.items())
    formatted = [HEADER, SOURCE, REPLAY]
    formatter = 'uc-library/.venv/bin/clang-format'
    run([formatter, '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror', *map(str, formatted)])
    sources = {str(p.relative_to('uc-library')): digest(p) for p in formatted}
    pending = [{
        'original_elf_sha256': row['elf_sha256'], 'mangled': SYMBOL,
        'original_address': row['original']['address'], 'cpp_compiled': True,
        'mangling_namespace_checked': True, 'portable_ready': False,
        'domain': DOMAIN, 'validation_domain': DOMAIN, 'sources': sources,
        'repository_sources': core, 'declaration_uncertainties': LIMITATIONS,
    } for row in native]
    proof = dict(replay_passed=True, cpp_differential_passed=True,
                 compiled_mangled_names_matched=True,
                 validation_domain=DOMAIN, fixture_sha256=digest(args.fixture),
                 native=fixture, portable_stdout=actual,
                 portable_cases=len(actual), symbols=symbols,
                 original_object_sha256=digest(args.object), replay_executable_sha256=digest(args.exe),
                 canonical_integration_sha256=digest(args.integration) if args.integration else None,
                 format_check_passed=True, formatter=run([formatter, '--version']).strip(),
                 producer_sha256=digest(__file__), native_producer_sha256=digest(TEST / 'native.py'),
                 utc=datetime.now(timezone.utc).isoformat(), limitations=LIMITATIONS,
                 proposed_readiness={'ready': [], 'pending': pending})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(proof, indent=2) + '\n')
    print('Verified six exact ARM and three real portable D0 lifetime observations')


if __name__ == '__main__':
    main()
