import pathlib,json,hashlib,struct
from elftools.elf.elffile import ELFFile
from unicorn import *
from unicorn.arm_const import *
ROOT=pathlib.Path.cwd(); ELF=ROOT/'rootfs/RML16AI_Rack_13731/home/root/mixer';RAW=ELF.read_bytes(); SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
assert hashlib.sha256(RAW).hexdigest()==SHA
with ELF.open('rb') as f:
 e=ELFFile(f);segments=[(s['p_vaddr'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD'];sec=e.get_section(12);off=sec['sh_offset']+0xa276c-sec['sh_addr']
assert off==0x9a76c and hashlib.sha256(RAW[off:off+752]).hexdigest()=='22f70171c6f9b60507e7cd4a5329ea644603332d1f0e5cc248565e40271a3c94'
OBJ=0x600000;STACK=0x700000;STOP=0x800000
# Verified target literal at a2a3c = singleton address
SINGLE=struct.unpack_from('<I',RAW,off+0x2d0)[0]
# Both3-byte ELF objects remain distinct identities despite identical bytes.
LITERALS={}
with ELF.open('rb') as f:
 e=ELFFile(f)
 for a in [0x35ab70,0x35ab73]:
  sec=next(s for s in e.iter_sections() if s['sh_addr']<=a<s['sh_addr']+s['sh_size']);o=sec['sh_offset']+a-sec['sh_addr'];b=RAW[o:o+3];assert b==bytes.fromhex('f040f7');LITERALS[hex(a)]={'file_offset':o,'bytes':b.hex(),'sha256':hashlib.sha256(b).hexdigest()}
AUDIT={'versions':{'unicorn':__import__('unicorn').__version__,'pyelftools':__import__('elftools').__version__},'literals':LITERALS,'elf_sha256':SHA,'address':0xa276c,'size':752,'section':'.text','file_offset':off,'range_sha256':hashlib.sha256(RAW[off:off+752]).hexdigest(),'pc_count':0,'writes':0,'unexpected':[],'boundaries':{},'native_allocation_unwind':'excluded: singleton preinitialized in ARM; host lazy lifecycle exercised separately'}
def signed(x): return x-(1<<64) if x>>63 else x

def execute(c):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x500000)
 for a,d in segments:u.mem_write(a,d)
 for a in [OBJ,STACK,STOP]:u.mem_map(a,0x10000)
 def w(a,v,n=4):u.mem_write(a,int(v&((1<<(8*n))-1)).to_bytes(n,'little'))
 def r(a,n=4):return int.from_bytes(u.mem_read(a,n),'little')
 w(OBJ+8,1,1);w(OBJ+0x60,c['flag']);w(OBJ+0x68,c['last'],8);w(OBJ+0x70,c['received'],8);w(SINGLE,OBJ+0x1000)
 ticks=iter(c['clocks']); clocks=[];posts=[];poststates=[];remaining=[c['queue']];reads=[0];trace=[]
 def clock():
  v=next(ticks);clocks.append(v);trace.append('clock');return v
 def cb(uc,a,size,data):
  if 0xa276c<=a and a+size<=0xa276c+752:AUDIT['pc_count']+=1;return
  entries={0x104548:'empty',0xaa60:'memset',0x116908:'clock',0x157a08:'divide',0x1037d8:'read',0xa38fc:'post',0xae68:'memcpy',0xa2a94:'construct',0xa2b94:'singleton'}
  if a not in entries:raise RuntimeError('unexpected PC '+hex(a))
  k=entries[a];AUDIT['boundaries'][k]=AUDIT['boundaries'].get(k,0)+1
  r0,r1,r2,r3=[uc.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]];v=None
  if k=='empty':assert r0==OBJ+0x34;v=int(remaining[0]==0);trace.append('empty')
  elif k=='memset':u.mem_write(r0,bytes([r1&255])*r2);v=r0
  elif k=='memcpy':u.mem_write(r0,bytes(u.mem_read(r1,r2)));v=r0
  elif k=='clock':v=clock()*1000000;uc.reg_write(UC_ARM_REG_R1,(v>>32)&0xffffffff)
  elif k=='divide':
   n=signed(r0|(r1<<32));d=r2|(r3<<32);v=abs(n)//d*(-1 if n<0 else 1);uc.reg_write(UC_ARM_REG_R1,(v>>32)&0xffffffff)
  elif k=='read':
   assert r0==OBJ+0x34 and remaining[0]>0
   payload=bytes([0xf0,0x40,0,0,0,0,0,reads[0]&15,0xf7]);u.mem_write(r1,payload);w(r2,len(payload),1);remaining[0]-=1;reads[0]+=1;v=1;trace.append('read')
  elif k=='post':
   posts.append(bytes(u.mem_read(r1+8,r(r1+0x108,1))).hex());poststates.append([r(OBJ+0x60),r(OBJ+0x68,8),r(OBJ+8,1)]);trace.append('post')
  elif k=='construct':
   p=bytes(u.mem_read(r1,r2));u.mem_write(r0,bytes(8)+bytes([0x45])*255);w(r0+0x108,r2,1);clock();u.mem_write(r0+8,p);clock();v=r0
  elif k=='singleton':v=OBJ+0x1000
  if v is not None:uc.reg_write(UC_ARM_REG_R0,v&0xffffffff)
  uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 def writes(uc,access,a,size,value,data):
  assert (STACK<=a and a+size<=STACK+0x10000) or (a==OBJ+8 and size==1) or (OBJ+0x60<=a and a+size<=OBJ+0x64) or (OBJ+0x68<=a and a+size<=OBJ+0x70),(hex(a),size)
  AUDIT['writes']+=1
 u.hook_add(UC_HOOK_CODE,cb);u.hook_add(UC_HOOK_MEM_WRITE,writes)
 u.reg_write(UC_ARM_REG_R0,OBJ);u.reg_write(UC_ARM_REG_SP,STACK+0x9000);u.reg_write(UC_ARM_REG_LR,STOP)
 u.emu_start(0xa276c,STOP,count=20000);assert u.reg_read(UC_ARM_REG_PC)==STOP
 c.update(expected_flag=r(OBJ+0x60),expected_last=r(OBJ+0x68,8),expected_byte=r(OBJ+8,1),remaining=remaining[0],posts=posts,poststates=poststates,clock_count=len(clocks),trace=trace);return c
cases=[]
for n in [0,1,5,6,7,12]:cases.append(dict(flag=1,queue=n,last=77,received=88,clocks=list(range(100,125))))
for last in [0,0xfffffff0,0x100000010,-1000 & ((1<<64)-1)]:
 for delta in [399,400,401]:
  now=signed((last+delta)&((1<<64)-1));cases.append(dict(flag=0,queue=7,last=last,received=now-5000,clocks=[now,now+1,now+2]))
for delta in [4999,5000,5001]:cases.append(dict(flag=0,queue=1,last=6000,received=1000,clocks=[1000+delta]*3))
for received in [0xfffffff0,-6000]:
 for delta in [4999,5000,5001]:
  now=received+delta;cases.append(dict(flag=0,queue=5,last=now & ((1<<64)-1),received=received,clocks=[now]*3))
for last in [(1<<63)-100,(1<<64)-100]:
 for now in [-1,0,400]:cases.append(dict(flag=0,queue=6,last=last,received=now,clocks=[now]*3))
out=ROOT/'evidence/recovery/2026-11-05/ucnet-idle';out.mkdir(parents=True,exist_ok=True)
results=[execute(c) for c in cases];(out/'fixtures.json').write_text(json.dumps(results,indent=2));(out/'native-proof.json').write_text(json.dumps(AUDIT,indent=2))
print(json.dumps({'native_cases':len(results),'single_address':hex(SINGLE),'range_verified':True}))
