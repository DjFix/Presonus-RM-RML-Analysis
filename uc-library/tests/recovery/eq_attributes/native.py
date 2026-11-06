"""Offline exact app instruction oracle. Provider boundaries intercepted before execution.
No guest Core, system calls, hardware or reconstructed C++ supplies expectations.
"""
import hashlib,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[4]; T=Path(__file__).resolve().parent
ELF=R/'rootfs/CS18_v13840/home/root/surface'; SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
NAME='_ZN8Presonus9EQControl13setAttributesERKN4Core8Portable10AttributesE'
OBJ=0x400000;STACK=0x500000;STOP=0x600000;A=0x410000;PARAM=0x420000;BAND=0x430000;QUEUE=0x440000;CTL=0x450000;BITMAP=0x460000;VT=0x470000;STYLE=0x480000
RAW=ELF.read_bytes();assert hashlib.sha256(RAW).hexdigest()==SHA
with ELF.open('rb') as f:
 e=ELFFile(f);s=next(s for s in e.get_section_by_name('.symtab').iter_symbols() if s.name==NAME);sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr']
 RANGE={'address':s['st_value'],'size':s['st_size'],'file_offset':off,'section_index':s['st_shndx'],'section':sec.name,'sha256':hashlib.sha256(RAW[off:off+s['st_size']]).hexdigest()}
