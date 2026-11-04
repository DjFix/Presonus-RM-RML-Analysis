"""Execute only assigned original ARM body; observe outbound provider calls."""
import hashlib,json,struct
from pathlib import Path
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *
elf=Path('rootfs/CS18_v13840/home/root/surface').read_bytes()
assert hashlib.sha256(elf).hexdigest()=='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
body=elf[0x97574:0x97574+96]
assert hashlib.sha256(body).hexdigest()=='755fa9e3d9fe247e087207c02a0a3501ceaf3bf91b1822744cc499fde04a34e4'
results=[]
for n in range(6):
 for selected in (0,0x12345678):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for addr,size in ((0x9f000,0x1000),(0x10a000,0x1000),(0x300000,0x10000),(0x400000,0x10000)):
   u.mem_map(addr,size)
  u.mem_write(0x9f574,body)
  u.mem_write(0x300004,struct.pack('<II',0x301000,n))
  for i in range(n):u.mem_write(0x301000+i*4,struct.pack('<I',0x302000+i*0x100))
  calls=[]
  def hook(uc,pc,size,data):
   if pc==0x10a3d0:
    calls.append(uc.reg_read(UC_ARM_REG_R0));uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   if pc==0x400100:uc.emu_stop()
  u.hook_add(UC_HOOK_CODE,hook)
  for reg,val in ((UC_ARM_REG_R0,0x300000),(UC_ARM_REG_R1,selected),(UC_ARM_REG_SP,0x40f000),(UC_ARM_REG_LR,0x400100)):u.reg_write(reg,val)
  u.emu_start(0x9f574,0x400104,count=1000)
  stored=struct.unpack('<I',u.mem_read(0x300034,4))[0]
  assert stored==selected and calls==[0x302000+i*0x100 for i in range(n)]
  results.append({'view_count':n,'selected':selected,'stored':stored,'calls':calls})
print(json.dumps({'cases':results,'scope':'original ARM target only; CCL call intercepted, not emulated'},indent=2))
