"""Fail-closed original ARM app/runtime execution; Core and allocator entries
are explicit provider boundaries. No Core body is executed or reconstructed.
"""
import pathlib,json,hashlib,struct,itertools
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
ROOT=pathlib.Path(__file__).resolve().parents[4]
BASE=ROOT/'uc-library/tests/recovery/network_setup_view'
PACKETS=ROOT/'temp/recovery-work/rolling200-02/next-implementation20/prepared-network-view20/packets'
ELF=ROOT/'rootfs/CS18_v13840/home/root/surface'
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
OBJ=0x400000;PARAM=OBJ+0x1000;VT=OBJ+0x2000;STR=OBJ+0x3000;IMAGE=OBJ+0x4000;ICON=OBJ+0x5000;MODEL=OBJ+0x6000;HEAP=OBJ+0x8000;STACK=0x500000;STOP=0x600000
NAMES=[None,'','RadioToggleButton','networkList','ListModel','other','child/custom','choice','child']
def fb(x):return struct.unpack('<I',struct.pack('<f',x))[0]
def w(u,a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
def r(u,a):return struct.unpack('<I',u.mem_read(a,4))[0]
RAW=ELF.read_bytes();assert hashlib.sha256(RAW).hexdigest()==SHA
RANGES={};PROVENANCE={}
def add_context(path,key):
 j=json.loads(path.read_text());b=j['bodies'][j['roots'][0]]
 with ELF.open('rb') as f:
  e=ELFFile(f);s=e.get_section(b['section_index']);off=s['sh_offset']+b['address']-s['sh_addr']
  assert off==b['file_offset'];assert hashlib.sha256(RAW[off:off+b['size']]).hexdigest()==b['bytes_sha256']
 RANGES[key]={k:b[k] for k in ['address','size','file_offset','section_index','section','bytes_sha256']}
 PROVENANCE[key]={'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
for t in range(1,6):add_context(PACKETS/f'rolling200_02_network_view20_{t:02}'/'native-context.json',str(t))
for path in sorted((ROOT/'temp/recovery-work/rolling200-02/next-implementation20').glob('expand-*-44/native-context.json')):
 add_context(path,path.parent.name)
# Runtime expansion may contain multiple bodies: independently verify each one.
for path in sorted(list((ROOT/'temp/recovery-work/rolling200-02/next-implementation20').glob('expand-*-44/native-context.json')) + [ROOT/'temp/recovery-work/rolling200-02/next-implementation20/runtime-closure48/native-context.json']):
 j=json.loads(path.read_text())
 for node,b in j['bodies'].items():
  key=path.parent.name+':'+node
  with ELF.open('rb') as f:
   e=ELFFile(f);s=e.get_section(b['section_index']);off=s['sh_offset']+b['address']-s['sh_addr']
   assert off==b['file_offset'];assert hashlib.sha256(RAW[off:off+b['size']]).hexdigest()==b['bytes_sha256']
  RANGES[key]={k:b[k] for k in ['address','size','file_offset','section_index','section','bytes_sha256']}
  PROVENANCE[key]={'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
AUDIT={'pcs':{},'intercepts':{},'unexpected':0,'runtime_bodies_executed':[],'Core_body_instructions_executed':0}
INTERCEPTS={0xb0f8:'strcmp PLT',0xa90c:'operator new PLT',0xfb98c:'CCL RadioButton constructor',0x5d1e0:'historical PageComponent createView fallback',0x5d5ac:'historical PageComponent getObjectForView fallback',0x108bdc:'CCL ListViewModel constructor',0xa0104:'existing app setupListModel boundary',0xfb15c:'CCL Control destructor',0xad5c:'operator delete PLT',STOP+0x100:'Parameter beginEdit',STOP+0x104:'Parameter getValue',STOP+0x108:'Parameter setValue',STOP+0x10c:'Parameter endEdit'}
def execute(inp):
 t,a,b,c,d,v=inp;u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x300000)
 with ELF.open('rb') as f:
  for seg in ELFFile(f).iter_segments():
   if seg['p_type']=='PT_LOAD':u.mem_write(seg['p_vaddr'],seg.data())
 for start,size in [(OBJ,0x10000),(STACK,0x10000),(STOP,0x1000)]:u.mem_map(start,size)
 def string(index,text):
  if text is None:return 0
  p=STR+index*256;u.mem_write(p,text.encode()+b'\0');return p
 def text(p):
  out=b''
  while u.mem_read(p,1)!=b'\0':out+=u.mem_read(p,1);p+=1
  return out.decode()
 w(u,PARAM,VT)
 for offset,entry in [(0x10,STOP+0x100),(0x44,STOP+0x104),(0x58,STOP+0x108),(0x14,STOP+0x10c)]:w(u,VT+offset,entry)
 allocations=[];events=[];setups=[];deletes=[];cleanup=[];fallback=[]
 if t==3:
  w(u,OBJ+0x48,PARAM if a else 0);u.mem_write(OBJ+0xe1,bytes([d]));w(u,OBJ+0xe4,b);w(u,OBJ+0xe8,c)
 if t in [4,5]:
  w(u,OBJ+0x48,PARAM if c else 0);w(u,OBJ+0x58,IMAGE if a else 0);w(u,OBJ+0x5c,(IMAGE if a==2 else ICON) if b else 0)
  w(u,IMAGE+0x34,int(bool(a))+int(bool(b) and a==2));w(u,ICON+0x34,int(bool(b) and a!=2))
 if t==2:w(u,OBJ+0x104,MODEL if c else 0)
 allowed=[RANGES[str(t)]]+([b for k,b in RANGES.items() if k.startswith(('expand-','runtime-closure48'))] if t==3 else [])
 def hook(uc,pc,size,_):
  if pc in INTERCEPTS:
   AUDIT['intercepts'][hex(pc)]=AUDIT['intercepts'].get(hex(pc),0)+1
  elif any(body['address']<=pc and pc+size<=body['address']+body['size'] for body in allowed):
   AUDIT['pcs'][hex(pc)]=AUDIT['pcs'].get(hex(pc),0)+1;return
  else:
   AUDIT['unexpected']+=1;raise RuntimeError(f'unbound PC {pc:#x} target {t}; exact expansion required')
  x=uc.reg_read(UC_ARM_REG_R0);y=uc.reg_read(UC_ARM_REG_R1);z=uc.reg_read(UC_ARM_REG_R2)
  if pc==0xb0f8:
   xtext,ytext=text(x),text(y);uc.reg_write(UC_ARM_REG_R0,0 if xtext==ytext else 1)
  elif pc==0xa90c:
   allocations.append(x);uc.reg_write(UC_ARM_REG_R0,HEAP)
  elif pc==0xfb98c:
   assert x==HEAP and z==0 and uc.reg_read(UC_ARM_REG_R3)==0
   assert bytes(uc.mem_read(y,16))==bytes(16)
  elif pc in [0x5d1e0,0x5d5ac]:
   assert x==OBJ+0x84;fallback.append([pc,y,z]);uc.reg_write(UC_ARM_REG_R0,0)
  elif pc==0x108bdc:assert x==HEAP
  elif pc==0xa0104:
   assert x==OBJ and r(u,OBJ+0x104)==HEAP and r(u,HEAP+0x38)==OBJ and r(u,HEAP+0x34)==0
   setups.append(1)
  elif pc==STOP+0x100:assert x==PARAM;events.append([1,0,0])
  elif pc==STOP+0x104:assert x==PARAM;events.append([2,0,0]);uc.reg_write(UC_ARM_REG_R0,v)
  elif pc==STOP+0x108:assert x==PARAM;events.append([3,y,z])
  elif pc==STOP+0x10c:assert x==PARAM;events.append([4,0,0])
  elif pc==0xfb15c:
   assert x==OBJ and r(u,OBJ+0x58)==0 and r(u,OBJ+0x5c)==0
   cleanup.append(1)
  elif pc==0xad5c:assert x==OBJ;deletes.append(1)
  uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,hook);u.reg_write(UC_ARM_REG_SP,STACK+0xf000);u.reg_write(UC_ARM_REG_LR,STOP);u.reg_write(UC_ARM_REG_R0,OBJ)
 if t==1:u.reg_write(UC_ARM_REG_R1,string(0,NAMES[a]))
 if t==2:u.reg_write(UC_ARM_REG_R1,string(0,NAMES[a]));u.reg_write(UC_ARM_REG_R2,string(1,[None,'','ListModel','Other'][b]))
 u.emu_start(RANGES[str(t)]['address'],STOP,count=10000);assert u.reg_read(UC_ARM_REG_PC)==STOP
 if t==3:return [u.mem_read(OBJ+0xe1,1)[0],len(events)]+[x for event in events for x in event]
 if t in [4,5]:
  assert len(cleanup)==1;return [r(u,IMAGE+0x34),r(u,(IMAGE if a==2 else ICON)+0x34),int(bool(c)),len(deletes)]
 result=u.reg_read(UC_ARM_REG_R0)
 if t==1:
  if allocations:assert allocations==[240] and r(u,HEAP+0xe8)==0
  return [int(result==HEAP),len(allocations),0]
 if allocations:assert allocations==[60]
 return [int(result in [MODEL,HEAP]),len(allocations),len(setups)]
def generate():
 cases=[]
 for n in range(len(NAMES)):
  inp=[1,n,0,0,0,0];cases.append({'input':inp,'expected':execute(inp)})
 for a,b,c in itertools.product(range(len(NAMES)),range(4),range(2)):
  inp=[2,a,b,c,0,0];cases.append({'input':inp,'expected':execute(inp)})
 values=[0,0x80000000,fb(1),fb(-1),fb(1.25),fb(-1.25),fb(16777216),fb(-2147483648),0x7f800000,0xff800000,0x7fc00000,0x7f800001,1,0x80000001]
 integers=[-2147483648,-16777217,-1,0,1,16777217,2147483647]
 for a,b,c,d,v in itertools.product([0,1],integers,[-1,0,2147483647],[0,1],values):
  inp=[3,a,b,c,d,v];cases.append({'input':inp,'expected':execute(inp)})
 for t,a,b,c in itertools.product([4,5],[0,1,2],[0,1],[0,1]):
  inp=[t,a,b,c,0,0];cases.append({'input':inp,'expected':execute(inp)})
 AUDIT['runtime_bodies_executed']=[k for k,b in RANGES.items() if k.startswith(('expand-','runtime-closure48')) and any(b['address']<=int(pc,16)<b['address']+b['size'] for pc in AUDIT['pcs'])]
 return {'version':1,'elf':str(ELF.relative_to(ROOT)),'elf_sha256':SHA,'ranges':RANGES,'range_provenance':PROVENANCE,'boundary_entries':{hex(k):v for k,v in INTERCEPTS.items()},'audit':AUDIT,'cases':cases}
if __name__=='__main__':
 data=generate();(BASE/'fixtures.json').write_text(json.dumps(data,indent=2)+'\n');print(len(data['cases']),'independent original instruction cases')
