"""Execute exact original ARM application instructions; no pseudocode oracle."""
import hashlib, json, struct, random
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC
ROOT=Path(__file__).resolve().parents[5]
ELF=ROOT/'rootfs/CS18_v13840/home/root/surface'
PACKETS=ROOT/'temp/recovery-work/reconstruction-200-01/large-batch01/packets'
HASH='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
BASE=0x1000000
OBJ=BASE+0x1000; BUF=BASE+0x2000; ARG=BASE+0x3000; OTHER=BASE+0x4000; OUT=BASE+0x5000; STACK=BASE+0x9000; STOP=BASE+0xf000
REG=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
def u32(v): return struct.pack('<I',v & 0xffffffff)
def get32(u,a):return struct.unpack('<I',u.mem_read(a,4))[0]
def metadata():
 b=ELF.read_bytes(); assert hashlib.sha256(b).hexdigest()==HASH
 result=[]
 with ELF.open('rb') as f:
  e=ELFFile(f)
  for i in range(1,11):
   d=json.loads((PACKETS/f'large01_w06_{i:02}'/'native-context.json').read_text())
   body=d['bodies'][d['roots'][0]]; section=e.get_section(body['section_index'])
   off=section['sh_offset']+body['address']-section['sh_addr']
   assert off==body['file_offset']
   assert hashlib.sha256(b[off:off+body['size']]).hexdigest()==body['bytes_sha256']
   result.append({k:body[k] for k in ('address','size','section','section_index','file_offset','bytes_sha256')})
 return result
SUPPLEMENT=ROOT/'temp/recovery-work/reconstruction-200-01/expansions02/palette-initializer01'
def provider_metadata():
 d=json.loads((SUPPLEMENT/'native-context.json').read_text());t=d['bodies'][d['roots'][0]]
 with ELF.open('rb') as f:
  e=ELFFile(f);sec=e.get_section(t['section_index']);off=sec['sh_offset']+t['address']-sec['sh_addr']
 assert off==t['file_offset']
 assert hashlib.sha256(ELF.read_bytes()[off:off+t['size']]).hexdigest()==t['bytes_sha256']
 return {k:t[k] for k in ('address','size','section','section_index','file_offset','bytes_sha256')}
RANGES=None
def machine(index):
 global RANGES
 if RANGES is None:RANGES=metadata()
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x1000,0x300000);u.mem_map(BASE,0x10000)
 with ELF.open('rb') as f:
  e=ELFFile(f)
  for s in e.iter_segments():
   if s['p_type']=='PT_LOAD':u.mem_write(s['p_vaddr'],s.data())
 target=provider_metadata() if index==0 else RANGES[index-1]; traces=[];writes=[]
 def code(uc,a,size,user):
  if a==STOP:uc.emu_stop();return
  valid=target['address']<=a<target['address']+target['size'] or 0x187000<=a<0x188000
  if 2<=index<=7:valid=valid or 0x63094<=a<0x63370
  if index in (9,10):valid=valid or 0x74b08<=a<0x74c08
  if not valid:raise RuntimeError(f'Unapproved execution {a:x}')
  if a in (0x18714c,0x187150,0x1873f0,0x187588,0x187798,0x1877e0,0x187780,0x18730c,0x74b08):traces.append(a)
 def write(uc,access,a,size,value,user):
  if not STACK-0x1000 <= a <= STACK: writes.append([a,size,value])
 u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
 u.reg_write(UC_ARM_REG_SP,STACK);u.reg_write(UC_ARM_REG_LR,STOP)
 return u,target,traces,writes

def run(index,regs,setup):
 u,t,trace,writes=machine(index)
 setup(u)
 for r,v in zip(REG,regs):u.reg_write(r,v&0xffffffff)
 u.emu_start(t['address'],STOP,count=2000000)
 assert u.reg_read(UC_ARM_REG_PC)==STOP, hex(u.reg_read(UC_ARM_REG_PC))
 return u,trace,writes

def observe_palette():
 u,t,tr,w=machine(0);u.emu_start(t['address'],STOP,count=10000);assert u.reg_read(UC_ARM_REG_PC)==STOP
 raw=bytes(u.mem_read(2528052,476));items=[]
 with ELF.open('rb') as f:
  e=ELFFile(f)
  for i in range(17):
   v=struct.unpack('<III4f',raw[i*28:(i+1)*28]);addr=v[0];name=bytes(u.mem_read(addr,100)).split(b'\0')[0]
   sec=next(sec for sec in e.iter_sections() if sec['sh_addr']<=addr<sec['sh_addr']+sec['sh_size'])
   items.append(dict(pointer=addr,enumeration=v[1],color=v[2],hsl=list(v[3:]),name=name.decode('ascii'),string_section=sec.name,string_file_offset=sec['sh_offset']+addr-sec['sh_addr'],string_sha256=hashlib.sha256(name+b'\0').hexdigest()))
 return dict(provider_range=provider_metadata(),raw=raw.hex(),items=items,writes=w,calls=tr)
