import json,hashlib,struct,pathlib
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
base=pathlib.Path('uc-library/candidates/graph-live-trial-04-panel')
elf=pathlib.Path('rootfs/RML16AI_Rack_13731/home/root/mixer').read_bytes()
assert hashlib.sha256(elf).hexdigest()=='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
bodies=[]
for i in range(1,6):
 p=json.load(open(f'temp/recovery-work/graph-live-trial-04/trial04_panel_{i}-packet/native-context.json'))
 b=list(p['bodies'].values())[0]; raw=elf[b['file_offset']:b['file_offset']+b['size']]; assert hashlib.sha256(raw).hexdigest()==b['bytes_sha256']; bodies.append((b,raw))
rows=[]
for method,(b,raw) in enumerate(bodies):
 for n in [-1,0,1,3,12]:
  for flag in [0,1]:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x110000);u.mem_map(0x200000,0x10000)
   for bb,rr in bodies:u.mem_write(bb['address'],rr)
   def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
   obj,group,control,vt=0x200000,0x201000,0x202000,0x203000
   w(obj,vt);w(obj+0x90,0x204000);w(vt+0x38,0xa0010);w(vt+0x10,0xa0020);w(control,vt);w(group+4,n)
   u.reg_write(UC_ARM_REG_SP,0x20f000);u.reg_write(UC_ARM_REG_LR,0xa0000)
   for reg,val in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_R1,group if method==0 else 7),(UC_ARM_REG_R2,9),(UC_ARM_REG_R3,flag)]:u.reg_write(reg,val)
   trace=[]
   def hook(u,pc,size,data):
    if pc==0xa0000:u.emu_stop();return
    args=[u.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2]]
    names={0x8db08:'controlCount',0x8d9a8:'controlAt',0x8db34:'groupCount',0x8db48:'groupAt',0x8e4ac:'findGroup',0x8d9ec:'byTag',0xacf4:'cast',0x8fbc8:'blink',0xa0010:'slot38',0xa0020:'slot10'}
    if pc not in names:return
    name=names[pc]
    trace.append([name,args])
    ret=0
    if name in ['controlCount','groupCount']:ret=n
    elif name=='groupAt':ret=group
    elif name=='controlAt':ret=control if args[1]%2==0 else 0
    elif name=='findGroup':ret=group
    elif name=='byTag':ret=control if n!=0 else 0
    elif name=='cast':ret=control if n>0 else 0
    u.reg_write(UC_ARM_REG_R0,ret&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
   u.hook_add(UC_HOOK_CODE,hook);u.emu_start(b['address'],0,count=10000)
   assert u.reg_read(UC_ARM_REG_PC)==0xa0000
   rows.append({'method':method,'count_or_tag':n,'flag':flag,'trace':trace})
(base/'fixtures.json').write_text(json.dumps(rows,indent=2)+'\n')
(base/'native-ranges.json').write_text(json.dumps([b for b,r in bodies],indent=2)+'\n')
print('original ARM executions',len(rows))
