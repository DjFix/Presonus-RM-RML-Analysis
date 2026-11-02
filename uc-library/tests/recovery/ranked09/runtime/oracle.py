"""Offline original ARM execution only; no device or original process launch."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_R0, UC_ARM_REG_PC
from elftools.elf.elffile import ELFFile

PACKETS = Path('temp/recovery-work/ranked-trial-09-small01/batch02/packets')
ELF = Path('rootfs/RML16AI_Rack_13731/home/root/mixer')
SHA = '9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'

def native_ranges():
    data = ELF.read_bytes()
    assert hashlib.sha256(data).hexdigest() == SHA
    output=[]
    with ELF.open('rb') as stream:
        elf=ELFFile(stream)
        for i in range(1,6):
            packet=PACKETS/f'rank09_runtime_{i:02}'
            context=json.loads((packet/'native-context.json').read_text())
            body=next(iter(context['bodies'].values()))
            section=elf.get_section(body['section_index'])
            offset=int(section['sh_offset'])+body['address']-int(section['sh_addr'])
            assert offset == body['file_offset']
            raw=data[offset:offset+body['size']]
            assert len(raw)==body['size'] and hashlib.sha256(raw).hexdigest()==body['bytes_sha256']
            output.append(dict(body=body,raw=raw,packet=str(packet)))
    return output

def observe(target, link, field, seed, native):
    body=native['body']; address=body['address']
    uc=Uc(UC_ARCH_ARM,UC_MODE_ARM)
    pages={address&~4095,0x494000,0x49d000,0x200000,0x203000,0x204000,0x700000,0x701000,0x800000}
    for page in pages: uc.mem_map(page,4096)
    uc.mem_write(address,native['raw'])
    def put(a,v): uc.mem_write(a,struct.pack('<I',v))
    put(0x494054,0x200000); put(0x20001c,field); put(0x49db64,link)
    # Raw guest words are explicitly supplied fixtures, not inferred live values.
    if link:
        put(link+0x3dec,field);put(link+0x3df0,seed);put(link+0x3df4,field)
    uc.reg_write(UC_ARM_REG_SP,0x701000)
    uc.reg_write(UC_ARM_REG_LR,0x800000)
    uc.reg_write(UC_ARM_REG_R0,0x76543210)
    trace=[]
    def hook(uc,access,a,size,value,_):
        if a in {0x494054,0x20001c,0x49db64} or (link and link+0x3dec<=a<=link+0x3df4):
            assert size==4
            if access==unicorn.UC_MEM_READ:
                value=struct.unpack('<I',uc.mem_read(a,size))[0];kind='R'
            else: kind='W'
            trace.append([kind,a,value])
    uc.hook_add(UC_HOOK_MEM_READ|UC_HOOK_MEM_WRITE,hook)
    uc.emu_start(address,0x800000,count=100)
    assert uc.reg_read(UC_ARM_REG_PC)==0x800000
    result=uc.reg_read(UC_ARM_REG_R0)
    after=struct.unpack('<I',uc.mem_read(link+0x3df0,4))[0] if link else seed
    return dict(result=result if target!=4 else None,shutdown_word=after,trace=trace)

def generate():
    ranges=native_ranges();cases=[]
    fields=[0,1,0xffffffff,0x80000000,0x12345678,0xffffff50,0xbadb100d,0xbadb100c,0xbadb100e]
    for target,native in enumerate(ranges):
        for link in ([0x200000] if target==0 else [0,0x200000]):
            for j,field in enumerate(fields):
                seed=[0,1,0xffffffff][j%3]
                cases.append(dict(target=target,link=link,field=field,seed=seed,**observe(target,link,field,seed,native)))
    return dict(version=1,elf_sha256=SHA,unicorn_version=unicorn.__version__,ranges=[{k:v for k,v in x['body'].items() if k in ['address','size','section','section_index','file_offset','bytes_sha256']} for x in ranges],cases=cases)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);args=p.parse_args()
    Path(args.out).write_text(json.dumps(generate(),indent=2)+'\n')
