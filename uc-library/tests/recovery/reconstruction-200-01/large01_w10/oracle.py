"""Execute exact hash-bound ELF ARM targets; actual isLinked/isLinkSlave bodies executed."""
import hashlib,json,struct,io
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
INPUTS={'server':('rootfs/RML16AI_Rack_13731/home/root/mixer','9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'),'client':('rootfs/CS18_v13840/home/root/surface','304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0')}
CACHE={}
def execute(address,updates,arg=0,role='server',linked=None):
 if role not in CACHE:
  path,digest=INPUTS[role];b=Path(path).read_bytes();assert hashlib.sha256(b).hexdigest()==digest
  if role=='server': assert hashlib.sha256(b[0x7a3c0:0x7a3dc]).hexdigest()=='ffbd31d06860bac1bd4715e6b766488412b4fe339647e126dc23520d5ff8d151'
  CACHE[role]=[(s['p_vaddr'],s.data()) for s in ELFFile(io.BytesIO(b)).iter_segments() if s['p_type']=='PT_LOAD']
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x800000)
 for addr,b in CACHE[role]:u.mem_write(addr,b)
 u.mem_map(0x1000000,0x20000);u.mem_map(0x2000000,0x10000);obj=0x1000000
 for off,value,width in updates:u.mem_write(obj+off,int(value).to_bytes(width,'little'))
 trace=[]
 def hook(uc,pc,size,unused):
  if pc==0x823c0 and linked is not None:
   trace.append(['isLinked'])
  elif pc==0x823dc:trace.append(['isLinkSlave'])
 u.hook_add(UC_HOOK_CODE,hook)
 u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,arg&0xffffffff);u.reg_write(UC_ARM_REG_SP,0x2008000);u.reg_write(UC_ARM_REG_LR,0x100f000)
 before=bytes(u.mem_read(obj,1024));u.emu_start(address,0x100f000,count=300);assert u.reg_read(UC_ARM_REG_PC)==0x100f000;assert bytes(u.mem_read(obj,1024))==before
 result=u.reg_read(UC_ARM_REG_R0)
 if address==0x52c0c:result=bytes(u.mem_read(result,11)).split(b'\0')[0].decode()
 return result,trace
def generate():
 rows=[]
 def add(k,args,addr,updates=[],arg=0,role='server',linked=None):
  result,trace=execute(addr,updates,arg,role,linked)
  if k=='cast':result=int(result!=0)
  rows.append({'operation':k,'input':args+[0]*(4-len(args)),'result':result,'calls':trace,'object_writes':[]})
 for v in range(256):add('slave',[v],0x823dc,[(0x8c,v,1)])
 for v in [0,0xffffffff,1282304865,1400259439,1131375984,2147483648]:add('cast',[v],0x3fb48,arg=v)
 for v in [0xffffffff,2147483648,*range(33),2147483647]:add('toggle',[v],0x638ac,arg=v)
 for v in [0,1,0xffffffff,0x1000000]:add('copy',[v],0x62b90,[(0x158,v,4)])
 for v in [0xffffffff,2147483648,*range(10),2147483647]:add('map',[v],0x52c3c,arg=v)
 add('name',[],0x52c0c)
 for v in [0,1,0x1000000,0xffffffff]:
  add('panelport',[v],0x54500,[(0xbc,v,4)])
  add('surfaceport',[v],0xa6a1c,[(0x1cc,v,4)],role='client')
 for category in [0,4,0xffffffff]:
  for index in [0,1,2,3,31,32,0x7fffffff,0x80000000,0xfffffffe,0xffffffff]:
   for linked in [0,1]:
    for slave in [0,1,255]:add('send',[category,index,linked,slave],0x67764,[(0x16c,category,4),(0x170,index,4),(0x8c,slave,1),(0x88,0x1000000 if linked else 0,4)],arg=0x1000000,linked=linked)
 return rows
if __name__=='__main__':print(json.dumps(generate(),indent=2))
