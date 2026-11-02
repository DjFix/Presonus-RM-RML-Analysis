import json,pathlib,struct
from unicorn import *
from unicorn.arm_const import *
elf=pathlib.Path('rootfs/RML16AI_Rack_13731/home/root/mixer').read_bytes();rows=[]
for method,pc in [('construct',0x82588),('syncValues',0x82428),('syncReadouts',0x825a0),('load',0x82ecc),('onIdle',0x828e8),('paramChanged',0x827f8),('constructor',0x82ab4)]:
 for flag in range(4):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x500000);u.mem_write(0x8000,elf[:0x500000]);u.mem_map(0x1000000,0x10000);u.mem_map(0x2000000,0x10000)
  def put(a,v):u.mem_write(a,struct.pack('<I',v))
  obj=0x1000000;ctl=0x1001000;vt=0x1002000;trace=[]
  put(obj,vt);put(obj+0xb0,ctl if flag else 0);put(obj+0xb4,obj+0xbc);put(obj+0xb8,0);put(ctl,vt)
  for off in [12,16,24,60,64,68]:put(vt+off,0x1004000+off)
  u.reg_write(UC_ARM_REG_SP,0x2008000);u.reg_write(UC_ARM_REG_LR,0x100f000);u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,flag);u.reg_write(UC_ARM_REG_R2,ctl)
  hooks={0x82e94:'base_load',0x82898:'base_idle',0x8275c:'base_param',0x82a48:'base_constructor'}
  def hook(uc,a,s,d):
   if a in hooks or 0x1004000<=a<0x1004100:
    what=hooks.get(a,'slot_'+hex(a-0x1004000));trace.append([what,uc.reg_read(UC_ARM_REG_R1),uc.reg_read(UC_ARM_REG_R2)])
    uc.reg_write(UC_ARM_REG_R0,flag if a==0x100403c else 37 if a==0x82e94 else 0);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,hook);u.emu_start(pc,0x100f000,count=10000)
  rows.append(dict(method=method,flag=flag,result=u.reg_read(UC_ARM_REG_R0),count=struct.unpack('<I',u.mem_read(obj+0xb8,4))[0],trace=trace))
pathlib.Path('uc-library/tests/recovery/trial08/dspcomponent/native-control.json').write_text(json.dumps(rows,indent=2));print(len(rows))
