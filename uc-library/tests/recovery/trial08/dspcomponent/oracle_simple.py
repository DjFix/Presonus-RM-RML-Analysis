import json,pathlib,struct
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM
from unicorn.arm_const import *
elf=pathlib.Path('rootfs/RML16AI_Rack_13731/home/root/mixer').read_bytes()
rows=[]
for name,pc,vals in [('castTo',0x3c8e4,[1148416067,1282304865,1400259439,1131375984,0,1,-1]),('getController',0x823f0,[0,1,0x12345678,0xffffffff]),('isDspParameter',0x82404,[-2147483648,-1,0,1,2,3,4,2147483647])]:
 for value in vals:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x500000);u.mem_write(0x8000,elf[:0x500000]);u.mem_map(0x1000000,0x10000);u.mem_map(0x2000000,0x10000)
  u.reg_write(UC_ARM_REG_SP,0x2008000);u.reg_write(UC_ARM_REG_LR,0x100f000);u.reg_write(UC_ARM_REG_R0,0x1000000)
  if name=='castTo':u.reg_write(UC_ARM_REG_R1,value&0xffffffff)
  if name=='getController':u.mem_write(0x10000b0,struct.pack('<I',value))
  if name=='isDspParameter':
   u.reg_write(UC_ARM_REG_R1,0x1001000);u.mem_write(0x100100c,struct.pack('<I',0x1002000));u.mem_write(0x1002000,struct.pack('<i',value))
  u.emu_start(pc,0x100f000,count=1000)
  rows.append(dict(method=name,input=value,result=u.reg_read(UC_ARM_REG_R0)))
p=pathlib.Path('uc-library/tests/recovery/trial08/dspcomponent/native-simple.json');p.write_text(json.dumps(rows,indent=2));print(len(rows))
