"""Private-memory execution of exact ARM app body; providers intercepted, never Core firmware."""
import hashlib,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ELF=Path('/home/rs/projects/opencs/ai-line-analysis/rootfs/CS18_v13840/home/root/surface')
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
NAME='_ZNK8Presonus7Surface16MappingComponent22getBankScrollingOffsetEv'
ADDRESS=519672
SIZE=48
RANGE_SHA='1289ce06c741e4340ebf74c1fed59942e10f12f8c1e750e5c085c8d87e425ae9'
KIND='mapping_bank'
def generate():
 data=ELF.read_bytes();assert hashlib.sha256(data).hexdigest()==SHA
 with ELF.open('rb') as f:
  elf=ELFFile(f);symbol=next(s for s in elf.get_section_by_name('.symtab').iter_symbols() if s.name==NAME)
  assert symbol['st_value']==ADDRESS and symbol['st_size']==SIZE
  sec=elf.get_section(symbol['st_shndx']);offset=sec['sh_offset']+ADDRESS-sec['sh_addr'];body=data[offset:offset+SIZE]
 assert hashlib.sha256(body).hexdigest()==RANGE_SHA
 values=[-2147483648,-99,-1,0,1,2,3,4,134217727,134217728,268435455,268435456,2147483647] if KIND=='mapping_bank' else [0]
 cases=[]
 for value in values:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x1000000);u.mem_write(ADDRESS,body)
  obj=0x400000;vtable=0x410000;provider=0xe00000;stop=0xf00000
  u.mem_write(obj,struct.pack('<I',vtable));u.mem_write(vtable+0x34,struct.pack('<I',provider))
  trace=[];writes=[];sites=[]
  def hook(u,a,size,user):
   if a==stop:u.emu_stop();return
   if ADDRESS<=a<ADDRESS+SIZE:sites.append(a);return
   assert u.reg_read(UC_ARM_REG_R0)==obj
   if KIND=='mapping_bank':
    assert a==provider
    args=[u.reg_read(UC_ARM_REG_R1),u.reg_read(UC_ARM_REG_R2)];assert args==[0,3]
    trace.append(['getRadioValue',*args]);u.reg_write(UC_ARM_REG_R0,value&0xffffffff)
   else:
    assert a in [0x11a74c,0xa3da0],hex(a)
    trace.append(['Core::Portable::Component::onIdle' if a==0x11a74c else 'checkNetworkScanning'])
    # Clobber call-volatile r0 after Core to prove original restores receiver.
    if a==0x11a74c:u.reg_write(UC_ARM_REG_R0,0xdeadbeef)
   u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  def write(u,access,a,size,value,user):writes.append([a,size,value])
  u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
  for reg,val in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_SP,0x8ff000),(UC_ARM_REG_LR,stop)]:u.reg_write(reg,val)
  u.emu_start(ADDRESS,stop,count=1000);assert u.reg_read(UC_ARM_REG_PC)==stop
  assert all(0x8fe000<=w[0]<0x8ff000 for w in writes)
  cases.append(dict(input=value,result=u.reg_read(UC_ARM_REG_R0),trace=trace,sites=sites,stack_writes=writes))
 return dict(elf_sha256=SHA,mangled=NAME,address=ADDRESS,size=SIZE,section='.text',section_index=12,file_offset=offset,range_sha256=RANGE_SHA,cases=cases,provider_boundary='virtual getRadioValue supplied signed int32; Wifi Core idle and existing scan intercepted; no Core instructions, hardware or syscalls executed')
if __name__=='__main__':
 import sys
 Path(sys.argv[1]).write_text(json.dumps(generate(),indent=2)+'\n')
