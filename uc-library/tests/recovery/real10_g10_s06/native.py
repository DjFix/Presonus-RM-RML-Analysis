import hashlib,json,struct,sys
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
ELF=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261116/prepared-main/snapshot/rootfs/CS18_v13840/home/root/surface')
ADDRESS=707436
SIZE=172
DELETING=True
def observe():
 data=ELF.read_bytes();sha=hashlib.sha256(data).hexdigest();assert sha=='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
 with ELF.open('rb') as f:
  sec=ELFFile(f).get_section(12);offset=ADDRESS-int(sec['sh_addr'])+int(sec['sh_offset'])
 body=data[offset:offset+SIZE];assert hashlib.sha256(body).hexdigest()=='0b67b0c92a43dcdeb1c4a98f2e6e7fe055d792a0c68d7efb18072002acb0048c';rows=[]
 for n in [0,1,3]:
  for mode in [0,1,2]:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x300000);u.mem_write(ADDRESS,body);u.mem_map(0x400000,0x20000)
   obj=0x400100;stop=0x410000;u.mem_write(obj,b'\x5a'*256)
   put=lambda a,v:u.mem_write(a,struct.pack('<I',v))
   put(obj+0x8c,n);put(obj+0xa8,0 if mode==0 else 0x402000);put(obj+0xac,16 if mode else 0);put(obj+0xb4,int(mode==1))
   u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_SP,0x40f000);u.reg_write(UC_ARM_REG_LR,stop);calls=[];writes=[]
   def hook(uc,a,size,_):
    if a in [0xe5c24,0xacb3c,0x11b5e0,0xad5c]:
     calls.append([a,uc.reg_read(UC_ARM_REG_R0)]);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   def write(uc,access,a,size,value,_):
    if obj<=a<obj+256:writes.append([a-obj,size,value])
   u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write);u.emu_start(ADDRESS,stop,count=1000)
   expected=[[0xe5c24,obj+0xa0],[0xacb3c,obj+0x84],[0x11b5e0,obj]]+([[0xad5c,obj]] if DELETING else [])
   assert calls==expected;assert [x[0] for x in writes]==[4,156,0,152,156,152]
   rows.append({'records':n,'buffer_mode':mode,'outer_delete':int(DELETING),'calls':calls,'writes':writes,'returned_receiver':u.reg_read(UC_ARM_REG_R0)==obj})
 return {'elf_sha256':sha,'address':ADDRESS,'size':SIZE,'section':12,'offset':offset,'range_sha256':hashlib.sha256(body).hexdigest(),'cases':rows,'domain':'Nine valid receiver states:0/1/3 file records crossed with empty/owned/borrowed buffer. Exact app ARM Buffer(receiver+0xa0), Vector<WriteRecord>(receiver+0x84), Component(receiver) cleanup ordering and six dispatch-table writes; D0 actual outer-delete call separate. Provider bodies are explicit native call boundaries. Real pinned Buffer ownership, FileStream vector cleanup and Component child cleanup execute independently in C++, with actual forwarded core_free/fclose/delete observations and borrowed bytes/file preservation. No Core binary recovery.'}
if __name__=='__main__':Path(sys.argv[1]).write_text(json.dumps(observe(),indent=2)+'\n')
