"""Original lookup ARM callers with libc bsearch boundary emulated explicitly."""
import json,pathlib,struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
from native_oracle import ROOT,ELF,SHA

def main():
 cases=[]
 for method in [8,9]:
  for entries in [[],[[-3,20,0]],[[-10,30,0],[0,-5,1],[10,20,2],[20,0,3],[30,10,4]]]:
   entries=sorted(entries,key=lambda x:x[1 if method==8 else 0])
   for key in [-2147483648,-11,-10,-5,-3,0,1,10,20,30,31,2147483647]:
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
    with ELF.open('rb') as f:
     for seg in ELFFile(f).iter_segments():
      if seg['p_type']=='PT_LOAD':
       start=int(seg['p_vaddr']);base=start&~4095;u.mem_map(base,((start+int(seg['p_memsz'])+4095)&~4095)-base);u.mem_write(start,seg.data())
    u.mem_map(0x400000,0x10000)
    def word(p,v):u.mem_write(p,struct.pack('<I',v&0xffffffff))
    offset=0x534 if method==8 else 4;word(0x400000+offset,0x401000);word(0x400004+offset,len(entries))
    for i,row in enumerate(entries):u.mem_write(0x401000+i*12,struct.pack('<iii',*row))
    u.reg_write(UC_ARM_REG_SP,0x408000);u.reg_write(UC_ARM_REG_LR,0x40f000);u.reg_write(UC_ARM_REG_R0,0x400000);u.reg_write(UC_ARM_REG_R1,key&0xffffffff)
    trace=[]
    def hook(u,address,size,user):
     if address!=0xac84:return
     kp=u.reg_read(UC_ARM_REG_R0);base=u.reg_read(UC_ARM_REG_R1);n=u.reg_read(UC_ARM_REG_R2);width=u.reg_read(UC_ARM_REG_R3);cmp=struct.unpack('<I',u.mem_read(u.reg_read(UC_ARM_REG_SP),4))[0];keyrow=list(struct.unpack('<iii',u.mem_read(kp,12)));trace.append({'key':keyrow,'count':n,'width':width,'comparator':cmp});lo=0;hi=n;result=0
     # libc dependency contract only; target caller and key construction execute natively.
     while lo<hi:
      mid=(lo+hi)//2;row=struct.unpack('<iii',u.mem_read(base+mid*width,12));idx=1 if cmp==0xc01a0 else 0
      if keyrow[idx]<row[idx]:hi=mid
      elif keyrow[idx]>row[idx]:lo=mid+1
      else:result=base+mid*width;break
     u.reg_write(UC_ARM_REG_R0,result);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    u.hook_add(UC_HOOK_CODE,hook);u.emu_start(0xc0e7c if method==8 else 0xc0ed0,0x40f000,count=500);r=u.reg_read(UC_ARM_REG_R0);cases.append({'method':method,'entries':entries,'key':key,'index':(r-0x401000)//12 if r else -1,'trace':trace})
 (pathlib.Path(__file__).parent/'lookup-fixtures.json').write_text(json.dumps({'elf_sha256':SHA,'cases':cases},indent=2)+'\n');print('Original lookup callers',len(cases))
if __name__=='__main__':main()
