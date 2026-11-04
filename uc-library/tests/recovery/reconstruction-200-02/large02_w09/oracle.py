"""Bound original ARM instructions only; CCL calls are explicit recorded boundaries."""
import hashlib,json,struct,sys,math
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
PACKETS=Path('temp/recovery-work/reconstruction-200-02/isolated-batch01/packets')
elfpaths={'client':Path('rootfs/CS18_v13840/home/root/surface'),'server':Path('rootfs/RML16AI_Rack_13731/home/root/mixer')}
hashes={'client':'304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0','server':'9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'}
import re
TARGETS={}
for i in range(1,26):
 s=(PACKETS/f'large02_w09_{i:02}'/'ELF_CONTEXT.md').read_text();m=re.search(r'original `([^`]+)`; address `(0x[0-9a-f]+)`; size (\d+); section (\S+); SHA256 `([^`]+)`',s);off=int(re.search(r'file offset `(0x[0-9a-f]+)`',s)[1],16);role='client' if hashes['client'] in s else 'server';data=elfpaths[role].read_bytes();assert hashlib.sha256(data).hexdigest()==hashes[role];body=data[off:off+int(m[3])];assert hashlib.sha256(body).hexdigest()==m[5];TARGETS[i]=(role,int(m[2],16),body,m[1])
# Root-expanded existing app dependency, still frozen to the parent baseline.
p=Path('temp/recovery-work/reconstruction-200-02/expansions02/04-large02_w09-native_body/ELF_CONTEXT.md');s=p.read_text();m=re.search(r'address `(0x[0-9a-f]+)`; size (\d+); section (\S+); SHA256 `([^`]+)`',s);off=int(re.search(r'file offset `(0x[0-9a-f]+)`',s)[1],16);body=elfpaths['server'].read_bytes()[off:off+int(m[2])];assert hashlib.sha256(body).hexdigest()==m[4];TARGETS[26]=('server',int(m[1],16),body,'_ZN8Presonus13MuteGroupBase12updateStatusEv')
p=Path('temp/recovery-work/reconstruction-200-02/dependency-research06/batch/packets/large02_dep_r08/ELF_CONTEXT.md');s=p.read_text();m=re.search(r'address `(0x[0-9a-f]+)`; size (\d+); section (\S+); SHA256 `([^`]+)`',s);off=int(re.search(r'file offset `(0x[0-9a-f]+)`',s)[1],16);body=elfpaths['client'].read_bytes()[off:off+int(m[2])];assert hashlib.sha256(body).hexdigest()==m[4];TARGETS[27]=('client',int(m[1],16),body,'_ZN8Presonus10PotControlD1Ev')
p=Path('temp/recovery-work/reconstruction-200-02/expansions02/03-large02_w09-native_body/ELF_CONTEXT.md');s=p.read_text();m=re.search(r'address `(0x[0-9a-f]+)`; size (\d+); section (\S+); SHA256 `([^`]+)`',s);off=int(re.search(r'file offset `(0x[0-9a-f]+)`',s)[1],16);body=elfpaths['client'].read_bytes()[off:off+int(m[2])];assert hashlib.sha256(body).hexdigest()==m[4];TARGETS[28]=('client',int(m[1],16),body,'_ZN8Presonus10PotControl12changeFramesEv')
def bits(x):return struct.unpack('<I',struct.pack('<f',x))[0]
def floating(x):return struct.unpack('<f',struct.pack('<I',x))[0]
class Native:
 def __init__(self,i,extra=()):
  role,start,body,_=TARGETS[i];self.start=start;self.role=role;self.trace=[];self.u=Uc(UC_ARCH_ARM,UC_MODE_ARM);self.allowed=[]
  for a in [0x100000,0x200000,0x300000,0x500000]:self.u.mem_map(a,0x20000)
  self.pages=set()
  for n in (i,*extra):
   r,a,b,_=TARGETS[n];assert r==role
   for page in range(a&~4095,(a+len(b)+4095)&~4095,4096):
    if page not in self.pages:self.u.mem_map(page,4096);self.pages.add(page)
   self.u.mem_write(a,b);self.allowed.append((a,a+len(b)))
  self.u.reg_write(UC_ARM_REG_SP,0x218000);self.u.reg_write(UC_ARM_REG_LR,0x300000);self.u.reg_write(UC_ARM_REG_R0,0x100000)
  self.handlers={};self.u.hook_add(UC_HOOK_CODE,self.hook)
 def write(self,a,*x):self.u.mem_write(a,struct.pack('<'+'I'*len(x),*(v&0xffffffff for v in x)))
 def read(self,a):return struct.unpack('<I',self.u.mem_read(a,4))[0]
 def r(self,n):return self.u.reg_read([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2][n])
 def hook(self,u,a,size,_):
  if any(l<=a<h for l,h in self.allowed):return
  if a not in self.handlers:raise RuntimeError(f'unbound non-app boundary {a:x}')
  self.handlers[a]();u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def ret(self,v=0):self.u.reg_write(UC_ARM_REG_R0,v&0xffffffff)
 def run(self):
  for address in self.handlers:
   page=address&~4095
   if not any(lo<=address<hi for lo,hi in [(0x100000,0x120000),(0x200000,0x220000),(0x300000,0x320000),(0x500000,0x520000)]) and page not in self.pages:self.u.mem_map(page,4096);self.pages.add(page)
  self.u.emu_start(self.start,0x300000,count=20000)
  assert self.u.reg_read(UC_ARM_REG_PC)==0x300000,"native did not return"
 def param(self):
  self.write(0x110000,0x500000);self.write(0x500044,0x510004);self.write(0x500058,0x510000);self.write(0x500060,0x510008)
  def setvalue():self.write(self.r(0)+0x10,self.r(1));self.trace.append(['setValue',self.r(1),self.r(2)]);self.ret()
  self.handlers[0x510000]=setvalue;self.handlers[0x510004]=lambda:self.ret(self.read(self.r(0)+0x10));self.handlers[0x510008]=lambda:self.ret(self.read(self.r(0)+0x10))
