"""Execute exact FX application instructions and native libgcc conversion."""
import argparse, hashlib, json, struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
MANGLED='_ZNK8Presonus5Mixer11FXComponent10getTypeNumEv'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def generate(path):
 assert sha(path)==SHA
 with open(path,'rb') as f:
  e=ELFFile(f);sec=e.get_section(12);off=sec['sh_offset']+240104-sec['sh_addr'];f.seek(off);body=f.read(40)
  segments=[(s['p_vaddr'],s['p_memsz'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
 cases=[]
 values=[-2147483648.,-12345.75,-100.,-1.999,-1.,-.999,-0.,0.,.999,1.,1.999,32.,127.9,65535.75,2147483520.]
 for v in values:
  bits=struct.unpack('<I',struct.pack('<f',v))[0];u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  pages=set()
  for a,n,d in segments:
   for pg in range(a&~4095,(a+n+4095)&~4095,4096):
    if pg not in pages:u.mem_map(pg,4096);pages.add(pg)
   u.mem_write(a,d)
  u.mem_map(0x60000000,0x10000);u.mem_map(0x70000000,0x10000)
  def put(a,v):u.mem_write(a,struct.pack('<I',v))
  put(0x60000120,0x60001000);put(0x60001000,0x60002000);put(0x60002044,0x60003000)
  calls=[];writes=[]
  def hook(m,a,n,d):
   if a==0x60003000:
    assert m.reg_read(UC_ARM_REG_R0)==0x60001000;calls.append('parameter.getValue');m.reg_write(UC_ARM_REG_R0,bits);m.reg_write(UC_ARM_REG_PC,m.reg_read(UC_ARM_REG_LR))
  def write(m,access,a,n,v,d):
   if not 0x70000000<=a<a+n<=0x70010000:writes.append([a,n,v])
  u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
  u.reg_write(UC_ARM_REG_R0,0x60000000);u.reg_write(UC_ARM_REG_SP,0x70008000);u.reg_write(UC_ARM_REG_LR,0x6000f000)
  u.emu_start(240104,0x6000f000,count=1000);assert u.reg_read(UC_ARM_REG_PC)==0x6000f000
  r=u.reg_read(UC_ARM_REG_R0);r=r if r<2**31 else r-2**32
  assert calls==['parameter.getValue'] and not writes
  cases.append(dict(input_bits=bits,result=r,calls=calls,nonstack_writes=writes))
 return dict(original_elf_sha256=SHA,mangled=MANGLED,original_range=dict(address=240104,size=40,section=12,file_offset=off,sha256=hashlib.sha256(body).hexdigest()),cases=cases,oracle=dict(engine='Unicorn '+unicorn.__version__,producer_sha256=sha(__file__),stubs=['Parameter::getValue vtable boundary returns supplied IEEE float bits; native provider body not executed'],executed='Original application and original __aeabi_f2iz body; mapped ELF PT_LOAD regions',domain='15 finite binary32 values in signed int32 range, fractions, signs, zero and integer boundaries; no nonstack writes'))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--elf',required=True);p.add_argument('--out');p.add_argument('--verify');a=p.parse_args();r=generate(a.elf)
 if a.verify:assert r==json.loads(Path(a.verify).read_text());print('15 native cases verified')
 else:Path(a.out).write_text(json.dumps(r,indent=2)+'\n')
