#!/usr/bin/env python3
"""Execute exact ELF ARM getTags bytes and compare the portable C++ source port.

The original return declaration and class ABI remain unresolved. No hardware is used.
"""
import hashlib
import io
import json
import platform
import random
import struct
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM
from unicorn.arm_const import (UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2,
                              UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR,
                              UC_ARM_REG_PC)

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
WORK = ROOT / 'temp/recovery-work/native-live-trial-02/beast-validation'
ELF_PATH = ROOT / 'rootfs/RML16AI_Rack_13731/home/root/mixer'
ELF_SHA = '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
SYMBOL = '_ZNK8Presonus5Panel19BeastPanelRegistrar7getTagsEiRi'
SOURCE = ROOT / 'uc-library/src/Presonus/Panel/BeastPanelRegistrar.cpp'
HEADER = ROOT / 'uc-library/include/presonus/panel/BeastPanelRegistrar.hpp'
TEST = ROOT / 'uc-library/tests/native_beast_tests.cpp'
FORMAT = ROOT / 'uc-library/.venv/bin/clang-format'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run(args):
    start = time.monotonic()
    result = subprocess.run([str(a) for a in args], cwd=ROOT, text=True,
                            capture_output=True)
    with (OUT / 'commands.jsonl').open('a') as log:
        log.write(json.dumps({'timestamp': datetime.now(timezone.utc).isoformat(),
                              'argv': [str(a) for a in args],
                              'cwd': str(ROOT), 'elapsed_seconds': time.monotonic()-start,
                              'returncode': result.returncode, 'stdout': result.stdout,
                              'stderr': result.stderr}) + '\n')
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    return result.stdout


