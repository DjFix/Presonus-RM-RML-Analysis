from pathlib import Path
import json,hashlib,struct,itertools,math
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
BASE=Path('uc-library/candidates/graph-live-trial-04-mutegroup')
elf=Path('rootfs/RML16AI_Rack_13731/home/root/mixer').read_bytes()
assert hashlib.sha256(elf).hexdigest()=='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
packets=[json.loads(Path(f'temp/recovery-work/graph-live-trial-04/trial04_mutegroup_{i}-packet/native-context.json').read_text()) for i in range(1,6)]
ranges=[]
for p in packets:
 for key,b in p['bodies'].items():
  data=elf[b['file_offset']:b['file_offset']+b['size']];assert hashlib.sha256(data).hexdigest()==b['bytes_sha256'];ranges.append({k:b[k] for k in ['address','size','section','file_offset','bytes_sha256']})
def bits(v):return struct.unpack('<I',struct.pack('<f',v))[0]
def fl(v):return struct.unpack('<f',struct.pack('<I',v))[0]
def run(method,active,status,alternate,maximum,values):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x10000,0x190000);u.mem_map(0x200000,0x10000)
 for p in packets:
  for b in p['bodies'].values():u.mem_write(b['address'],elf[b['file_offset']:b['file_offset']+b['size']])
 def w(a,v):u.mem_write(a,struct.pack('<I',v))
 obj=0x200000;params=[0x201000+i*0x100 for i in range(3+len(values))];vt=0x204000
 for i,slot in enumerate([0x3c,0x44,0x50,0x58,0x5c]):w(vt+slot,0x180000+i*4)
 vals=[active,status,alternate]+list(values);maxs=[maximum]*len(vals)
 for p in params:w(p,vt)
 w(obj+4,params[0]);w(obj+8,params[1]);w(obj+12,params[2]);w(obj+20,0x205000);w(obj+24,len(values))
 for i,p in enumerate(params[3:]):w(0x205000+i*4,p)
 trace=[]
 def hook(u,a,size,data):
  r0=u.reg_read(UC_ARM_REG_R0);r1=u.reg_read(UC_ARM_REG_R1);r2=u.reg_read(UC_ARM_REG_R2)
  result=None
  if a in [0x1578e0,0x157940,0x157928]:
   x,y=fl(r0),fl(r1);result=int((x==y) if a==0x1578e0 else ((x>y) if a==0x157940 else (x>=y)))
  elif a==0x157474:result=bits(float(r0))
  elif 0x180000<=a<0x180014:
   i=params.index(r0);slot=[0x3c,0x44,0x50,0x58,0x5c][(a-0x180000)//4];trace.append([slot,i,r1,r2])
   if slot==0x3c:result=bits(maxs[i])
   elif slot==0x44:result=bits(vals[i])
   elif slot==0x50:maxs[i]=fl(r1);result=0
   elif slot==0x58:vals[i]=fl(r1);result=0
   else: vals[i]=0.;result=0
  elif a==0x11dbd4:trace.append(['rangeChanged',params.index(r0)]);result=0
  elif a==0x775f0:trace.append(['provider.empty',r0-obj]);w(obj+24,0);result=0
  elif a==0x190000:u.emu_stop();return
  if result is not None:u.reg_write(UC_ARM_REG_R0,result);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,hook);u.reg_write(UC_ARM_REG_SP,0x20f000);u.reg_write(UC_ARM_REG_LR,0x190000);u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,params[1]);u.emu_start(ranges[method]['address'],0x190004,count=10000)
 return {'result':u.reg_read(UC_ARM_REG_R0),'values':vals[:3],'maximum':maxs[1],'count':struct.unpack('<I',u.mem_read(obj+24,4))[0],'trace':trace}
cases=[]
for method in range(5):
 for active,status,alt,maximum in itertools.product([0.,1.],[-1.,0.,1.],[-1.,0.,1.],[0.,2.]):
  for values in [[],[0.],[1.],[0.,1.],[1.,1.]]:
   inp=[method,active,status,alt,maximum,values];out=run(*inp);cases.append({'input':inp,'native':out})
(BASE/'fixtures.json').write_text(json.dumps(cases,indent=2));(BASE/'ranges.json').write_text(json.dumps(ranges,indent=2));print('native cases',len(cases))
