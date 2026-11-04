"""Original ARM instruction oracle; explicit non-Core softfloat/external boundaries."""
import argparse,hashlib,json,struct,itertools,math
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=Path.cwd();PACKETS=ROOT/'temp/recovery-work/reconstruction-200-02/isolated-batch01/packets'
B=0x6000000;D=B+0x2000;P=B+0x4000;V=B+0x5000;H=B+0x6000;T=B+0x7000;STOP=B+0xf000
R=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
def w(v):return struct.pack('<I',v&0xffffffff)
def fl(v):return struct.unpack('<f',w(v))[0]
def fb(v):return struct.unpack('<I',struct.pack('<f',v))[0]
def targets():
 out=[]
 for p in sorted(PACKETS.glob('large02_w03_*')):
  req=json.loads((p/'request.json').read_text());ctx=json.loads((p/'native-context.json').read_text());t=req['targets'][0];body=ctx['bodies'][ctx['roots'][0]];binary=ctx['binaries'][t['original_elf_sha256']];out.append(dict(t,**body,elf_path=binary['path'],firmware=binary['firmware'],role=binary['role'],packet=str(p.relative_to(ROOT))))
 return out
class Oracle:
 def __init__(self,ts):
  self.ts=ts;self.extra={'bodies':{}}
  for name in ['temp/recovery-work/reconstruction-200-02/expansions01/15-large02_w03-native_body/native-context.json', 'temp/recovery-work/reconstruction-200-02/dependency-research06/batch/packets/large02_dep_r02/native-context.json', 'temp/recovery-work/reconstruction-200-02/dependency-research06/batch/packets/large02_dep_r03/native-context.json', 'temp/recovery-work/reconstruction-200-02/dependency-research06/batch/packets/large02_dep_r05/native-context.json', 'temp/recovery-work/reconstruction-200-01/large-batch01/packets/large01_w03_03/native-context.json']:
   context=json.loads((ROOT/name).read_text());assert context['binaries'].get(ts[0]['original_elf_sha256']);self.extra['bodies'].update(context['bodies'])
  self.raw=(ROOT/ts[0]['elf_path']).read_bytes();assert hashlib.sha256(self.raw).hexdigest()==ts[0]['original_elf_sha256'];self.u=Uc(UC_ARCH_ARM,UC_MODE_ARM);pages=set()
  with (ROOT/ts[0]['elf_path']).open('rb') as f:
   e=ELFFile(f)
   for t in ts+list(self.extra['bodies'].values()):
    sec=e.get_section(t['section_index']);assert sec['sh_offset']+t['address']-sec['sh_addr']==t['file_offset'];assert hashlib.sha256(self.raw[t['file_offset']:t['file_offset']+t['size']]).hexdigest()==t['bytes_sha256']
   for seg in e.iter_segments():
    if seg['p_type']=='PT_LOAD':
     a=seg['p_vaddr'];n=seg['p_memsz']
     for page in range(a&~4095,(a+n+4095)&~4095,4096):
      if page not in pages:self.u.mem_map(page,4096);pages.add(page)
     self.u.mem_write(a,seg.data())
  
  for body in self.extra['bodies'].values():assert hashlib.sha256(self.raw[body['file_offset']:body['file_offset']+body['size']]).hexdigest()==body['bytes_sha256']
  self.u.mem_map(B,0x20000);self.object_unmapped=False
 def run(self,m,a):
  u=self.u
  if self.object_unmapped:u.mem_map(B,4096);self.object_unmapped=False
  u.mem_write(B,bytes(0x20000));u.reg_write(UC_ARM_REG_CPSR,0x13)
  for reg in R+[UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_R8,UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_R11,UC_ARM_REG_R12]:u.reg_write(reg,0)
  u.reg_write(UC_ARM_REG_SP,B+0xe000);u.reg_write(UC_ARM_REG_LR,STOP)
  def put(p,v):u.mem_write(p,w(v))
  def get(p):return struct.unpack('<I',u.mem_read(p,4))[0]
  def byte(p,v):u.mem_write(p,bytes([v]))
  def bget(p):return u.mem_read(p,1)[0]
  def ret(v=None):
   if v is not None:u.reg_write(R[0],v&0xffffffff)
   u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  put(B,V);put(H,V+0x200);put(T,V+0x300)
  for off in range(0,0x100,4):put(V+off, B+0x10000+off);put(V+0x200+off,B+0x11000+off);put(V+0x300+off,B+0x12000+off)
  u.reg_write(R[0],B);calls=[];sends=0;releases=0;frees=0;updates=0;payload=[];writes=[];lifecycle=[]
  def bands(n=2):
   put(B+40,D);put(B+44,n);byte(B+0xa30,1)
   for k in range(n):
    q=D+k*320;put(q,6);put(q+4,0x44960000);put(q+8,0x3f3504f3);put(q+12,0);byte(q+0x13a,0)
    
    calc=q+16;put(calc+0x50,6)
    for off,v in [(0x58,48000.),(0x60,0.),(0x68,1000.),(0x70,.7),(0xb8,math.pi/48000)]+[(0xc0+8*z,1.) for z in range(13)]:u.mem_write(calc+off,struct.pack('<d',v))
    for j in range(5):u.mem_write(q+0x88+8*j,struct.pack('<d',1. if j==0 else 0.))
  def bandout(n=2):
   o=[bget(B+0xa30),bget(B+28)]
   for k in range(n):
    q=D+k*320;o +=[get(q),get(q+4),get(q+8),get(q+12),bget(q+312),bget(q+313),bget(q+314),bget(q+0x58)]
   return o
  if m==1:
   typ,ch,owner,tag,val=a[:5];put(P,typ);put(P+8,ch);put(P+12,tag if typ==1348563553 else owner);put(P+16,val);put(B+4,111);u.reg_write(R[1],P)
  elif m==2:
   has,flag,ch,old=a;put(B+20,T if has else 0);put(B+4,ch);put(P+8,old);u.reg_write(R[1],P);u.reg_write(R[2],flag)
  elif m in (3,11):
   n=a[0] if a[0]!=0xffffffff else 0;put(B+12,D if a[0]!=0xffffffff else 0);put(D+4,D+0x100);put(D+8,n)
   for k in range(n):put(D+0x100+k*4,D+0x200+k*64);put(D+0x200+k*64,10+k);put(D+0x214+k*64,fb(k*.25))
  elif m==4:put(B+24,a[0]);u.reg_write(R[1],a[1])
  elif m==5:u.reg_write(R[1],H if a[0] else 0)
  elif m==6:put(B+24,a[0]);u.reg_write(R[1],a[1]);u.reg_write(R[2],a[2])
  elif m==8:put(B+24,a[0]);put(P+16,a[1]);put(P+20,a[2]);put(P+24,a[3]);u.reg_write(R[1],P)
  elif m in (9,15):
   bands();u.reg_write(R[1],a[0]);
   if m==9:u.reg_write(R[2],a[1]);byte(B+0xa30,a[2]);byte(B+28,a[3]);enabled=a[4];edge=a[5]
   else:byte(B+0xa30,a[1]);enabled=a[2];edge=a[3]
   for k in range(2):
    q=D+k*320;byte(q+314,enabled);byte(q+312,edge)
    if m==15:
     for off,v in zip([0,4,8,12],a[4:]):put(q+off,v)
  elif m==10:put(B+24,a[0])
  elif m in (12,17,19,20,22,24,25):byte(B+29,a[0]);put(B+20,T if a[1] else 0)
  elif m==13:put(B+20,T if a[0] else 0);put(P,a[1]);u.reg_write(R[1],P)
  elif m==14:put(B+20,T if a[0] else 0);byte(B+29,a[2]);u.reg_write(R[1],T if a[1]==1 else H if a[1]==2 else 0)
  elif m==16:byte(B+28,a[0]);put(B+20,T if a[1] else 0);put(B+36,a[2]);put(B+32,a[3])
  elif m==18:
   bands(a[0]);byte(B+0xa30,a[1]);put(B+20,T if a[3] else 0);put(B+4,55)
   if a[4]:byte(B+28,1);put(B+36,fb(48000));put(V+0x54,self.ts[17]['address'])
   for k in range(a[0]):byte(D+k*320+313,(a[2]>>k)&1);byte(D+k*320+314,1)
  elif m in (21,23):u.reg_write(R[1],a[0]);u.reg_write(R[2],a[1]);u.reg_write(R[3],0)
  allowed=[(t['address'],t['address']+t['size']) for t in self.ts]+[(t['address'],t['address']+t['size']) for t in self.extra['bodies'].values()]
  def hook(u,pc,size,_):
   nonlocal sends,releases,frees,updates,payload
   if pc==STOP:u.emu_stop();return
   r=[u.reg_read(reg) for reg in R]
   if pc in (B+0x11000,B+0x12000):
    sends+=1
    if m==18:
     prop=r[1];count=get(prop+204);payload=[get(prop+8),count]
     for k in range(count):payload +=[get(prop+12+24*k)]+[get(prop+16+24*k+4*j) for j in range(5)]
    ret();return
   if pc in (B+0x11008,B+0x12008):
    releases+=1;lifecycle.append(dict(event="target_release",target=r[0]));ret();return
   if pc==B+0x10014:calls.extend([20,r[1],r[2]]);ret();return
   if pc==B+0x10050:
    calls.append(80)
    if len(a)>5 and a[5]:u.reg_write(UC_ARM_REG_PC,0xb2664)
    else:ret()
    return
   if pc==B+0x10054:updates+=1;ret();return
   if pc in [B+0x10058,B+0x1005c,B+0x10060]:
    target={B+0x10058:0xc4f04,B+0x1005c:0xc4ecc,B+0x10060:0xc4fac}[pc]
    calls.extend([target,r[1]]);u.reg_write(UC_ARM_REG_PC,target);return
   if pc==B+0x1004c:u.reg_write(UC_ARM_REG_PC,self.ts[19]['address']);return
   if pc==0xac10:
    assert r[0]==B;u.mem_unmap(B,4096);self.object_unmapped=True;frees+=1;lifecycle.append(dict(event="operator_delete",pointer=r[0],allocation_live=False));ret();return
   if pc in [0x1578e0,0x157940]:ret(int(fl(r[0])==fl(r[1])) if pc==0x1578e0 else int(fl(r[0])>fl(r[1])));return
   if pc==0x1572b0:ret(fb(fl(r[0])+fl(r[1])));return
   if pc==0x157958:
    assert math.isfinite(fl(r[0])),(m,a,hex(r[0]));ret(int(fl(r[0])));return
   if pc==0x15746c:ret(fb(float(r[0] if r[0]<2**31 else r[0]-2**32)));return
   if pc==0x157204:
    value=struct.unpack('<d',w(r[0])+w(r[1]))[0];ret(fb(value));return
   if pc==0xbb514:
    calls.extend([pc,r[1],r[2],r[3],get(u.reg_read(UC_ARM_REG_SP))]);return
   def double(lo,hi):return struct.unpack('<d',w(lo)+w(hi))[0]
   def dret(value):
    lo,hi=struct.unpack('<II',struct.pack('<d',value));u.reg_write(R[0],lo);u.reg_write(R[1],hi);ret()
   if pc==0x156ac4:dret(float(fl(r[0])));return
   if pc==0x157550:ret(fb(fl(r[0])*fl(r[1])));return
   if pc==0x1578f8:ret(int(fl(r[0])<fl(r[1])));return
   if pc in [0x156768,0x156764,0x156b78,0x156e08]:
    left=double(*r[:2]);right=double(*r[2:]);dret({0x156768:lambda:left+right,0x156764:lambda:left-right,0x156b78:lambda:left*right,0x156e08:lambda:left/right}[pc]());return
   if pc in [0x1570f4,0x15710c,0x157124]:
    left=double(*r[:2]);right=double(*r[2:]);ret(int({0x1570f4:left<right,0x15710c:left<=right,0x157124:left>=right}[pc]));return
   if pc in [0xaa30,0xae74,0xb06c,0xa820,0xab50]:
    left=double(*r[:2]);dret({0xaa30:lambda:math.cos(left),0xae74:lambda:math.tan(left),0xb06c:lambda:math.sin(left),0xa820:lambda:math.sqrt(left),0xab50:lambda:math.pow(left,double(*r[2:]))}[pc]());return
   if pc==0xb251c:
    # Existing Controller C1 source-provider boundary, record native stores.
    for off,v in [(4,0),(8,0xffffffff),(12,r[2]),(16,0),(20,0),(24,r[1]),(28,0),(32,0),(36,0)]:put(B+off,v)
    ret();return
   if not any(lo<=pc<hi for lo,hi in allowed):raise RuntimeError(f'method{m}: unbound instruction {pc:x}')
  def memory_write(u,access,address,size,value,_):
   if B<=address<B+0xa40 or D<=address<D+8*320:writes.append([address-B,size,value])
  wh=u.hook_add(UC_HOOK_MEM_WRITE,memory_write)
  handle=u.hook_add(UC_HOOK_CODE,hook)
  try:u.emu_start(self.ts[15]['address'] if m==18 and a[4] else self.ts[m-1]['address'],STOP,count=100000)
  finally:u.hook_del(handle);u.hook_del(wh)
  assert u.reg_read(UC_ARM_REG_PC)==STOP,f'No return m{m}'
  result=u.reg_read(R[0])
  if m==1:o=[get(B+4),bget(B+28),bget(B+29)]+calls+([get(B+36)] if len(a)>5 and a[5] else [])
  elif m==2:o=[get(P+8),sends]
  elif m==3:o=calls
  elif m in (4,6,8,10,11,15):o=[result]
  elif m==5:o=[int(get(B+16)!=0)]
  elif m==7:o=[bget(B+29)]
  elif m==9:o=bandout()
  elif m in (12,17,19,20,22,24,25):o=[releases,frees]
  elif m==13:o=[sends]
  elif m==14:o=[releases,1 if get(B+20)==T else 2 if get(B+20)==H else 0]
  elif m==16:o=[result,bget(B+28),get(B+32),updates]
  elif m==18:o=[bget(B+28),sends]+[bget(D+k*320+313) for k in range(a[0])]+payload+([result] if a[4] else [])
  elif m in (21,23):
   # Native constructor uses inline slots at B+0x30.
   oldD=D;DUMMY=0
   n=get(B+44);o=[n,bget(B+0xa30),bget(B+28)]
   for k in range(n):
    q=B+48+k*320;o +=[get(q),get(q+4),get(q+8),get(q+12),bget(q+312),bget(q+313),bget(q+314),bget(q+0x58)]
  return dict(method=m,input=[v&0xffffffff for v in a],expected=o,external_calls=calls,native_memory_writes=writes,native_lifecycle=lifecycle)
