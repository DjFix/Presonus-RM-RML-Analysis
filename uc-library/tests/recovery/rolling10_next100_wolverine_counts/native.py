import hashlib,json,random
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ELF=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared06/snapshot/rootfs/RML16AI_Rack_13731/home/root/mixer')
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
NAME='_ZN8Presonus5Panel23WolverinePanelRegistrar29getParamInfoListSizeFromGroupEi'
def generate():
 data=ELF.read_bytes();assert hashlib.sha256(data).hexdigest()==SHA
 with ELF.open('rb') as f:
  e=ELFFile(f);s=next(x for x in e.get_section_by_name('.symtab').iter_symbols() if x.name==NAME);sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];body=data[off:off+s['st_size']];assert (s['st_value'],s['st_size'],hashlib.sha256(body).hexdigest())==(504308,120,'5331f2082cbd17747513ded4f63f86b9ef413e7a904399aec1b3cd3e95a1a072')
 cases=[];rng=random.Random(610)
 inputs=list(range(-32,65))+[-2147483648,2147483647]+[rng.randrange(-2147483648,2147483648) for _ in range(512)]
 for value in inputs:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x70000,0x10000);u.mem_write(s['st_value'],body);u.mem_map(0x800000,0x2000);u.mem_map(0x400000,0x1000);u.mem_write(0x400000,b'\xa5'*0x1000);u.mem_map(0xf00000,0x1000);sites=[];writes=[]
  def hook(u,a,n,_):
   assert s['st_value']<=a<s['st_value']+s['st_size'],hex(a)
   sites.append(a)
  u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,lambda u,k,a,n,v,_:writes.append([a,n,v]))
  for reg,val in [(UC_ARM_REG_R0,0x400000),(UC_ARM_REG_R1,value&0xffffffff),(UC_ARM_REG_SP,0x801000),(UC_ARM_REG_LR,0xf00000),(UC_ARM_REG_R11,0x12345678)]:u.reg_write(reg,val)
  u.emu_start(s['st_value'],0xf00000,count=40);assert u.reg_read(UC_ARM_REG_PC)==0xf00000;assert u.reg_read(UC_ARM_REG_SP)==0x801000 and u.reg_read(UC_ARM_REG_R11)==0x12345678
  assert bytes(u.mem_read(0x400000,0x1000))==b'\xa5'*0x1000;assert all(0x800000<=w[0]<0x801000 for w in writes)
  cases.append(dict(stdin=str(value),stdout=str(u.reg_read(UC_ARM_REG_R0)),sites=sites,nonstack_writes=[]))
 return dict(elf_sha256=SHA,ranges=[dict(mangled=NAME,address=s['st_value'],size=s['st_size'],section=sec.name,file_offset=off,sha256=hashlib.sha256(body).hexdigest())],cases=cases,external_calls=[])
if __name__=='__main__':
 import sys
 Path(sys.argv[1]).write_text(json.dumps(generate(),indent=2)+'\n')
