"""Independent original ARM execution with bounded libc/guard models; no Core bodies."""
import hashlib, importlib.util, json, struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'uc-library/tools/recovery/accept_worker.py').exists())
ELF=ROOT/'rootfs/CS18_v13840/home/root/surface'
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
PACK=ROOT/'temp/recovery-work/rolling200-03/mapping154/prepared154/packets'
BASE=0x1000000; ARG=BASE+0x1000; OBJ=BASE+0x2000; PAGE=BASE+0x3000; PARAM=BASE+0x4000; SP=BASE+0x9000; STOP=BASE+0xf000
REG=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
def load():
 raw=ELF.read_bytes(); assert hashlib.sha256(raw).hexdigest()==SHA
 ranges=[]
 with ELF.open('rb') as f:
  e=ELFFile(f); segments=[(s['p_vaddr'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
  for i in (1,2):
   d=json.loads((PACK/f'rolling200_03_mapping154_0{i}'/'native-context.json').read_text());b=d['bodies'][d['roots'][0]];s=e.get_section(b['section_index']);off=s['sh_offset']+b['address']-s['sh_addr'];assert off==b['file_offset'];assert hashlib.sha256(raw[off:off+b['size']]).hexdigest()==b['bytes_sha256'];ranges.append({k:b[k] for k in ('address','size','section','section_index','file_offset','bytes_sha256')})
 return segments,ranges

def palette():
 p=ROOT/'uc-library/tests/recovery/reconstruction-200-01/large01_w06/oracle.py'
 spec=importlib.util.spec_from_file_location('independent_palette',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 m.RANGES=[] # Only the separately hash/range-verified initializer is requested.
 return m.observe_palette()
def string(u,a):
 out=bytearray()
 for i in range(4096):
  c=u.mem_read(a+i,1)[0]
  if c==0:return bytes(out)
  out.append(c)
 raise ValueError('unterminated')
def fixture():
 segments,ranges=load();pal=palette();u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x1000,0x300000);u.mem_map(BASE,0x10000)
 for a,b in segments:u.mem_write(a,b)
 u.mem_write(2528052,bytes.fromhex(pal['raw']))
 trace=[];writes=[];executed=set();active=[0]
 def ret(v=0):u.reg_write(REG[0],v&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def hook(uc,pc,size,user):
  if pc==STOP:uc.emu_stop();return
  b=ranges[active[0]]
  if b['address']<=pc<b['address']+b['size']:executed.add(pc);return
  a,b,n=[uc.reg_read(r) for r in REG[:3]];trace.append([pc,a,b,n])
  if pc==0xb0f8:
   x,y=string(u,a),string(u,b);ret((x>y)-(x<y))
  elif pc==0xae7c:
   pos=string(u,a).find(string(u,b));ret(0 if pos<0 else a+pos)
  elif pc==0xb260:
   pos=string(u,a).find(bytes([b&255]));ret(0 if pos<0 else a+pos)
  elif pc==0xb02c:ret(len(string(u,a)))
  elif pc==0xb170:u.mem_write(a,bytes(u.mem_read(b,n)));ret(a)
  elif pc==0xb1c4:ret(int(not (u.mem_read(a,1)[0]&1)))
  elif pc==0xab7c:u.mem_write(a,b'\1');ret()
  else:raise RuntimeError(f'unapproved instruction {pc:x}')
 def write(uc,access,a,size,value,user):
  if not SP-0x1000<=a<=SP:writes.append([a,size,value])
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
 def run(index,args):
  active[0]=index;trace.clear();writes.clear();executed.clear()
  for r,v in zip(REG,args):u.reg_write(r,v&0xffffffff)
  u.reg_write(UC_ARM_REG_SP,SP);u.reg_write(UC_ARM_REG_LR,STOP);u.emu_start(ranges[index]['address'],STOP,count=100000)
  assert u.reg_read(UC_ARM_REG_PC)==STOP
  return dict(result=u.reg_read(REG[0]),calls=list(trace),writes=list(writes),instructions=sorted(executed))
 cases=[]
 names=[x['name'] for x in pal['items']]+['','RED','Red','unknown','red ',' red','lightorangeX','off.x']
 for name in names:
  for fallback in (0,16,17,0xffffffff,0x80000000,12345):
   u.mem_write(ARG,name.encode()+b'\0');u.mem_write(OBJ,struct.pack('<I',ARG));o=run(0,[OBJ,fallback]);cases.append(dict(kind='color',input=name,fallback=fallback,**o))
 # Same machine exercises cold initialization once and warm/repeated calls.
 inputs=[None,'','page:','page:x','xpage:a.b','Page:a.b','page:a.b','page:.','page:.suffix','page:name.','page:a.b.c','.','page:..x','page:'+('a'*31)+'.x','page:'+('a'*32)+'.x','page:'+('a'*80)+'.'+('b'*80),'page:x.'+('b'*80),'page:'+('a'*30)+'.xyz','page:a.b','wrong']
 inputs += ['page:'+('a'*n)+'.'+('b'*m) for n in (0,1,29,30,31,32,33,100) for m in (0,1,30,31,32,33,100)]
 inputs += [('z'*100)+'page:a.b','page:a'+('.'*40)+'x']
 for text in inputs*2:
  u.mem_write(PAGE,b'old-page\0'+b'\xa5'*23);u.mem_write(PARAM,b'old-param\0'+b'\x5a'*22)
  if text is not None:u.mem_write(ARG,text.encode()+b'\0')
  o=run(1,[0 if text is None else ARG,PAGE,PARAM]);cases.append(dict(kind='page',input=text,page=string(u,PAGE).decode(),parameter=string(u,PARAM).decode(),page_bytes=bytes(u.mem_read(PAGE,32)).hex(),parameter_bytes=bytes(u.mem_read(PARAM,32)).hex(),**o))
 return dict(version=1,elf_sha256=SHA,ranges=ranges,palette=pal,cases=cases,limitations='libc strings and guard runtime modeled at explicit boundaries; disjoint NUL-terminated ASCII buffers <=4095 bytes; no Core firmware, hardware or ARM ABI claim')
if __name__=='__main__':
 import sys
 Path(sys.argv[1]).write_text(json.dumps(fixture(),indent=2)+'\n')
