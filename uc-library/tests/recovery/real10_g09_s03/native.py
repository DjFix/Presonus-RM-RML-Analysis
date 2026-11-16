"""Independent ARM doLink dispatch observations. Virtual providers are traced stubs."""
import importlib.metadata
import argparse,hashlib,io,json,struct,itertools
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
def generate(path):
 raw=Path(path).read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 elf=ELFFile(io.BytesIO(raw));sec=elf.get_section(12);start=0x2cb54;size=200;offset=sec['sh_offset']+start-sec['sh_addr']
 assert hashlib.sha256(raw[offset:offset+size]).hexdigest()=='d5d1525292a6796f5ea495e8598aefffdf5864410e0051a51692b756c218cf84'
 vtable=elf.get_section_by_name('.symtab').get_symbol_by_name('_ZTVN8Presonus5Mixer12GEQComponentE')[0]['st_value']+8
 rows=[]
 vectors=[[],[1],[1,2],[1,2,3],[1,2,3,4],[0,2],[1,0],[1,2,1,3],[1,1],[1,0,1,2]]
 for entries,target,link in itertools.product(vectors,[1,2,3,4,5],[False,True]):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x600000)
  for seg in elf.iter_segments():
   if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
  u.mem_map(0x1000000,0x20000);obj=0x1000000;vec=obj+0x1000;sp=obj+0x18000;stop=obj+0x1f000
  ptr=lambda i:obj+0x2000+i*0x100 if i else 0
  def word(a,v):u.mem_write(a,struct.pack('<I',v))
  word(obj+0x2b0,vec);word(obj+0x2b4,len(entries))
  for i,x in enumerate(entries):word(vec+4*i,ptr(x))
  for i in range(1,6):
   word(ptr(i),vtable)
  assert struct.unpack('<I',u.mem_read(vtable+0x3c,4))[0]==0x82d70
  assert struct.unpack('<I',u.mem_read(vtable+0x40,4))[0]==0x822a4
  calls=[];writes=[]
  def code(u,a,n,d):
   if a in [0x82d70,0x822a4]:
    r=[u.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2]]
    calls.append({'slot':60 if a==0x82d70 else 64,'receiver':(r[0]-obj-0x2000)//0x100,'partner':(r[1]-obj-0x2000)//0x100,'flag':r[2] if a==0x82d70 else None})
    u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  def write(u,access,a,n,v,d):
   if obj<=a<obj+0x5000:writes.append([a-obj,n,v])
  u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
  for r,v in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_R1,ptr(target)),(UC_ARM_REG_R2,int(link)),(UC_ARM_REG_SP,sp),(UC_ARM_REG_LR,stop)]:u.reg_write(r,v)
  u.emu_start(start,stop,count=2000);assert u.reg_read(UC_ARM_REG_PC)==stop
  rows.append({'input':{'entries':entries,'target':target,'link':link},'calls':calls,'writes':writes})
 return {'elf_sha256':SHA,'range':{'address':start,'size':size,'section':12,'file_offset':offset},'producer':{'path':__file__,'sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'unicorn_version':importlib.metadata.version('unicorn'),'pyelftools_version':importlib.metadata.version('pyelftools'),'oracle':'original ARM Unicorn; slots 0x3c/0x40 traced boundary stubs'},'receiver_vptr':{'symbol':'_ZTVN8Presonus5Mixer12GEQComponentE','address_point':vtable,'slots':{'0x3c':0x82d70,'0x40':0x822a4},'scope':'exact GEQ primary table; no arbitrary subclass vtable claim'},'domain':'empty/singleton/odd/even lists; missing/matching target; null neighbors; duplicate target identities; both link flags; valid nonnull GEQ target','cases':rows}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--elf',required=True);p.add_argument('--out',required=True);a=p.parse_args();Path(a.out).write_text(json.dumps(generate(a.elf),indent=2)+'\n')
