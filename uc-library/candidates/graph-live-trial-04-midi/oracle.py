import hashlib,json,struct
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
p=Path('rootfs/CS18_v13840/home/root/surface'); data=p.read_bytes()
assert hashlib.sha256(data).hexdigest()=='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
results=[]
for name,addr,size in [('getMappingName',0xb86bc,44),('resetAccumulation',0xb87d8,44)]:
 for flag in [0,1,255]:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM); u.mem_map(0x10000,0x300000);u.mem_write(addr,data[addr-0x8000:addr-0x8000+size]);u.mem_write(0x280000,b'\xa5'*512);u.mem_write(0x280094,bytes([flag]));u.reg_write(UC_ARM_REG_R0,0x280000);u.reg_write(UC_ARM_REG_R1,0xdeadbeef);u.reg_write(UC_ARM_REG_SP,0x2f0000);u.reg_write(UC_ARM_REG_LR,0x10000)
  u.emu_start(addr,0x10000,count=1000)
  results.append(dict(name=name,flag=flag,r0=u.reg_read(UC_ARM_REG_R0),memory=bytes(u.mem_read(0x280000,256)).hex(),address=addr,size=size,offset=addr-0x8000,range_sha256=hashlib.sha256(data[addr-0x8000:addr-0x8000+size]).hexdigest()))
Path('temp/recovery-work/graph-live-trial-04/midi-worker/native-observations.json').write_text(json.dumps(results,indent=2))
print('6 original ARM executions passed')
for name,addr,size in [('resetColors',0xbd5ec,80),('updateRecordReadyMappings',0xbd934,108),('onIdle',0xb8780,88)]:
 for variant in range(4):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x10000,0x300000);u.mem_write(addr,data[addr-0x8000:addr-0x8000+size]);base=0x280000;table=0x281000;obj=0x282000;vt=0x283000;trace=[]
  def word(a,v):u.mem_write(a,struct.pack('<I',v))
  word(base+4,0x284000);word(base+0x98,table);word(base+0xe8,table)
  if name=='resetColors':
   for i in range(variant):u.mem_write(table+i*44,b'x\0')
  else:
   word(table,obj if variant&1 else 0);word(table+12,obj+128 if variant&2 else 0);word(obj,vt);word(obj+128,vt);word(vt+40,0x10100);word(vt+68,0x10200)
  def hook(uc,pc,size,_):
   if pc in [0x76c6c,0x11acf0,0x187780,0xbd854,0x10100,0x10200]:
    trace.append([hex(pc),uc.reg_read(UC_ARM_REG_R0),uc.reg_read(UC_ARM_REG_R1),uc.reg_read(UC_ARM_REG_R2)])
    if pc==0x11acf0:uc.reg_write(UC_ARM_REG_R0,obj if variant else 0)
    if pc==0x10200:uc.reg_write(UC_ARM_REG_R0,0 if variant==1 else 0x3f800000)
    if pc==0x187780:uc.reg_write(UC_ARM_REG_R0,int(uc.reg_read(UC_ARM_REG_R0)==0))
    uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,hook);u.reg_write(UC_ARM_REG_R0,base);u.reg_write(UC_ARM_REG_SP,0x2f0000);u.reg_write(UC_ARM_REG_LR,0x10000);u.emu_start(addr,0x10000,count=10000)
  assert u.reg_read(UC_ARM_REG_PC)==0x10000
  results.append(dict(name=name,variant=variant,trace=trace,address=addr,size=size,offset=addr-0x8000,range_sha256=hashlib.sha256(data[addr-0x8000:addr-0x8000+size]).hexdigest()))
Path('temp/recovery-work/graph-live-trial-04/midi-worker/native-observations.json').write_text(json.dumps(results,indent=2))
print('18 original ARM executions passed; dependency calls stubbed and traced')
