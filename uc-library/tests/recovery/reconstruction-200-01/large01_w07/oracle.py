"""Original ARM instructions only; explicit Core provider boundary, never execute Core."""
import hashlib,json,struct
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
ROOT=Path(__file__).resolve().parents[5]
ELF=ROOT/'rootfs/CS18_v13840/home/root/surface'
EXPECTED='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
def execute(address,value=0):
 b=ELF.read_bytes();assert hashlib.sha256(b).hexdigest()==EXPECTED
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x400000)
 with ELF.open('rb') as f:
  e=ELFFile(f)
  for seg in e.iter_segments():
   if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
 u.mem_map(0x800000,0x10000);u.mem_map(0x900000,0x10000)
 obj=0x800000;stop=0x900000;u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,value)
 u.mem_write(obj+136,struct.pack('<I',value));u.reg_write(UC_ARM_REG_SP,0x90f000);u.reg_write(UC_ARM_REG_LR,stop)
 calls=[]
 def hook(uc,pc,size,data):
  if pc==stop:uc.emu_stop();return
  if pc==0x11b5e0:
   calls.append({'provider':'Core::Portable::Component::~Component','words':struct.unpack('<II',bytes(uc.mem_read(obj,8)))})
   uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
  allowed=(0xb7280<=pc<0xb72a0 or 0xb7264<=pc<0xb7280 or 0xb68d8<=pc<0xb6944 or 0xb6c34<=pc<0xb6c94 or 0xb6e84<=pc<0xb6ee4 or 0xab950<=pc<0xab96c or 0x1870a4<=pc<0x187144 or 0x18714c<=pc<0x18730c or 0x187798<=pc<0x1877b0 or 0x187768<=pc<0x187780 or 0x1876f8<=pc<0x187758)
  if not allowed:raise RuntimeError('Unbound native execution at '+hex(pc))
 u.hook_add(UC_HOOK_CODE,hook);u.emu_start(address,stop,count=100000)
 assert u.reg_read(UC_ARM_REG_PC)==stop
 return {'result':u.reg_read(UC_ARM_REG_R0),'words':list(struct.unpack('<II',bytes(u.mem_read(obj,8)))),'calls':calls}
if __name__=='__main__':
 import sys
 print(json.dumps(execute(int(sys.argv[1],0),int(sys.argv[2],0) if len(sys.argv)>2 else 0)))
