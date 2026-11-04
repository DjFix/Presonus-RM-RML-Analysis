"""Independent bounded ARM app oracle. Never executes Core provider instructions."""
import hashlib,json,re,struct,argparse
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
ROOT=Path(__file__).resolve().parents[5]
PACKETS=ROOT/'temp/recovery-work/reconstruction-200-01/large-batch01/packets'
BASE=0x6000000; DATA=BASE+0x1000; PROP=BASE+0x3000; STOP=BASE+0xf000
REG=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
def u32(x):return struct.pack('<I',x&0xffffffff)
def f32(x):return struct.unpack('<f',u32(x))[0]
def bits(x):return struct.unpack('<I',struct.pack('<f',x))[0]
def targets():
 out=[]
 for p in sorted(PACKETS.glob('large01_w03_*')):
  t=(p/'ELF_CONTEXT.md').read_text(); m=re.search(r'ELF `([^`]+)`; version `([^`]+)`; `([^`]+)`; original `([^`]+)`; address `(0x[0-9a-f]+)`; size (\d+); section ([^;]+); SHA256 `([^`]+)`',t)
  h,fw,role,name,addr,size,section,rh=m.groups(); path=re.search(r'Original ELF path: `([^`]+)`; file offset `(0x[0-9a-f]+)`',t)
  out.append(dict(elf_sha256=h,firmware=fw,role=role,mangled=name,address=int(addr,16),size=int(size),section=section,path=path[1],file_offset=int(path[2],16),range_sha256=rh,packet=str(p.relative_to(ROOT))))
 return out
class Oracle:
 def __init__(self,target):
  self.t=target; path=ROOT/target['path']; raw=path.read_bytes(); assert hashlib.sha256(raw).hexdigest()==target['elf_sha256']; assert hashlib.sha256(raw[target['file_offset']:target['file_offset']+target['size']]).hexdigest()==target['range_sha256']
  self.segments=[]
  with path.open('rb') as f:
   elf=ELFFile(f)
   sec=elf.get_section_by_name(target['section']); assert sec['sh_offset']+target['address']-sec['sh_addr']==target['file_offset']
   for seg in elf.iter_segments():
    if seg['p_type']=='PT_LOAD':self.segments.append((seg['p_vaddr'],seg['p_memsz'],seg.data()))
  self.uc=Uc(UC_ARCH_ARM,UC_MODE_ARM); pages=set()
  for a,n,b in self.segments:
   for page in range(a&~4095,(a+n+4095)&~4095,4096):
    if page not in pages:self.uc.mem_map(page,4096);pages.add(page)
   self.uc.mem_write(a,b)
  self.uc.mem_map(BASE,0x10000)
 def run(self,method,inp):
  uc=self.uc
  # Targets only write independent scratch. Restore every scratch byte and
  # argument/temporary register between cases; ELF inputs remain immutable.
  uc.mem_write(BASE,bytes(0x10000))
  uc.reg_write(UC_ARM_REG_CPSR,0x13)
  for reg in REG+[UC_ARM_REG_R4,UC_ARM_REG_R5,UC_ARM_REG_R6,UC_ARM_REG_R7,UC_ARM_REG_R8,UC_ARM_REG_R9,UC_ARM_REG_R10,UC_ARM_REG_R11,UC_ARM_REG_R12]:uc.reg_write(reg,0)
  uc.reg_write(UC_ARM_REG_SP,BASE+0xe000);uc.reg_write(UC_ARM_REG_LR,STOP)
  uc.reg_write(REG[0],BASE);uc.reg_write(REG[1],inp[0] if inp else 0)
  calls=[]
  def word(a,v):uc.mem_write(a,u32(v))
  def read(a):return struct.unpack('<I',uc.mem_read(a,4))[0]
  if method==1:
   index,value=inp; word(BASE+44+index*4 if 0<=index<=32 else BASE+44,value)
  elif method==2:word(BASE+44,inp[0])
  elif method==3:
   n,index,old,edge,dirty=inp;word(BASE+44,n);word(BASE+40,DATA);uc.reg_write(REG[1],index&0xffffffff);uc.mem_write(BASE+28,bytes([dirty]));
   for i in range(n): word(DATA+i*320,old);uc.mem_write(DATA+i*320+312,bytes([edge]))
  elif method==4:
   n,old,new,dirty=inp; word(BASE+44,n);word(BASE+40,DATA);word(BASE+36,old);word(PROP+8,new);uc.mem_write(BASE+28,bytes([dirty]));uc.reg_write(REG[1],PROP)
   for i in range(n):uc.mem_write(DATA+i*320+313,b'\x00')
  elif method in (6,7):
   slots=inp[:6];p=inp[6];uc.reg_write(REG[1],p)
   for i,v in enumerate(slots):word(BASE+i*4,v)
  elif method==8:uc.mem_write(BASE+281,bytes(inp))
  def hook(u,a,size,_):
   if a==STOP:u.emu_stop();return
   if method==4 and a in (0x1578e0,0x156ac4,0xbb3e0):
    r=[u.reg_read(x) for x in REG]
    if a==0x1578e0:u.reg_write(REG[0],int(f32(r[0])==f32(r[1])))
    elif a==0x156ac4:
     lo,hi=struct.unpack('<II',struct.pack('<d',float(f32(r[0]))));u.reg_write(REG[0],lo);u.reg_write(REG[1],hi)
    else:calls.append([r[1],r[2],r[3],(r[0]-DATA-16)//320])
    u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR));return
   if not self.t['address']<=a<self.t['address']+self.t['size']:raise RuntimeError(f'Unexpected execution {a:x}')
  handle=uc.hook_add(UC_HOOK_CODE,hook)
  try:uc.emu_start(self.t['address'],STOP,count=10000)
  finally:uc.hook_del(handle)
  if uc.reg_read(UC_ARM_REG_PC)!=STOP:raise RuntimeError('Did not return')
  result=uc.reg_read(REG[0])
  if method in (1,2,5,6,8):out=[result]
  elif method==7:out=[read(BASE+i*4) for i in range(6)]
  elif method==3:out=[uc.mem_read(BASE+28,1)[0]]+[read(DATA+i*320) for i in range(inp[0])]
  else:out=[read(BASE+36),uc.mem_read(BASE+28,1)[0],len(calls)]+[v for c in calls for v in c]+[uc.mem_read(DATA+i*320+313,1)[0] for i in range(inp[0])]
  return dict(method=method,input=inp,expected=out,calls=calls)
