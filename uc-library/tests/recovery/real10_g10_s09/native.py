"""Original ARM application cleanup; Core destructor and delete are observed boundaries."""
import hashlib,json,struct,sys
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
ELF=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261116/prepared-main/snapshot/rootfs/CS18_v13840/home/root/surface')
ADDRESS=412800
def observe():
 data=ELF.read_bytes();sha=hashlib.sha256(data).hexdigest();assert sha=='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
 with ELF.open('rb') as f:
  sec=ELFFile(f).get_section(12);offset=ADDRESS-int(sec['sh_addr'])+int(sec['sh_offset'])
 body=data[offset:offset+72];assert hashlib.sha256(body).hexdigest()=='ec7bcb949016f505a011587fbb022975ba9fec2bcc51fd1e70fe2146cda4323c';rows=[]
 for count in [0,1,3,8]:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x300000);u.mem_write(ADDRESS,body);u.mem_map(0x400000,0x20000)
  obj=0x400100;items=0x401000;stop=0x410000;entries=[0x402000+32*i for i in range(count)]
  u.mem_write(obj,struct.pack('<III',0x12345678,items,count));u.mem_write(items,b''.join(struct.pack('<I',x) for x in entries));calls=[]
  u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_SP,0x40f000);u.reg_write(UC_ARM_REG_LR,stop)
  def hook(uc,a,size,_):
   if a in [0xad5c,0x6a104]:
    calls.append([a,uc.reg_read(UC_ARM_REG_R0)]);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,hook);u.emu_start(ADDRESS,stop,count=1000)
  assert calls==[[0xad5c,x] for x in entries]+[[0x6a104,obj]]
  assert bytes(u.mem_read(obj,12))==struct.pack('<III',0x12345678,items,count)
  rows.append({'count':count,'delete_arguments':entries,'core_vector_receiver':obj,'returned_receiver':u.reg_read(UC_ARM_REG_R0)==obj,'memory_unchanged_before_provider':True})
 return {'elf_sha256':sha,'address':ADDRESS,'size':72,'section':12,'offset':offset,'range_sha256':hashlib.sha256(body).hexdigest(),'cases':rows,'domain':'Empty and 1/3/8 distinct owned scalar allocations: ordered delete(element), then Core Vector destructor(receiver), receiver return; native Core/delete bodies stubbed as explicit observed boundaries. Actual pinned template Core Vector array release and actual scalar deletes independently execute in C++.'}
if __name__=='__main__':Path(sys.argv[1]).write_text(json.dumps(observe(),indent=2)+'\n')
