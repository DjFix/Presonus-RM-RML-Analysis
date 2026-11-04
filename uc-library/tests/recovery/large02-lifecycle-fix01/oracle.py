"""Exact app ARM instructions, explicitly bounded source-provider boundaries.
No Core firmware bodies are recovered or executed. Core cleanup adapters model
provider operations and are compared separately to real pinned C++ providers.
"""
import argparse, hashlib, importlib.util, json, random, struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UcError, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'uc-library/tools/recovery/accept_worker.py').is_file())
ELF=ROOT/'rootfs/CS18_v13840/home/root/surface'
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
PACKETS=ROOT/'temp/recovery-work/large02-lifecycle-fix01/batch03/packets'
EXTRA=ROOT/'temp/recovery-work/large02-lifecycle-fix01/expansions01'
OLD=ROOT/'uc-library/tests/recovery/reconstruction-200-01/large01_w06/oracle.py'
SPEC=importlib.util.spec_from_file_location('palette_original_oracle',OLD); OLD_ORACLE=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(OLD_ORACLE)
REG=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
BASE=0x1000000; OBJ=BASE+0x1000; COLOR=BASE+0x2000; EQ=BASE+0x3000; GEQ=BASE+0x4000; ARG=BASE+0x5000; SP=BASE+0x9000; STOP=BASE+0xf000
RAW=ELF.read_bytes();assert hashlib.sha256(RAW).hexdigest()==SHA
with ELF.open('rb') as f:
 E=ELFFile(f)
 SECTIONS=[dict(address=s['sh_addr'],size=s['sh_size'],offset=s['sh_offset'],name=s.name,nobits=s['sh_type']=='SHT_NOBITS') for s in E.iter_sections()]
 SEGMENTS=[(s['p_vaddr'],s.data()) for s in E.iter_segments() if s['p_type']=='PT_LOAD']
 SYMBOLS={s.name:s['st_value'] for s in E.get_section_by_name('.symtab').iter_symbols()}
RANGES=[];BINDINGS=[]
def bind(path):
 path=Path(path);BINDINGS.append(dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
 d=json.loads(path.read_text())
 for key in d['roots']:
  b=d['bodies'][key];sec=SECTIONS[b['section_index']];off=sec['offset']+b['address']-sec['address']
  assert off==b['file_offset'];assert hashlib.sha256(RAW[off:off+b['size']]).hexdigest()==b['bytes_sha256']
  RANGES.append({k:b[k] for k in ['address','size','section','section_index','file_offset','bytes_sha256']})
for d in sorted(PACKETS.iterdir()):bind(d/'native-context.json')
for name in ['eq-remove','geq-remove','digital-detach','map-color-value-wrapper','map-color-name-wrapper']:
 bind(EXTRA/name/'native-context.json')
# Reuse independent original palette work with current exact ELF/range checks.
PALETTE=OLD_ORACLE.observe_palette()
RANGES.extend(OLD_ORACLE.metadata()[7:]);RANGES.append(PALETTE['provider_range'])
TIMER=EXTRA/'delay-d1/native-context.json'
if TIMER.exists():bind(TIMER)

def u32(v):return struct.pack('<I',v&0xffffffff)
def r32(u,a):return struct.unpack('<I',u.mem_read(a,4))[0]
def cstring(u,a):
 if not a:return b''
 out=bytearray()
 for i in range(4096):
  b=u.mem_read(a+i,1)[0]
  if not b:return bytes(out)
  out.append(b)
 raise RuntimeError('unterminated oracle input')
def data(a,n):
 sec=next(s for s in SECTIONS if s['address']<=a and a+n<=s['address']+s['size'] and not s['nobits'])
 off=sec['offset']+a-sec['address'];raw=RAW[off:off+n]
 return dict(address=a,size=n,section=sec['name'],file_offset=off,sha256=hashlib.sha256(raw).hexdigest(),hex=raw.hex())
TABLE=data(1703284,68)
STRINGS=[]
for pointer in struct.unpack('<17I',bytes.fromhex(TABLE['hex'])):
 sec=next(s for s in SECTIONS if s['address']<=pointer<s['address']+s['size']);off=sec['offset']+pointer-sec['address'];n=RAW.index(0,off)-off+1;record=data(pointer,n);record['string']=RAW[off:off+n-1].decode();STRINGS.append(record)

def machine():
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x1000,0x300000);u.mem_map(BASE,0x10000)
 for a,b in SEGMENTS:u.mem_write(a,b)
 u.mem_write(2528052,bytes.fromhex(PALETTE['raw']))
 u.reg_write(UC_ARM_REG_SP,SP);u.reg_write(UC_ARM_REG_LR,STOP)
 return u

