import argparse,hashlib,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ELF="rootfs/RML16AI_Rack_13731/home/root/mixer"
SHA="9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
def run(address,mode=0,index=0,present=True,a=0,b=0,msg=0,own=False,name="other",value=0):
 data=Path(ELF).read_bytes();assert hashlib.sha256(data).hexdigest()==SHA
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x600000)
 with open(ELF,"rb") as f:
  e=ELFFile(f)
  for seg in e.iter_segments():
   if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
 u.mem_map(0x1000000,0x200000);obj=0x1000000;manager=obj+0x1000;listener=obj+0x2000;vt=obj+0x3000;param=obj+0x4000;info=obj+0x5000
 def w(at,n):u.mem_write(at,struct.pack('<I',n&0xffffffff))
 def r(at):return struct.unpack('<I',u.mem_read(at,4))[0]
 w(obj+0x98,manager);w(manager+0x380,manager+0x800);w(manager+0x800,vt);w(vt,0x1100000);w(manager+0x174,0x98765432)
 w(obj+0xb0,mode);w(obj+0xa0,listener if present else 0);u.mem_write(listener,bytes([index]));w(obj+0x9c,listener if present else 0)
 if address in (0xa8e0c,0xa8e88,0xa8f0c):w(listener,vt);w(vt+0x10,0x1100004)
 w(param,vt);w(vt+0x44,0x1100008);w(param+0xc,info);u.mem_write(info+8,name.encode()+b'\0')
 u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,param if address==0xa928c else a&0xffffffff);u.reg_write(UC_ARM_REG_R2,msg if address==0xa928c else b&0xffffffff);u.reg_write(UC_ARM_REG_SP,0x11ff000);u.reg_write(UC_ARM_REG_LR,0x1100100)
 trace=[];writes=[]
 def write_hook(u,access,at,size,value,unused):
  if obj<=at<obj+0x100:writes.append({"offset":at-obj,"size":size,"value":value})
 u.hook_add(UC_HOOK_MEM_WRITE,write_hook)
 def hook(u,pc,size,unused):
  if pc==0x1100100:u.emu_stop();return
  if pc==0x1100000:
   ptr=u.reg_read(UC_ARM_REG_R1);n=r(ptr+4);assert n in (24,28);trace.append(['packet',list(struct.unpack('<'+'I'*(n//4),u.mem_read(ptr,n)))])
  elif pc==0x1100004:trace.append(['release'])
  elif pc==0x11a53c:trace.append(['core_cleanup'])
  elif pc==0xac10:trace.append(['delete'])
  elif pc==0x116a38:trace.append(['debug',u.reg_read(UC_ARM_REG_R1)])
  elif pc==0x11c1d4:u.reg_write(UC_ARM_REG_R0,obj+4 if own else obj+0x6000)
  elif pc==0x11c2e4:trace.append(['remove_observer'])
  elif pc==0xaf70:
   def cstr(at):
    out=b''
    while u.mem_read(at,1)!=b'\0':out+=u.mem_read(at,1);at+=1
    return out
   u.reg_write(UC_ARM_REG_R0,0 if cstr(u.reg_read(UC_ARM_REG_R0))==cstr(u.reg_read(UC_ARM_REG_R1)) else 1)
  elif pc==0x1100008:u.reg_write(UC_ARM_REG_R0,struct.unpack('<I',struct.pack('<f',value))[0])
  elif pc==0x157958:u.reg_write(UC_ARM_REG_R0,int(value)&0xffffffff)
  elif pc==0xa8f88:trace.append(['update']);u.reg_write(UC_ARM_REG_PC,0x1100100);return
  else:return
  u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,hook);u.emu_start(address,0,count=10000)
 assert u.reg_read(UC_ARM_REG_PC)==0x1100100
 return {'memory_writes':writes,'trace':trace,'mode':r(obj+0xb0),'vptr_writes':[r(obj),r(obj+4),r(obj+0x88)] if address in (0xa8e0c,0xa8e88,0xa8f0c,0x1cfe8) else []}
def generate():
 cases=[]
 def add(kind,address,**kw):cases.append({'kind':kind,'address':address,'inputs':kw,'observed':run(address,**kw)})
 for mode in (0,1,2,3,-1):add('static',0xa7fd0,mode=mode)
 for present in (False,True):
  for index in (0,1,17,255):add('route',0xa854c,present=present,index=index)
 for a,b in ((-1,0),(-1,99),(0,0),(1,2),(2147483647,-2147483648)) :add('spectrum',0xa8454,a=a,b=b)
 for addr in (0x1cfe8,0xa8e0c,0xa8e88,0xa8f0c):
  for present in (False,True):add('destructor',addr,present=present)
 for msg,own,name,value in ((0,False,'other',0),(3,True,'linkstate',2),(3,False,'other',2),(3,False,'linkstate',2),(5,False,'other',0)):
  add('param',0xa928c,msg=msg,own=own,name=name,value=value)
 native_only=[c for c in cases if c['kind']=='param'];cases=[c for c in cases if c['kind']!='param']
 return {'native_only_cases':native_only,'oracle':'Unicorn exact original ARM app instructions; Core/provider calls intercepted, never executed from firmware','elf_sha256':SHA,'cases':cases}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();Path(a.out).write_text(json.dumps(generate(),indent=2)+'\n')
