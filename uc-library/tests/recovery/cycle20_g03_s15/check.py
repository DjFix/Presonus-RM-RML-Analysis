"""Compile the local replay or check a supplied canonical object and executable."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shlex
import subprocess
import sys
from datetime import datetime, timezone

TASK = 'cycle20_g03_s15'
PAGE = 'Marker'
SYMBOL = '_ZN8Presonus7Surface19MarkerPageComponent20setMappingControllerEPNS_18IMappingControllerE'
DOMAIN = 'Offline original ARM exact direct and primary vtable-word routing with two mapped receiver/argument states and temporary frame-only access; portable qualified member and virtual dispatch on an actual live MarkerPageComponent, with null and live typed trap controller plus two registry values and no observer events or controller calls.'
LIMITATIONS = ['No original return declaration, complete inheritance, ARM ABI, hardware or native constructed-object layout established. Native receiver and any non-null argument are independently mapped byte regions; no original app constructor was executed.', 'Native primary slot evidence covers its observed target word; portable dispatch establishes only the chosen C++ interface.']
ENTRIES = ('member', 'virtual')
FROZEN_DEPS = {'third_party/ccl-framework/core/gui/corebitmapprimitives.h': 'a27637637ae3b5142020f09f388ef21f3b76b56df0074e5eab3da898e0ca79f7', 'third_party/ccl-framework/core/gui/coreskinformat.h': '7ce4e9cc66d18399611f316c1f59d9cacb1211785a5569d19d620e477482bfe3', 'third_party/ccl-framework/core/meta/generated/cpp/coregui-constants-generated.h': '00ebeec80cf708c529c0a6d63b6a65c84af8c07410e891f2f1df3a8466369d7c', 'third_party/ccl-framework/core/portable/coreattributes.h': '7070be8a1fccb67814b25b77db3fc0c14283c009a59c2a4060cfe23ded517e96', 'third_party/ccl-framework/core/portable/corecomponent.h': '3c9507761a27b802d8221eaead5450aa612b85caa9d77b7ac4eb2a4d74aa24cb', 'third_party/ccl-framework/core/portable/corecomponentflags.h': 'ec762b9af8f44333c7c7c6e0dd4b1225691fc9233eadf10d95ec89c65850640c', 'third_party/ccl-framework/core/portable/coreparaminfo.h': '5465baf63065883e6f63d446609ef2feeea513853246c1f04c887be1d25f30f0', 'third_party/ccl-framework/core/portable/coreparams.h': '50784dfb1ff6f3a4ce7134560d8a042b850971f96ebac6476be16326ed2c93cd', 'third_party/ccl-framework/core/portable/coresingleton.h': '2dfdb591516c9b3eb0c124a33a32bd7eb220f2f58a9c42a0e43ddeec454783fe', 'third_party/ccl-framework/core/portable/coretypeinfo.h': '2c5c4ac61b372f490ad071f6a610f5dbbfe9946b3ac38b25d210a97d637261dc', 'third_party/ccl-framework/core/portable/gui/corebitmap.h': '59f7e8af9fd892e0e206c5e73748b0f5d7a03ce3019e6ce7fa532368c5cb18e7', 'third_party/ccl-framework/core/portable/gui/coregraphics.h': 'd5f06493cffe691b7fa3ab6d5ffa53ee8c3b4391c62e7f530a9c211cb02e2fcb', 'third_party/ccl-framework/core/portable/gui/coreview.h': 'ab6167c58ad2847ae0b0ecd7a60390d36a65b6b044e8d883b3d2940a60aa5eca', 'third_party/ccl-framework/core/portable/gui/coreviewshared.h': '019137efd018010b8f8a15d85d39257620cdb3a86a2b18c0558f5c0617809793', 'third_party/ccl-framework/core/public/corebasicmacros.h': '9b879c0b7d7c02ba55e881c2cc768f04f60aa2e8d6d2834cf4afe43e6ca5d0ce', 'third_party/ccl-framework/core/public/corebuffer.h': '2dbfa18dea304df10fd9f9494889b9f2ccd2a438c592eb1bbb495ebafe84026e', 'third_party/ccl-framework/core/public/coreclassmacros.h': 'f67174739f108e57b6fdf4fe0a64a7c9df2a38b69841a97bb6ad8b762652ac77', 'third_party/ccl-framework/core/public/coreclibrary.h': 'be34ea81e1ef1f42c0f66df7584757089e75f1e41df835db2075a21c629f26bc', 'third_party/ccl-framework/core/public/corecontainer.h': 'e0c4482b13494aa0aa1d0a1713276bb42c7cdeb2609df7ab73b1a5be395e280a', 'third_party/ccl-framework/core/public/coreenumdef.h': '68c1e9b7b4be635c5aeab9bde97154e91e9f56f0f49b2daf17354b77915f14cb', 'third_party/ccl-framework/core/public/coreformatter.h': 'cc9215eeea8262be411ed08b2dcda376a2bc2510d5b0cf49b123be82b583d023', 'third_party/ccl-framework/core/public/corehashmap.h': '5e1bd0f3be25b23a487a90267a148383cca6c43bf7e79fb43ff64c1ceda41220', 'third_party/ccl-framework/core/public/coreinterpolator.h': 'df53a9ef512006a619b46831a7026380154a0589032290748737b8b2f030a202', 'third_party/ccl-framework/core/public/coreintrusivelist.h': '5e14ca4c99dbb03c15d560fbb3739515a2caf8faa10567e4f7952371b402aae3', 'third_party/ccl-framework/core/public/corelinkedlist.h': '31eb6bef4fe35fb8e6050f224923b8458733ace303a7c56dc464f1f38ef92cf2', 'third_party/ccl-framework/core/public/coremacros.h': 'd2827dfd0182e53757411849b4e582e5a2d4926814a0d21720472432a0ef7829', 'third_party/ccl-framework/core/public/coremalloc.h': '619ed30f6e89ed3bb27c9179819864a7069a123e9c96ad5b950f5494729f14ff', 'third_party/ccl-framework/core/public/coremap.h': 'e46b8e5ab7da50939e5a5b035ce0d538c5385507f63e36e9489e27d4b5501f36', 'third_party/ccl-framework/core/public/coreobserver.h': 'fcdacfdeda3f3a98d6078895c64e80a5174b7059948a0d704dbfb40e2fd5d4f9', 'third_party/ccl-framework/core/public/coreplatform.h': 'c0c45a8fcce4d694ff6b440a64769c30dcf0a8592c5e24a27d48dc7ac5e854d1', 'third_party/ccl-framework/core/public/coreprimitives.h': '7587ed00af9010e37d6a76f0e004bfe919e7d71958d831bb533beabd46daa429', 'third_party/ccl-framework/core/public/coreproperty.h': '5c66c9d3de7afaf716f298a3fbd0f76265f459fd9dae76a6cd7fc5a752365377', 'third_party/ccl-framework/core/public/corestream.h': '6d1728b889ebf8428a510a78e30fd0f0e44bee063cf4cb7b325109f3213b774d', 'third_party/ccl-framework/core/public/corestringbuffer.h': '46de7c2332457b082b9078b75b32ddb8ca35ce01d063fb9b330ffaa7e7acd55c', 'third_party/ccl-framework/core/public/corestringtraits.h': '887b7de884ad52608e4fa3a74c45102b6fbcac863a8b9db4f54618bc2534275f', 'third_party/ccl-framework/core/public/coretypes.h': '42caf0a821eb374df5fe0e8b14b3ea1fa368ce06c025710b47abb5a71f247a68', 'third_party/ccl-framework/core/public/coreuid.h': 'aac2bbacbb5cc1663753e377b851f8d7fed0ccfb7e977dbc02bf5cb2750ad667', 'third_party/ccl-framework/core/public/corevector.h': '49634ef286112cfa48357391a3cdddbee86e76cfe5e820b6b74c6ec913aeed32', 'third_party/ccl-framework/core/public/gui/corealignment.h': '9ed58580f1154804e8b8606620f3a30dcb1bf88d3576bf4a23ed3e2d702a9058', 'third_party/ccl-framework/core/public/gui/corebitmapdata.h': 'dda5aba4e4479dd5f07426ee631f8a64b7f3e550baae1531f205133c57a0a1fa', 'third_party/ccl-framework/core/public/gui/corecolor.h': 'bde1a05f098448b42041d5d66f79753dae4383ec09266d2dba6217a82d643b54', 'third_party/ccl-framework/core/public/gui/coremultitouch.h': '0705bbe0b25cb515ab039ff139bc86c8bf8e983f37f741fad549a07fc4dbf338', 'third_party/ccl-framework/core/public/gui/corepoint.h': 'c9c376f8da51e59c74d69b188a674d443e728302f8c537532ec6b23eac618df8', 'third_party/ccl-framework/core/public/gui/corerect.h': 'd57d20d379847940ab9109b3caaa52e3775f072e926edc80661504c7f5b89c12', 'third_party/ccl-framework/core/public/gui/corerectlist.h': '2b48aa9fc3098338c8216e303af9437da9970b46bba4b41080925d1f5ad2bf5a', 'third_party/ccl-framework/core/public/gui/coreviewinterface.h': 'b7d139266745ba7a0b7bbb5c6cd4faebc0fed870bfb765fee95b78c1b1bc2ad2', 'third_party/ccl-framework/core/text/coreattributehandler.h': 'f89302cc58e295cd92c389f934c15e77614a822a25f2bad1ed9eb73f3ab4e56c', 'uc-library/include/presonus/color/IColorConverter.hpp': '9246b45055c511e46fdda60178a2f32c53dc31ccfb017bae925c5baa30ecfbc0', 'uc-library/include/presonus/delay_timer.hpp': '3da2b15d6b56b8f921983ea0c97585736dbaa9d3757da8e708bbf81b2f2c9e55', 'uc-library/include/presonus/panel/key_input_provider.hpp': '3af10ca3b42989dcf3f87abfa939181eccb40fe8c72852c0e6ace0a876a9dbdb', 'uc-library/include/presonus/surface/DawFxPageComponent.hpp': 'e0bfeb44a8eb27ef92122ffaaa8670ff44c3261d4a750a535a5a38703a3f9333', 'uc-library/include/presonus/surface/MidiMixerHandler.hpp': '448be5fe6ad592ff80de9c2dc3d33830fc370c3ede7dd5898814232109986e64', 'uc-library/include/presonus/surface/sl_mixer_encoder.hpp': 'e9e0415a8f0d8b0a3bd15cf9dfe8eec37f3ae838d75da3d67f2a1e017b17b4fa'}
SNAPSHOT = Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/control10x20-after-4fed70d11/packeting/actual05-next-batch02/snapshot')
TEST = Path('uc-library/tests/recovery') / TASK
SCRATCH = Path('temp/recovery-work/cycle20-g03')
HEADER = Path(f'uc-library/include/presonus/surface/{PAGE}PageComponent.hpp')
SOURCE = Path(f'uc-library/src/Presonus/Surface/{PAGE}PageComponent.cpp')
PYTHON = 'uc-library/.venv/bin/python'
FORMATTER = 'uc-library/.venv/bin/clang-format'
PINS = {
    'libcorelib.a': '3c4f0825acb529fda135587b7ff5cb92ca0100bb417a20c034d3fdef80a93e0c',
    'libpresonus_core_allocator.a': '69892fbcec9a50a140462982073c686a67ca4763dfb5dfa190534d022b78a40d',
}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def run(argv):
    return subprocess.check_output(argv, text=True)


def output(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + '\n')


def compile_local():
    overlay = SCRATCH / 'include'
    own = overlay / HEADER.relative_to('uc-library/include')
    own.parent.mkdir(parents=True, exist_ok=True)
    if not own.is_symlink():
        own.symlink_to(HEADER.resolve())
    require(own.resolve() == HEADER.resolve(), 'Owned header overlay changed')
    flags = ['c++', '-std=c++20', '-O3', '-DNDEBUG=1', '-DCORE_USE_OPENSSL=1',
             '-DPRESONUS_HAS_UPSTREAM_CORE=1', '-Wall', '-Wextra', '-Wpedantic',
             '-pthread', '-Ulinux', '-fno-lto', '-fno-rtti', '-fno-fast-math',
             '-ffp-contract=off', '-I', str(overlay), '-I', str(SNAPSHOT / 'uc-library/include'),
             '-isystem', str(SNAPSHOT / 'third_party/ccl-framework')]
    frozen_paths = {(SNAPSHOT / relative).resolve(): relative for relative in FROZEN_DEPS}
    objects = []
    dep_hashes = {}
    commands = []
    for source, name in [(SOURCE, 'app'), (TEST / 'Replay.cpp', 'test')]:
        obj = SCRATCH / f'{TASK}.{name}.o'
        depfile = SCRATCH / f'{TASK}.{name}.d'
        argv = [*flags, '-MD', '-MF', str(depfile), '-c', str(source), '-o', str(obj)]
        commands.append(argv)
        run(argv)
        objects.append(obj)
        deps = shlex.split(depfile.read_text().replace('\\\n', ' '))[1:]
        bindings = {}
        for dependency in map(Path, deps):
            if dependency in (SOURCE, TEST / 'Replay.cpp', own):
                continue
            relative = frozen_paths.get(dependency.resolve())
            if relative is not None:
                expected = FROZEN_DEPS.get(relative)
                require(expected == digest(dependency), f'Unsealed or changed dependency {dependency}')
                bindings[relative] = expected
            else:
                require(dependency.is_absolute() and str(dependency).startswith('/usr/'),
                        f'Unexpected project dependency {dependency}')
        require(bindings == FROZEN_DEPS, f'Depfile closure changed for {source}')
        dep_hashes[str(depfile)] = digest(depfile)
    archives = []
    for name, expected in PINS.items():
        archive = SCRATCH / 'archives' / name
        require(digest(archive) == expected, f'Provider archive hash differs for {name}')
        archives.append(archive)
    link = ['c++', '-pthread', *map(str, [*objects, *archives]), '-lssl', '-lcrypto', '-ldl',
            '-o', str(SCRATCH / f'{TASK}.replay')]
    commands.append(link)
    run(link)
    output(SCRATCH / f'{TASK}.compile.json', {
        'commands': commands, 'depfiles': dep_hashes, 'frozen_dependencies': FROZEN_DEPS,
        'provider_archives': PINS, 'compiler': run(['c++', '--version']).splitlines()[0]})


def symbol_check(obj):
    symbols = run(['nm', '--defined-only', str(obj)]).splitlines()
    matches = [line for line in symbols if line.split()[-1:] == [SYMBOL]]
    require(len(matches) == 1 and matches[0].split()[1] in ('T', 'W'),
            f'Expected one defined function {SYMBOL}')
    return matches[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compile', action='store_true')
    parser.add_argument('--symbols-only', action='store_true')
    parser.add_argument('--exe', type=Path)
    parser.add_argument('--object', type=Path)
    parser.add_argument('--integration', type=Path)
    parser.add_argument('--fixture', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if args.compile:
        compile_local()
        return
    symbol = symbol_check(args.object)
    if args.symbols_only:
        print(symbol)
        return
    fixture = json.loads(args.fixture.read_text())
    require(fixture['original']['mangled'] == SYMBOL, 'Unexpected fixture identity')
    native = fixture['native_cases']
    require(len(native) == 4 and all(row['state_unchanged'] for row in native),
            'Original observations do not establish unchanged state')
    exe = args.exe.resolve()
    actual = run([str(exe)]).splitlines()
    expected = [f'{value} {entry} unchanged' for value in ('-0.25', '0.75') for entry in ENTRIES]
    require(actual == expected, 'Missing or mismatching portable replay observations')
    core = {path: expected for path, expected in FROZEN_DEPS.items() if path.startswith('third_party/')}
    for path, expected in core.items():
        require(digest(Path(path)) == expected, f'Pinned Core source drift at {path}')
    formatted = [HEADER, SOURCE, TEST / 'Replay.cpp']
    run([FORMATTER, '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror', *map(str, formatted)])
    original = fixture['original']
    row = {
        'original_elf_sha256': fixture['elf_sha256'], 'mangled': SYMBOL,
        'original_address': original['address'], 'cpp_compiled': True,
        'mangling_namespace_checked': True, 'portable_ready': False,
        'validation_domain': DOMAIN, 'domain': DOMAIN,
        'sources': {str(path.relative_to('uc-library')): digest(path) for path in formatted},
        'repository_sources': core,
        'declaration_uncertainties': ['Original ordinary return declaration and complete class layout unresolved. Portable void is intentional.'],
    }
    integration = None if args.integration is None else {'path': str(args.integration), 'sha256': digest(args.integration)}
    proof = {
        'replay_passed': True, 'cpp_differential_passed': True, 'compiled_mangled_names_matched': True,
        'mangled': SYMBOL, 'validation_domain': DOMAIN, 'fixture_sha256': digest(args.fixture),
        'native': fixture, 'portable_stdout': actual, 'portable_cases': len(actual),
        'canonical_binding': integration, 'production_object_sha256': digest(args.object),
        'replay_executable_sha256': digest(exe), 'compiled_symbol': symbol,
        'format_check_passed': True, 'formatter': run([FORMATTER, '--version']).strip(),
        'producer_sha256': digest(Path(__file__)),
        'native_producer_sha256': digest(TEST / 'native.py'),
        'utc': datetime.now(timezone.utc).isoformat(),
        'limitations': LIMITATIONS,
        'proposed_readiness': {'ready': [], 'pending': [row]},
    }
    output(args.out, proof)
    print(f'{TASK}: {len(native)} exact ARM observations, {len(actual)} portable observations')


if __name__ == '__main__':
    main()
