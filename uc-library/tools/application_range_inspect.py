#!/usr/bin/env python3
"""Verify and disassemble one selected Presonus application range, not Core."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
from capstone.arm import ARM_OP_IMM, ARM_OP_MEM, ARM_REG_PC, ARM_INS_LDR, ARM_INS_BL, ARM_INS_BLX
from elftools.elf.elffile import ELFFile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(default_mangled=None,default_role='client',evidence_group='application-static'):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository',type=Path)
    parser.add_argument('--mangled',default=default_mangled,required=default_mangled is None)
    parser.add_argument('--role',choices=('client','server'),default=default_role)
    args=parser.parse_args()
    repo=args.repository.resolve()
    lib=repo/'uc-library'
    scope=lib/'recovered-all'/args.role
    manifest=json.loads((scope/'manifest.json').read_text())
    symbols=json.loads((scope/'symbols.json').read_text())
    assert args.mangled=='main' or args.mangled.startswith(('_ZN8Presonus','_ZNK8Presonus')), 'Presonus application scope only; no Core body inspection'
    selected=[row for row in symbols if row.get('mangled')==args.mangled and row.get('kind')=='STT_FUNC']
    assert len(selected)==1
    row=selected[0]
    binary=(repo/manifest['path']).resolve()
    assert binary.is_relative_to(repo)
    identities={'client':'304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0',
                'server':'9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'}
    assert manifest['sha256']==identities[args.role]
    assert sha(binary)==manifest['sha256']
    with binary.open('rb') as stream:
        elf=ELFFile(stream)
        section=elf.get_section(row['section'])
        assert section['sh_type']!='SHT_NOBITS'
        offset=section['sh_offset']+row['address']-section['sh_addr']
        assert offset==row['file_offset']
        assert section['sh_addr']<=row['address'] and row['address']+row['size']<=section['sh_addr']+section['sh_size']
        read_only_data=[(part['sh_addr'],part['sh_offset'],part['sh_size'])
                        for part in elf.iter_sections() if part.name.startswith('.rodata')]
    image=binary.read_bytes()
    raw=image[offset:offset+row['size']]
    assert raw==(scope/row['export_path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==row['sha256']
    by_address={}
    for symbol in symbols:
        if symbol.get('kind')=='STT_FUNC':
            by_address.setdefault(symbol['address'],[]).append(symbol.get('demangled',symbol['mangled']))
    engine=Cs(CS_ARCH_ARM,CS_MODE_ARM)
    engine.detail=True
    engine.skipdata=True
    instructions=[]
    for instruction in engine.disasm(raw,row['address']):
        item=dict(address=instruction.address,bytes=instruction.bytes.hex(),
                  mnemonic=instruction.mnemonic,operands=instruction.op_str)
        if instruction.id==ARM_INS_LDR and len(instruction.operands)>1:
            operand=instruction.operands[1]
            if operand.type==ARM_OP_MEM and operand.mem.base==ARM_REG_PC:
                literal=instruction.address+8+operand.mem.disp
                if row['address']<=literal and literal+4<=row['address']+row['size']:
                    at=literal-row['address']
                    item.update(literal_address=literal,literal_word=int.from_bytes(raw[at:at+4],'little'))
                    for base,file_base,size in read_only_data:
                        if base<=item['literal_word']<base+size:
                            position=file_base+item['literal_word']-base
                            data=image[position:min(position+256,file_base+size)]
                            text=data.split(b'\0',1)[0]
                            if b'\0' in data and text and all(value in (9,10,13) or 32<=value<127 for value in text):
                                item['referenced_rodata_text']=text.decode('ascii')
        if instruction.id in (ARM_INS_BL,ARM_INS_BLX) and instruction.operands and instruction.operands[0].type==ARM_OP_IMM:
            target=instruction.operands[0].imm
            item.update(call_target=target,call_symbols=by_address.get(target,[]))
        instructions.append(item)
    assert sum(len(bytes.fromhex(item['bytes'])) for item in instructions)==row['size']
    literal_addresses={item['literal_address'] for item in instructions if 'literal_address' in item}
    for item in instructions:
        item['literal_pool_word']=item['address'] in literal_addresses
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    out=repo/'evidence/recovery/2026-10-27'/evidence_group/stamp
    out.mkdir(parents=True,exist_ok=False)
    (out/'instructions.json').write_text(json.dumps(instructions,indent=2)+'\n')
    (out/'instructions.txt').write_text(''.join(
        f"{item['address']:08x}  {item['mnemonic']:8} {item['operands']}"+
        (f"  ; literal=0x{item['literal_word']:08x}" if 'literal_word' in item else '')+
        ('  ; EMBEDDED DATA' if item['literal_pool_word'] else '')+
        (('  ; rodata='+repr(item['referenced_rodata_text'])) if 'referenced_rodata_text' in item else '')+
        (('  ; '+repr(item['call_symbols'])) if 'call_target' in item else '')+'\n'
        for item in instructions))
    (out/'application-range.bin').write_bytes(raw)
    proof=dict(original_symbol=row,role=args.role,original_elf_sha256=manifest['sha256'],
        source_range_verified=True,instruction_count=len(instructions),
        core_bodies_decoded=False,original_code_executed=False,
        literal_pool_caveat='Range may contain embedded literal words; disassembly is inspection evidence, not executed-instruction coverage.',
        hardware_accessed=False,semantic_reconstruction_verified=False,
        tool_sha256=sha(Path(__file__)),
        evidence={p.name:sha(p) for p in out.iterdir() if p.is_file()})
    (out/'validation.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps(dict(output=str(out.relative_to(repo)),instructions=len(instructions),
                          validation_sha256=sha(out/'validation.json'))))


if __name__=='__main__':
    main()