def execute(address,argv,setup=None):
 u=machine();calls=[];writes=[];deallocated=[];source_frees=[];hooks={};allocations={};vectors={};parameters={};observers={};removed=[];before_free={};cleanup=[]
 def w(a,v):u.mem_write(a,u32(v))
 def ret(value=0):u.reg_write(REG[0],value&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def allocate(a,label):allocations[a]=label
 def release(a,origin):
  if not a:return
  assert a in allocations, ('unknown/double free',hex(a),origin)
  label=allocations.pop(a)
  before_free[str(label)]=bytes(u.mem_read(a,0x144 if label==1 else 16)).hex()
  if label==1:assert r32(u,a+0xe4)==r32(u,a+0xe8)==0
  if label==0:assert r32(u,a)==0x1a00b0
  u.mem_unmap(a,0x1000)
  try:u.mem_read(a,1)
  except UcError:pass
  else:raise AssertionError('freed native allocation remains mapped')
  deallocated.append(label);cleanup.append(label);source_frees.append([label,origin])
 def delete():
  p=u.reg_read(REG[0]);calls.append(['operator_delete',p]);release(p,'executed_app_delete_call');ret()
 hooks[0xad5c]=delete
 def strcmp():
  a,b=[cstring(u,u.reg_read(x)) for x in REG[:2]];ret((a>b)-(a<b))
 hooks[0xb0f8]=strcmp
 def string64():
  dest=u.reg_read(REG[0]);src=u.reg_read(REG[1]);u.mem_write(dest,cstring(u,src)[:63]+b'\0');ret(dest)
 hooks[0x3ae34]=string64
 def remove_param():
  p,o=[u.reg_read(x) for x in REG[:2]];removed.append([p,o]);cleanup.append(10);items=observers[p]
  if o in items:items.remove(o)
  ret()
 hooks[0x11e2e0]=remove_param
 def vector_cleanup():
  p=u.reg_read(REG[0]);calls.append(['source_Core_Vector_cleanup',p]);storage=vectors[p]
  if storage:release(storage,'pinned_source_Vector_delete_array_boundary')
  ret()
 for a in [0x5cad4,0x8c01c]:hooks[a]=vector_cleanup
 def param_cleanup():
  p=u.reg_read(REG[0]);calls.append(['source_Core_ParamList_cleanup',p])
  for item in parameters[p]:release(item,'pinned_source_ParamList_delete_parameter_boundary')
  if vectors[p]:release(vectors[p],'pinned_source_ParamList_member_Vector_delete_array_boundary')
  ret()
 hooks[0x11f77c]=param_cleanup
 def code(uc,a,size,user):
  if a==STOP:uc.emu_stop();return
  if a in hooks:hooks[a]();return
  # Runtime compiler floating support is not Core; existing provider oracle
  # already uses this exact original compiler-support closure.
  allowed=any(b['address']<=a<b['address']+b['size'] for b in RANGES) or 0x187000<=a<0x188000
  if not allowed:raise RuntimeError(f'unbound execution {a:x}')
  if a in [0x8d7e4,0x8da24,0x82474,0x8be8c,0x8be1c,0x8be38,0x8beb8,0x11fe8]:calls.append(['app',a])
  if a in {0x8d7e4:7,0x8da24:8,0x82474:9,0x11fe8:6}:cleanup.append({0x8d7e4:7,0x8da24:8,0x82474:9,0x11fe8:6}[a])
 def write(uc,access,a,size,value,user):
  if not SP-0x1000<=a<SP:writes.append([a,size,value])
 u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
 if setup:setup(u,w,allocate,vectors,parameters,observers)
 for r,v in zip(REG,argv):u.reg_write(r,v&0xffffffff)
 u.emu_start(address,STOP,count=2000000);assert u.reg_read(UC_ARM_REG_PC)==STOP
 return dict(u=u,result=u.reg_read(REG[0]),calls=calls,writes=writes,freed=deallocated,source_free_boundaries=source_frees,removed=removed,allocator_snapshots=before_free,cleanup=cleanup)

def lifecycle(variant,mask):
 address=[0x827d0,0x82914,0x82a50][variant]
 def setup(u,w,allocate,vectors,parameters,observers):
  allocate(OBJ,1)
  w(OBJ+0x28,EQ if mask&1 else 0);w(OBJ+0x2c,GEQ if mask&2 else 0)
  for page,offset,observer,flag in [(EQ,0xc8,OBJ+0x10,1),(GEQ,0xd0,OBJ+0x14,2)]:
   store=page+0x300;w(page+offset,store);w(page+offset+4,3 if mask&flag else 0)
   for i,p in enumerate([0x12340000,observer,0x12340004]):w(store+i*4,p)
  if mask&4:w(OBJ+0x24,COLOR);w(COLOR,0x1a0048);allocate(COLOR,0)
  first=ARG+0x100;second=first if mask&16 else ARG+0x200
  w(OBJ+0xe4,first if mask&8 else 0);w(OBJ+0xe8,second if mask&8 else 0)
  observers[first]=[OBJ+0x18] if mask&8 else []
  observers[second]=[OBJ+0x18] if mask&8 else []
  for offset,label in [(0x130,2),(0x11c,3),(0xcc,4)]:
   storage=0x1100000+label*0x1000 if mask&32 else 0
   vectors[OBJ+offset]=storage
   if storage:u.mem_map(storage,0x1000);allocate(storage,label)
  parameters[OBJ+0x78]=[];vectors[OBJ+0x78]=0
  if mask&32:
   item=0x1105000;u.mem_map(item,0x1000);allocate(item,5);parameters[OBJ+0x78].append(item)
   storage=0x110b000;u.mem_map(storage,0x1000);allocate(storage,11);vectors[OBJ+0x78]=storage
 o=execute(address,[OBJ],setup)
 # Observe actual native helper writes before object deallocation; EQ/GEQ
 # objects are outside the allocation whose lifetime the destructor ends.
 u=o.pop('u');o['expected']=dict(eq=r32(u,EQ+0xcc),geq=r32(u,GEQ+0xd4),removed=len(o['removed']),freed=o['freed'],cleanup=o['cleanup'])
 o['remaining_observer_data']=[bytes(u.mem_read(EQ+0x300,12)).hex(),bytes(u.mem_read(GEQ+0x300,12)).hex()]
 if variant:o['receiver_after']=bytes(u.mem_read(OBJ,0x144)).hex();assert r32(u,OBJ+0xe4)==r32(u,OBJ+0xe8)==0
 return dict(argv=['life',str(variant),str(mask)],**o)

def fixtures():
 cases=[]
 for variant in range(3):
  for mask in range(64):cases.append(lifecycle(variant,mask))
 for variant,address in enumerate([0x8be8c,0x8be38,0x8be1c,0x8beb8]):
  def setup(u,w,allocate,*rest):w(COLOR,0x1a0048);allocate(COLOR,0)
  o=execute(address,[COLOR],setup);u=o.pop('u');o['expected']=len(o['freed'])
  if variant in [1,2]:o['vptr_after']=r32(u,COLOR);assert o['vptr_after']==0x1a00b0
  cases.append(dict(argv=['colorlife',str(variant)],**o))
 names=[s['string'] for s in STRINGS]+['off','','<NULL>','RED','Red','unknown','red ','x'*64,'x'*256,'blueishwhite\u00e9']
 for name in names:
  def setup(u,w,*rest):u.mem_write(ARG,name.encode()+b'\0')
  o=execute(0x74c18,[0 if name=='<NULL>' else ARG],setup);o.pop('u');o['expected']=o['result'];cases.append(dict(argv=['name',name],**o))
 for index in [-2147483648,-2,-1,*range(17),17,18,2147483647]:
  o=execute(0x8c120,[COLOR,index]);o.pop('u');o['expected']=o['result'];cases.append(dict(argv=['index',str(index)],**o))
 rng=random.Random(17723)
 colors=[item['color'] for item in PALETTE['items']]+[rng.randrange(2**32) for _ in range(64)]+[0,0xffffff,0xffffffff,0xff000000]
 for color in colors:
  def setup(u,w,*rest):w(ARG,color)
  o=execute(0x8c0a8,[COLOR,ARG],setup);o.pop('u');o['expected']=o['result'];cases.append(dict(argv=['rgb',str(color)],**o))
 return dict(version=1,elf_sha256=SHA,ranges=RANGES,bound_context=BINDINGS,converter_table=TABLE,converter_strings=STRINGS,palette_observation=PALETTE,cases=cases,unicorn_version=__import__('unicorn').__version__,provider_boundary='Core source adapters, libc strings and allocator hooks explicit; original app helpers executed; no Core binary behavior claim')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();out=fixtures();Path(a.out).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(cases=len(out['cases']),out=a.out)))
