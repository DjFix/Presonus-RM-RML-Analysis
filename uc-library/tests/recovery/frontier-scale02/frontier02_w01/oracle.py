"""Original SceneBook ARM execution with explicit Book(int) test boundary."""
import hashlib,json
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
def observe():
 p=Path("rootfs/RML16AI_Rack_13731/home/root/mixer");raw=p.read_bytes()
 assert hashlib.sha256(raw).hexdigest()=="9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
 with p.open("rb") as f:
  s=ELFFile(f).get_section(12);off=448600-s["sh_addr"]+s["sh_offset"]
 body=raw[off:off+44];assert off==0x65858
 assert hashlib.sha256(body).hexdigest()=="c634d9db11860615ded14ca95c3206b4c8a9c41d3e023db261d8520a0190ba26"
 rows=[]
 for n in [-2147483648,-1,0,1,31,2147483647]:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for a,size in [(0x6d000,4096),(0x97000,4096),(0x1000000,4096),(0x2000000,8192),(0x3000000,4096)]:u.mem_map(a,size)
  u.mem_write(448600,body);u.mem_write(0x1000000,bytes([165])*256)
  for r,v in [(UC_ARM_REG_R0,0x1000000),(UC_ARM_REG_R1,n&0xffffffff),(UC_ARM_REG_SP,0x2001000),(UC_ARM_REG_LR,0x3000000)]:u.reg_write(r,v)
  calls=[];writes=[];ins=[]
  def hook(u,a,size,data):
   ins.append(a)
   if a==0x97bfc:
    calls.append([a,u.reg_read(UC_ARM_REG_R0),u.reg_read(UC_ARM_REG_R1)])
    for reg in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]:u.reg_write(reg,0xbad00000)
    u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,hook)
  u.hook_add(UC_HOOK_MEM_WRITE,lambda u,access,a,size,v,data:writes.append([a,size,v]))
  u.emu_start(448600,0x3000000,count=32)
  mem=bytes(u.mem_read(0x1000000,256));assert mem[4:]==bytes([165])*252
  assert calls==[[0x97bfc,0x1000000,n&0xffffffff]]
  assert [w for w in writes if 0x1000000<=w[0]<0x1001000]==[[0x1000000,4,0x32a268]]
  assert u.reg_read(UC_ARM_REG_R0)==0x1000000 and u.reg_read(UC_ARM_REG_SP)==0x2001000
  rows.append(dict(input=n,call=calls,dispatch=int.from_bytes(mem[:4],"little"),writes=writes,instructions=ins))
 return dict(elf_sha256=hashlib.sha256(raw).hexdigest(),file_offset=off,size=44,section=12,range_sha256=hashlib.sha256(body).hexdigest(),boundary="Book(int) intercepted without executing provider; preserves object bytes",cases=rows)
if __name__=="__main__":print(json.dumps(observe(),indent=2))
