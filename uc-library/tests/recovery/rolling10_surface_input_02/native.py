import hashlib,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import *
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[4]
NAME='_ZNK8Presonus7Surface21SurfaceInputComponent11getPotValueEv'
ADDRESS=748284;SIZE=28;TAG=301;RANGE_HASH='7d090f67b16165a200de9ca3d080934f5e2831021733228cbe1c0dde1082ef1b'
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
def generate():
 binding=json.loads((R/'temp/recovery-work/rolling10x10-20261114/READ_INPUTS-rolling10_surface_input.json').read_text())
 elf=Path(binding['rootfs/CS18_v13840/home/root/surface']['frozen_read_path']);data=elf.read_bytes();assert hashlib.sha256(data).hexdigest()==SHA
 with elf.open('rb') as f:
  e=ELFFile(f);s=next(s for s in e.get_section_by_name('.symtab').iter_symbols() if s.name==NAME);sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];body=data[off:off+SIZE]
  assert (s['st_value'],s['st_size'],hashlib.sha256(body).hexdigest())==(ADDRESS,SIZE,RANGE_HASH)
 cases=[]
 for returned in [0,0x500000,0x500100,0x7fffffff]:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x1000000);u.mem_write(ADDRESS,body);trace=[];writes=[];sites=[]
  def hook(u,a,n,_):
   sites.append(a)
   if a==0xf00000:u.emu_stop();return
   if ADDRESS<=a<ADDRESS+SIZE:return
   assert a==0x11acf0,hex(a)
   trace.append([u.reg_read(UC_ARM_REG_R0),u.reg_read(UC_ARM_REG_R1)])
   u.reg_write(UC_ARM_REG_R0,returned);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,lambda u,ac,a,n,v,_:writes.append([a,n,v]))
  for reg,value in [(UC_ARM_REG_R0,0x400000),(UC_ARM_REG_SP,0x8ff000),(UC_ARM_REG_LR,0xf00000)]:u.reg_write(reg,value)
  u.emu_start(ADDRESS,0xf00000,count=30)
  assert trace==[[0x400000,TAG]] and u.reg_read(UC_ARM_REG_R0)==returned
  assert all(0x8fe000<=w[0]<0x8ff000 for w in writes)
  cases.append(dict(boundary_return=returned,observed_return=u.reg_read(UC_ARM_REG_R0),trace=trace,writes=writes,sites=sites))
 return dict(elf_sha256=SHA,mangled=NAME,address=ADDRESS,size=SIZE,section='.text',file_offset=off,range_sha256=RANGE_HASH,cases=cases,boundary='Core provider not executed in ARM; observed tail-call args and passthrough only. Actual pinned CCL separately executed by Replay.cpp.')
if __name__=='__main__':
 import sys
 Path(sys.argv[1]).write_text(json.dumps(generate(),indent=2)+'\n')