cases=[]
def add(command,n,result,trace=None):cases.append({'command':command,'target':n,'expected':result,'trace':trace or []})
for options in [0,0x400000]:
 for count in [0,1,8]:
  for old in [-1,0,3]:
   for frame in [-2,0,3,9]:
    for dirty in [0,1]:
     n=Native(16);n.write(0x100040,options);n.write(0x100068,old,count);n.u.mem_write(0x100084,bytes([dirty]));n.u.reg_write(UC_ARM_REG_R1,frame&0xffffffff);n.run();result=struct.unpack('<i',n.u.mem_read(0x100068,4))[0];add(f'frame {old} {count} {options} {dirty} {frame}',16,[result,n.u.mem_read(0x100084,1)[0]])
for options in [0,0x400000]:
 for thresholds in [[.2],[.2,.5],[.2,.5,.8],[.2,.5,.8,1.0]]:
  for value in [0,.2,.3,.5,.8,1.]:
   n=Native(17,(16,));n.param();n.write(0x100000,0x501000);n.write(0x501068,TARGETS[16][1]);n.write(0x100040,options);n.write(0x100068,-1,len(thresholds));n.write(0x100074,0x112000,len(thresholds));n.write(0x112000,*map(bits,thresholds));n.write(0x110010,bits(value));n.handlers[0xf6cf8]=lambda:n.ret(0x110000);n.handlers[0x187798]=lambda:n.ret(int(floating(n.r(0))<floating(n.r(1))));n.run();result=struct.unpack('<i',n.u.mem_read(0x100068,4))[0];add('threshold '+f'{options} {len(thresholds)} {value} '+' '.join(map(str,thresholds)),17,[result,n.u.mem_read(0x100084,1)[0]])
for count in [0,1,3,8]:
 n=Native(2);n.param();n.write(0x100024,0x108000);n.write(0x1082c4,0x109000,count)
 for i in range(count):n.write(0x109000+4*i,0x110000+i*0x100);n.write(0x110000+i*0x100,0x500000)
 def append():n.trace.append(['append',n.read(n.r(1))]);n.ret()
 n.handlers[0x4c1bc]=append;n.run();add(f'all {count}',2,[len([t for t in n.trace if t[0]=='append'])]+[floating(n.read(0x110010+i*0x100)) for i in range(count)],n.trace)
for enabled in [0,1]:
 for message in [0,2,3,4]:
  for value in [-1.,0.,1.]:
   n=Native(9);n.param();n.write(0x110010,bits(value));n.u.mem_write(0x1000ad,bytes([enabled]));n.u.reg_write(UC_ARM_REG_R1,0x110000);n.u.reg_write(UC_ARM_REG_R2,message);n.handlers[0x1578e0]=lambda:n.ret(int(floating(n.r(0))==floating(n.r(1))));n.run();add(f'param {enabled} {message} {value}',9,[floating(n.read(0x110010)),n.u.mem_read(0x1000ad,1)[0]],n.trace)
