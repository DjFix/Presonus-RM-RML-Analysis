"""Original ARM application instructions with explicit provider-boundary contracts.

Core instructions never execute. libc operations are byte-string boundary models;
app lookups use supplied initialized records. No expected data uses new C++.
"""
import argparse,hashlib,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
BASE=Path('temp/recovery-work/stabilized-cycle01/batch02/packets')
OBJ,ITEM,ALIAS,CONTROL,PARAM,OTHER,PAGE,LIST,STR,VT,STOP,STACK= [0x1000000+i*0x1000 for i in range(12)]
STACK=0x1100000
REG=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
def packet(i):return BASE/f'stabilized01_mapping_{i:02}'
def getcontext(i):return json.loads((packet(i)/'context.json').read_text())
def ranges():
 result=[]
 for i in range(1,9):
  c=getcontext(i);n=c['native_context'];nid=c['native_roots'][0];m=n['nodes'][nid]['metadata'];b=n['bodies'][nid];path=Path(n['binaries'][m['elf']]['path']);raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==m['elf']
  with path.open('rb') as f:
   elf=ELFFile(f);symbols=[s for s in elf.get_section_by_name('.symtab').iter_symbols() if s.name==m['mangled']];assert len(symbols)==1;s=symbols[0];sec=elf.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];assert int(s['st_value'])==b['address'] and int(s['st_size'])==b['size'] and sec.name==b['section'] and off==b['file_offset'];assert hashlib.sha256(raw[off:off+b['size']]).hexdigest()==b['bytes_sha256']
  result.append(dict(task_id=c['task_id'],original=m,section=b['section'],file_offset=off,bytes_sha256=b['bytes_sha256'],address=b['address'],size=b['size']))
 return result
RAW=Path('rootfs/CS18_v13840/home/root/surface').read_bytes()
def cases():
 result=[]
 def add(i,argv,setup):result.append(dict(packet=i,argv=argv,setup=setup))
 modes=['-','unknown','meter-audio','meter-audio-reverse','meter-centered','meter-stereobar','meter-single-seg','meter-single-reverse','meter-disabled-h','meter-disabled-v','meter-bar','meter-audio-no-taper','meter-bar-reverse','meter-bar-upsidedown','meter-raw','meter-audio-lineardb','METER-RAW']
 for m in modes:add(2,['mode',m],dict(mode=m))
 for initial in ['', 'x'*58,'x'*60,'x'*62,'x'*63]:
  for a,b in [('-','-'),('',''),('p','gain'),('p'*90,'z'*90)]:add(3,['page',initial,a,b],dict(initial=initial,page=a,param=b))
 for name in ['', 'mix', 'n'*31]:add(4,['name',name],dict(name=name))
 for kind in ['alias','numeric','missing']:
  for present in [0,1]:add(5,['pageconnect',kind,str(present)],dict(kind=kind,present=present))
 for count in [0,1,3,8]:add(6,['disconnect',str(count)],dict(count=count))
 for i in [7,8]:
  for screen in [0,1]:
   for tag in [-1,0,42,43,2147483647]:add(i,['get',str(i),str(screen),str(tag)],dict(screen=screen,tag=tag))
 for found in [0,1]:
  for ctrl in [0,1]:
   for param in [0,1]:
    for mode in ['-','meter-raw','unknown']:
     for force in [0,1]:
      for same in [0,1]:
       for oldmode in [0,12]:add(1,['connect',str(found),str(ctrl),str(param),mode,str(force),str(same),str(oldmode)],dict(found=found,ctrl=ctrl,param=param,mode=mode,force=force,same=same,oldmode=oldmode))
 # Extend the original matrix with a valid optional/null AliasParam state.
 # Raw original setOriginal(null, parameter) boundary calls are retained;
 # pinned CCL cannot execute a null-this member, so host provider guard is separate.
 for ctrl in [0,1]:
  for param in [0,1]:
   for mode in ['-','meter-raw','unknown']:
    for force in [0,1]:
     for same in [0,1]:
      for oldmode in [0,12]:add(1,['connect','1',str(ctrl),str(param),mode,str(force),str(same),str(oldmode),'0'],dict(found=1,ctrl=ctrl,param=param,mode=mode,force=force,same=same,oldmode=oldmode,alias=0))
 for name in ['page:p.gain','page:missing.gain','page:p.','page:p.'+'x'*60,'garbage','page:p','xpage:p.gain','page:.gain']:
  add(1,['route',name],dict(route=name))
 return result