assert RANGE=={'address':450424,'size':1788,'file_offset':417656,'section_index':12,'section':'.text','sha256':'9897fcf9a80bf68391d5d3bfbd2064998b75a37dc5f9c7612d410889a56487c8'}
def execute(c):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x300000)
 with ELF.open('rb') as f:
  for seg in ELFFile(f).iter_segments():
   if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
 u.mem_protect(0,0x300000,5);u.mem_map(OBJ,0x90000);u.mem_map(STACK,0x10000);u.mem_map(STOP,0x1000)
 def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def si(v):return v if v<2**31 else v-2**32
 def fl(v):return struct.unpack('<I',struct.pack('<f',float(v)))[0]
 def string(a):
  if not a:return None
  b=bytearray()
  while len(b)<128:
   x=u.mem_read(a,1)[0];a+=1
   if not x:break
   b.append(x)
  return b.decode()
 strings={};n=0
 def st(s):
  nonlocal n
  if s is None:return 0
  if s not in strings:
   strings[s]=A+0x8000+n;n+=len(s)+1;u.mem_write(strings[s],s.encode()+b'\0')
  return strings[s]
 flags,count,entries,repeat=c
 attrs={A:{'numBands':count,'bufferedDraw':int(bool(flags&1)),'handleDiameter':17}}
 if flags&2:attrs[A]['hpf']='hp' if flags&4 else 'missing'
 if flags&(8|2048):attrs[A]['displayRange']=A+0x100;attrs[A+0x100]={'minFreq':20} if flags&2048 else {'minFreq':20,'maxFreq':20000,'minLevel':-24,'maxLevel':18}
 if flags&16:attrs[A]['image']='img'
 if flags&32:attrs[A]['handle']='handle'
 rect=[3,-4,3 if flags&64 else 83,-4 if flags&64 else 46]
 if flags&128:attrs[A]['offLineColor']=0x7f332211
 keys=['type','gain','q','freq','active','selected']; queue=[]
 for i in range(entries):
  ptr=A+0x400+i*0x100; record={k:f'{k}{i}' for k in keys if not(flags&256 and k in ['q','selected'])}
  if flags&512:record['handle']='band'
  attrs[ptr]=record
  # A mixed queue begins with one non-Attributes record.
  if i==0 and flags&1024:queue.append(None)
  queue.append(ptr)
 qitems=QUEUE+0x100
 for i,a in enumerate(queue):
  v=QUEUE+0x1000+i*32;w(qitems+i*4,v);u.mem_write(v+4,struct.pack('<H',5 if a else 1));w(v+8,a or 42)
 w(QUEUE+8,qitems);w(QUEUE+12,len(queue))
 if queue:attrs[A]['bands']=QUEUE
 u.mem_write(OBJ+0x2c,struct.pack('<4i',0,0,100,50))
 w(OBJ,VT);w(VT+0x18,STOP+8);w(OBJ+0x5c,CTL);w(CTL,VT+0x100);w(VT+0x10c,STOP+4)
 w(OBJ+0x70,0);w(OBJ+0x78,PARAM);w(OBJ+0xf0,BAND);w(OBJ+0x68,10);w(STYLE+4,0xffa0b0c0)
 for i,dim in enumerate([(22,30,3),(33,40,4),(12,24,2)]):
  p=BITMAP+i*0x100;w(p+8,dim[2]);w(p+0xc,dim[0]);w(p+0x10,dim[1]);w(p+0x34,0)
 bitmap_names={'img':BITMAP,'handle':BITMAP+0x100,'band':BITMAP+0x200}
 names={};nextid=1
 def parameter(name):
  nonlocal nextid
  if not name or name=='missing':return 0
  if name not in names:names[name]=nextid;nextid+=1
  return CTL+0x1000+names[name]*32
 def pid(p):return (p-CTL-0x1000)//32 if p else 0
 for tag in [0,1,2]:parameter('hpf'+str(tag))
 trace=[];sets=[];pcs=[];writes=[];counts=[]
 def init():
  left,top,right,bottom=struct.unpack('<4i',u.mem_read(OBJ+0x2c,16))
  if right<=left or bottom<=top:return
  for i in range(10):
   old=r(BAND+i*40+32)
   if old:w(old+0x34,r(old+0x34)-1)
   u.mem_write(BAND+i*40,b'\0'*40)
 def code(uc,address,size,unused):
  regs=[uc.reg_read(z) for z in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]];a,b,d,g=regs
  result=None;high=0
  if address==STOP:uc.emu_stop();return
  if address==0x124324:
   key=string(b);v=attrs[a].get(key,0);assert isinstance(v,int);result=v;high=0xffffffff if v<0 else 0
  elif address in [0x124200,0x124184,0x124108]:
   key=string(b);v=attrs[a].get(key);result=st(v) if address==0x124200 else v or 0
  elif address==STOP+4:
   name=string(b);assert string(d)=='Param';result=parameter(name);trace.append([name,pid(result)])
  elif address==0x6dbe0:counts.append(r(OBJ+0x70));init()
  elif address==0x1147a4:
   u.mem_write(OBJ+0x2c,struct.pack('<4i',*rect));init()
  elif address==0x6df0c:w(OBJ+0x118,b);init()
  elif address==0x6d070:
   # Capture the actual native call argument and pre-call dirty/force/image phase.
   slots=[d,g]+[r(uc.reg_read(UC_ARM_REG_SP)+i*4) for i in range(4)]
   sets.append([b,[pid(p) for p in slots],r(BAND+b*40+32),u.mem_read(BAND+b*40+36,1)[0]])
  elif address==0x11f24c:result=parameter('hpf'+str(b))
  elif address==0xf940c:
   name=attrs[b].get(string(d));image=bitmap_names.get(name,0);w(a,image)
   if image:w(image+0x34,r(image+0x34)+1)
  elif address==0x1864b8:result=int(si(a)/si(b))
  elif address in [0x187344,0x187314]:
   val=a+si(b)*2**32 if address==0x187344 else si(a);result=fl(val)
  elif address==0xf92b4:
   if b:
    rr=list(struct.unpack('<4i',u.mem_read(a,16)));rr[2]=rr[0]+r(b+0xc);rr[3]=rr[1]+r(b+0x10)//r(b+8);u.mem_write(a,struct.pack('<4i',*rr));result=1
   else:result=0
  elif address==STOP+8:
   u.mem_write(OBJ+0x2c,bytes(u.mem_read(b,16)));init()
  elif address==0x10f4b4:result=STYLE
  elif address==0x11422c:result=attrs[a].get(string(b),d)
  else:
   assert RANGE['address']<=address< RANGE['address']+RANGE['size'],('unbound PC',hex(address))
   pcs.append(address);return
  if result is not None:uc.reg_write(UC_ARM_REG_R0,result&0xffffffff);uc.reg_write(UC_ARM_REG_R1,high)
  uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 def write(uc,access,address,size,value,unused):
  assert OBJ<=address<OBJ+0x90000 or STACK<=address<STACK+0x10000
  if OBJ<=address<OBJ+0x200:writes.append([address-OBJ,size,value])
 u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
 u.reg_write(UC_ARM_REG_R0,OBJ);u.reg_write(UC_ARM_REG_R1,A);u.reg_write(UC_ARM_REG_SP,STACK+0xff00);u.reg_write(UC_ARM_REG_LR,STOP)
 u.emu_start(RANGE['address'],STOP,count=30000);assert u.reg_read(UC_ARM_REG_PC)==STOP
 if repeat:
  flags ^= 33
  attrs[A]['bufferedDraw']=int(bool(flags&1))
  if flags&32:attrs[A]['handle']='handle'
  else:attrs[A].pop('handle',None)
  u.reg_write(UC_ARM_REG_R0,OBJ);u.reg_write(UC_ARM_REG_R1,A);u.reg_write(UC_ARM_REG_SP,STACK+0xff00);u.reg_write(UC_ARM_REG_LR,STOP)
  u.emu_start(RANGE['address'],STOP,count=30000);assert u.reg_read(UC_ARM_REG_PC)==STOP
 def f(o):return struct.unpack('<f',u.mem_read(OBJ+o,4))[0]
 output={'count':si(r(OBJ+0x70)),'buffered':r(OBJ+0x118)&1,'diameter':si(r(OBJ+0x68)),'rect':list(struct.unpack('<4i',u.mem_read(OBJ+0x2c,16))),'color':list(u.mem_read(OBJ+0x6c,4)),'ranges':[[f(o+i*4) for i in range(3)] for o in [0xa4,0xb8,0xcc,0xe0]],'lookups':trace,'sets':[[i,slots,int(bool(image)),force] for i,slots,image,force in sets],'image_refs':[r(BITMAP+i*0x100+0x34) for i in range(3)]}
 return {'input':c,'output':output,'executed_pcs':pcs,'native_stores':writes,'init_count_updates':counts}
def cases():
 inputs=[[f,c,n] for f,c,n in [(0,0,0),(0,3,2),(1,2,2),(2,2,2),(6,2,2),(8,2,2),(16|64,2,1),(32,2,1),(128,2,1),(256,2,2),(512,2,2),(1024,3,2),(8|1|6|16|32|512|1024,3,2),(8|16|64|512,2,1),(8|128|256|512,3,2),(8|1|16,0,0),(2048,2,1),(2048|16|32,2,1)]]
 return [execute(c+[repeat]) for c in inputs for repeat in [0,1]]
if __name__=='__main__':
 (T/'fixtures.json').write_text(json.dumps({'elf_sha256':SHA,'mangled':NAME,'range':RANGE,'policy':'Actual target ARM instructions only; provider/app-helper boundaries intercepted, no guest Core/syscalls; valid non-overflow HPF setup domain.','cases':cases()},indent=2)+'\n');print('36 exact original setAttributes scenarios, 54 original calls')