# Original constructors keep C1 and C2 as distinct native ranges.
for target in [4,11,21,22]:
 n=Native(target,(4,) if target in [21,22] else ());n.u.reg_write(UC_ARM_REG_R1,0x108000)
 def vector_ctor():n.write(n.r(0)+4,0,0,0);n.trace.append(['vectorCtor',n.r(1),n.r(2)]);n.ret()
 n.handlers[0x77634]=vector_ctor;n.run();add('allctor' if target in [21,22] else 'basector',target,[n.read(0x100018),int(n.read(0x100024)==0x108000)],n.trace)
for target in [24,25]:
 n=Native(target,(4,10));filename=b'fixture\0'+bytes(248);sp=n.u.reg_read(UC_ARM_REG_SP);n.u.mem_write(sp,filename[12:]+struct.pack('<II',0x110000,0x108000));n.u.reg_write(UC_ARM_REG_R1,struct.unpack('<I',filename[:4])[0]);n.u.reg_write(UC_ARM_REG_R2,struct.unpack('<I',filename[4:8])[0]);from unicorn.arm_const import UC_ARM_REG_R3
 n.u.reg_write(UC_ARM_REG_R3,struct.unpack('<I',filename[8:12])[0]);n.handlers[0x77634]=lambda:n.ret();n.handlers[0x119e8c]=lambda:n.ret()
 def copy():n.u.mem_write(n.r(0),bytes(n.u.mem_read(n.r(1),n.r(2))));n.ret(n.r(0))
 n.handlers[0xae68]=copy;n.handlers[0x11d4f4]=lambda:(n.trace.append(['addObserver',n.r(0),n.r(1)]),n.ret());n.run();assert bytes(n.u.mem_read(0x1000b4,256))==filename;identity=int(n.read(0x100024)==0x108000);n.handlers[0x11c2e4]=lambda:(n.trace.append(['removeObserver',n.r(0),n.r(1)]),n.ret());n.handlers[0x11a53c]=lambda:n.ret();n.handlers[0x12740]=lambda:n.ret();n.start=TARGETS[10][1];n.u.reg_write(UC_ARM_REG_R0,0x100000);n.u.reg_write(UC_ARM_REG_LR,0x300000);n.run();adds=sum(t[0]=='addObserver' for t in n.trace);removes=sum(t[0]=='removeObserver' for t in n.trace);add('filector',target,[adds,adds-removes,identity],n.trace)
for target in [5,6,7,8,10,12,13,18,19,27]:
 n=Native(target);n.write(0x1001b4,0x110000);removed=[];freed=[]
 def remove():removed.append(n.r(1));n.trace.append(['removeObserver',n.r(0),n.r(1)]);n.ret()
 def deallocate():assert n.r(0)==0x100000;freed.append(n.r(0));n.trace.append(['operatorDeleteBoundary',n.r(0)]);n.ret()
 for address in [0x12740,0x11a53c,0x11fe8,0x69f64,0xfb15c]:n.handlers[address]=lambda:n.ret()
 n.handlers[0x11c2e4]=remove;n.handlers[0xac10]=deallocate;n.handlers[0xad5c]=deallocate
 if target in [18,19,27]:
  for off,ptr in [(0x58,0x111000),(0x5c,0x112000),(0x60,0x113000)]:n.write(0x100000+off,ptr);n.write(ptr+0x34,1)
 n.run();kind='base' if target in [6,8] else 'all' if target in [7,12] else 'vu' if target in [18,19] else 'pot' if target==27 else 'file';deleting=target in [5,6,7,19]
 result=[len(freed)]+([n.read(p+0x34) for p in [0x111000,0x112000,0x113000]] if kind in ['vu','pot'] else [int(kind=='file')-len(removed)])
 add(f'destroy {kind} {int(deleting)}',target,result,n.trace)
for target in [14,15]:
 n=Native(target)
 def pot_ctor():n.write(0x100040,0x14);n.write(0x100068,-1,0);n.trace.append(['appPotCtorBoundary']);n.ret()
 n.handlers[0x6637c]=pot_ctor;n.handlers[0x69e64]=lambda:n.ret()
 for address,name in [(0x11f54,'timerCtorBoundary'),(0x12228,'timerBeginBoundary')]:
  n.handlers[address]=lambda name=name:(n.trace.append([name,n.r(1)]),n.ret())
 n.run();add('ctor',target,[struct.unpack('<i',n.u.mem_read(0x100068,4))[0],n.read(0x10006c),n.read(0x100040),n.u.mem_read(0x100084,1)[0]],n.trace)
