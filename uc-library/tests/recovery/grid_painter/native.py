"""Execute only original application instructions; intercept all Core providers.
Provider values/widths are independently observed from pinned CCL and existing
EQControl through the replay's --providers mode, never from GridPainter output.
"""
import hashlib,itertools,json,struct,subprocess,sys
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent
ELF=R/'rootfs/CS18_v13840/home/root/surface';RAW=ELF.read_bytes();SHA=hashlib.sha256(RAW).hexdigest()
assert SHA=='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
PACKETS=[Path(f'temp/recovery-work/rolling200-03/grid140/prepared140/packets/rolling200_03_grid140_{i:02}') for i in range(1,8)]
RANGES=[];NAMES=[]
with ELF.open('rb') as f:
 elf=ELFFile(f)
 for p in PACKETS:
  j=json.loads((R/p/'native-context.json').read_text());b=j['bodies'][j['roots'][0]];request=json.loads((R/p/'request.json').read_text());name=request['targets'][0]['mangled'];NAMES.append(name)
  sec=elf.get_section(b['section_index']);off=sec['sh_offset']+b['address']-sec['sh_addr'];assert off==b['file_offset'] and sec.name==b['section'];assert hashlib.sha256(RAW[off:off+b['size']]).hexdigest()==b['bytes_sha256']
  RANGES.append(dict(mangled=name,**{k:b[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']}))
 # Application BackgroundPainter already bound in paint packet.
 j=json.loads((R/PACKETS[1]/'native-context.json').read_text())
 EXPANSION=Path('temp/recovery-work/rolling200-03/grid140/expansion180')
 j=json.loads((R/EXPANSION/'native-context.json').read_text());BACKGROUND=next(b for b in j['bodies'].values() if b['address']==0x6a5b8)
 sec=elf.get_section(BACKGROUND['section_index']);off=sec['sh_offset']+BACKGROUND['address']-sec['sh_addr'];assert off==BACKGROUND['file_offset'];assert hashlib.sha256(RAW[off:off+BACKGROUND['size']]).hexdigest()==BACKGROUND['bytes_sha256']

O=0x400000;P=O+0x1000;V=O+0x2000;E=O+0x3000;G=O+0x4000;S=O+0x5000;F=O+0x6000;A=O+0x7000;STACK=0x500000;STOP=0x600000
VALUES=[-12,0,6,12,24,32,36,42,48,60]
CLIPS=[[0,0,64,48],[8,7,54,41],[70,60,80,70],[30,20,20,10]]
BACKS=[0xfff06e0c,0x4f00cdfa];FORE=0xff461e04
class Machine:
 def __init__(self,providers,font=False):
  self.u=u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x300000)
  with ELF.open('rb') as f:
   for seg in ELFFile(f).iter_segments():
    if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
  u.mem_protect(0,0x300000,5);u.mem_map(O,0x90000);u.mem_map(STACK,0x10000);u.mem_map(STOP,0x1000)
  self.providers={r[0]:r[1:] for r in providers[1:]};self.height=providers[0][0];self.font=font
  self.trace=[];self.internal=[];self.raster=[];self.calls=[];self.writes=[];self.pc=set();self.graphics={G:False};self.bitmaps={};self.allocation=O+0x10000
  self.w(P,V);self.w(V,STOP+4);self.w(V+4,STOP+8)
  self.w(G,V+0x100);self.gtable(V+0x100)
  self.w(E,G);self.w(F+0x44,self.height);self.w(S+8,FORE);u.mem_write(S+0x14,b'grid-test\0')
  self.w(O+8,P);self.w(O+0x10,A);self.w(O+0x18,64);self.w(O+0x1c,5);self.w(O+0x2c,A+0x100);self.w(O+0x34,64);self.w(O+0x38,5)
  self.w(O+0x24,0);self.w(O+0x40,0)
  self.w(V+0x200+8,STOP+32)
  for i,v in enumerate(VALUES):u.mem_write(A+4*i,struct.pack('<f',v));u.mem_write(A+0x100+4*i,struct.pack('<f',v))
  self.w(O+0x14,len(VALUES));self.w(O+0x30,len(VALUES))
  u.hook_add(UC_HOOK_CODE,self.code);u.hook_add(UC_HOOK_MEM_WRITE,self.write)
 def w(self,a,v):self.u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def r(self,a):return struct.unpack('<I',self.u.mem_read(a,4))[0]
 def si(self,v):return v if v<2**31 else v-2**32
 def ints(self,a,n):return list(struct.unpack('<'+'i'*n,self.u.mem_read(a,n*4)))
 def rect(self,a,v):self.u.mem_write(a,struct.pack('<4i',*v))
 def f(self,v):return struct.unpack('<f',struct.pack('<I',v))[0]
 def bits(self,v):return struct.unpack('<I',struct.pack('<f',float(v)))[0]
 def string(self,a):
  out=b''
  while True:
   b=bytes(self.u.mem_read(a+len(out),1))
   if b==b'\0':return out
   out+=b
   assert len(out)<=64
 def gtable(self,a):
  for off,target in [(0x14,12),(0x1c,16),(0x20,20),(0x28,24),(0x2c,28)]:self.w(a+off,STOP+target)
 def ret(self,v=0):self.u.reg_write(UC_ARM_REG_R0,v&0xffffffff);self.u.reg_write(UC_ARM_REG_PC,self.u.reg_read(UC_ARM_REG_LR))
 def emit(self,g,row):
  (self.internal if self.graphics[g] else self.trace).append(row)
  self.raster.append([6,*row[1:]] if row[0]==4 else row)
 def code(self,u,a,size,_):
  q=[u.reg_read(z) for z in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]];x,y,z,t=q
  if a==STOP:u.emu_stop();return
  if a in [STOP+4,STOP+8]:
   assert x==P;value=int(self.f(y));result=self.providers[value][1 if a==STOP+4 else 0];self.calls.append(['Y' if a==STOP+4 else 'X',value,result]);self.ret(result)
  elif a==STOP+12:self.emit(x,[2,*self.ints(y,4),self.r(z)]);self.ret(1)
  elif a==STOP+16:self.emit(x,[1,*self.ints(y,2),*self.ints(z,2),self.r(t)]);self.ret(1)
  elif a==STOP+20:
   sp=u.reg_read(UC_ARM_REG_SP);assert self.string(self.r(sp))==b'grid-test';self.emit(x,[3,*self.ints(y,4),self.r(t),self.r(sp+4),*self.string(z)]);self.ret(1)
  elif a==STOP+24:self.emit(x,[4,*self.ints(y,2),*self.ints(t,4)]);assert z in self.bitmaps;self.ret(1)
  elif a==STOP+28:assert self.string(y)==b'grid-test';self.ret(F if self.font and not self.graphics[x] else 0)
  elif a==STOP+32:
   assert x==F+0x100;assert self.r(y)==O and self.r(y+8)==32 and self.r(y+16)==0
   value=int(self.f(self.r(y+12)));self.u.mem_write(self.r(y+4),str(value).encode()+b'\0');self.calls.append(['formatter',value]);self.ret()
  elif a==STOP+36:
   assert x in self.bitmaps;self.calls.append(['delete_bitmap',x]);del self.bitmaps[x];self.ret()
  elif a==0x69e64:
   self.calls.append(['vector_resize',x-O,self.si(y)])
   # Real vector policy replaced at declared provider boundary; sufficient
   # capacity for fixtures. Original resize instructions are never executed.
   if y==0:self.w(x+4,0);self.w(x+12,0)
   else:
    if not self.r(x+4):self.w(x+4,A if x==O+12 else A+0x100)
    self.w(x+12,max(64,y))
   self.ret(1)
  elif a==0x69f64:self.calls.append(['vector_destroy',x-O]);self.ret()
  elif a==0x187314:self.ret(self.bits(x))
  elif a==0x187150:self.ret(self.bits(self.f(x)+self.f(y)))
  elif a==0x1877e0:self.ret(int(self.f(x)>self.f(y)))
  elif a==0x187798:self.ret(int(self.f(x)<self.f(y)))
  elif a in [0x187854,0x1877f8]:self.ret(int(self.f(x)))
  elif a==0x24268:self.u.mem_write(x,b'\0');self.ret(x)
  elif a==0x4b47c:
   assert self.string(y)==b'%d';self.u.mem_write(x,str(self.si(z)).encode()+b'\0');self.ret(x)
  elif a==0xb02c:self.ret(len(self.string(x)))
  elif a==0xfdf78:
   assert x==F and z==len(self.string(y));value=int(self.string(y));self.ret(self.providers[value][2])
  elif a==0xa90c:
   assert x==0x38;ptr=self.allocation;self.allocation+=0x1000;self.calls.append(['allocate_bitmap',ptr]);self.ret(ptr)
  elif a==0xf02b8:
   assert t==4 and self.r(u.reg_read(UC_ARM_REG_SP))==0;self.w(x,V+0x300);self.w(V+0x304,STOP+36)
   self.w(x+8,1);self.w(x+12,y);self.w(x+16,z);self.bitmaps[x]=[y,z];self.raster.append([5,y,z]);self.calls.append(['bitmap_construct',y,z,4]);self.ret(x)
  elif a==0x102d50:
   assert y in self.bitmaps;self.w(x,V+0x100);self.graphics[x]=True;self.ret(x)
  elif a==0x1018e8:
   self.emit(x,[2,*self.ints(y,4),self.r(z)]);self.ret(1)
  elif a==0x10e7cc:
   self.w(x,y);self.rect(x+4,self.ints(z,4));self.rect(x+20,[*self.ints(t,2),0,0]);self.ret(x)
  elif a==0x1864b8:self.ret(int(self.si(x)/self.si(y)))
  elif any(b['address']<=a<a+size<=b['address']+b['size'] for b in [*RANGES,BACKGROUND]):self.pc.add(a)
  else:raise AssertionError(('unbound guest instruction',hex(a),list(map(hex,q))))
 def write(self,u,access,a,size,value,_):
  if O<=a<O+0x58:self.writes.append([a-O,size,value])
 def run(self,address,args):
  self.u.reg_write(UC_ARM_REG_SP,STACK+0xff00);self.u.reg_write(UC_ARM_REG_LR,STOP)
  for reg,v in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3],args):self.u.reg_write(reg,v)
  self.u.emu_start(address,STOP,count=100000);assert self.u.reg_read(UC_ARM_REG_PC)==STOP
 def case(self,c):
  cached,labels,font,ox,oy,fx,fy,ci,bi,ri,repeat=c
  self.u.mem_write(O+4,bytes([cached,labels]));self.w(O+0x20,ox);self.w(O+0x3c,oy)
  self.w(F+0x100,V+0x200)
  self.w(O+0x24,F+0x100 if fx else 0);self.w(O+0x40,F+0x100 if fy else 0)
  self.rect(E+4,CLIPS[ci]);self.w(S,BACKS[bi]);self.rect(O+0x800,[3,4,67,52] if ri else [0,0,64,48])
  self.run(RANGES[1]['address'],[O,O+0x800,E,S])
  if repeat:
   self.run(RANGES[0]['address'],[O,0,0,0]);self.run(RANGES[1]['address'],[O,O+0x800,E,S])
   if repeat==2:
    self.rect(O+0x800,[0,0,65,49]);self.run(RANGES[1]['address'],[O,O+0x800,E,S])
  before=len(self.calls);self.run(RANGES[5]['address'],[O]);destruction=self.calls[before:]
  assert not self.bitmaps
  return dict(input=c,trace=self.trace,raster=self.raster,internal=self.internal,calls=self.calls,destruction=destruction,object_writes=self.writes,instruction_count=len(self.pc))
