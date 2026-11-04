import hashlib,json,struct,sys
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
elf=Path('rootfs/CS18_v13840/home/root/surface').read_bytes()
assert hashlib.sha256(elf).hexdigest()=='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
body=elf[0x5b5a4:0x5b5a4+200]
assert hashlib.sha256(body).hexdigest()=='3b4f72110cac8abe75784688f0f2a85bc906f0078f6c107074f87f16345a5086'
def run(t,i,x,y):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
 for base,size in [(0x63000,0x1000),(0x100000,0x10000),(0x200000,0x10000),(0x269000,0x1000)]:u.mem_map(base,size)
 u.mem_write(0x635a4,body)
 def put(a,*v):u.mem_write(a,struct.pack('<'+'I'*len(v),*[n&0xffffffff for n in v]))
 put(0x200030,0x200100,3);put(0x200100,0x200200,0,0x200300)
 put(0x108000,x,y)
 for reg,val in [(UC_ARM_REG_R0,0x200000),(UC_ARM_REG_R1,0xdeadbeef),(UC_ARM_REG_R2,t&0xffffffff),(UC_ARM_REG_R3,i&0xffffffff),(UC_ARM_REG_SP,0x108000),(UC_ARM_REG_LR,0x100000)]:u.reg_write(reg,val)
 out=[0,-1,-1,0,0]
 def hook(u,a,size,data):
  if a==0x10f21c:
   ptr=u.reg_read(UC_ARM_REG_R0);ev=struct.unpack('<iii',u.mem_read(u.reg_read(UC_ARM_REG_R1),12));out[:]=[1,0 if ptr==0x200200 else 2,*ev];u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  elif a==0x100000:u.emu_stop()
 u.hook_add(UC_HOOK_CODE,hook);u.emu_start(0x635a4,0,count=200)
 return out
cases=[]
for t in [-1,0,1,2,3,2147483647]:
 for i in [-1,0,1,2,3,2147483647]:
  for x,y in [(0,0),(-2147483648,2147483647),(123,-456)]:cases.append({'input':[t,i,x,y],'output':run(t,i,x,y)})
result={'cases':cases,'oracle':'original ARM instructions; CCL call intercepted; no Core binary execution'}
if len(sys.argv)>1:Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+'\n')
else:print(json.dumps(result))
