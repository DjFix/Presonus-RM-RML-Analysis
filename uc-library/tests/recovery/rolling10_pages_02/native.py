"""Independent original non-Core ARM execution; no external substitutions."""
import hashlib,json,random
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
ROOT=Path(__file__).resolve().parents[4]
TASK=Path(__file__).parent.name
PACKET=ROOT/'temp/recovery-work/rolling10x10-20261114/prepared05/packets'/TASK
READS=json.loads((ROOT/'temp/recovery-work/rolling10x10-20261114/READ_INPUTS-rolling10_pages.json').read_text())
def generate():
 t=json.loads((PACKET/'request.json').read_text())['targets'][0]
 elfpath=Path(READS['rootfs/CS18_v13840/home/root/surface']['frozen_read_path'])
 assert hashlib.sha256(elfpath.read_bytes()).hexdigest()==t['original_elf_sha256']
 with elfpath.open('rb') as f:
  e=ELFFile(f);s=e.get_section(12);sym=e.get_section_by_name('.symtab').get_symbol_by_name(t['mangled'])[0]
  assert (sym['st_value'],sym['st_size'],sym['st_shndx'])==(t['address'],t['size'],12)
  offset=s['sh_offset']+t['address']-s['sh_addr'];f.seek(offset);body=f.read(t['size'])
 rng=random.Random(301)
 ids=[0,1,-1,-2147483648,2147483647,1835102288,1348560741,1131375984,1835102287,1835102289]+[rng.randint(-2147483648,2147483647) for _ in range(40)]
 cases=[]
 for obj in (0x1000000,0x1000200):
  for cid in ids:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);address=t['address'];u.mem_map(address&~4095,4096);u.mem_write(address,body)
   u.mem_map(0x1000000,4096);u.mem_map(0x2000000,65536)
   state=bytes(rng.getrandbits(8) for _ in range(4096));u.mem_write(0x1000000,state)
   u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,cid&0xffffffff);u.reg_write(UC_ARM_REG_SP,0x2008000);u.reg_write(UC_ARM_REG_LR,0x1000800)
   pcs=[];writes=[]
   u.hook_add(UC_HOOK_CODE,lambda uc,a,n,x:pcs.append(a))
   u.hook_add(UC_HOOK_MEM_WRITE,lambda uc,k,a,n,v,x:writes.append([a,n,v]))
   u.emu_start(address,0x1000800,count=30)
   assert u.reg_read(UC_ARM_REG_PC)==0x1000800
   assert bytes(u.mem_read(0x1000000,4096))==state
   assert all(address<=pc<address+52 for pc in pcs)
   assert all(0x2007ff0<=a<0x2008000 for a,n,v in writes)
   ret=u.reg_read(UC_ARM_REG_R0);assert ret in (0,obj)
   cases.append(dict(input=cid,object=obj,returns_self=ret==obj,return_word=ret,executed=pcs,stack_writes=writes,application_writes=[],external_calls=[]))
 return dict(elf_sha256=t['original_elf_sha256'],mangled=t['mangled'],address=t['address'],size=t['size'],section=12,file_offset=offset,range_sha256=hashlib.sha256(body).hexdigest(),unicorn_version=unicorn.__version__,cases=cases,domain='100 finite signed class-ID cases on two caller-owned objects; branch paths, object immutability, stack-only writes, no external execution')
if __name__=='__main__':
 import sys
 Path(sys.argv[1]).write_text(json.dumps(generate(),indent=2)+'\n')
