"""Execute original scrubwheel ARM body; intercept only memcpy and MIDI boundary."""
import json,struct,pathlib
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
from native_oracle import ROOT,ELF,SHA

def main():
 cases=[]
 for direction in [-2147483648,-100,-1,0,1,100,2147483647]:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  with ELF.open('rb') as f:
   elf=ELFFile(f)
   for seg in elf.iter_segments():
    if seg['p_type']!='PT_LOAD':continue
    start=int(seg['p_vaddr']);size=int(seg['p_memsz']);base=start&~4095
    u.mem_map(base,((start+size+4095)&~4095)-base);u.mem_write(start,seg.data())
  u.mem_map(0x400000,0x10000);u.reg_write(UC_ARM_REG_SP,0x408000);u.reg_write(UC_ARM_REG_LR,0x40f000);u.reg_write(UC_ARM_REG_R0,0x400000);u.reg_write(UC_ARM_REG_R1,direction&0xffffffff)
  trace=[]
  def hook(u,address,size,user):
   if address==0xaffc:
    dst=u.reg_read(UC_ARM_REG_R0);src=u.reg_read(UC_ARM_REG_R1);n=u.reg_read(UC_ARM_REG_R2);u.mem_write(dst,bytes(u.mem_read(src,n)));u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
   elif address==0xc0480:
    ptr=u.reg_read(UC_ARM_REG_R1);n=u.reg_read(UC_ARM_REG_R2);trace.append(list(u.mem_read(ptr,n)));u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,hook);u.emu_start(0xc04b0,0x40f000,count=500);cases.append({'direction':direction,'midi':trace})
 path=pathlib.Path(__file__).parent/'scrub-fixtures.json';path.write_text(json.dumps({'elf_sha256':SHA,'cases':cases},indent=2)+'\n');print('Original scrubwheel cases',len(cases))
if __name__=='__main__':main()
