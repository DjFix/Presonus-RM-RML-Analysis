import pathlib,json,struct,math
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
p=pathlib.Path('uc-library/candidates/graph-live-trial-05-linkcontrol'); rows=json.loads((p/'range-checks.json').read_text())['ranges']; raw=pathlib.Path('rootfs/CS18_v13840/home/root/surface').read_bytes(); cases=[]
for row in rows:
 for old,new,msg,value in [(0,0,0,0),(1,0,3,0),(1,1,3,1),(1,2,5,-1),(0,1,3,0),(2,1,5,1),(1,2,0,float('nan'))]:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x60000,0x10000);u.mem_map(0x100000,0x100000);u.mem_map(0x200000,0x10000)
  a=row['address'];u.mem_write(a,raw[row['file_offset']:row['file_offset']+row['size']]); obj=0x200000; pars=[0,0x201000,0x202000]; trace=[]
  def wr(a,v):u.mem_write(a,struct.pack('<I',v))
  wr(obj+0x64,pars[old]);wr(obj+0x58,0);wr(obj+0x5c,0)
  for q in pars[1:]:wr(q,0x203000)
  wr(0x203044,0x180000)
  # Bounded external providers: callbacks record contracts; Core instructions never executed.
  hooks={0xf6cf8:'getParameter',0x180000:'getValue',0x187780:'fcmpeq',0x11e2e0:'remove',0x11f4f0:'add',0x10e9fc:'invalidate',0xf8768:'baseChanged',0x1147a4:'baseAttributes',0xf940c:'getBitmap'}
  for h in hooks:
   if not (0x100000<=h<0x200000):u.mem_map(h&~4095,4096)
  def cb(uc,pc,size,data):
   if pc==0x20f000:uc.emu_stop();return
   if pc not in hooks:return
   name=hooks[pc];trace.append(name)
   if name=='getParameter':uc.reg_write(UC_ARM_REG_R0,pars[old])
   elif name=='getValue':uc.reg_write(UC_ARM_REG_R0,struct.unpack('<I',struct.pack('<f',value))[0])
   elif name=='fcmpeq':uc.reg_write(UC_ARM_REG_R0,int(value==0))
   elif name=='getBitmap':wr(uc.reg_read(UC_ARM_REG_R0),0)
   uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,cb);u.reg_write(UC_ARM_REG_SP,0x20e000);u.reg_write(UC_ARM_REG_LR,0x20f000);u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,pars[new]);u.reg_write(UC_ARM_REG_R2,msg)
  u.emu_start(a,0x20f000,count=1000)
  cases.append(dict(packet=row['packet'],old=old,new=new,msg=msg,value='nan' if math.isnan(value) else value,result=u.reg_read(UC_ARM_REG_R0) if row['packet']<3 else None,right=pars.index(struct.unpack('<I',u.mem_read(obj+100,4))[0]),trace=trace))
(p/'fixtures.json').write_text(json.dumps(cases,indent=2)+'\n');print(len(cases))
