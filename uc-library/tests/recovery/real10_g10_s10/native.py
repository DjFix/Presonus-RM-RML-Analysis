"""Independent original D0 execution. Runtime delete is an explicit call boundary."""
import hashlib,json,struct,sys
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
ELF=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261116/prepared-main/snapshot/rootfs/CS18_v13840/home/root/surface')
def observe():
 data=ELF.read_bytes(); assert hashlib.sha256(data).hexdigest()=='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
 with ELF.open('rb') as f:
  e=ELFFile(f);s=e.get_section(12); offset=783760-int(s['sh_addr'])+int(s['sh_offset']);assert offset==0xb7590
  body=data[offset:offset+44]; assert hashlib.sha256(body).hexdigest()=='9cb2fe4e9aa4d461895d2005530b7e73624655189fbde6c2444951a442a23aad'
 rows=[]
 for i in range(8):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x300000);u.mem_write(783760,body)
  u.mem_map(0x400000,0x20000);obj=0x400100+0x100*i;stop=0x410000
  u.mem_write(obj,struct.pack('<II',0xabcdef00+i,0x12345678))
  u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_SP,0x40f000);u.reg_write(UC_ARM_REG_LR,stop)
  calls=[];writes=[]
  def code(uc,a,size,_):
   if a==0xad5c:
    calls.append(uc.reg_read(UC_ARM_REG_R0));uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   elif a==stop:uc.emu_stop()
  def write(uc,access,a,size,value,_):
   if obj<=a<obj+8:writes.append([a-obj,size,value])
  u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write);u.emu_start(783760,stop,count=100)
  assert calls==[obj] and writes==[[0,4,0x1ea828]]
  assert struct.unpack('<I',u.mem_read(obj+4,4))[0]==0x12345678
  rows.append({'delete_calls':1,'vptr_write':writes,'returned_receiver':u.reg_read(UC_ARM_REG_R0)==obj,'adjacent_preserved':True})
 return {'elf_sha256':hashlib.sha256(data).hexdigest(),'address':783760,'size':44,'section':'.text','offset':offset,'range_sha256':hashlib.sha256(body).hexdigest(),'cases':rows,'domain':'Eight distinct nonnull writable receiver addresses; vptr reset, unsized delete(receiver), receiver return and adjacent sentinel preserved. Imported delete hook records boundary only; host runtime deallocation observed separately.'}
if __name__=='__main__':
 Path(sys.argv[1]).write_text(json.dumps(observe(),indent=2)+'\n')