def execute(case):
 i=case['packet'];s=case['setup'];u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
 with Path('rootfs/CS18_v13840/home/root/surface').open('rb') as f:
  elf=ELFFile(f);pages=set()
  for segment in elf.iter_segments():
   if segment['p_type']!='PT_LOAD':continue
   start,length=int(segment['p_vaddr']),int(segment['p_memsz'])
   for p in range(start&~4095,(start+length+4095)&~4095,4096):
    if p not in pages:u.mem_map(p,4096);pages.add(p)
   u.mem_write(start,segment.data())
 u.mem_map(OBJ,0x10000);u.mem_map(STACK,0x10000)
 def w(a,*v):u.mem_write(a,struct.pack('<'+'I'*len(v),*v))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def string(a):
  if not a:return ''
  out=bytearray()
  while u.mem_read(a+len(out),1)!=b'\0':out.extend(u.mem_read(a+len(out),1));assert len(out)<1024
  return out.decode('ascii')
 def put(a,v):u.mem_write(a,v.encode()+b'\0');return a
 def argstr(a,v):return 0 if v=='-' else put(a,v)
 w(ITEM,CONTROL if s.get('ctrl') else 0);w(ITEM+0x24,ALIAS if s.get('alias',1) else 0);w(CONTROL,VT);w(CONTROL+8,(ALIAS if s.get('alias',1) else 0) if s.get('same') else OTHER);w(CONTROL+12,s.get('oldmode',0));w(ALIAS,VT+0x100)
 for slot in [0,1,4,5,8]:w(VT+slot*4,STOP+0x100+slot*4)
 w(VT+0x100,STOP+0x200)
 w(OBJ+0xb8,LIST,s.get('count',0))
 for j in range(s.get('count',0)):w(LIST+j*4,ALIAS+0x100+j*0x20)
 regs=[OBJ,0,0,0];out=[];boundary=[];writes=[];trace=[]
 if i==2:regs[0]=argstr(STR,s['mode'])
 if i==3:put(OBJ,s['initial']);regs[1]=argstr(STR,s['page']);regs[2]=argstr(STR+0x200,s['param'])
 if i==4:put(OBJ+8,s['name'])
 if i==5:regs[1]=put(STR,'gain');regs[2]=PARAM if s['present'] else 0
 if i in [7,8]:regs[1]=s['tag']&0xffffffff;w(OBJ+0x88,PAGE if s['screen'] else 0)
 if i==1:
  regs[1]=put(STR,s.get('route','control'));regs[2]=PARAM if s.get('param',1) else 0;regs[3]=argstr(STR+0x200,s.get('mode','-'))
 for reg,val in zip(REG,regs):u.reg_write(reg,val)
 u.reg_write(UC_ARM_REG_SP,STACK+0xf000);u.reg_write(UC_ARM_REG_LR,STOP);w(STACK+0xf000,s.get('force',0))
 def ret(v=None):
  if v is not None:u.reg_write(UC_ARM_REG_R0,v&0xffffffff)
  u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def hook(uc,a,size,_):
  x,y,z,t=[uc.reg_read(q) for q in REG]
  if a==STOP:uc.emu_stop();return
  trace.append(a)
  if a in [0xb02c,0xb0f8,0xae7c,0xb260,0xb170,0xaf84,0x24268,0xb1c4,0xab7c,0x762a8,0x120e24,0x15cc0,0x75e48,0x11f0c8,0x11acf0] or STOP+0x100<=a<=STOP+0x200:
   boundary.append(dict(address=a,arguments=[x,y,z,t]))
   if a==0xb02c:ret(len(string(x)))
   elif a==0xb0f8:ret((string(x)>string(y))-(string(x)<string(y)))
   elif a==0xae7c:
    pos=string(x).find(string(y));ret(0 if pos<0 else x+pos)
   elif a==0xb260:
    pos=string(x).find(chr(y));ret(0 if pos<0 else x+pos)
   elif a==0xb170:
    b=string(y).encode()[:z];u.mem_write(x,b+b'\0'*(z-len(b)));ret(x)
   elif a==0xaf84:put(x,string(x)+string(y)[:z]);ret(x)
   elif a==0x24268:put(x,'');ret(x)
   elif a==0xb1c4:ret(1)
   elif a==0xab7c:u.mem_write(x,b'\x01');ret()
   elif a==0x762a8:ret(ITEM if s.get('found') else 0)
   elif a==0x120e24:
    if x:w(x+8,y)
    if i==1:out.append(['alias',int(y!=0)])
    elif i==5:out.append(['alias',int(y!=0)])
    else:out.append(['alias',0])
    ret()
   elif a==0x15cc0:ret(r(x+8))
   elif a==0x75e48:
    boundary[-1]['page_name']=string(y);ret(PAGE if string(y)=='p' else 0)
    if string(y)=='p':w(PAGE,VT+0x300);w(VT+0x304,STOP+0x204)
   elif a==0x11f0c8:ret(0 if s['kind']=='missing' else ALIAS)
   elif a==0x11acf0:ret(PARAM if y==42 else 0)
   elif a==STOP+0x200:ret(ALIAS if s.get('kind')=='alias' else 0)
   elif a==STOP+0x110:out.append(['set',int(y==ALIAS),z]);w(CONTROL+8,y);ret(1)
   elif a==STOP+0x114:ret(r(CONTROL+12))
   elif a==STOP+0x104:out.append(['notify',t if False else z]);ret()
   elif a==STOP+0x120:out.append(['broadcast',y]);ret()
   else:raise AssertionError(hex(a))
  elif a==STOP+0x204:out.append(['connectpage',string(y),int(z!=0)]);ret(1)
  elif not (0x76d0c<=a<0x7701c or 0x75ee8<=a<0x75f44 or (ranges_by_i[i]['address']<=a<ranges_by_i[i]['address']+ranges_by_i[i]['size'])):raise AssertionError(('unexpected execution',hex(a)))
 def mem(uc,access,a,size,value,_):
  if OBJ<=a<STR:writes.append(dict(address=a,size=size,value=value))
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,mem)
 u.emu_start(ranges_by_i[i]['address'],STOP,count=100000)
 assert u.reg_read(UC_ARM_REG_PC)==STOP
 if i==2:observed=u.reg_read(UC_ARM_REG_R0)
 elif i in [3,4]:observed=string(OBJ if i==3 else u.reg_read(UC_ARM_REG_R0))
 elif i in [7,8]:observed=int(u.reg_read(UC_ARM_REG_R0)!=0)
 elif i==5:observed={'result':u.reg_read(UC_ARM_REG_R0),'calls':out}
 else:observed=out
 result=dict(observed=observed,executed_addresses=trace,boundaries=boundary,writes=writes)
 if i==1 and s.get('alias',1)==0:
  p=r(CONTROL+8);result['final_control_parameter']='null' if not p else 'alias' if p==ALIAS else 'other'
 return result

