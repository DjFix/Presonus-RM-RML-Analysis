"""Execute hash-verified ARM application body; libc/allocator/Core are boundaries."""
import argparse,hashlib,json,struct
from pathlib import Path
import unicorn
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
HASH='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
SYM='_ZN8Presonus17MeterScaleControl6Ranges8addRangeEPKciPKi'
def load(path,symbol,address,size,digest):
 blob=Path(path).read_bytes();assert hashlib.sha256(blob).hexdigest()==HASH
 with open(path,'rb') as f:
  elf=ELFFile(f); syms=[s for sec in elf.iter_sections() if sec['sh_type']=='SHT_SYMTAB' for s in sec.iter_symbols() if s.name==symbol];assert len(syms)==1
  s=syms[0];sec=elf.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];assert (s['st_value'],s['st_size'],sec.name)==(address,size,'.text')
 body=blob[off:off+size];assert hashlib.sha256(body).hexdigest()==digest
 return blob,body,off

def machine(address,body):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x1000,0x210000);u.mem_write(address,body);u.mem_map(0x300000,0x20000);u.reg_write(UC_ARM_REG_SP,0x31ff00);u.reg_write(UC_ARM_REG_LR,0x1000);return u

def word(u,a):return struct.unpack('<I',u.mem_read(a,4))[0]
def put(u,a,*v):u.mem_write(a,struct.pack('<'+'I'*len(v),*[x&0xffffffff for x in v]))
def string(u,a):
 b=bytearray()
 while True:
  c=bytes(u.mem_read(a+len(b),1))
  if c==b'\0':return bytes(b)
  b+=c

def main():
 p=argparse.ArgumentParser();p.add_argument('--elf',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 _,body,off=load(a.elf,SYM,0x68558,192,'d64ffd097508db35ba43037050ee051fd5e43f1799d55ec86b1d84b56960ef81');cases=[]
 for name in [None,'','A','x'*127,'x'*128,'q'*511]:
  for count in [-1,0,3]:
   for initial in [0,1,5,20]:
    for failure in [False,True] if initial==0 else [False]:
     u=machine(0x68558,body);put(u,0x300000,0,0x301000,initial,initial);u.mem_write(0x301000,b'\xa5'*(4*initial));u.mem_write(0x304000,b'\xcc'*136)
     if name is not None:u.mem_write(0x302000,name.encode()+b'\0')
     u.reg_write(UC_ARM_REG_R0,0x300000);u.reg_write(UC_ARM_REG_R1,0x302000 if name is not None else 0);u.reg_write(UC_ARM_REG_R2,count&0xffffffff);u.reg_write(UC_ARM_REG_R3,0x303000);trace=[]
     def hook(uc,pc,size,data):
      r0=uc.reg_read(UC_ARM_REG_R0);r1=uc.reg_read(UC_ARM_REG_R1);r2=uc.reg_read(UC_ARM_REG_R2)
      if pc==0x1000:uc.emu_stop();return
      if pc==0xa90c:trace.append(['new',r0]);uc.reg_write(UC_ARM_REG_R0,0x304000)
      elif pc==0xb02c:trace.append(['strlen']);uc.reg_write(UC_ARM_REG_R0,len(string(uc,r0)))
      elif pc==0xb170:trace.append(['strncpy',r2]);uc.mem_write(r0,bytes(uc.mem_read(r1,r2)))
      elif pc==0x69fcc:trace.append(['resize',r1,not failure]);put(uc,0x30000c,r1) if not failure else None;uc.reg_write(UC_ARM_REG_R0,0 if failure else 1)
      else:return
      uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
     u.hook_add(UC_HOOK_CODE,hook);u.emu_start(0x68558,0x210000,count=2000)
     end=word(u,0x300008);assert end==initial+(not failure);assert word(u,0x304000)==0x303000;assert word(u,0x304004)==count&0xffffffff
     if not failure:assert word(u,0x301000+4*initial)==0x304000
     assert bytes(u.mem_read(0x301000,initial*4))==b'\xa5'*(4*initial)
     cases.append(dict(name=name,count=count,initial=initial,resize_failure=failure,result_count=end,stored_name=string(u,0x304008).decode(),borrowed=True,trace=trace,allocated_record_retained_on_failure=failure))
 out=dict(elf_sha256=HASH,mangled=SYM,address=0x68558,size=192,section='.text',file_offset=off,range_sha256=hashlib.sha256(body).hexdigest(),unicorn=unicorn.__version__,producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cases=cases,boundaries='new returns mapped record; strlen/strncpy standard byte semantics; Core resize success/failure scripted, no Core binary execution; new failure not emulated')
 Path(a.out).write_text(json.dumps(out,indent=2)+'\n');print(len(cases),'ARM cases')
if __name__=='__main__':main()
