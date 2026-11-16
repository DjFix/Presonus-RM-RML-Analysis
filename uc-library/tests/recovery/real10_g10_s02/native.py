import hashlib,json,struct,sys
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
ELF=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261116/prepared-main/snapshot/rootfs/CS18_v13840/home/root/surface')
ADDRESS=408476
SIZE=184
DELETING=False
def observe():
 data=ELF.read_bytes();sha=hashlib.sha256(data).hexdigest();assert sha=='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
 with ELF.open('rb') as f:
  sec=ELFFile(f).get_section(12);offset=ADDRESS-int(sec['sh_addr'])+int(sec['sh_offset'])
 body=data[offset:offset+SIZE];assert hashlib.sha256(body).hexdigest()=='45643b3f2d99bb2f1f391e3e6cf50a2fd8b51ca9af615570d87127472f4281f1';rows=[]
 for n in [0,1,3]:
  for storage in [False,True]:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x300000);u.mem_write(ADDRESS,body);u.mem_map(0x400000,0x20000)
   obj=0x400100;items=0x401000;vtable=1683072;dispatch=406720;stop=0x410000;command=0x406000 if storage else 0
   put=lambda a,v:u.mem_write(a,struct.pack('<I',v))
   views=[0x402000+0x100*i for i in range(n)]+[0]
   for i,p in enumerate(views):
    put(items+4*i,p)
    if p:put(p,vtable)
   table=data[1650296:1650296+156];assert struct.unpack_from('<I',table,16)[0]==dispatch;u.mem_write(1683064,table);put(obj+0x30,items);put(obj+0x34,len(views));put(obj+0x40,command);put(0x269134,obj)
   u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_SP,0x40f000);u.reg_write(UC_ARM_REG_LR,stop);calls=[]
   def hook(uc,a,size,_):
    if a in [0xad5c,0x64588,dispatch]:
     calls.append([a,uc.reg_read(UC_ARM_REG_R0)]);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   u.hook_add(UC_HOOK_CODE,hook);u.emu_start(ADDRESS,stop,count=1000)
   expected=[[dispatch,p] for p in views if p]+[[0xad5c,command],[0x64588,obj+0x2c]]+([[0xad5c,obj]] if DELETING else [])
   assert calls==expected and struct.unpack('<I',u.mem_read(0x269134,4))[0]==0
   rows.append({'views':n,'storage':storage,'outer_delete':int(DELETING),'singleton_cleared':True,'calls':calls,'returned_receiver':u.reg_read(UC_ARM_REG_R0)==obj})
 return {'elf_sha256':sha,'address':ADDRESS,'size':SIZE,'section':12,'offset':offset,'range_sha256':hashlib.sha256(body).hexdigest(),'vtable':{'symbol':'_ZTVN8Presonus7LcdViewE','address':1683064,'size':156,'file_offset':1650296,'sha256':hashlib.sha256(table).hexdigest(),'address_point':1683072,'slot8_target':406720,'target_mangled':'_ZN8Presonus7LcdViewD0Ev','assumption':'Controlled native receiver uses this exact original primary vptr; no arbitrary dynamic type/layout claim.'},'cases':rows,'domain':'0/1/3 owned views plus a null slot, null/non-null command storage: ordered view virtual deleting-destructor calls, scalar command deletion, Core Vector cleanup, singleton clear and selected outer D0 deletion. Native call bodies are explicit boundaries; actual pinned Core RootView, container and forwarded global delete run independently in portable replay. Borrowed view stays live.'}
if __name__=='__main__':Path(sys.argv[1]).write_text(json.dumps(observe(),indent=2)+'\n')
