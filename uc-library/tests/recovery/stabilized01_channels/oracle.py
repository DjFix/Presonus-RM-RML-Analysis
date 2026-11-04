"""Execute original application instructions; explicit offline provider boundaries only."""
import hashlib, json, random, struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC

ROOT = Path(__file__).resolve().parents[4]
TEST = Path(__file__).resolve().parent
PACKETS = ROOT / 'temp/recovery-work/stabilized-cycle01/batch02/packets'
R0,R1,R2,R3,SP,LR,PC = UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
S = 0x10000000
STOP = 0x30000000
NAMES=['line','return','fxreturn','talkback','aux','fxbus','sub','main','mono','unused','signalgen']
def sha(b): return hashlib.sha256(b).hexdigest()
def bits(f): return struct.unpack('<I',struct.pack('<f',f))[0]
def floating(b): return struct.unpack('<f',struct.pack('<I',b))[0]

class Native:
 def __init__(self,path,targets):
  self.path=path;self.data=path.read_bytes();self.digest=sha(self.data);self.targets=targets
  assert all(t['original']['elf']==self.digest for t in targets.values()), 'ELF identity mismatch'
  self.u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  with path.open('rb') as f:
   elf=ELFFile(f)
   pages={}
   for seg in elf.iter_segments():
    if seg['p_type']=='PT_LOAD':
     lo=seg['p_vaddr']&~4095;hi=(seg['p_vaddr']+seg['p_memsz']+4095)&~4095
     for a in range(lo,hi,4096):pages[a]=True
   for a in pages:self.u.mem_map(a,4096)
   for seg in elf.iter_segments():
    if seg['p_type']=='PT_LOAD':self.u.mem_write(seg['p_vaddr'],seg.data())
   self.ranges=[]
   for n,t in targets.items():
    sym=t['original'];a=sym['address'];size=sym['size']
    sec=next(x for x in elf.iter_sections() if x['sh_addr']<=a and a+size<=x['sh_addr']+x['sh_size'] and x['sh_type']!='SHT_NOBITS')
    offset=sec['sh_offset']+a-sec['sh_addr'];raw=self.data[offset:offset+size]
    packet=(PACKETS/f'stabilized01_channels_{n:02}/ELF_CONTEXT.md').read_text()
    assert sha(raw) in packet, 'range hash differs from sealed packet'
    self.ranges.append(dict(elf_sha256=self.digest,mangled=sym['mangled'],demangled=sym['demangled'],firmware=sym['firmware'],role=sym['role'],address=a,size=size,section=sec.name,file_offset=offset,sha256=sha(raw)))
  self.u.mem_map(S,0x200000);self.u.mem_map(0x20000000,0x10000);self.u.mem_map(STOP,4096)
  self.u.hook_add(UC_HOOK_CODE,self.hook)
  self.u.hook_add(UC_HOOK_MEM_WRITE,self.write_hook)
  self.client='surface' in path.name
  self.cast=0xae58 if self.client else 0xacf4
  self.cmp=0xb0f8 if self.client else 0xaf70
  self.gt=0x1877e0 if self.client else 0x157940
  self.trace=[];self.writes=[];self.lookup={};self.castable=set();self.params={};self.reads=0
 def word(self,a,v=None):
  if v is not None:self.u.mem_write(a,struct.pack('<I',v&0xffffffff))
  return struct.unpack('<I',self.u.mem_read(a,4))[0]
 def cstring(self,a):
  out=bytearray()
  while self.u.mem_read(a,1)!=b'\0':out+=self.u.mem_read(a,1);a+=1
  return out.decode()
 def ret(self,v):self.u.reg_write(R0,v&0xffffffff);self.u.reg_write(PC,self.u.reg_read(LR))
 def write_hook(self,u,access,address,size,value,user):
  if address==S+0x680:self.writes.append(value)
 def hook(self,u,a,size,user):
  if a==STOP:u.emu_stop();return
  if a==S+0xff000:
   name=self.cstring(u.reg_read(R1));self.trace.append(['lookup',name]);self.ret(self.lookup.get(name,0))
  elif a==self.cast:
   obj=u.reg_read(R0);self.trace.append(['cast',obj]);self.ret(obj if obj in self.castable else 0)
  elif a==S+0xff100:
   obj=u.reg_read(R0);self.reads+=1;self.trace.append(['value',obj]);self.ret(self.params[obj])
  elif a==self.gt:
   self.ret(int(floating(u.reg_read(R0))>floating(u.reg_read(R1))))
  elif a==self.cmp:
   left=self.cstring(u.reg_read(R0));right=self.cstring(u.reg_read(R1));self.trace.append(['strcmp',left,right]);self.ret((left>right)-(left<right))
 def call(self,n,r0=S,r1=0):
  self.u.reg_write(SP,0x2000f000);self.u.reg_write(LR,STOP);self.u.reg_write(R0,r0);self.u.reg_write(R1,r1&0xffffffff)
  self.u.emu_start(self.targets[n]['original']['address'],STOP,count=100000)
  assert self.u.reg_read(PC)==STOP,'execution did not return'
  return self.u.reg_read(R0)
 def setup(self):
  self.u.mem_write(S,b'\0'*0x200000);self.trace=[];self.writes=[];self.lookup={};self.castable=set();self.params={};self.reads=0
  vt=S+0xf0000;self.word(S,vt);self.word(vt+0x20,self.targets[5]['original']['address'])
  self.word(S+0x30,vt+0x100);self.word(vt+0x114,S+0xff000)
 def selection(self,entries,cached):
  self.setup();self.word(S+0x680,S+0xe0000 if cached else 0)
  groups={};ids={S+0xe0000:-1};offsets={}
  for i,(ty,kind,val) in enumerate(entries,1):
   group=groups.setdefault(ty,S+0x1000+ty*0x100)
   self.lookup[NAMES[ty]]=group
   if kind==5:continue
   arr=S+0x4000+ty*0x100
   index=offsets.get(ty,0);offsets[ty]=index+1
   self.word(group+0x58,arr);self.word(group+0x5c,index+1)
   obj=S+0x10000+i*0x400;ids[obj]=i
   self.word(arr+index*4,obj if kind else 0)
   if kind>=2:
    self.castable.add(obj);vt=S+0xf1000+(0 if kind==2 else 0x100)
    self.word(obj,vt);self.word(vt+0x38,self.targets[1 if kind==2 else 2]['original']['address'])
    if kind==4:
     p=S+0x80000+i*0x100;self.word(obj+0x200,p);self.word(p,S+0xf2000);self.word(S+0xf2044,S+0xff100);self.params[p]=val
  result=self.call(4);reads=self.reads;again=self.call(4)
  return [ids.get(result,0),reads,int(again==result),self.reads],dict(trace=self.trace,cache_writes=[ids.get(x,0) for x in self.writes],cache=ids.get(self.word(S+0x680),0))

