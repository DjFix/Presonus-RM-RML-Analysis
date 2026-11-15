#!/usr/bin/env python3
"""Execute verified original start; downstream tail provider requires expanded body."""
import hashlib, json, struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=Path(__file__).resolve().parents[4]
ELF_SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
START=0x524fc

def execute():
    bindings=json.loads((ROOT/'temp/recovery-work/rolling10x10-20261114/READ_INPUTS-rolling10_panel.json').read_text())
    elfpath=Path(bindings['rootfs/RML16AI_Rack_13731/home/root/mixer']['frozen_read_path'])
    data=elfpath.read_bytes()
    assert hashlib.sha256(data).hexdigest()==ELF_SHA
    with elfpath.open('rb') as f:
        elf=ELFFile(f); sec=elf.get_section(12)
        offset=sec['sh_offset']+START-sec['sh_addr']
        body=data[offset:offset+20]
        assert hashlib.sha256(body).hexdigest()=='916cbf8ab21f18283895d4913ef51613ecab7695dcd43245171ec2ab6c675bda'
    def read_range(address,size,expected):
        with elfpath.open('rb') as f:
            elf=ELFFile(f)
            sec=next(s for s in elf.iter_sections() if s['sh_type']!='SHT_NOBITS' and s['sh_addr']<=address and address+size<=s['sh_addr']+s['sh_size'])
            off=sec['sh_offset']+address-sec['sh_addr']
            b=data[off:off+size]
        assert hashlib.sha256(b).hexdigest()==expected
        return b,{'address':address,'size':size,'section':sec.name,'file_offset':off,'sha256':expected}
    activate,activate_range=read_range(0x524e0,28,'2620db362d0ff0f5f2e0561bc25ca9ebfc78c4593bea0467637e70fbd9a0200c')
    provider,provider_range=read_range(0x52bfc,16,'60cf0e8b51daf6a0ce5a5eea619d9a3e219bccf7fa26c553983e5baf3012cfad')
    table,table_range=read_range(3250376,116,'e620c890984a198c2542229f60ffa3fc04ee0a67b3acd2a790bbecb35d85b4b8')
    ctors=[]
    for addr,digest in [(0x52a14,'b766b57703204a441b0fa6a9a323bacb678eb7c3d8e7c36f84c8d4f975912d5a'),(0x52ae0,'68351853593c84c531f329b35aa0b4bc515f0b4167535aa2e51b2dc391b5180d')]:
        ctor,rr=read_range(addr,204,digest)
        # Execute ONLY the no-call vptr-install slice after real Core ctor site,
        # before DelayTimer. This is not full constructor/provider execution.
        u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x50000,0x10000);u.mem_write(addr,ctor)
        u.mem_map(0x200000,0x1000);u.reg_write(UC_ARM_REG_R6,0x200000)
        u.reg_write(UC_ARM_REG_R4,0x22222222);u.reg_write(UC_ARM_REG_R5,0x55555555)
        writes=[]
        u.hook_add(UC_HOOK_MEM_WRITE,lambda uc,access,a,z,v,_:writes.append([a,z,v]))
        u.emu_start(addr+0x20,addr+0x4c,count=32)
        vptr=struct.unpack('<I',u.mem_read(0x200000,4))[0]
        assert vptr==3250376+8
        target=struct.unpack_from('<I',table,8+0x38)[0]
        assert target==0x52bfc
        ctors.append({'range':rr,'executed_slice':[addr+0x20,addr+0x4c],'vptr':vptr,'slot38_target':target,'writes':writes,'exclusion':'No Core or timer calls executed; not full constructor lifecycle validation.'})
    provider_cases=[]
    for i in range(8):
        u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x50000,0x10000)
        for a,b in [(START,body),(0x524e0,activate),(0x52bfc,provider)]:u.mem_write(a,b)
        u.mem_map(0x319000,0x1000);u.mem_write(3250376,table)
        u.mem_map(0x200000,0x1000);obj=0x200000
        before=struct.pack('<I',3250376+8)+bytes([0x55 if i&1 else 0xaa])*252
        u.mem_write(obj,before);u.mem_map(0x300000,0x10000)
        sp=0x308000;u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_FP,0x76543210)
        u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_LR,0x60000)
        pcs=[];writes=[]
        u.hook_add(UC_HOOK_CODE,lambda uc,pc,z,_:pcs.append(pc))
        u.hook_add(UC_HOOK_MEM_WRITE,lambda uc,access,a,z,v,_:writes.append([a,z,v]))
        u.emu_start(START,0x60000,count=64)
        assert pcs.count(0x524e0)==1 and pcs.count(0x52bfc)==1 and u.reg_read(UC_ARM_REG_PC)==0x60000
        assert u.reg_read(UC_ARM_REG_SP)==sp and u.reg_read(UC_ARM_REG_FP)==0x76543210
        assert bytes(u.mem_read(obj,len(before)))==before
        assert len(writes)==12 and all(sp-32<=x[0]<sp for x in writes)
        provider_cases.append({'index':i,'object_fill':0x55 if i&1 else 0xaa,'activate_calls':pcs.count(0x524e0),'slot38_calls':pcs.count(0x52bfc),'pcs':pcs,'writes':writes,'object_unchanged':True,'returned':True})
    cases=[]
    for obj in [0,0x200000,0x200080,0xffffffff]:
      for sentinel in [0,0x12345678,0xffffffff]:
        u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x50000,0x10000);u.mem_write(START,body)
        u.mem_map(0x300000,0x10000)
        sp=0x308000;u.reg_write(UC_ARM_REG_SP,sp)
        for reg in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_R8,UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_FP]:u.reg_write(reg,sentinel)
        u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_LR,0x60000)
        writes=[];pcs=[];tail=[]
        def code(uc,pc,size,_):
          pcs.append(pc)
          if pc==0x524e0:
            tail.append({'address':pc,'this':uc.reg_read(UC_ARM_REG_R0),'sp':uc.reg_read(UC_ARM_REG_SP),'lr':uc.reg_read(UC_ARM_REG_LR),'fp':uc.reg_read(UC_ARM_REG_FP)})
            uc.emu_stop()
        u.hook_add(UC_HOOK_CODE,code)
        u.hook_add(UC_HOOK_MEM_WRITE,lambda uc,access,addr,size,value,_:writes.append([addr,size,value]))
        u.emu_start(START,0x60000,count=20)
        assert len(tail)==1 and tail[0]['this']==obj and tail[0]['sp']==sp and tail[0]['lr']==0x60000 and tail[0]['fp']==sentinel
        assert len(writes)==4 and all(sp-16<=x[0]<sp for x in writes)
        cases.append({'this':obj,'sentinel':sentinel,'tail':tail,'pcs':pcs,'stack_writes':writes})
    return {'elf_sha256':ELF_SHA,'range':{'address':START,'size':20,'section':12,'file_offset':offset,'sha256':hashlib.sha256(body).hexdigest()},'wrapper_cases':cases,'provider_ranges':[activate_range,provider_range,table_range],'constructor_address_point_slices':ctors,'provider_cases':provider_cases,'limitations':['Concrete base PanelComponent table only; derived slot implementations excluded.','Opaque/null this wrapper-only cases stop before activateAll; invalid object behavior excluded.','No Core native body executed. Constructor slices confirm vptr installation, not complete construction.']}
if __name__=='__main__':
    print(json.dumps(execute(),indent=2))