def fixtures():
 palette=observe_palette()
 rng=random.Random(6106); cases=[]
 for i in range(20):
  vals=[rng.randrange(-2147483648,2147483648) for _ in range(4)]
  def setup(u):u.mem_write(OBJ+48,struct.pack('<4i',*vals));u.mem_write(OUT,b'\xa5'*16)
  u,tr,w=run(1,[OUT,OBJ],setup)
  cases.append(dict(kind='rect',index=1,values=vals,result=bytes(u.mem_read(OUT,16)).hex(),writes=w))
 for index in range(2,8):
  for count in (0,1,24,49,50,51,2147483647):
   for n in range(4):
    vals=[rng.randrange(-2147483648,2147483648) for _ in range(4)];color=[rng.randrange(256) for _ in range(4)];aux=rng.randrange(2**32)
    initial=bytes(rng.randrange(256) for _ in range(1000))
    def setup(u):
     u.mem_write(OBJ,u32(0)+u32(BUF)+u32(count));u.mem_write(OBJ+0x3f8,u32(aux));u.mem_write(BUF,initial);u.mem_write(ARG,struct.pack('<4i',*vals));u.mem_write(OTHER,bytes(color))
     if index==2:u.mem_write(STACK,u32(vals[3])+u32(OTHER))
     if index in (5,7):u.mem_write(STACK,u32(OTHER))
    regs={2:[OBJ,*vals[:3]],3:[OBJ,ARG,OTHER],4:[OBJ,ARG],5:[OBJ,*vals[:3]],6:[OBJ],7:[OBJ,*vals[:3]]}[index]
    u,tr,w=run(index,regs,setup)
    cases.append(dict(kind='command',index=index,count=count,aux=aux,values=vals,color=color,initial=initial.hex(),result=bytes(u.mem_read(BUF,1000)).hex(),result_count=get32(u,OBJ+8),result_aux=get32(u,OBJ+0x3f8),writes=w))
 for n in range(12):
  initial=bytes(rng.randrange(256) for _ in range(1000));count=(0,48,50)[n%3];aux=rng.randrange(2**32)
  u,t,tr,w=machine(2);u.mem_write(OBJ,u32(0)+u32(BUF)+u32(count));u.mem_write(OBJ+0x3f8,u32(aux));u.mem_write(BUF,initial)
  operations=[]
  for step in range(70):
   index=6 if step==58 else rng.choice([2,3,4,5,7])
   vals=[rng.randrange(-2147483648,2147483648) for _ in range(4)];color=[rng.randrange(256) for _ in range(4)]
   u.mem_write(ARG,struct.pack('<4i',*vals));u.mem_write(OTHER,bytes(color))
   if index==2:u.mem_write(STACK,u32(vals[3])+u32(OTHER))
   if index in (5,7):u.mem_write(STACK,u32(OTHER))
   regs={2:[OBJ,*vals[:3]],3:[OBJ,ARG,OTHER],4:[OBJ,ARG],5:[OBJ,*vals[:3]],6:[OBJ],7:[OBJ,*vals[:3]]}[index]
   for r,v in zip(REG,regs):u.reg_write(r,v&0xffffffff)
   u.reg_write(UC_ARM_REG_SP,STACK);u.reg_write(UC_ARM_REG_LR,STOP)
   u.emu_start(RANGES[index-1]['address'],STOP,count=2000000);assert u.reg_read(UC_ARM_REG_PC)==STOP
   operations.append(dict(index=index,values=vals,color=color))
  cases.append(dict(kind='sequence',index=2,count=count,aux=aux,initial=initial.hex(),operations=operations,result=bytes(u.mem_read(BUF,1000)).hex(),result_count=get32(u,OBJ+8),result_aux=get32(u,OBJ+0x3f8),writes=w))
 for n in range(160):
  a=[rng.choice([0.,90.,180.,270.,360.,rng.uniform(-360,720)]),rng.random(),rng.random(),rng.random()]
  b=[rng.choice([0.,90.,180.,270.,360.,rng.uniform(-360,720)]),rng.random(),rng.random(),rng.random()]
  a=list(struct.unpack('<4f',struct.pack('<4f',*a)));b=list(struct.unpack('<4f',struct.pack('<4f',*b)))
  def setup(u):u.mem_write(ARG,b'\0'*12+struct.pack('<4f',*a));u.mem_write(OTHER,b'\0'*12+struct.pack('<4f',*b))
  u,tr,w=run(8,[ARG,OTHER],setup)
  cases.append(dict(kind='diff',index=8,a=a,b=b,result=u.reg_read(UC_ARM_REG_R0),calls=tr,writes=w))
 colors=[[((item['color']>>(8*i))&255) for i in range(4)] for item in palette['items']]
 colors += [[v,v,v,255] for v in range(0,256,16)]
 colors += [[r,g,b,a] for r in (0,255) for g in (0,255) for b in (0,255) for a in (0,255)]
 colors += [[rng.randrange(256) for _ in range(4)] for n in range(96)]
 for index in (9,10):
  for color in colors:
   value=sum(v<<(8*i) for i,v in enumerate(color))
   def setup(u):u.mem_write(2528052,bytes.fromhex(palette['raw']))
   u,tr,w=run(index,[value],setup); result=u.reg_read(UC_ARM_REG_R0)
   name=bytes(u.mem_read(result,100)).split(b'\0')[0].decode('ascii') if index==10 and result else None
   assert bytes(u.mem_read(2528052,476)).hex()==palette['raw']
   cases.append(dict(kind='map',index=index,color=color,result=result,name=name,calls=tr,writes=w))
 return dict(version=1,elf_sha256=HASH,ranges=metadata(),palette=palette,cases=cases)
if __name__=='__main__':
 import sys
 dest=Path(sys.argv[1]);dest.write_text(json.dumps(fixtures(),indent=2)+'\n');print(dest)