def provider_observations():
 p=subprocess.run([str(R/'temp/recovery-work/grid140/replay'),'--providers'],cwd=R,capture_output=True,text=True,check=True);return json.loads(p.stdout)
def lifecycle(providers):
 out=[]
 for i in [3,4]:
  m=Machine(providers);m.u.mem_write(O,b'\xa5'*0x58);m.run(RANGES[i]['address'],[O,P]);assert m.r(O+8)==P
  for off in [0x10,0x14,0x18,0x20,0x24,0x2c,0x30,0x34,0x3c,0x40,0x44,0x48,0x4c,0x50,0x54]:
   # Boundary resize supplies capacity/backing, both original constructors
   # still independently observed zero writes before provider calls.
   if off not in [0x10,0x18,0x2c,0x34]:assert m.r(O+off)==0,(hex(off),m.r(O+off))
  assert bytes(m.u.mem_read(O+4,2))==b'\0\0' and m.r(O+0x1c)==5 and m.r(O+0x38)==5
  out.append(dict(mangled=NAMES[i],writes=m.writes,calls=m.calls,instruction_count=len(m.pc)))
 for i,cached in itertools.product([5,6],[False,True]):
  m=Machine(providers)
  if cached:
   m.bitmaps[O+0x10000]=[64,48];m.w(O+0x54,O+0x10000);m.w(O+0x10000,V+0x300);m.w(V+0x304,STOP+36)
  m.run(RANGES[i]['address'],[O]);assert not m.bitmaps
  out.append(dict(mangled=NAMES[i],cached=cached,writes=m.writes,calls=m.calls,instruction_count=len(m.pc)))
 return out