for values in [(-1,0,1),(1,1,1),(0,0,0),(-1,-1,-1),(2,0,2),(.5,1.5,-.5),(.01,1.0,2.5)]:
 is_float=any(type(x)==float for x in values)
 n=Native(3,(26,));n.write(0x100024,0x108000);n.write(0x108120,0x109000,3);n.u.reg_write(UC_ARM_REG_R1,0x114000)
 for i,name in enumerate(['a','b','c']):
  channel=0x10a000+i*0x200;n.write(0x109000+4*i,channel);n.write(channel+0x50,0x10f000);n.u.mem_write(0x10f008,b'input\0');n.u.mem_write(channel+8,name.encode()+b'\0');n.write(channel+0xe8,0x110000+i*0x100);n.write(0x11000c+i*0x100,0x10f100);n.u.mem_write(0x10f108,b'mute\0');n.u.mem_write(0x115004+i*0x100,struct.pack('<H',2 if is_float else 1));n.u.mem_write(0x115008+i*0x100,struct.pack('<d' if is_float else '<q',values[i]))
 def attrs():
  key=bytes(n.u.mem_read(n.r(1),8)).split(b'\0')[0].decode();n.ret(0x114100 if key=='input' else 0x114200+['a','b','c'].index(key)*0x100)
 def lookup():n.ret(0x115000+((n.r(0)-0x114200)//0x100)*0x100)
 def append_cache():n.write(0x100018,n.read(0x100018)+1);n.trace.append(['append',n.read(n.r(1))]);n.ret()
 def fixdfdi():
  value=struct.unpack('<d',struct.pack('<II',n.r(0),n.r(1)))[0];integer=int(value)&0xffffffffffffffff;n.ret(integer&0xffffffff);n.u.reg_write(UC_ARM_REG_R1,integer>>32)
 n.handlers[0x157aa4]=fixdfdi
 n.handlers[0x122198]=attrs;n.handlers[0x121d4c]=lookup;n.handlers[0x775f0]=lambda:n.write(0x100018,0);n.handlers[0x11697c]=lambda:n.ret();n.handlers[0x116a38]=lambda:n.ret();n.handlers[0xae98]=lambda:n.ret(1);n.handlers[0xafe8]=lambda:(n.u.mem_write(n.r(0),bytes(n.u.mem_read(n.r(1),n.r(2)))),n.ret());n.handlers[0x4c1bc]=append_cache;n.run();add(('cachef ' if is_float else 'cache ')+' '.join(map(str,values)),3,[n.read(0x100018)],n.trace)
for mode in [1,2]:
 for frame in [0,1,3,4]:
  for options in [0,8]:
   n=Native(1);n.write(0x100040,options);n.write(0x100058,0x111000,0x112000,0x113000,mode,frame,4);n.write(0x114000,0x115000);n.write(0x115000,0x500000);n.write(0x500028,0x51000c);n.u.reg_write(UC_ARM_REG_R1,0x114000);calls=[]
   for i in range(3):n.write(0x111008+i*0x1000,4,10+2*i,40+40*i)
   def draw():calls.extend([(n.r(2)-0x111000)//0x1000,*struct.unpack('<ii',n.u.mem_read(n.r(1),8)),*struct.unpack('<iiii',n.u.mem_read(n.u.reg_read(UC_ARM_REG_R3),16))]);n.ret(1)
   n.handlers[0x51000c]=draw;n.handlers[0x1864b8]=lambda:n.ret(int(struct.unpack('<i',struct.pack('<I',n.r(0)))[0]/struct.unpack('<i',struct.pack('<I',n.r(1)))[0]));n.run();add(f'draw {mode} {frame} {options}',1,[len(calls)//7,*calls])
for options in [0,0x400000]:
 for value in [0,.01,.5,1.]:
  n=Native(17,(16,28));n.param();n.write(0x100000,0x501000);n.write(0x501068,TARGETS[16][1]);n.write(0x100040,options);n.write(0x100068,-1,4);n.write(0x110010,bits(value));n.handlers[0xf6cf8]=lambda:n.ret(0x110000);n.handlers[0x1877e0]=lambda:n.ret(int(floating(n.r(0))>floating(n.r(1))));n.handlers[0x187314]=lambda:n.ret(bits(struct.unpack('<i',struct.pack('<I',n.r(0)))[0]));n.handlers[0x1873f0]=lambda:n.ret(bits(floating(n.r(0))*floating(n.r(1))));n.handlers[0x1877f8]=lambda:n.ret(int(floating(n.r(0))));n.run();add(f'threshold {options} 0 {value}',17,[struct.unpack('<i',n.u.mem_read(0x100068,4))[0],n.u.mem_read(0x100084,1)[0]],n.trace)
Path(sys.argv[1]).write_text(json.dumps({'oracle':'original ARM instructions, bounded CCL/softfloat boundaries; never Core execution','cases':cases},indent=2)+'\n');print(len(cases),'original ARM observations')
