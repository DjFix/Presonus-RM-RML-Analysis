"""Execute original application instructions only; explicit bounded provider hooks.
Private emulated memory has no hardware/syscall passthrough or Core execution.
"""
import hashlib,json,struct,itertools
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[4]; T=Path(__file__).resolve().parent
ELF=R/'rootfs/RML16AI_Rack_13731/home/root/mixer'; SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
RAW=ELF.read_bytes(); assert hashlib.sha256(RAW).hexdigest()==SHA
P=R/'temp/recovery-work/rolling200-03/enablement01/prepared01/packets'
REQUESTS=[json.loads((p/'request.json').read_text()) for p in sorted(P.iterdir())]
RANGES=[]
with ELF.open('rb') as f:
 e=ELFFile(f)
 for req in REQUESTS:
  name=req['targets'][0]['mangled']; s=next(s for s in e.get_section_by_name('.symtab').iter_symbols() if s.name==name); sec=e.get_section(s['st_shndx']); off=sec['sh_offset']+s['st_value']-sec['sh_addr']
  RANGES.append(dict(mangled=name,address=s['st_value'],size=s['st_size'],section=sec.name,file_offset=off,sha256=hashlib.sha256(RAW[off:off+s['st_size']]).hexdigest()))
 SEGS=[(s['p_vaddr'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
def execute(which,inp):
 msg,nd,nt,*bits=inp; u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x400000)
 for addr,data in SEGS:
  if addr<0x400000:u.mem_write(addr,data[:0x400000-addr])
 u.mem_protect(0,0x400000,5);u.mem_map(0x400000,0x40000)
 obj=0x400000; dep=0x401000; tar=0x402000; vt=0x403000; stop=0x430000
 def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def rd(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 for a,v in [(obj+8,tar),(obj+12,nt),(obj+28,dep),(obj+32,nd),(vt+0x44,stop+4),(vt+0x24,stop+8)]:w(a,v)
 for i in range(3):w(0x404000+i*0x100,vt)
 w(0x405000,vt)
 for i in range(nd):w(dep+4*i,0x404000+(i%3)*0x100)
 for i in range(nt):w(tar+4*i,0x405000)
 events=[];calls=[];pcs=[];writes=[]
 allowed=[(r['address'],r['address']+r['size']) for r in RANGES]
 def hook(uc,pc,size,data):
  if pc==stop:u.emu_stop();return
  if any(a<=pc<b for a,b in allowed):pcs.append(pc);return
  r0=u.reg_read(UC_ARM_REG_R0);r1=u.reg_read(UC_ARM_REG_R1)
  if pc==stop+4:
   i=(r0-0x404000)//0x100;events.append('g'+str(i));value=bits[i]
  elif pc==stop+8:events.append('e3:'+str(r1));value=0
  elif pc==0x1578e0:value=int(struct.unpack('<f',struct.pack('<I',r0))[0]==struct.unpack('<f',struct.pack('<I',r1))[0])
  elif pc==0x4c1bc:
   base=r0;value=rd(r1);calls.append(['append',base-obj,value]);count=rd(base+4);w(rd(base)+count*4,value);w(base+4,count+1);value=1
  elif pc==0x11d4f4:calls.append(['addObserver',r0,r1]);value=0
  elif pc==0x11c2e4:calls.append(['removeObserver',r0,r1]);value=0
  elif pc==0x12740:calls.append(['destroyVector',r0-obj]);value=0
  else:raise AssertionError(hex(pc))
  u.reg_write(UC_ARM_REG_R0,value&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def write(uc,access,a,size,value,data):
  assert 0x400000<=a<0x420000,hex(a);writes.append([a,size,value])
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
 for reg,val in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_R1,0x404000),(UC_ARM_REG_R2,msg&0xffffffff),(UC_ARM_REG_SP,0x41ff00),(UC_ARM_REG_LR,stop)]:u.reg_write(reg,val)
 u.emu_start(RANGES[which]['address'],stop,count=2000);assert u.reg_read(UC_ARM_REG_PC)==stop
 return dict(which=which,input=inp,events=events,calls=calls,executed_pcs=pcs,writes=writes)
def cases():
 values=[0,0x80000000,0x3f800000,0xbf800000,0x7f800000,0xff800000,0x7fc00001,1,0x80000001]
 result=[]
 for msg,nd,nt,b in itertools.product([-1,0,1,2,3,4,5,6,99],range(5),range(4),values):
  result.append(execute(2 if msg==99 else 0,[msg,nd,nt,b,0x3f800000,0]))
 for which in [1,3,4,5]:
  for obs,nd,nt in itertools.product([0,1],range(5),range(3)):
   c=execute(which,[obs,nd,nt,0,0,0]);calls=c['calls']
   if which==1:assert [x[0] for x in calls]==['append']+(['addObserver'] if obs else [])
   elif which==3:assert [x[0] for x in calls]==['append']
   else:assert [x[0] for x in calls]==['removeObserver']*nd+['destroyVector']*2;assert [x[1] for x in calls[-2:]]==[24,4];assert [x[1] for x in calls[:-2]]==[0x404000+(i%3)*0x100 for i in range(nd)]
   result.append(c)
 return result
if __name__=='__main__':
 data=dict(elf_sha256=SHA,ranges=RANGES,cases=cases());(T/'fixtures.json').write_text(json.dumps(data,separators=(',',':'))+'\n');print(len(data['cases']))
