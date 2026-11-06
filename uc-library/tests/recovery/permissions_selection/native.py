#!/usr/bin/env python3
"""Execute exact original application ARM ranges; no recovered C++ or Core instructions.
Core/libc/ABI calls have named private-memory semantic boundaries.
"""
import io,json,struct,hashlib,argparse
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
P=Path('temp/recovery-work/rolling200-02/next-implementation61/prepared-permissions61/packets')
E=Path('rootfs/RML16AI_Rack_13731/home/root/mixer')
C=Path('rootfs/CS18_v13840/home/root/surface')
SELF,CLIENT,MIXER,ARRAY,LIST,VT,NEW,DEVICE= [0x1000000+i*0x1000 for i in range(8)]
STACK,STOP,HOOK=0x1100000,0x1200000,0x1300000
R=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
def sha(b):return hashlib.sha256(b).hexdigest()
def bits(v):return struct.unpack('<I',struct.pack('<f',v))[0]
def flt(v):return struct.unpack('<f',struct.pack('<I',v))[0]
def signed(v):return v if v<2**31 else v-2**32
class Oracle:
 def __init__(self,path=E):
  self.path=path;self.raw=path.read_bytes();self.elf=ELFFile(io.BytesIO(self.raw));self.syms={s.name:s for s in self.elf.get_section_by_name('.symtab').iter_symbols() if s.name};self.ranges=[]
  self.targets={}
  for p in sorted(P.iterdir()):
   req=json.loads((p/'request.json').read_text())
   for t in req['targets']:
    if t['original_elf_sha256']!=sha(self.raw):continue
    r=self.verify(t['mangled']);assert r['address']==t['address'] and r['size']==t['size'];self.ranges.append(r);self.targets[req['task_id'][-2:]]=t['address']
  self.u=Uc(UC_ARCH_ARM,UC_MODE_ARM);pages=set()
  for s in self.elf.iter_segments():
   if s['p_type']!='PT_LOAD':continue
   for a in range(s['p_vaddr']&~4095,(s['p_vaddr']+s['p_memsz']+4095)&~4095,4096):
    if a not in pages:self.u.mem_map(a,4096);pages.add(a)
   self.u.mem_write(s['p_vaddr'],s.data())
  for a,n in [(SELF,0x20000),(STACK,0x10000),(STOP,4096),(HOOK,4096)]:self.u.mem_map(a,n)
  self.u.hook_add(UC_HOOK_CODE,self.code);self.u.hook_add(UC_HOOK_MEM_WRITE,self.write)
  if path==E:
   self.boundaries={0x1cf90:'cstring',0xac10:'delete',0xa7e4:'new',0xae98:'strlen',0xafe8:'strncpy',0x116a38:'debug',0x2f464:'count',0x52368:'resize',0x11f9a0:'remove',0x11ecd8:'append',0x50f14:'app',0x51eec:'info',0xaf70:'strcmp',0x157474:'intFloat',0x11dc28:'changed',0x11dbd4:'range',0x119c4c:'tag',0xacf4:'cast',0x11df74:'default',0x516e8:'load',HOOK:'set'}
  else:self.boundaries={0x3ae34:'cstring'}
 def verify(self,name):
  s=self.syms[name];sec=self.elf.get_section(s['st_shndx']);a=s['st_value'];z=s['st_size'];off=sec['sh_offset']+a-sec['sh_addr']
  return dict(elf_sha256=sha(self.raw),path=str(self.path),mangled=name,address=a,size=z,section=sec.name,file_offset=off,sha256=sha(self.raw[off:off+z]))
 def put(self,a,v):self.u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def word(self,a):return struct.unpack('<I',self.u.mem_read(a,4))[0]
 def string(self,a):
  if not a:return ''
  b=bytearray()
  for i in range(1024):
   v=self.u.mem_read(a+i,1)[0]
   if v==0:return b.decode('latin1')
   b.append(v)
  raise AssertionError('unterminated string')
 def text(self,a,s):self.u.mem_write(a,s.encode('latin1')+b'\0')
 def write(self,u,access,a,n,v,data):
  assert STACK<=a<a+n<=STACK+0x10000 or SELF<=a<a+n<=SELF+0x20000,('write',hex(a),n)
  self.writes.append([a,n,v])
 def set(self,value):
  value=max(min(value,max(0,len(self.items)-1)),min(0,len(self.items)-1))
  if value!=self.value:self.value=value;self.events.append(0)
 def maxchange(self,old):
  if old!=len(self.items)-1:
   if self.value>len(self.items)-1:self.set(len(self.items)-1)
   else:self.events.append(0)
 def code(self,u,a,n,data):
  if a==STOP:self.done=True;u.emu_stop();return
  if a not in self.boundaries:
   assert any(r['address']<=a<r['address']+r['size'] for r in self.ranges),('PC',hex(a));self.pcs.append(a);return
  name=self.boundaries[a];r0,r1,r2,r3=[u.reg_read(r) for r in R];result=0;detail={}
  if name=='cstring':assert r1==0;self.text(r0,'')
  elif name=='delete':self.deleted.append(r0)
  elif name=='new':assert r0==408;result=NEW;self.u.mem_write(NEW,b'\xa5'*408)
  elif name=='strlen':result=len(self.string(r0))
  elif name=='strncpy':self.u.mem_write(r0,bytes(self.u.mem_read(r1,r2)))
  elif name=='debug':pass
  elif name=='count':result=len(self.case['clients'])
  elif name=='resize':self.put(SELF+0xe8,DEVICE);self.put(SELF+0xf0,256);result=1
  elif name=='remove':old=len(self.items)-1;self.items=[];self.maxchange(old)
  elif name=='append':old=len(self.items)-1;self.items.append(self.string(r1));self.maxchange(old)
  elif name=='set':assert r2==0;self.set(flt(r1));detail['float']=flt(r1)
  elif name=='app':
   app=self.string(r1+0x58);result=1 if 'qmix' in app else 2 if 'ucapp' in app or 'ucremoteapp' in app else 0
  elif name=='info':
   name0=self.string(r2+0x118)[:16];device=self.string(r2+0x98);self.text(r0,(name0+': '+device)[:63])
  elif name=='strcmp':x,y=self.string(r0),self.string(r1);result=(x>y)-(x<y)
  elif name=='intFloat':result=bits(signed(r0))
  elif name=='changed':self.events.append(0)
  elif name=='range':self.events.append(1)
  elif name=='tag':assert r1==4;result=LIST+0x400 if self.case['type']!='none' else 0
  elif name=='cast':result=r0 if self.case['type']=='string' else 0
  elif name=='default':self.default=self.string(r1)
  elif name=='load':
   # Explicit provider/archive boundary; real canonical load runs in C++ replay.
   if self.case['type']=='string':self.access=self.case['file'] if self.case['file'] not in ['absent',''] else self.default
  else:raise AssertionError(name)
  self.calls.append(dict(pc=a,name=name,args=[r0,r1,r2,r3],result=result,**detail));u.reg_write(UC_ARM_REG_R0,result&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def client(self,p,values):
  self.u.mem_write(p,b'\xa5'*408);self.put(p,values[0])
  for off,text in zip([0x18,0x58,0x98,0xd8,0x118],values[1:]):self.text(p+off,text)
 def snapshot(self,p):
  return dict(id=signed(self.word(p)),initial=all(self.word(p+o)==0 for o in [8,12,20]) and self.u.mem_read(p+16,1)==b'\0' and self.string(p+0x158)=='',strings=[self.string(p+o) for o in [0x18,0x58,0x98,0xd8,0x118]])
 def run(self,c):
  self.case=c;self.pcs=[];self.calls=[];self.writes=[];self.done=False;self.deleted=[];self.items=['seed']*c['old'];self.value=float(max(0,c['old']-1));self.events=[];self.default='old';self.access='initial'
  self.u.mem_write(SELF,b'\0'*0x20000);self.u.mem_write(STACK,b'\xcc'*0x10000)
  self.put(SELF+0x94,MIXER);self.put(MIXER+0xa8,ARRAY);self.put(MIXER+0xac,len(c['clients']));self.put(SELF+0x90,LIST);self.put(LIST,VT);self.put(VT+0x58,HOOK)
  self.put(SELF+0xf8,CLIENT if c['selected']!='null' else 0)
  self.client(CLIENT,[-7,'','','',c['selected'],''])
  for i,values in enumerate(c['clients']):
   p=0 if values is None else SELF+0x9000+i*0x200;self.put(ARRAY+i*4,p)
   if values:self.client(p,values)
  op=c['op'];target={'set':'01','init':'02','copy':'03','update':'04','ctor':'05','get':'06'}[op];arg=SELF;r1=0
  if op=='ctor':arg=NEW;r1=c['id'];self.u.mem_write(NEW,b'\xa5'*408)
  if op=='get':arg=MIXER;r1=c['id']
  if op in ['copy','set']:r1=self.word(ARRAY+c['id']*4)
  for r in R:self.u.reg_write(r,0)
  self.u.reg_write(UC_ARM_REG_CPSR,0x10);self.u.reg_write(UC_ARM_REG_SP,STACK+0xff00);self.u.reg_write(UC_ARM_REG_LR,STOP);self.u.reg_write(R[0],arg);self.u.reg_write(R[1],r1&0xffffffff)
  self.u.emu_start(self.targets[target],STOP+4,count=100000);assert self.done
  if op=='ctor':
   result=self.snapshot(NEW);assert self.u.mem_read(NEW+4,4)==b'\xa5'*4
   for off in [0x18,0x58,0x98,0xd8,0x118,0x158]:assert self.u.mem_read(NEW+off+1,63)==b'\xa5'*63
  elif op=='get':
   p=self.u.reg_read(R[0]);result=next((i for i in range(len(c['clients'])) if p and p==self.word(ARRAY+i*4)),-1)
  elif op in ['copy','set']:result=dict(snapshot=self.snapshot(NEW),released=CLIENT in self.deleted)
  else:
   result=dict(list=self.items,value=self.value,events=self.events,access=self.access,devices=[signed(self.word(self.word(DEVICE+i*4))) for i in range(self.word(SELF+0xec))] or [None])
  return result,dict(pcs=self.pcs,calls=self.calls,writes=self.writes,deleted=self.deleted)
def cases():
 def c(op,clients=[],selected='null',id=0,old=0,type='string',file='absent'):return dict(op=op,clients=clients,selected=selected,id=id,old=old,type=type,file=file)
 for id in [-2147483648,-1,0,1,2147483647]:yield c('ctor',id=id)
 clients=[[10,'alpha','qmix','iPad','a','first'],None,[20,'beta','ucapp','iPhone','b','second'],[30,'gamma','unknown','x','a','third'],[40,'delta','ucremoteapp','iPod','a','12345678901234567890']]
 for id in [-2147483648,-1,0,1,2,4,5,2147483647]:yield c('get',clients,id=id)
 for op in ['copy','set']:
  for selected in ['null','prior']:
   for values in [clients[0],[99,'','qmix','','',''],[-1,'n'*63,'a'*63,'d'*63,'i'*63,'v'*63]]:
    yield c(op,[values],selected)
 for op in ['update','init']:
  for collection in [[],[None],[clients[3]],clients,[clients[2],clients[0],clients[4]],[[1,'','QMIX','x','',''],[2,'','ucappqmix','iPad','','']]]:
   for selected in ['null','','a','b','missing']:
    for old in [0,3]:yield c(op,collection,selected,old=old)
 for type in ['none','numeric','string']:
  for file in ['absent','','87654']:yield c('init',clients,type=type,file=file)
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True);o=Oracle();cs=Oracle(C);rows=[];traces=[]
 for i,c in enumerate(cases()):
  result,trace=o.run(c);rows.append(dict(id=i,input=c,observed=result));traces.append(dict(id=i,elf_sha256=sha(o.raw),**trace))
 for c in cases():
  if c['op']!='ctor':continue
  result,trace=cs.run(c);assert result==o.run(c)[0];rows.append(dict(id=len(rows),input=c,observed=result,role='client'));traces.append(dict(id=len(rows)-1,elf_sha256=sha(cs.raw),**trace))
 (out/'fixtures.json').write_text(json.dumps(dict(cases=rows),indent=2)+'\n');(out/'native-traces.jsonl').write_text(''.join(json.dumps(t)+'\n' for t in traces))
 (out/'native-proof.json').write_text(json.dumps(dict(ranges=o.ranges+cs.ranges,cases=len(rows),producer_sha256=sha(Path(__file__).read_bytes()),unicorn=unicorn.__version__,boundaries=o.boundaries,fixture_sha256=sha((out/'fixtures.json').read_bytes()),trace_sha256=sha((out/'native-traces.jsonl').read_bytes()),limits='Exact seven original target ranges execute separately. Core/libc/AEABI/archive/type checks/classifier/display helper boundaries modeled explicitly, not native provider behavior. Constructor +4 and all six string tails checked unchanged. No syscalls/hardware or original Core bodies.'),indent=2)+'\n');print(len(rows))
if __name__=='__main__':main()