def main():
    started = time.monotonic()
    WORK.mkdir(parents=True, exist_ok=True)
    paths = [SOURCE, HEADER, TEST]
    formatter = run([FORMAT, '--version']).strip()
    run([FORMAT, '--style=file', '--fallback-style=LLVM', '-i', *paths])
    run([FORMAT, '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror', *paths])
    blob = ELF_PATH.read_bytes()
    assert sha(blob) == ELF_SHA
    elf = ELFFile(io.BytesIO(blob))
    symbols = elf.get_section_by_name('.symtab')
    matches = [s for s in symbols.iter_symbols() if s.name == SYMBOL]
    assert len(matches) == 1
    symbol = matches[0]
    assert int(symbol['st_value']) == 500368 and int(symbol['st_size']) == 40
    section = elf.get_section(symbol['st_shndx'])
    assert section.name == '.text' and int(symbol['st_shndx']) == 12

    def extract(address, size):
        sections = [s for s in elf.iter_sections() if
                    s['sh_type'] != 'SHT_NOBITS' and int(s['sh_flags']) & 2 and
                    int(s['sh_addr']) <= address and
                    address + size <= int(s['sh_addr']) + int(s['sh_size'])]
        assert len(sections) == 1
        sec = sections[0]
        offset = int(sec['sh_offset']) + address - int(sec['sh_addr'])
        return blob[offset:offset+size], offset

    native, file_offset = extract(500368, 40)
    assert sha(native) == 'fba1fb4c083be623d62b3eed478fefc76d6d418f98ffddfe9c8d4ec6c5bf2182'
    table, table_offset = extract(3472468, 128)
    assert sha(table) == '0ea48b362e628d8d19f7e4ddc27fb32d369544646437c89479a5da61e338e0ca'
    words = list(struct.unpack('<32I', table))
    table_symbols = [s for s in symbols.iter_symbols() if s.name == '_ZL9g48vTagsA' and int(s['st_value']) == 3472468]
    assert len(table_symbols) == 1
    assert int(table_symbols[0]['st_value']) == 3472468 and int(table_symbols[0]['st_size']) == 128
    assert int.from_bytes(native[36:40], 'little') == 3472468
    exe = WORK / 'native_beast_tests'
    obj = WORK / 'BeastPanelRegistrar.o'
    compiler = run(['c++', '--version']).splitlines()[0]
    flags = ['c++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-Iuc-library/include']
    run([*flags, '-c', SOURCE, '-o', obj])
    nm = run(['nm', '--defined-only', obj])
    assert any(line.split()[-1] == SYMBOL for line in nm.splitlines())
    run([*flags, SOURCE, TEST, '-o', exe])
    run([exe])
    rng = random.Random(20261031)
    groups = sorted(set([-2147483648, -2147483647, -21, -20, -1, 0, 1, 18, 19,
                         20, 21, 22, 2147483646, 2147483647] +
                        [rng.randrange(-2147483648, 2147483648) for _ in range(16)]))
    sentinels = [-2147483648, -12345, 0, 2147483647]
    fixtures = []
    for group in groups:
        for count in sentinels:
            uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
            uc.mem_map(0x7a000, 0x1000)
            uc.mem_write(500368, native)
            uc.mem_map(0x34f000, 0x2000)
            uc.mem_write(3472468, table)
            uc.mem_map(0x800000, 0x10000)
            uc.mem_map(0x900000, 0x1000)
            out_count = 0x800100
            uc.mem_write(out_count - 4, struct.pack('<III', 0x12345678, count & 0xffffffff, 0x87654321))
            for reg, value in [(UC_ARM_REG_R0, 0xdeadbeec),
                               (UC_ARM_REG_R1, group & 0xffffffff),
                               (UC_ARM_REG_R2, out_count), (UC_ARM_REG_R3, 0xabcdef),
                               (UC_ARM_REG_SP, 0x80ff00), (UC_ARM_REG_LR, 0x900000)]:
                uc.reg_write(reg, value)
            uc.emu_start(500368, 0x900000, count=32)
            assert uc.reg_read(UC_ARM_REG_PC) == 0x900000
            result = uc.reg_read(UC_ARM_REG_R0)
            actual_count = struct.unpack('<i', uc.mem_read(out_count, 4))[0]
            assert uc.mem_read(out_count - 4, 4) == struct.pack('<I', 0x12345678)
            assert uc.mem_read(out_count + 4, 4) == struct.pack('<I', 0x87654321)
            native_words = list(struct.unpack('<32I', uc.mem_read(result, 128))) if result else []
            assert result == (3472468 if group == 20 else 0)
            assert actual_count == (32 if group == 20 else count)
            portable = [int(x) for x in run([exe, str(group), str(count)]).split()]
            assert portable == [int(bool(result)), actual_count, *native_words]
            fixtures.append({'group': group, 'initial_count': count, 'native_r0': result,
                             'count': actual_count, 'tag_words_u32': native_words,
                             'cpp_matches': True, 'adjacent_count_canaries_preserved': True})
    (OUT / 'fixture.json').write_text(json.dumps({'cases': fixtures}, indent=2) + '\n')
    original = {'elf_sha256': ELF_SHA, 'firmware': 'RM/RML mixer 13731', 'role': 'server',
                'mangled': SYMBOL, 'demangled': 'Presonus::Panel::BeastPanelRegistrar::getTags(int, int&) const',
                'address': 500368, 'size': 40, 'section': '.text', 'section_index': 12,
                'file_offset': file_offset, 'bytes_sha256': sha(native)}
    proof = {'version': 1, 'status': 'portable-validated-original-declaration-pending',
             'original': original, 'native_execution': 'Unicorn ARM mode, exact ELF range, bounded synthetic memory; no hardware',
             'native_table': {'mangled': '_ZL9g48vTagsA', 'address': 3472468, 'size': 128,
                              'file_offset': table_offset, 'sha256': sha(table), 'words_u32': words},
             'original_declaration_verified': False, 'original_arm_abi_verified': False,
             'hardware_verified': False, 'binary_behavior_verified': False,
             'portable_behavior_verified': True, 'native_differential_verified': True,
             'original_mangling_verified': True, 'formatter': formatter, 'compiler': compiler,
             'platform': platform.platform(), 'unicorn_version': unicorn.__version__,
             'symbol_output': nm, 'cases': len(fixtures),
             'validation_domains': ['signed int group boundaries, adjacent values around 20 and 16 seeded samples',
                                    'four signed out-count sentinels, preserved on rejection',
                                    'exact returned 32 table words including eight 0xffffffff encodings',
                                    'native out-count adjacent canaries', 'portable repeated-call table identity'],
             'source_port_choices': ['const std::int32_t* return and pointee const qualification',
                                     'minimal class definition without native layout or inheritance claims',
                                     'private immutable table with process lifetime'],
             'unresolved': ['original return declaration and pointee qualifiers',
                            'original class layout/inheritance and binary interoperability',
                            'native table ownership, mutability and lifetime declaration'],
             'source_hashes': {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in paths},
             'producer_sha256': sha(Path(__file__).read_bytes()),
             'fixture_sha256': sha((OUT / 'fixture.json').read_bytes()),
             'ccl_dependencies': [], 'format_checked': True}
    (OUT / 'NATIVE.json').write_text(json.dumps(proof, indent=2) + '\n')
    (OUT / 'metrics.json').write_text(json.dumps({'elapsed_seconds': time.monotonic()-started,
                                                'native_cpp_comparisons': len(fixtures),
                                                'intentional_replays': 2,
                                                'prior_failure': 'Initial section-range lookup included nonallocated debug sections; corrected to require SHF_ALLOC before extraction. A second pre-execution attempt found three same-named local table symbols; selection now requires exact original table address. No native execution or C++ comparison occurred in either failed attempt.',
                                                'reviewed_paths': [str(p.relative_to(ROOT)) for p in paths] +
                                                ['AGENTS.md',
                                                 'temp/recovery-work/native-live-trial-02/beast-packet/TASK.md',
                                                 'temp/recovery-work/native-live-trial-02/beast-packet/ELF_CONTEXT.md',
                                                 'temp/recovery-work/native-live-trial-02/beast-packet/SOURCE_SLICES.md',
                                                 'temp/recovery-work/native-live-trial-02/beast-packet/CONTEXT.md',
                                                 'temp/recovery-work/native-live-trial-02/beast-packet/request.json',
                                                 'temp/recovery-work/native-live-trial-02/beast-packet/native-context.json'],
                                                'administrative_context_requests': ['Validator schema request withdrawn; Root retains readiness admission.'],
                                                'native_context_expansions': 0}, indent=2) + '\n')
    print(json.dumps({'status': proof['status'], 'cases': len(fixtures), 'proof': str(OUT / 'NATIVE.json')}))


if __name__ == '__main__':
    main()
