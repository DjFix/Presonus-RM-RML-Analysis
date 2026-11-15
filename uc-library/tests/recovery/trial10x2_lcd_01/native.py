"""Original ARM execution; pushBackPage is an observed application boundary.
Core firmware is never executed. Real CCL container behavior is checked in C++.
"""
import argparse,hashlib,json,struct,itertools
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
ROOT=Path(__file__).resolve().parents[4]
MAP=ROOT/'temp/recovery-work/trial10x2-20261115/READ_INPUTS-prepared01-trial10x2_lcd.json'
def capture():
 e=Path(json.loads(MAP.read_text())['rootfs/CS18_v13840/home/root/surface']['frozen_read_path']); data=e.read_bytes()
 assert hashlib.sha256(data).hexdigest()=='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
 ranges=[]
 with e.open('rb') as f:
  sec=ELFFile(f).get_section(12)
  for addr,size,sha in [(473264,56,'5ca6029c602b04e51e8829be6db36772d22e5b8145d93a1d9aa410203547dd1a'),(473320,100,'e3484c650935b55eca51dc68e5a0f668ba95f7b72335440bfc25a3f2a74d05e9'),(411232,20,'4014368c8d506bc68887e9836906d65b99b948f0edbfc4947d10ec3d5708ddba')]:
   off=sec['sh_offset']+addr-sec['sh_addr'];code=data[off:off+size];assert hashlib.sha256(code).hexdigest()==sha
   ranges.append(dict(address=addr,size=size,offset=off,sha256=sha,section='.text'))
 cases=[]
 for cur,nxt,alias,tag,flag,back,count in itertools.product([0,1],[0,1],[0,1],[-2147483648,-1000,-1,0,2147483647],[0,1,255],[0,1],[0,8,9]):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x10000,0x200000);u.mem_map(0x300000,0x20000);u.mem_map(0x400000,0x10000);u.mem_map(0x600000,0x1000)
  for r in ranges:u.mem_write(r['address'],data[r['offset']:r['offset']+r['size']])
  w=lambda a,v:u.mem_write(a,struct.pack('<I',v&0xffffffff))
  current=0x300000 if cur else 0;nextp=(0x300000 if alias else 0x301000) if nxt else 0
  w(0x310000+0xbc,current);w(0x310000+0xc0,nextp);w(0x310000+0xc8,0x302000 if back else 0)
  w(0x300000+0x8c,tag);w(0x301000+0x8c,123);u.mem_write((nextp or 0x301000)+0x89,bytes([flag]));trace=[];writes=[]
  def hook(uc,a,size,x):
   if a==0x600000:uc.emu_stop()
   if a==0x7351c:
    trace.append([uc.reg_read(UC_ARM_REG_R0),uc.reg_read(UC_ARM_REG_R1)]);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  def write(uc,access,address,size,value,x):
   if 0x300000<=address<0x311000:writes.append([address,size,value])
  u.hook_add(UC_HOOK_MEM_WRITE,write)
  u.hook_add(UC_HOOK_CODE,hook)
  def run(addr):
   u.reg_write(UC_ARM_REG_R0,0x310000);u.reg_write(UC_ARM_REG_SP,0x408000);u.reg_write(UC_ARM_REG_LR,0x600000);u.emu_start(addr,0x600004,count=200);assert u.reg_read(UC_ARM_REG_PC)==0x600000
  run(473264);result=u.reg_read(UC_ARM_REG_R0);result=result if result<2**31 else result-2**32
  run(473320);b=struct.unpack('<I',bytes(u.mem_read(0x310000+0xc8,4)))[0]
  cases.append(dict(inputs=[cur,nxt,alias,tag,flag,back,count],observed=[result,int(bool(b)),len(trace)],trace=trace,writes=writes))
 return dict(ranges=ranges,cases=cases,boundary='pushBackPage intercepted; real CCL stack separately compared in replay; no provider firmware')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out');p.add_argument('--verify');a=p.parse_args();d=capture()
 if a.verify:assert d==json.loads(Path(a.verify).read_text());print(len(d['cases']),'native cases reproduced')
 else:Path(a.out).write_text(json.dumps(d,indent=2)+'\n')
