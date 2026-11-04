"""Execute original app ARM only; pinned CCL boundaries are independent models."""
import argparse,hashlib,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ELF='rootfs/RML16AI_Rack_13731/home/root/mixer'
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
RANGE_SHA='0f37549f17dcda15ea26357a76a90d1cf9cecc6402f3990a90cb763593faf72d'
def signed(v):return v if v < 0x80000000 else v-0x100000000
def run(v):
 data=Path(ELF).read_bytes();assert hashlib.sha256(data).hexdigest()==SHA
 with open(ELF,'rb') as f:
  elf=ELFFile(f);sec=elf.get_section(12);off=sec['sh_offset']+0x359a8-sec['sh_addr'];assert off==0x2d9a8
  assert hashlib.sha256(data[off:off+180]).hexdigest()==RANGE_SHA
  segments=[(s['p_vaddr'],s.data()) for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x600000)
 for at,b in segments:u.mem_write(at,b)
 u.mem_map(0x1000000,0x200000)
 obj=0x1000000;line=obj+0x1000;vt=obj+0x2000;channel=obj+0x3000;param=obj+0x4000
 def w(at,n):u.mem_write(at,struct.pack('<I',n&0xffffffff))
 def r(at):return struct.unpack('<I',u.mem_read(at,4))[0]
 def text(at):
  out=bytearray()
  while True:
   c=bytes(u.mem_read(at,1));at+=1
   if c==b'\0':return out.decode()
   out.extend(c)
 literals={hex(at):text(at) for at in (0x35b15c,0x16de6c,0x158f94)}
 assert literals=={'0x35b15c':'','0x16de6c':'ch%d','0x158f94':'line'}
 w(obj,vt);w(line,vt);w(vt+0x14,0x1100000);w(obj+0x1d8,v['count'])
 events=[];writes=[];current=0;tag=None
 def memory(u,access,at,size,value,_):
  if at==obj+0x1d8:writes.append(value)
 u.hook_add(UC_HOOK_MEM_WRITE,memory)
 def hook(u,pc,size,_):
  nonlocal current,tag
  a=u.reg_read(UC_ARM_REG_R0);b=u.reg_read(UC_ARM_REG_R1)
  if pc==0x1100100:u.emu_stop();return
  if pc==0x1debc:
   # CStringBuffer<32>(char const*) preferred provider semantics; no Core ELF execution.
   u.mem_write(a,text(b).encode()[:31]+b'\0')
  elif pc==0x3987c:
   assert text(b)=='ch%d';current=signed(u.reg_read(UC_ARM_REG_R2))
   u.mem_write(a,(text(a)+('ch%d'%current)).encode()[:31]+b'\0')
  elif pc==0x1100000:
   name=text(b);actor='root' if a==obj else 'line';events.append(['lookup',actor,name])
   if a==obj:assert name=='line';result=line if v['line'] else 0
   else:
    assert a==line and name=='ch%d'%current
    result=channel if current in v['channels'] else 0
   if result==channel:w(channel,vt)
   u.reg_write(UC_ARM_REG_R0,result)
  elif pc==0x119c4c:
   assert a==channel and b==0x130;tag=b
   u.reg_write(UC_ARM_REG_R0,param)
  elif pc==0x11dc28:
   assert a==param and tag==0x130
   # Pinned Parameter::changed() sends controller feedback first then observers.
   if v['feedback']:events.append(['controller',current,tag,3])
   events.append(['observer',current,tag,3])
   if current==v['mutate_at']:
    w(obj+0x1d8,v['mutate_count']);writes.append(v['mutate_count']&0xffffffff)
  else:return
  u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,hook)
 u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_SP,0x11ff000);u.reg_write(UC_ARM_REG_LR,0x1100100)
 u.emu_start(0x359a8,0,count=100000)
 assert u.reg_read(UC_ARM_REG_PC)==0x1100100,'bounded execution did not terminate'
 return {'events':events,'count':r(obj+0x1d8),'count_writes':writes},literals

def generate():
 inputs=[]
 def add(count,line=True,channels=None,mutate_at=0,mutate_count=0,feedback=False):
  inputs.append(dict(count=count,line=line,channels=list(range(1,max(0,min(count,64))+1)) if channels is None else channels,mutate_at=mutate_at,mutate_count=mutate_count,feedback=feedback))
 for count in (-2147483648,-1,0,1,2,10,32):
  for line in (False,True):add(count,line)
 add(5,channels=[]);add(6,channels=[2,4,6]);add(4,channels=[1,3],feedback=True)
 for initial,at,new in ((4,1,0),(4,2,-1),(2,1,5),(5,2,2),(2147483647,1,0),(1,1,-2147483648)):
  add(initial,channels=[1,2,3,4,5],mutate_at=at,mutate_count=new,feedback=True)
 cases=[]
 for v in inputs:
  observed,literals=run(v);cases.append({'inputs':v,'observed':observed})
 return {'elf':ELF,'elf_sha256':SHA,'range':{'address':0x359a8,'size':180,'section':'.text','file_offset':0x2d9a8,'sha256':RANGE_SHA},'literals':literals,'oracle':'Original ARM application instructions in Unicorn; independent source-based CCL boundaries, no firmware Core execution','cases':cases}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();Path(a.out).write_text(json.dumps(generate(),indent=2)+'\n')
