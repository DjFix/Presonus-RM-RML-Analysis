"""Independent seeded ARM registry lookup observations."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'rolling_next_meter_ranges_add'))
from native import load,machine,put,word,string,HASH
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *
import unicorn
SYM='_ZN8Presonus17MeterScaleControl6Ranges8getRangeEPKc'
NAMES=['','A','A','a','x'*127,'tail']
def main():
 p=argparse.ArgumentParser();p.add_argument('--elf',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 blob,body,off=load(a.elf,SYM,0x64a7c,112,'ea1a796f8000608a75871d5ba46961579a63615e07ca7df05bda9b03697e5305');cases=[]
 from elftools.elf.elffile import ELFFile
 with open(a.elf,'rb') as f:
  elf=ELFFile(f);sec=next(s for s in elf.iter_sections() if s['sh_addr']<=0x1f2670<s['sh_addr']+s['sh_size']);literal_off=sec['sh_offset']+0x1f2670-sec['sh_addr'];assert blob[literal_off:literal_off+1]==b'\0'
 for n in [0,1,3,6]:
  for key in [None,'','A','a','missing','x'*127,'x'*128,'tail']:
   u=machine(0x64a7c,body);put(u,0x300000,0,0x301000,n,n);u.mem_write(0x1f2670,b'\0')
   for i,name in enumerate(NAMES):put(u,0x301000+4*i,0x304000+256*i);u.mem_write(0x304008+256*i,name.encode()+b'\0')
   if key is not None:u.mem_write(0x302000,key.encode()+b'\0')
   before=bytes(u.mem_read(0x300000,0x6000));u.reg_write(UC_ARM_REG_R0,0x300000);u.reg_write(UC_ARM_REG_R1,0x302000 if key is not None else 0);trace=[]
   def hook(uc,pc,size,data):
    if pc==0x1000:uc.emu_stop()
    elif pc==0xb0f8:
     l=string(uc,uc.reg_read(UC_ARM_REG_R0));r=string(uc,uc.reg_read(UC_ARM_REG_R1));trace.append([l.decode(),r.decode()]);uc.reg_write(UC_ARM_REG_R0,0 if l==r else 1);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   u.hook_add(UC_HOOK_CODE,hook);u.emu_start(0x64a7c,0x210000,count=2000);r=u.reg_read(UC_ARM_REG_R0);assert bytes(u.mem_read(0x300000,0x6000))==before
   cases.append(dict(count=n,key=key,index=(r-0x304000)//256 if r else -1,comparisons=trace,no_mutation=True))
 Path(a.out).write_text(json.dumps(dict(elf_sha256=HASH,mangled=SYM,address=0x64a7c,size=112,section='.text',file_offset=off,range_sha256=hashlib.sha256(body).hexdigest(),producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),unicorn=unicorn.__version__,names=NAMES,cases=cases,boundaries='strcmp equality modeled; records explicitly seeded independent of new C++; no Core execution'),indent=2)+'\n');print(len(cases),'ARM cases')
if __name__=='__main__':main()
