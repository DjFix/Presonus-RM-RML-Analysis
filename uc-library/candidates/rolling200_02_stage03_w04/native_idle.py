from pathlib import Path
import json, hashlib, struct, itertools
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import *
R=Path.cwd();O=R/'evidence/recovery/2026-11-05/rolling200-02/stage03-w04/native-idle';O.mkdir(exist_ok=True)
p=R/'rootfs/CS18_v13840/home/root/surface';data=p.read_bytes();sha=hashlib.sha256(data).hexdigest();assert sha=='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
raw=data[0x5d9b0:0x5d9b0+100];assert hashlib.sha256(raw).hexdigest()=='78372c876a37da69cac69bb398fdc7596406e9c46f61739cb01311ed9ab3e181'
u=Uc(UC_ARCH_ARM,UC_MODE_ARM);obj=0x300000;stack=0x400000;stop=0x500000
for p,n in [(0x65000,0x1000),(obj,0x1000),(stack,0x1000),(stop,0x1000),(0xf8000,0x1000),(0x12000,0x1000),(0x11000,0x1000),(0x10e000,0x1000)]:u.mem_map(p,n)
u.mem_write(0x659b0,raw);records=[];trace=[];state={}
def hook(uc,pc,size,_):
 if pc==stop:uc.emu_stop();return
 names={0xf8588:'Control::onIdle',0x12110:'DelayTimer::isLongEnoughYet',0x11ff8:'DelayTimer::reset',0x12228:'DelayTimer::beginAction',0x10e9fc:'View::invalidate'}
 if pc in names:
  r0=uc.reg_read(UC_ARM_REG_R0);r1=uc.reg_read(UC_ARM_REG_R1);trace.append(dict(call=names[pc],r0=r0,r1=r1,dirty=bytes(uc.mem_read(obj+0x84,1))[0]))
  if pc==0x12110:assert r0==obj+0x88;uc.reg_write(UC_ARM_REG_R0,state['elapsed'])
  if pc==0x12228:assert r1==0xbf800000 and r0==obj+0x88
  uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
 assert 0x659b0<=pc<0x65a14,hex(pc)
u.hook_add(UC_HOOK_CODE,hook)
for elapsed,dirty in itertools.product([0,1],[0,1]):
 state={'elapsed':elapsed};trace=[];u.mem_write(obj,b'\xa5'*256);u.mem_write(obj+0x84,bytes([dirty]));before=bytes(u.mem_read(obj,256))
 u.reg_write(UC_ARM_REG_CPSR,0x10);u.reg_write(UC_ARM_REG_SP,stack+4000);u.reg_write(UC_ARM_REG_LR,stop);u.reg_write(UC_ARM_REG_R0,obj);u.emu_start(0x659b0,stop,count=200);assert u.reg_read(UC_ARM_REG_PC)==stop
 after=bytes(u.mem_read(obj,256));assert before[:132]==after[:132] and before[133:]==after[133:]
 records.append(dict(elapsed=elapsed,dirty=dirty,dirty_after=after[132],calls=trace))
(O/'cases.json').write_text(json.dumps(records,indent=2)+'\n');(O/'validation.json').write_text(json.dumps(dict(passed=True,cases=len(records),elf_sha256=sha,address=0x659b0,size=100,file_offset=0x5d9b0,section='.text',range_sha256=hashlib.sha256(raw).hexdigest(),limitations='Original app ARM instructions executed; actual provider bodies captured at explicit call boundaries, timer elapsed predicate supplied; no Core binary reconstruction, no layout/ABI/hardware claim.'),indent=2)+'\n');print(json.dumps(dict(passed=True,cases=len(records))))
