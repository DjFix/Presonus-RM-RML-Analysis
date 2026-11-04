import hashlib,json,struct
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
ELF=Path('rootfs/RML16AI_Rack_13731/home/root/mixer')
def observe(selected,component,value):
 data=ELF.read_bytes()
 assert hashlib.sha256(data).hexdigest()=='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
 body=data[0x55d8c:0x55d8c+68]
 assert hashlib.sha256(body).hexdigest()=='38103b62d3ee12048363116e5111bd3729b2aa21f2815d633e0a5e966bd844a8'
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x100000)
 u.mem_write(0x5dd8c,body);u.mem_write(0x800a0,struct.pack('<I',0x81000 if selected else 0));u.mem_write(0x8208c,struct.pack('<I',value))
 u.reg_write(UC_ARM_REG_R0,0x80000);u.reg_write(UC_ARM_REG_SP,0xf0000);u.reg_write(UC_ARM_REG_LR,0x90000)
 calls=[]
 def hook(uc,pc,size,user):
  if pc==0xc558:
   calls.append(uc.reg_read(UC_ARM_REG_R0));uc.reg_write(UC_ARM_REG_R0,0x82000 if component else 0);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,hook);u.emu_start(0x5dd8c,0x90000,count=100)
 return {'return':u.reg_read(UC_ARM_REG_R0),'calls':calls}
def cases():
 return [{'selected':s,'component':c,'id':v,'observations':[observe(s,c,v),observe(s,c,v^0xffffffff)]} for s,c in [(0,0),(1,0),(1,1)] for v in [0,1,0x7fffffff,0x80000000,0xffffffff]]
if __name__=='__main__':
 import sys
 Path(sys.argv[1]).write_text(json.dumps(cases(),indent=2)+'\n')