def data_ranges():
 records=[]
 rawpath=Path('rootfs/CS18_v13840/home/root/surface' if 'mapping'=='mapping' else 'rootfs/RML16AI_Rack_13731/home/root/mixer')
 raw=rawpath.read_bytes()
 with rawpath.open('rb') as f:
  sections=[(s.name,int(s['sh_addr']),int(s['sh_offset']),int(s['sh_size'])) for s in ELFFile(f).iter_sections() if s['sh_type']!='SHT_NOBITS']
 def data(a,n):
  sec=next(s for s in sections if s[1]<=a and a+n<=s[1]+s[3]);off=sec[2]+a-sec[1];b=raw[off:off+n];records.append(dict(address=a,size=n,section=sec[0],file_offset=off,sha256=hashlib.sha256(b).hexdigest(),hex=b.hex()));return b
 def text(a):
  sec=next(s for s in sections if s[1]<=a< s[1]+s[3]);off=sec[2]+a-sec[1];n=raw.index(b'\0',off)-off+1;return data(a,n)
 if 'mapping'=='mapping':
  table=data(1690900,120)
  for i in range(0,112,8):text(struct.unpack('<I',table[i:i+4])[0])
  text(1690512)
 else:
  for i in range(0x6a748,0x6a780,4):
   sec=next(s for s in sections if s[1]<=i< s[1]+s[3]);off=sec[2]+i-sec[1];text(struct.unpack('<I',raw[off:off+4])[0])
 return records

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();rr=ranges();ranges_by_i={j+1:r for j,r in enumerate(rr)}
 cc=cases()
 for c in cc:c['native']=execute(c)
 result=dict(version=1,ranges=rr,data_ranges=data_ranges(),cases=cc,engine='Unicorn '+unicorn.__version__,limitations='Original application instructions execute. Core/libc and initialized app lookup/virtual providers are explicit boundary models, not original provider execution. Native stack writes retained only in execution, object writes recorded. Original return declarations/layout/ARM ABI/hardware excluded.')
 Path(a.out).write_text(json.dumps(result,indent=2)+'\n');print('original application cases',len(cc))