def vectors(providers):
 out=[]
 for axis,count in itertools.product([0,1,-1,2147483647],[-7,0,1,len(VALUES)]):
  m=Machine(providers);m.w(O+0x54,0x12345678);selected=O+(12 if axis==0 else 40);m.w(selected+4,0);m.w(selected+12,0)
  for i,v in enumerate(VALUES):m.u.mem_write(A+0x200+4*i,struct.pack('<f',v))
  m.run(RANGES[0]['address'],[O,axis,A+0x200,count])
  assert [m.f(m.r(m.r(selected+4)+4*i)) for i in range(max(0,count))]==VALUES[:max(0,count)]
  assert m.r(selected+8)==max(0,count) and m.r(O+0x54)==0x12345678
  assert all(12<=a<28 if axis==0 else 40<=a<56 for a,n,v in m.writes),m.writes
  out.append(dict(axis=axis,count=count,writes=m.writes,calls=m.calls,cache_unchanged=True))
 return out
def generate():
 providers=provider_observations();cases=[]
 # Every orientation and formatter branch, both clips, font/label fallbacks,
 # brightened saturation and nonzero origin. Cache reuse and rebuild separate.
 for cached,labels,font,ox,oy,fx,fy,ci,bi,ri,repeat in [
  *itertools.product([0],[1],[1],range(4),range(2,6),range(2),range(2),range(4),range(2),[0,1],[0]),
  *itertools.product([0],[0,1],[0],range(3),range(3,5),[0],[0],[0,1],[0],[0],[0]),
  *itertools.product([1],[0,1],[0,1],[1,2],[3,4],[0,1],[0,1],range(4),range(2),[0,1],range(3))]:
  c=[cached,labels,font,ox,oy,fx,fy,ci,bi,ri,repeat];m=Machine(providers,font);cases.append(m.case(c))
 pixel_input=''.join(str(c['input'][7])+' '+str(len(c['raster']))+' '+ ' '.join(str(len(row))+' '+' '.join(map(str,row)) for row in c['raster'])+'\n' for c in cases)
 p=subprocess.run([str(R/'temp/recovery-work/grid140/replay'),'--raster'],input=pixel_input,cwd=R,capture_output=True,text=True,check=True)
 hashes=list(map(int,p.stdout.splitlines()));assert len(hashes)==len(cases)
 for c,h in zip(cases,hashes):c['trace'].append([9,h])
 return dict(elf=str(ELF.relative_to(R)),elf_sha256=SHA,ranges=RANGES,providers=providers,lifecycle=lifecycle(providers),vectors=vectors(providers),cases=cases,boundaries='Only seven original app targets and already-bound BackgroundPainter execute. All Core/CRT/libgcc bodies intercepted. Graphics/formatter/font/bitmap/vector boundaries record exact arguments. Provider widths/coordinates independently observed from real pinned CCL font and existing EQControl. Native RGB565 is intentionally adapted to current RGBA source port; no ARM class/layout/ordinary return/hardware claim. Vector successful allocations only; cache flag never mutated by setGridValues. Constructor and destructor variants have distinct original ranges, not native aliases.')
def verify():
 j=generate();assert j==json.loads((T/'fixtures.json').read_text());print(len(j['cases']),'fresh native render/cache cases;',len(j['lifecycle']),'variant lifecycle cases;',len(j['vectors']),'vector cases; no Core firmware instructions')
if __name__=='__main__':
 if '--generate' in sys.argv:
  j=generate();(T/'fixtures.json').write_text(json.dumps(j,separators=(',',':'))+'\n');print(len(j['cases']),'cases generated')
 else:verify()
