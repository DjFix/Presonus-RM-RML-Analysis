"""Exact numeric and string connect paths plus independently executed callback helper."""
import argparse,hashlib,importlib.util,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import *
from unicorn.arm_const import *
HERE=Path(__file__).parent
spec=importlib.util.spec_from_file_location('base',HERE.parent/'real10_g06_s04/native.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
def strings(path):
 assert base.sha(path)==base.SHA
 with open(path,'rb') as f:
  e=ELFFile(f);segments=[(s['p_vaddr'],s['p_memsz'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD'];s=e.get_section(12);off=s['sh_offset']+0x1d10c-s['sh_addr'];f.seek(off);helper=f.read(240)
 rows=[]
 for value in ['', '7.25', '4.5'+' '*80]:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);pages=set()
  for a,n,d in segments:
   for pg in range(a&~4095,(a+n+4095)&~4095,4096):
    if pg not in pages:u.mem_map(pg,4096);pages.add(pg)
   u.mem_write(a,d)
  u.mem_map(0x60000000,0x10000);u.mem_map(0x70000000,0x10000)
  def put(a,v):u.mem_write(a,struct.pack('<I',v))
  def text(a):
   b=b''
   while u.mem_read(a+len(b),1)!=b'\0':b+=bytes(u.mem_read(a+len(b),1));assert len(b)<512
   return b.decode()
  put(0x60000024,0x60001000);put(0x60000030,0);u.mem_write(0x6000002c,b'\1');u.mem_write(0x60000004,b'gain\0');put(0x60001000,0x60004000);put(0x6000100c,0x60005000);put(0x60005000,4);put(0x60004044,0x60006000);put(0x60004070,0x6000a000);put(0x60003000,0x60007000);put(0x60007058,0x60008000);put(0x60007074,0x6000b000)
  calls=[];forwarded=[]
  def hook(m,a,n,d):
   r0=m.reg_read(UC_ARM_REG_R0);r1=m.reg_read(UC_ARM_REG_R1)
   if a==0x11b968:calls.append('lookup');m.reg_write(UC_ARM_REG_R0,0x60003000)
   elif a==0x60006000:calls.append('get');m.reg_write(UC_ARM_REG_R0,0)
   elif a==0x60008000:assert r0==0x60003000 and r1==0 and m.reg_read(UC_ARM_REG_R2)==0;calls.append('set')
   elif a==0x11d4f4:calls.append('add')
   elif a==0x1cf90:m.mem_write(r0,b'\0'*64);calls.append('buffer')
   elif a==0x6000a000:
    assert r0==0x60001000 and m.reg_read(UC_ARM_REG_R2)==64;m.mem_write(r1,value.encode()[:63]+b'\0');calls.append('toString')
   elif a==0xae98:m.reg_write(UC_ARM_REG_R0,len(text(r0)));calls.append('strlen')
   elif a==0x116a38:calls.append('debug')
   elif a==0x11dc28:assert r0==0x60001000;calls.append('changed')
   elif a==0x6000b000:
    assert r0==0x60003000 and m.reg_read(UC_ARM_REG_R2)==1;forwarded.append(text(r1));calls.append('fromString')
   else:return
   m.reg_write(UC_ARM_REG_PC,m.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,hook)
  def execute(address,r1,r2=0):
   u.reg_write(UC_ARM_REG_R0,0x60000000);u.reg_write(UC_ARM_REG_R1,r1);u.reg_write(UC_ARM_REG_R2,r2);u.reg_write(UC_ARM_REG_SP,0x70008000);u.reg_write(UC_ARM_REG_LR,0x6000f000);u.emu_start(address,0x6000f000,count=1000);assert u.reg_read(UC_ARM_REG_PC)==0x6000f000
  execute(0x1d544,0x60009000);connect=list(calls);calls.clear()
  if 'changed' in connect:execute(0x1d10c,0x60001000,3)
  rows.append(dict(input=value,connect_calls=connect,helper_calls=list(calls),forwarded=forwarded))
 return rows,dict(address=0x1d10c,size=240,section=12,file_offset=off,sha256=hashlib.sha256(helper).hexdigest(),mangled='_ZN8Presonus5Mixer9ParamLink12paramChangedEPN4Core8Portable9ParameterEi',credit='supporting callback helper only; no additional original target admission')
def generate(path):
 d=base.generate(path,'real10_g06_s10');d['string_cases'],d['helper_original_range']=strings(path);d['string_producer_sha256']=base.sha(__file__);return d
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--elf',required=True);p.add_argument('--task',default='real10_g06_s10');p.add_argument('--out');p.add_argument('--verify');a=p.parse_args();d=generate(a.elf)
 if a.verify:assert d==json.loads(Path(a.verify).read_text());print('32 numeric +3 string native connect cases and helper verified')
 else:Path(a.out).write_text(json.dumps(d,indent=2)+'\n')
