"""Independent whole-body ARM oracle; intercept rand and positive virtual sink only."""
import hashlib,json,ctypes,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
CONTEXT='temp/recovery-work/rolling-c001-20261124/packeting/sqlite-cycle02/mackie_queries_sol61/NATIVE-CONTEXT.json'
def execute(original,identity,raw,fill):
    elfpath=Path(original['elf_path'])
    assert hashlib.sha256(elfpath.read_bytes()).hexdigest()==original['elf']
    with elfpath.open('rb') as f:
        e=ELFFile(f); sec=e.get_section(original['section']); offset=original['address']-sec['sh_addr']; body=sec.data()[offset:offset+original['size']]
        assert sec['sh_offset']+offset==original['file_offset']
        assert hashlib.sha256(body).hexdigest()==original['range_sha256']
        provider=sec.data()[0xc0480-sec['sh_addr']:0xc04b0-sec['sh_addr']]
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x100000);u.mem_write(original['address'],body);u.mem_write(0xc0480,provider)
    u.mem_map(0x200000,0x20000);u.mem_map(0x300000,0x20000)
    u.mem_write(0x300000,bytes([fill])*0x20000)
    obj=0x200000;sink=0x210000;vtable=0x210100;boundary=0x90000;stop=0x90010
    u.mem_write(obj+0xaec,bytes(identity));u.mem_write(obj+0xaf4,b'\xaa'*4)
    u.mem_write(obj+0xae0,struct.pack('<I',sink));u.mem_write(sink,struct.pack('<I',vtable));u.mem_write(vtable,struct.pack('<I',boundary))
    u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_SP,0x310000);u.reg_write(UC_ARM_REG_LR,stop)
    events=[];sent=[];calls=0
    def hook(uc,addr,size,data):
        nonlocal calls
        if addr==0xa930:
            assert calls<4;uc.reg_write(UC_ARM_REG_R0,raw[calls]);events.append('rand');calls+=1;uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
        elif addr==boundary:
            assert uc.reg_read(UC_ARM_REG_R0)==sink
            sent.append({'bytes':list(uc.mem_read(uc.reg_read(UC_ARM_REG_R1),uc.reg_read(UC_ARM_REG_R2))),'port':uc.reg_read(UC_ARM_REG_R3)})
            events.append('send');uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
        elif addr==stop:uc.emu_stop()
    u.hook_add(UC_HOOK_CODE,hook);u.emu_start(original['address'],stop+4,count=1000)
    assert calls==4 and events==['rand']*4+['send'] and len(sent)==1
    return {'challenge':list(u.mem_read(obj+0xaf4,4)),'sent':sent,'events':events}
def generate():
    d=json.loads(Path(CONTEXT).read_text()); libc=ctypes.CDLL(None); raws=[[0]*4,[127,128,255,2147483647],[1,2,3,4]]
    for seed in [1,7,12345]:
        libc.srand(seed);raws.append([libc.rand() for _ in range(4)])
    out=[]
    for n,item in enumerate(d['originals']):
        for identity in [[0]*8,[255,128,127,0,254,1,129,255],list(range(8))]:
            for index,raw in enumerate(raws):
                result=execute(item['original'],identity,raw,0);assert result==execute(item['original'],identity,raw,0xa5)
                out.append({'alternative':n==0,'identity':identity,'raw':raw,'seed':None if index<3 else [1,7,12345][index-3],'expected':result})
    return {'cases':out,'originals':[x['original'] for x in d['originals']],'native_provider_range':{'address':0xc0480,'size':48},'uninitialized_stack_independence':'00 and a5 stack fill produce identical complete outgoing bytes'}
if __name__=='__main__':
    import sys
    result=generate()
    if '--verify' in sys.argv:assert result==json.loads(Path('uc-library/tests/recovery/mackie_host_queries/fixtures.json').read_text())
    else:Path('uc-library/tests/recovery/mackie_host_queries/fixtures.json').write_text(json.dumps(result,indent=2)+'\n')
    print('native full-body executions',len(result['cases'])*2)
