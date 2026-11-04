import hashlib,json,struct
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
def observe(n,mode):
 elf=Path('rootfs/RML16AI_Rack_13731/home/root/mixer').read_bytes()
 assert hashlib.sha256(elf).hexdigest()=='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
 body=elf[0x6cb60:0x6cba4];assert hashlib.sha256(body).hexdigest()=='0f01723d589d566f21700096137320a8e832449d76f5381d96dbd856b0ca4be5'
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
 for addr,size in [(0x74000,0x1000),(0x11c000,0x1000),(0x300000,0x10000),(0x400000,0x10000)]:u.mem_map(addr,size)
 u.mem_write(0x74b60,body)
 def put(a,v):u.mem_write(a,struct.pack('<I',v))
 put(0x3000dc,0x301000);put(0x3012c4,0x302000);put(0x3012c8,n)
 for i in range(n):put(0x302000+4*i,0x303000+0x100*(i%2 if mode else i%4))
 calls=[]
 def hook(uc,pc,size,data):
  if pc==0x11c2e4:
   assert uc.reg_read(UC_ARM_REG_R1)==0x300004
   calls.append((uc.reg_read(UC_ARM_REG_R0)-0x303000)//0x100)
   uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  if pc==0x400100:uc.emu_stop()
 u.hook_add(UC_HOOK_CODE,hook)
 for r,v in [(UC_ARM_REG_R0,0x300000),(UC_ARM_REG_SP,0x40f000),(UC_ARM_REG_LR,0x400100)]:u.reg_write(r,v)
 u.emu_start(0x74b60,0x400104,count=10000)
 return {'n':n,'mode':mode,'calls':calls}
if __name__=='__main__':print(json.dumps([observe(n,m) for n in (0,1,2,4,8,16) for m in (0,1)],indent=2))