def verify_table():
 receipt_path=ROOT/'temp/recovery-work/reconstruction-200-01/expansions02/eq-table01/EVIDENCE.json'
 receipt=json.loads(receipt_path.read_text())
 for item in receipt['files']:
  raw=(ROOT/item['elf']).read_bytes(); assert hashlib.sha256(raw).hexdigest()==item['elf_sha256']
  data=raw[item['file_offset']:item['file_offset']+item['size']]
  assert data==(ROOT/item['path']).read_bytes()
  assert hashlib.sha256(data).hexdigest()==item['sha256']
  with (ROOT/item['elf']).open('rb') as f:
   section=ELFFile(f).get_section_by_name(item['section'])
   assert section['sh_offset']+item['address']-section['sh_addr']==item['file_offset']
 return {'receipt':str(receipt_path.relative_to(ROOT)),'sha256':hashlib.sha256(receipt_path.read_bytes()).hexdigest(),'files':receipt['files']}
def generate():
 table=verify_table()
 ts=targets(); os=[Oracle(t) for t in ts];cases=[]
 def add(m,x):cases.append(os[m-1].run(m,x))
 for index in [0,1,16,32,33,100]:
  for v in [0,0x80000000,0x3f800000,0xc2480000,0x7fc01234]:add(1,[index,v])
 for n in [0,1,4,8]:add(2,[n])
 for n in [0,1,4,8]:
  for i in sorted(set([-1,0,1,n//2,n-1,n,n+1])):
   for old in [0,1,2,3,6,8,9]:
    for edge in [0,1]:
     for dirty in [0,1,7]:add(3,[n,i,old,edge,dirty])
 for n in [0,1,4,8]:
  for old,new in [(bits(48000),bits(48000)),(bits(44100),bits(48000)),(0,0x80000000),(bits(96000),bits(44100)),(0x7fc00001,bits(48000))]:
   for d in [0,1,7]:add(4,[n,old,new,d])
 add(5,[])
 for slots in [[0x100+i*16 for i in range(6)],[0]*6,[0x100]*6,[0x100,0x200,0x100,0,0x300,0x400]]:
  for p in [0,0x100,0x110,0x120,0x130,0x140,0x150,0x200,0x300,0x400,0xfff]:
   add(6,slots+[p]);add(7,slots+[p])
 for b in [0,1]:add(8,[b])
 return dict(table_evidence=table,version=1,oracle='Unicorn exact ARM target instructions',unicorn_version=__import__('unicorn').__version__,targets=ts,cases=cases,boundaries={'setupProcess':['0x1578e0 __aeabi_fcmpeq host IEEE binary32 comparison','0x156ac4 __aeabi_f2d exact binary32 widening','0xbb3e0 DSP Biquad setup capture arguments only; no provider memory emulation'], 'Core':'Never executed from firmware'},limitations='Only n=0,1,4,8; getValue nonnegative indices; buffered flag 0/1; setup positive finite new sample rates or unchanged zero. Biquad native body excluded; portable real provider separately executes. Ordinary returns and ARM layout unresolved.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();result=generate();Path(a.out).write_text(json.dumps(result,indent=2)+'\n');print('Native cases:',len(result['cases']))
