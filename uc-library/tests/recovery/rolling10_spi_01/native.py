import hashlib,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ELF=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared05/snapshot/rootfs/RML16AI_Rack_13731/home/root/mixer')
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
NAME='_ZN8Presonus5Panel15SPIControlGroup9broadcastEPNS0_7ControlE'
def generate():
 data=ELF.read_bytes(); assert hashlib.sha256(data).hexdigest()==SHA
 with ELF.open('rb') as f:
  e=ELFFile(f);s=next(x for x in e.get_section_by_name('.symtab').iter_symbols() if x.name==NAME);sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr']
  body=data[off:off+s['st_size']]
  assert (s['st_value'],s['st_size'],off,hashlib.sha256(body).hexdigest())==(709528,28,676760,'916b313686ad22488f02791c9f7f7e4abfc64aeea466ae4ee991367358780b6a')
 cases=[]
 for initial in range(256):
  for pointer in [0,1,0x500000,0xffffffff]:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0xa0000,0x10000);u.mem_write(s['st_value'],body);u.mem_map(0x400000,0x2000);u.mem_map(0x800000,0x2000);u.mem_map(0xf00000,0x1000)
   before=bytearray([0xa5]*0x800);before[0x426]=initial;u.mem_write(0x400000,bytes(before));sites=[];writes=[]
   def code(u,a,n,_):
    assert s['st_value']<=a<s['st_value']+len(body),hex(a)
    sites.append(a)
   u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,lambda u,k,a,n,v,_:writes.append([a,n,v]))
   for r,v in [(UC_ARM_REG_R0,0x400000),(UC_ARM_REG_R1,pointer),(UC_ARM_REG_SP,0x801000),(UC_ARM_REG_LR,0xf00000)]:u.reg_write(r,v)
   u.emu_start(s['st_value'],0xf00000,count=30);assert u.reg_read(UC_ARM_REG_PC)==0xf00000
   after=bytes(u.mem_read(0x400000,0x800));changed=[i for i,(a,b) in enumerate(zip(before,after)) if a!=b]
   cases.append(dict(initial=initial,pointer=pointer,result=u.reg_read(UC_ARM_REG_R0),dirty=after[0x426],changed=changed,writes=[w for w in writes if not 0x800000<=w[0]<0x802000],sites=sites))
 return dict(elf_sha256=SHA,ranges=[dict(mangled=NAME,address=s['st_value'],size=s['st_size'],section=sec.name,file_offset=off,sha256=hashlib.sha256(body).hexdigest())],cases=cases,external_calls=[],domain='256 byte states x four opaque pointer values; valid mapped caller-owned object; complete object sentinel and writes recorded; no external calls')
if __name__=='__main__':
 import sys
 Path(sys.argv[1]).write_text(json.dumps(generate(),indent=2)+'\n')
