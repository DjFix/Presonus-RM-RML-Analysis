"""Execute exact original app ARM ranges; explicit strcmp/CCL add boundaries."""
import hashlib,json,pathlib,struct,sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[4]
BASE=pathlib.Path('uc-library/tests/recovery/safe_mute_filter')
PACKETS=pathlib.Path('temp/recovery-work/rolling200-02/next-implementation103/prepared-safe-mute103/packets')
ELF='rootfs/RML16AI_Rack_13731/home/root/mixer'
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
OBJ=0x1000000;VEC=OBJ+0x100;ITEMS=OBJ+0x200;PAR=OBJ+0x1000;STACK=0x1100000;SP=STACK+0x8000;STOP=0x1200000
NAMES=['mute','','Mute','muteX','xmute','volume','mute ','']
TYPES=[1131375984,1348563553,0,0xffffffff]
LISTS=[[],[1],[2,1,3],[2,3,1],[2,3],[0,1,1,0]]
def verified():
 raw=(ROOT/ELF).read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 bodies=[];segments=[]
 with (ROOT/ELF).open('rb') as f:
  elf=ELFFile(f)
  for segment in elf.iter_segments():
   if segment['p_type']=='PT_LOAD':
    a=int(segment['p_vaddr']);data=segment.data()
    # Only app bodies, their original literal strings and explicit call boundaries.
    # Keep exact segment-derived bytes; unmapped reads fail rather than expanding scope.
    for page in [0x76000,0xa000,0x4c000,0x35b000,0x339000]:
     if a<=page<page+4096<=a+len(data):segments.append((page,4096,data[page-a:page-a+4096]))
  for n in ['01','02']:
   j=json.loads((ROOT/PACKETS/f'rolling200_02_safe_mute103_{n}/native-context.json').read_text());b=j['bodies'][j['roots'][0]]
   sec=elf.get_section(b['section_index']);offset=sec['sh_offset']+b['address']-sec['sh_addr'];assert sec.name==b['section'] and offset==b['file_offset']
   assert hashlib.sha256(raw[offset:offset+b['size']]).hexdigest()==b['bytes_sha256']
   bodies.append({k:b[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']})
 return bodies,segments

def execute(bodies,segments,mode,typ,name,obj,initial,value):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);pages=set()
 for a,n,data in segments:
  for page in range(a&~4095,(a+n+4095)&~4095,4096):
   if page not in pages:u.mem_map(page,4096);pages.add(page)
  u.mem_write(a,data)
 for a,n in [(OBJ,0x10000),(STACK,0x10000),(STOP,4096)]:u.mem_map(a,n)
 def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def ptr(i):return PAR+0x100*i if i else 0
 def dec(p):return (p-PAR)//0x100 if p else 0
 def string(a):
  b=bytearray()
  while u.mem_read(a,1)!=b'\0':b+=u.mem_read(a,1);a+=1
  return bytes(b)
 w(OBJ+4,VEC);w(VEC+4,ITEMS);w(VEC+8,len(initial))
 for i,p in enumerate(initial):w(ITEMS+4*i,ptr(p))
 w(ptr(1)+12,0xfffffff8 if name==7 else OBJ+0x400)
 u.mem_write(OBJ+0x408,NAMES[name].encode()+b'\0')
 # Parameter value deliberately differs but is never read by either body.
 w(ptr(1)+0x24,value)
 trace=[];writes=[];body=bodies[mode]
 def hook(uc,a,size,user):
  if a==0xaf70:
   l=string(uc.reg_read(UC_ARM_REG_R0));rr=string(uc.reg_read(UC_ARM_REG_R1));trace.append(['strcmp',l.decode(),rr.decode()]);uc.reg_write(UC_ARM_REG_R0,0 if l==rr else 1);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
  if a==0x4c1bc:
   assert mode==0 and uc.reg_read(UC_ARM_REG_R0)==VEC+4
   p=r(uc.reg_read(UC_ARM_REG_R1));trace.append(['add',dec(p)]);n=r(VEC+8);w(ITEMS+4*n,p);w(VEC+8,n+1);uc.reg_write(UC_ARM_REG_R0,1);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
  assert body['address']<=a<a+size<=body['address']+body['size'],hex(a)
 def write(uc,access,a,size,v,user):
  assert STACK<=a<a+size<=SP,(hex(a),size)
  writes.append([a-SP,size,v])
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
 for reg,v in [(UC_ARM_REG_SP,SP),(UC_ARM_REG_LR,STOP),(UC_ARM_REG_R0,OBJ),(UC_ARM_REG_R1,TYPES[typ]),(UC_ARM_REG_R2,0xdeadbeef),(UC_ARM_REG_R3,ptr(obj))]:u.reg_write(reg,v)
 u.emu_start(body['address'],STOP,count=2000);assert u.reg_read(UC_ARM_REG_PC)==STOP
 return dict(input=[mode,typ,name,obj,value,len(initial)]+initial,result=u.reg_read(UC_ARM_REG_R0),final=[dec(r(ITEMS+4*i)) for i in range(r(VEC+8))],trace=trace,stack_writes=writes)
def generate():
 bodies,segments=verified();cases=[]
 for mode in range(2):
  for typ in range(4):
   for name in range(len(NAMES)):
    for obj in [0,1]:
     for initial in LISTS:
      for value in [0,0x3f800000]:cases.append(execute(bodies,segments,mode,typ,name,obj,initial,value))
 return dict(elf=ELF,elf_sha256=SHA,ranges=bodies,cases=cases,boundaries='Only exact app bodies executed. strcmp modeled from bytes. CCL add modeled as successful append; no Core firmware execution. Strict PC and app-write guards. Parameter names/valid allocated storage stable; allocation failure excluded.')
if __name__=='__main__':
 j=generate();p=ROOT/BASE/'fixtures.json'
 if '--generate' in sys.argv:p.write_text(json.dumps(j,indent=2)+'\n')
 else:assert j==json.loads(p.read_text())
 print(len(j['cases']),'exact ARM predicate observations')