def inputs():
 cases=[dict(op=0)]
 for ty in [-2147483648,-1,*range(14),65536,2147483647]:
  for present in [0,1]:cases.append(dict(op=1,type=ty,present=present))
 for name in NAMES+['','LINE','Line','line/x','returning','signalgenx','unknown']:
  cases.append(dict(op=2,name=name))
 entries=[[],[[0,0,0],[0,1,0],[0,2,0],[0,3,0]],[[0,4,bits(1.)],[0,4,bits(2.)]],[[0,4,bits(1.)],[8,4,bits(1.)]],[[10,4,bits(1.)]]]
 for ty in range(9):
  for val in [bits(-1.),bits(0.),bits(-0.),bits(0.001),bits(1.),0x7fc00000,0x7f800000,0xff800000]:
   entries.append([[ty,4,val]])
 entries += [[[ty,5,0] for ty in range(9)], [[ty,4,bits(1.)] for ty in range(9)], [[0,5,0],[8,4,bits(1.)]]]
 rng=random.Random(624)
 for _ in range(180):
  entries.append([[rng.randrange(11),rng.randrange(5),rng.choice([bits(-1.),bits(0.),bits(1.),bits(0.25),0x7fc00000])] for _ in range(rng.randrange(1,16))])
 for e in entries:
  for cached in [0,1]:cases.append(dict(op=3,cached=cached,entries=e))
 return cases

def line(c):
 if c['op']==0:return '0'
 if c['op']==1:return f"1 {c['type']} {c['present']}"
 if c['op']==2:return '2 '+(c['name'] or '<empty>')
 return '3 '+str(c['cached'])+' '+str(len(c['entries']))+' '+ ' '.join(' '.join(map(str,e)) for e in c['entries'])

def main():
 cases=inputs();records=[];ranges=[]
 for client in [True,False]:
  targets={}
  for n in range(1,6):
   req=json.loads((PACKETS/f'stabilized01_channels_{n:02}/request.json').read_text())
   originals=[t for t in req['originals'] if (t['original']['role']=='client')==client]
   if originals:targets[n]=originals[0]
  # Base getter only exists in CS18 packet. RM scan's own base provider is a
  # memory-bound null virtual boundary; do not execute another ELF's body.
  path=ROOT/'evidence/recovery/inputs'/('surface-13840.elf' if client else 'mixer-13731.elf')
  native=Native(path,targets);ranges+=native.ranges
  if not client:
   # Explicit base-null provider boundary, same typed source provider on host.
   native.targets[1]={'original':{'address':S+0xff200}}
   original_hook=native.hook
   def basehook(u,a,size,user):
    if a==S+0xff200:native.ret(0)
   native.u.hook_add(UC_HOOK_CODE,basehook)
  for c in cases:
   native.setup();op=c['op'];trace={}
   if op==0:
    if not client:continue
    a=native.call(1);native.word(S+0x200,S+0x90000);b=native.call(2);native.word(S+0x200,0);d=native.call(2)
    out=[int(a==0),int(b==S+0x90000),int(d==0)]
   elif op==1:
    if c['present']:
     for i,name in enumerate(NAMES):native.lookup[name]=S+0x1000+i*0x100
    value=native.call(5,r1=c['type']);out=next((name for name,addr in native.lookup.items() if addr==value),'NULL')
   elif op==2:
    native.u.mem_write(S+0x1008,c['name'].encode()+b'\0');v=native.call(3,r1=S+0x1000);out=v if v<0x80000000 else v-0x100000000
   else:out,trace=native.selection(c['entries'],c['cached'])
   records.append(dict(elf_sha256=native.digest,inputs=c,line=line(c),observed=out,native_trace=trace or native.trace))
 result=dict(version=1,oracle='Unicorn original ARM application instructions; modeled provider boundaries, not original Core/libc execution',ranges=ranges,cases=records)
 (TEST/'fixtures.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(dict(cases=len(records),ranges=len(ranges))))
if __name__=='__main__':main()
