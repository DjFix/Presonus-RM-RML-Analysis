"""Offline, hash-bound DSP loader extraction. No hardware access or execution."""
import argparse
import hashlib
import json
import platform
import re
import struct
from pathlib import Path

import capstone as cs
from capstone.arm import ARM_OP_IMM, ARM_OP_MEM, ARM_OP_REG, ARM_REG_PC
from elftools.elf.elffile import ELFFile

EXPECTED = '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    raw = args.input.read_bytes()
    assert sha(raw) == EXPECTED
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    with args.input.open('rb') as stream:
        elf = ELFFile(stream)
        sections = list(elf.iter_sections())
        syms = list(elf.get_section_by_name('.symtab').iter_symbols())
        named = {s.name: s for s in syms}

        def mapped(va, size):
            candidates = [(i, s) for i, s in enumerate(sections)
                          if s['sh_type'] != 'SHT_NOBITS' and s['sh_flags'] & 2
                          and s['sh_addr'] <= va and va + size <= s['sh_addr'] + s['sh_size']]
            assert len(candidates) == 1, (hex(va), size)
            i, sec = candidates[0]
            off = sec['sh_offset'] + va - sec['sh_addr']
            data = raw[off:off + size]
            assert len(data) == size
            return data, off, i, sec.name

        def identity(sym):
            idx = sym['st_shndx']
            return dict(mangled=sym.name, address=hex(sym['st_value']), size=sym['st_size'],
                        section=sections[idx].name if isinstance(idx, int) else idx,
                        firmware='RML16AI_Rack_13731', elf_sha256=EXPECTED)

        boot = named['bootDSP']
        code, _, _, _ = mapped(boot['st_value'], boot['st_size'])
        arm = cs.Cs(cs.CS_ARCH_ARM, cs.CS_MODE_ARM | cs.CS_MODE_LITTLE_ENDIAN)
        arm.detail = True
        regs = {}
        rows = []
        trace = []
        literal_reads = []
        for ins in arm.disasm(code, boot['st_value']):
            trace.append(f'{ins.address:08x}: {ins.bytes.hex()} {ins.mnemonic} {ins.op_str}')
            ops = ins.operands
            if ins.mnemonic == 'bl' and ops[0].type == ARM_OP_IMM:
                target = ops[0].imm
                if target == named['pma_getVirAddr']['st_value']:
                    assert isinstance(regs.get('r0'), int) and isinstance(regs.get('r1'), int)
                    dest = ('mapped', regs['r0'], regs['r1'], ins.address)
                    regs = {k: v for k, v in regs.items() if k not in ('r0', 'r1', 'r2', 'r3')}
                    regs['r0'] = dest
                    continue
                if target == 0xae68:  # verified memcpy PLT destination in ARM export
                    dst, src, size = (regs.get(r) for r in ('r0', 'r1', 'r2'))
                    assert isinstance(dst, tuple) and dst[0] == 'mapped', (hex(ins.address), regs)
                    assert isinstance(src, int) and isinstance(size, int) and size == dst[2]
                    data, off, idx, secname = mapped(src, size)
                    filename = f'segment-{len(rows):02d}-{dst[1]:08x}.bin'
                    (out / filename).write_bytes(data)
                    owners = [identity(s) for s in syms if s['st_shndx'] == idx and s['st_size']
                              and s['st_value'] <= src and src + size <= s['st_value'] + s['st_size']]
                    rows.append(dict(copy_call=hex(ins.address), map_call=hex(dst[3]),
                                     source_va=hex(src), source_file_offset=hex(off), source_section=secname,
                                     destination_va=hex(dst[1]), size=size, sha256=sha(data), filename=filename,
                                     enclosing_original_symbols=owners, source_bytes_verified=True))
                regs = {k: v for k, v in regs.items() if k not in ('r0', 'r1', 'r2', 'r3')}
                continue
            value = None
            if ins.mnemonic == 'mov' and len(ops) == 2:
                if ops[1].type == ARM_OP_IMM:
                    value = ops[1].imm & 0xffffffff
                elif ops[1].type == ARM_OP_REG:
                    value = regs.get(ins.reg_name(ops[1].reg))
            elif ins.mnemonic == 'ldr' and len(ops) == 2 and ops[1].type == ARM_OP_MEM:
                mem = ops[1].mem
                if mem.base == ARM_REG_PC and not mem.index:
                    addr = ins.address + 8 + mem.disp
                    lit, _, _, _ = mapped(addr, 4)
                    value = struct.unpack('<I', lit)[0]
                    literal_reads.append(dict(instruction=hex(ins.address), literal_va=hex(addr), value=hex(value)))
            if ops and ops[0].type == ARM_OP_REG and ins.mnemonic not in ('cmp', 'tst', 'str', 'strb'):
                name = ins.reg_name(ops[0].reg)
                if value is None:
                    regs.pop(name, None)
                else:
                    regs[name] = value
            if ins.mnemonic.startswith('ldm') and 'pc' in ins.op_str:
                break
        assert len(rows) == 10, len(rows)
        for i, a in enumerate(rows):
            for b in rows[i + 1:]:
                av, bv = int(a['destination_va'], 16), int(b['destination_va'], 16)
                assert av + a['size'] <= bv or bv + b['size'] <= av
        (out / 'bootDSP.arm.asm').write_text('\n'.join(trace) + '\n')
        (out / 'bootDSP.raw.bin').write_bytes(code)

        # Synthetic ELF PT_LOAD view: byte-exact payloads; original section names,
        # permissions, symbols and original DSP ELF entry are NOT recovered.
        header_size = 52 + 32 * len(rows)
        image = bytearray(header_size)
        ph = []
        for row in rows:
            image.extend(b'\0' * ((-len(image)) % 4096))
            off = len(image)
            image.extend((out / row['filename']).read_bytes())
            va = int(row['destination_va'], 16)
            ph.append(struct.pack('<IIIIIIII', 1, off, va, va, row['size'], row['size'], 7, 1))
        ident = b'\x7fELF\x01\x01\x01' + b'\0' * 9
        image[:52] = struct.pack('<16sHHIIIIIHHHHHH', ident, 2, 140, 1, 0x80000000, 52, 0, 0, 52, 32, len(rows), 0, 0, 0)
        image[52:header_size] = b''.join(ph)
        (out / 'dsp-load-image.synthetic.elf').write_bytes(image)

        strings = []
        dis_stats = []
        decoder = cs.Cs(cs.CS_ARCH_TMS320C64X, cs.CS_MODE_LITTLE_ENDIAN)
        decoder.skipdata = True
        for row in rows:
            data = (out / row['filename']).read_bytes()
            va = int(row['destination_va'], 16)
            for match in re.finditer(rb'[\x20-\x7e\t]{5,}', data):
                strings.append(dict(address=hex(va + match.start()), segment=row['filename'],
                                    text=match.group().decode('ascii')))
            decoded, skipped = 0, 0
            with (out / (row['filename'] + '.c64x.asm')).open('w') as target:
                target.write('; Exploratory Capstone C64x decode, includes DATA, not a recovered function map.\n')
                for ins in decoder.disasm(data, va):
                    target.write(f'{ins.address:08x}: {ins.bytes.hex():16} {ins.mnemonic} {ins.op_str}\n')
                    if ins.id:
                        decoded += ins.size
                    else:
                        skipped += ins.size
            dis_stats.append(dict(segment=row['filename'], decoded_bytes=decoded, skipped_bytes=skipped,
                                  unconsumed_bytes=len(data) - decoded - skipped))
        (out / 'strings.json').write_text(json.dumps(strings, indent=2) + '\n')
        (out / 'strings.txt').write_text('\n'.join(f"{r['address']} {r['text']}" for r in strings) + '\n')
        report = dict(input=str(args.input), elf_sha256=EXPECTED, firmware='RML16AI_Rack_13731',
                      platform=platform.platform(), capstone=cs.__version__, script_sha256=sha(Path(__file__).read_bytes()),
                      loader=identity(boot), segments=rows, total_payload_bytes=sum(r['size'] for r in rows),
                      arm_literal_reads=literal_reads, disassembly=dis_stats,
                      synthetic_elf=dict(sha256=sha(image), machine=140, entry='0x80000000',
                                         entry_basis='DSPBOOTADD write, not original ELF entry',
                                         permissions='synthetic RWX; original permissions unknown'),
                      scope='offline extraction; no DSP execution, hardware validation or C++ readiness claimed')
        # Verify independent ELF reader sees every exact PT_LOAD payload.
        with (out / 'dsp-load-image.synthetic.elf').open('rb') as synthetic:
            loads = list(ELFFile(synthetic).iter_segments())
            assert len(loads) == len(rows)
            for load, row in zip(loads, rows):
                assert load['p_vaddr'] == int(row['destination_va'], 16)
                assert sha(load.data()) == row['sha256']
        report['synthetic_elf']['payload_roundtrip_verified'] = True
        (out / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({k: report[k] for k in ('elf_sha256', 'total_payload_bytes', 'scope')}))
        for row in rows:
            print(row['filename'], row['source_va'], '->', row['destination_va'], row['size'], row['sha256'])
        print('printable strings:', len(strings))


if __name__ == '__main__':
    main()
