#!/usr/bin/env python3
"""Original application instructions only. Core interface dispatch is captured,
then its actual pinned source provider executes separately in Replay provider mode.
Stable non-reentrant binding makes application control independent of value effects.
"""
import hashlib,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=Path(__file__).resolve().parents[4]
TASK='rolling10_next100_about_store'
ELF_SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
SNAP=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared06/snapshot')
TYPED='temp/recovery-work/rolling10x10-20261114/selection/next100/parameter-setters01/native/098621a46438b36edb5648addec51d18b3adde063c71f31333b02352e99ecd7e.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def execute(present):
    evidence=SNAP/TYPED
    assert sha(evidence)=='0b20b970d2171f4d8ae470ac9c9f9d92e2745449b1c2fafd959874feb408ecdb'
    typed=json.loads(evidence.read_text())
    path=SNAP/'rootfs/RML16AI_Rack_13731/home/root/mixer';assert sha(path)==ELF_SHA
    ranges=[]
    def read(address,size,digest):
      with path.open('rb') as f:
        elf=ELFFile(f)
        sec=next(s for s in elf.iter_sections() if s['sh_type']!='SHT_NOBITS' and s['sh_addr']<=address and address+size<=s['sh_addr']+s['sh_size'])
        off=sec['sh_offset']+address-sec['sh_addr'];f.seek(off);body=f.read(size)
      assert hashlib.sha256(body).hexdigest()==digest
      ranges.append({'address':address,'size':size,'file_offset':off,'section':sec.name,'sha256':digest})
      return body
    body=read(0x6bf98,84,'70f5257f5eddf56077fb34f01b50f5fd060260b240d1087829a46d80c61751cb')
    vt=typed['verified_original_vtable'];table=read(vt['address'],vt['size'],vt['bytes_sha256'])
    assert struct.unpack_from('<I',table,8+0x58)[0]==1175964
    assert struct.unpack_from('<I',table,8+0x5c)[0]==1164760
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x60000,0x10000);u.mem_write(0x6bf98,body)
    u.mem_map(vt['address']&~4095,4096);u.mem_write(vt['address'],table)
    for a in [1175964,1164760]:
      u.mem_map(a&~4095,4096)
    u.mem_map(0x200000,4096);u.mem_map(0x210000,4096);u.mem_map(0x800000,65536)
    u.mem_write(0x200000,struct.pack('<I',vt['address']+8))
    u.mem_write(0x210000+0x124,struct.pack('<I',0x200000 if present else 0))
    before=bytes(u.mem_read(0x210000,0x200));param_before=bytes(u.mem_read(0x200000,0x100))
    u.reg_write(UC_ARM_REG_R0,0x210000);u.reg_write(UC_ARM_REG_SP,0x808000);u.reg_write(UC_ARM_REG_LR,0x70000);u.reg_write(UC_ARM_REG_R4,0xabcabc);u.reg_write(UC_ARM_REG_FP,0xfefefe)
    calls=[];pcs=[];writes=[]
    def code(uc,pc,size,_):
      pcs.append(pc)
      if pc in [1175964,1164760]:
        regs=[uc.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2]]
        assert regs[0]==0x200000
        if pc==1175964:
          value=struct.unpack('<f',struct.pack('<I',regs[1]))[0]
          calls.append({'target':pc,'operation':f'set:{value:.9g}:{regs[2]}','registers':regs})
        else:calls.append({'target':pc,'operation':f'reset:{regs[1]}','registers':regs})
        # Core instruction is never executed. Host provider mode independently
        # applies these captured operations, preserving actual source effects.
        uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,lambda uc,access,a,z,v,_:writes.append([a,z,v]))
    u.emu_start(0x6bf98,0x70000,count=64)
    assert u.reg_read(UC_ARM_REG_PC)==0x70000 and u.reg_read(UC_ARM_REG_SP)==0x808000
    assert u.reg_read(UC_ARM_REG_R4)==0xabcabc and u.reg_read(UC_ARM_REG_FP)==0xfefefe
    assert bytes(u.mem_read(0x210000,0x200))==before and bytes(u.mem_read(0x200000,0x100))==param_before
    assert len(writes)==5 and all(0x807fec<=w[0]<0x808000 for w in writes)
    assert len(calls)==(2 if present else 0)
    return {'present':present,'ranges':ranges,'calls':calls,'pcs':pcs,'stack_writes':writes,'application_object_unchanged':True,'core_execution':False,'source_provider_schedule':'Captured operations executed by real pinned NumericParam separately; stable binding/no value-dependent application branch; no original Core object layout/effects claimed.'}
if __name__=='__main__':print(json.dumps([execute(False),execute(True)],indent=2))