def generate():
 ts=targets();oracle=Oracle(ts);cases=[]
 def add(m,a):cases.append(oracle.run(m,a))
 for t in [0,1399157877,1415672423,1348563553]:
  for owner in [0,1,2,255]:
   add(1,[t,77,owner,3,fb(.25)])
   if t==1399157877:
    for rate in [0,0x80000000,fb(48000),0x7fc01234]:add(1,[t,rate,owner,3,fb(.25),1])
 for v in itertools.product([0,1],[0,1],[0,77,0xffffffff],[12]):add(2,list(v))
 for n in [0,1,3,0xffffffff]:add(3,[n]);add(11,[n])
 for flags in [0,1,2,4,7,8,15,0xffffffff]:
  for p in [0,1,2,0xffffffff]:add(4,[flags,p])
  add(10,[flags])
  for ins,outs in itertools.product([0,1,2,3],repeat=2):add(6,[flags,ins,outs])
  for ins,outs,p in itertools.product([0,1,2],[0,1,2],[0,1,2,0xffffffff]):add(8,[flags,ins,outs,p])
 for exists in [0,1]:add(5,[exists])
 add(7,[])
 for owner,target in itertools.product([0,1],[0,1]):
  for m in [12,17,19,20,22,24,25]:add(m,[owner,target])
 for t in [0,1]:add(13,[t,123])
 for old,new,owner in itertools.product([0,1],[0,1,2],[0,1]):add(14,[old,new,owner])
 for d,t,r,word in itertools.product([0,1],[0,1],[0,fb(-1),fb(48000),0x7fc00000],[0,2,7]):add(16,[d,t,r,word])
 for tag in [0,0xffffffff]+list(range(1,13)):
  values=[0,0x80000000,fb(.25),fb(-2),0x7fc01234,0x7f800000] if tag==0 or tag==0xffffffff or (tag-1)%6!=0 else [fb(v) for v in [0,1,2,3,4,99]]
  for enabled,dirty,benabled,edge in itertools.product([0,1],repeat=4):
   for v in values:add(9,[tag,v,enabled,dirty,benabled,edge])
  for enabled,benabled,edge,typ in itertools.product([0,1],[0,1],[0,1],[3,8,9,6,99]):add(15,[tag,enabled,benabled,edge,typ,fb(1200),fb(.70710677),fb(-3)])
 for n in [0,1,2,8]:
  for flags in [0,7,8,15]:add(21,[n,flags]);add(23,[n,flags])
 for n,enabled,mask,target,pipeline in itertools.product([0,1,2,8],[0,1],[0,1,255],[0,1],[0,1]):add(18,[n,enabled,mask,target,pipeline])
 return dict(version=1,targets=ts,cases=cases,boundaries={'softfloat':'Python IEEE binary32 conversion/add/compare adapters; no Core instructions executed','calculator':'exact expanded setParams mode6 instructions executed; Python IEEE/libm adapters only at recorded helper boundaries','ControllerC1':'actual existing source provider stores modeled at explicit boundary; source reused not reconstructed'})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();Path(a.out).write_text(json.dumps(generate(),indent=2)+'\n')
