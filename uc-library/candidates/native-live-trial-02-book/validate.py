#!/usr/bin/env python3
"""Replay exact ELF ranges under Unicorn and compare portable Book results."""
import hashlib
import json
import struct
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP, UC_ARM_REG_LR

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
LIB = ROOT / 'uc-library'
WORK = ROOT / 'temp/recovery-work/native-live-trial-02/book-validation'
PACKET = ROOT / 'temp/recovery-work/native-live-trial-02/book-packet02'
SYMBOL = '_ZN8Presonus5Panel4Book10isValidPosEi'
SOURCES = ['src/Presonus/Panel/Book.cpp', 'include/presonus/panel/Book.hpp', 'tests/native_book_tests.cpp']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def command(argv, input=None):
    start = time.monotonic()
    p = subprocess.run([str(x) for x in argv], input=input, text=True, capture_output=True, cwd=ROOT)
    with (HERE/'commands.jsonl').open('a') as out:
        out.write(json.dumps(dict(time=datetime.now(timezone.utc).isoformat(), argv=[str(x) for x in argv], elapsed_seconds=time.monotonic()-start, returncode=p.returncode, stdout=p.stdout, stderr=p.stderr))+'\n')
    if p.returncode:
        raise RuntimeError(p.stdout+p.stderr)
    return p.stdout

def native(code, address, count, index, null, byte):
    u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    u.mem_map(address & ~4095, 8192)
    u.mem_write(address, code)
    u.mem_map(0x200000, 0x10000)
    u.mem_write(0x200000, struct.pack('<III', 0, 0x201000, count & 0xffffffff))
    u.mem_write(0x201000, struct.pack('<I', 0 if null else 0x202000))
    u.mem_write(0x202005, bytes([byte]))
    u.reg_write(UC_ARM_REG_R0, 0x200000)
    u.reg_write(UC_ARM_REG_R1, index & 0xffffffff)
    u.reg_write(UC_ARM_REG_SP, 0x20f000)
    u.reg_write(UC_ARM_REG_LR, 0x20e000)
    u.emu_start(address, 0x20e000, count=30)
    return u.reg_read(UC_ARM_REG_R0)

def main():
    start = time.monotonic()
    WORK.mkdir(parents=True, exist_ok=True)
    fmt = LIB/'.venv/bin/clang-format'
    version = command([fmt, '--version']).strip()
    command([fmt, '--style=file', '--fallback-style=LLVM', '-i', *[LIB/p for p in SOURCES]])
    command([fmt, '--style=file', '--fallback-style=LLVM', '--dry-run', '--Werror', *[LIB/p for p in SOURCES]])
    command(['c++', '-std=c++17', '-Wall', '-Wextra', '-I'+str(LIB/'include'), '-I'+str(ROOT/'third_party/ccl-framework'), LIB/SOURCES[0], LIB/SOURCES[2], '-o', WORK/'book-test'])
    symbols = command(['nm', '--defined-only', WORK/'book-test'])
    assert any(line.split()[-1] == SYMBOL for line in symbols.splitlines())
    command([WORK/'book-test'])
    request = json.loads((PACKET/'request.json').read_text())
    context = json.loads((PACKET/'native-context.json').read_text())
    fixtures = []
    originals = []
    for wrapper in request['originals']:
        o = wrapper['original']
        path = ROOT/context['binaries'][o['elf']]['path']
        body = next(context['bodies'][r] for r in context['roots'] if context['nodes'][r]['elf']==o['elf'])
        assert sha(path) == o['elf']
        with path.open('rb') as f:
            elf = ELFFile(f)
            section = elf.get_section(int(o['section_json']))
            assert section.name == '.text'
            offset = o['address'] - section['sh_addr']
            assert 0 <= offset and offset+o['size'] <= section['sh_size']
            code = section.data()[offset:offset+o['size']]
        assert section['sh_offset']+offset == body['file_offset']
        assert len(code) == body['size']
        assert hashlib.sha256(code).hexdigest() == body['bytes_sha256']
        assert code == bytes.fromhex(''.join(i['bytes'] for i in body['instructions']))
        rows = []
        for b in range(256):
            for count,index,null in [(1,0,0),(1,0,1),(1,-1,0),(1,-2147483648,0),(1,1,0),(1,2147483647,0),(0,0,0),(-1,0,0),(-2147483648,0,0),(2147483647,-1,0)]:
                result = native(code,o['address'],count,index,null,b)
                rows.append([count,index,null,b,result])
        text = '\n'.join(' '.join(map(str,r)) for r in rows)+'\n'
        command([WORK/'book-test'], input=text)
        fixtures.append(dict(original_elf_sha256=o['elf'],rows=rows))
        originals.append(dict(o,section='.text',section_index=12,range_sha256=hashlib.sha256(code).hexdigest(),elf_path=str(path.relative_to(ROOT))))
    (HERE/'fixture.json').write_text(json.dumps(fixtures,indent=2)+'\n')
    proof = dict(originals=originals,cpp_compiled=True,mangling_namespace_checked=True,portable_ready=False,original_function_verified=False,hardware_verified=False,arm_differential_verified=True,original_arm_abi_verified=False,original_declaration_verified=False,validation_domain='Each ELF: all 256 raw bytes; signed index extrema, -1, 0 and upper bound; null slots; zero/negative counts. Valid mapped borrowed memory only; no concurrency, invalid-address fault equivalence, hardware or original C++ declaration/layout claim.',formatter_version=version,sources={p:sha(LIB/p) for p in SOURCES},repository_sources={'third_party/ccl-framework/core/public/corevector.h':sha(ROOT/'third_party/ccl-framework/core/public/corevector.h')},fixture_sha256=sha(HERE/'fixture.json'),producer_sha256=sha(Path(__file__)),declaration_uncertainties=['Original return declaration unresolved; std::uint32_t is an explicit portable choice.','Original Book layout, fields, ownership and inheritance unresolved; borrowed state is independent.'])
    (HERE/'NATIVE.json').write_text(json.dumps(proof,indent=2)+'\n')
    pending=[]
    for o in originals:
        pending.append(dict(original_elf_sha256=o['elf'],mangled=SYMBOL,demangled=o['demangled'],firmware=o['firmware'],address=o['address'],size=o['size'],section='.text',portable_ready=False,cpp_compiled=True,mangling_namespace_checked=True,sources=proof['sources'],repository_sources=proof['repository_sources'],validation='candidates/native-live-trial-02-book/NATIVE.json',validation_sha256=sha(HERE/'NATIVE.json'),validation_domain=proof['validation_domain'],declaration_uncertainties=proof['declaration_uncertainties']))
    (HERE/'pending.fragment.json').write_text(json.dumps({'functions':pending},indent=2)+'\n')
    (HERE/'ready.fragment.json').write_text('{"functions": []}\n')
    (HERE/'metrics.json').write_text(json.dumps(dict(finished_at=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-start,native_cases_per_elf=len(fixtures[0]['rows']),reviewed_paths=SOURCES+[str(Path(__file__).relative_to(LIB))]),indent=2)+'\n')
    print('Book validation passed; original declarations pending.')

if __name__ == '__main__':
    main()
