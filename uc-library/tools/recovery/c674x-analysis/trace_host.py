"""Capture app-only ARM evidence for the OMAP/NOAA processing boundary."""
import argparse
import hashlib
import json
import struct
import subprocess
from pathlib import Path

import capstone as cs
from capstone.arm import ARM_OP_IMM, ARM_OP_MEM, ARM_REG_PC
from elftools.elf.elffile import ELFFile

from analyze import EXPECTED, sha

ADDRESSES = [0x104ec8, 0x104a8c, 0x1049b4, 0x4c5a4, 0x31d24, 0x35528, 0x355f4,
             0x329b0, 0x869e0, 0x86d28, 0x8651c, 0x104e00, 0x104e64,
             0xb29ac, 0xb29d8, 0xb2750, 0xc5750, 0xc54f8, 0xb496c, 0xb711c,
             0xcd21c, 0xbe468, 0xb3f48, 0xce154, 0x9e85c, 0x9ee34, 0x9e9e8,
             0xa1144, 0x3cda8, 0x3bf30, 0x3d358, 0x3d430, 0x3d5f0, 0x3dd48,
             0x3c4b4, 0x8741c, 0x40ed8, 0x42808, 0x408f4, 0x41174, 0x49bb0,
             0x461b4, 0x463cc, 0x40c30, 0x40558, 0x432a4, 0x465ec]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    raw = args.input.read_bytes()
    assert sha(raw) == EXPECTED
    args.out.mkdir(parents=True, exist_ok=True)
    with args.input.open('rb') as source:
        elf = ELFFile(source)
        sections = list(elf.iter_sections())
        syms = list(elf.get_section_by_name('.symtab').iter_symbols())
        functions = [s for s in syms if s['st_info']['type'] == 'STT_FUNC' and s['st_size']]
        at = {}
        for sym in functions:
            at.setdefault(sym['st_value'], []).append(sym)
        allnames = {s['st_value']: s.name for s in functions}
        chosen = [s for addr in ADDRESSES for s in at.get(addr, [])]
        names = subprocess.run(['c++filt'], input='\n'.join(s.name for s in chosen),
                               text=True, capture_output=True, check=True).stdout.splitlines()
        decoder = cs.Cs(cs.CS_ARCH_ARM, cs.CS_MODE_ARM)
        decoder.detail = True
        report = []
        for sym, name in zip(chosen, names):
            assert not sym.name.startswith('_ZN4Core'), name
            sec = sections[sym['st_shndx']]
            off = sec['sh_offset'] + sym['st_value'] - sec['sh_addr']
            data = raw[off:off + sym['st_size']]
            lines, literals, calls = [], [], []
            for ins in decoder.disasm(data, sym['st_value']):
                ops = ins.operands
                note = ''
                if ins.mnemonic.startswith('bl') and ops and ops[0].type == ARM_OP_IMM:
                    dest = ops[0].imm & 0xffffffff
                    note = allnames.get(dest, '')
                    calls.append(dict(instruction=hex(ins.address), target=hex(dest), symbol=note))
                if ins.mnemonic.startswith('ldr') and len(ops) == 2 and ops[1].type == ARM_OP_MEM:
                    mem = ops[1].mem
                    if mem.base == ARM_REG_PC and not mem.index:
                        va = ins.address + 8 + mem.disp
                        for ls in sections:
                            if ls['sh_type'] != 'SHT_NOBITS' and ls['sh_flags'] & 2 and ls['sh_addr'] <= va and va + 4 <= ls['sh_addr'] + ls['sh_size']:
                                litoff = ls['sh_offset'] + va - ls['sh_addr']
                                word = raw[litoff:litoff + 4]
                                value = struct.unpack('<I', word)[0]
                                text = word.decode('ascii') if all(32 <= b < 127 for b in word) else None
                                literals.append(dict(instruction=hex(ins.address), literal_va=hex(va), value=hex(value), ascii_little_endian=text))
                                note = f'literal {value:#x}' + (f' bytes {text!r}' if text else '')
                                break
                lines.append(f'{ins.address:08x}: {ins.bytes.hex()} {ins.mnemonic} {ins.op_str}' + (f' ; {note}' if note else ''))
            filename = f'{sym["st_value"]:08x}.arm.asm'
            (args.out / filename).write_text(f'; {sym.name}\n; {name}\n' + '\n'.join(lines) + '\n')
            report.append(dict(mangled=sym.name, demangled=name, address=hex(sym['st_value']),
                               size=sym['st_size'], section=sec.name, file_offset=hex(off), sha256=sha(data),
                               firmware='RML16AI_Rack_13731', elf_sha256=EXPECTED,
                               assembly=filename, literals=literals, direct_calls=calls))
        # Retain original identities for data defining the target interface.
        vtable = next(s for s in syms if s.name == '_ZTVN8Presonus3Dsp17OMAPTargetHandlerE')
        report_meta = dict(elf_sha256=EXPECTED, capstone=cs.__version__,
                           script_sha256=sha(Path(__file__).read_bytes()), functions=report,
                           omap_vtable=dict(mangled=vtable.name, address=hex(vtable['st_value']),
                                            address_point=hex(vtable['st_value'] + 8),
                                            size=vtable['st_size']),
                           scope='ARM static evidence only; inferred decompiler declarations not validated')
        (args.out / 'manifest.json').write_text(json.dumps(report_meta, indent=2) + '\n')
        for row in report:
            properties = [x['ascii_little_endian'] for x in row['literals'] if x['ascii_little_endian']]
            print(row['address'], row['demangled'], properties)
        print('OMAP vtable address point:', report_meta['omap_vtable']['address_point'])


if __name__ == '__main__':
    main()
