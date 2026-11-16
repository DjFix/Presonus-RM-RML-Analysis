"""Original exact destructor variant, explicit Core/child/deallocator boundaries."""
import argparse,hashlib,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import *
from unicorn.arm_const import *
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def generate(path,task):
 variant,address,size={'real10_g06_s01':('D1',376480,260),'real10_g06_s02':('D2',376740,260),'real10_g06_s03':('D0',376212,268)}[task]
 assert sha(path)==SHA
 with open(path,'rb') as f:
  elf=ELFFile(f);section=elf.get_section(12);offset=section['sh_offset']+address-section['sh_addr'];f.seek(offset);body=f.read(size);segments=[(s['p_vaddr'],s['p_memsz'],s.data()) for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
 cases=[]
 for entries in [[],[0],[1],[0,2,1],[3,1,2]]:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);pages=set()
  for a,n,d in segments:
   for pg in range(a&~4095,(a+n+4095)&~4095,4096):
    if pg not in pages:u.mem_map(pg,4096);pages.add(pg)
   u.mem_write(a,d)
  u.mem_map(0x60000000,0x10000);u.mem_map(0x70000000,0x10000)
  def put(a,v):u.mem_write(a,struct.pack('<I',v))
  put(0x600000a4,0x60001000);put(0x600000a8,len(entries))
  for i,x in enumerate(entries):
   put(0x60001000+4*i,0x60002000+0x100*x if x else 0)
   if x:put(0x60002000+0x100*x,0x60003000);put(0x60003008,0x60004000)
  calls=[];writes=[]
  def hook(m,a,n,d):
   r0=m.reg_read(UC_ARM_REG_R0)
   if a==0x60004000:calls.append(['child_delete',(r0-0x60002000)//0x100])
   elif a==0x3874c:
    assert r0==0x600000a0 and m.reg_read(UC_ARM_REG_R1)==0;calls.append(['resize_owned',0])
   elif a==0x3884c:assert r0==0x600000a0;calls.append(['owned_vector_dtor'])
   elif a==0x3938c:assert r0==0x6000008c;calls.append(['borrowed_vector_dtor'])
   elif a==0x11a53c:assert r0==0x60000000;calls.append(['component_dtor'])
   elif a==0xac10:assert r0==0x60000000;calls.append(['receiver_delete'])
   else:return
   m.reg_write(UC_ARM_REG_PC,m.reg_read(UC_ARM_REG_LR))
  def write(m,access,a,n,v,d):
   if not 0x70000000<=a<a+n<=0x70010000:writes.append([a-0x60000000,n,v])
  u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write);u.reg_write(UC_ARM_REG_R0,0x60000000);u.reg_write(UC_ARM_REG_SP,0x70008000);u.reg_write(UC_ARM_REG_LR,0x6000f000)
  u.emu_start(address,0x6000f000,count=1000);assert u.reg_read(UC_ARM_REG_PC)==0x6000f000
  assert struct.unpack('<I',u.mem_read(0x600000a8,4))[0]==0
  cases.append(dict(entries=entries,calls=calls,writes=writes))
 return dict(task=task,variant=variant,mangled='_ZN8Presonus5Mixer22AutoFilterGroupManager'+variant+'Ev',original_elf_sha256=SHA,original_range=dict(address=address,size=size,section=12,file_offset=offset,sha256=hashlib.sha256(body).hexdigest()),cases=cases,oracle=dict(engine='Unicorn '+unicorn.__version__,producer_sha256=sha(__file__),stubs=['child virtual deleting destructor','Core resize/vector destructor/Component destructor','operator delete import for D0'],domain='5 valid unique-owned-entry lists, empty/null/mixed/three children; original order, receiver count reset and vtable writes; no EH/concurrency or child mutation',limitations='Core/child/deallocator calls are explicit native test boundaries; real CCL and actual host cleanup/deallocation observed in C++ separately. D1/D2 original ranges distinct, not aliases.'))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--elf',required=True);p.add_argument('--task',default=Path(__file__).parent.name);p.add_argument('--out');p.add_argument('--verify');a=p.parse_args();r=generate(a.elf,a.task)
 if a.verify:assert r==json.loads(Path(a.verify).read_text());print(a.task,'native5 PASS')
 else:Path(a.out).write_text(json.dumps(r,indent=2)+'\n')
