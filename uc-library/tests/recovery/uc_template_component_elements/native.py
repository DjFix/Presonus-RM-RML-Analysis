"""Fail-closed ARM app oracle. Core calls are modeled provider boundaries, never executed.
Each original range is independently checked against its own source ELF section.
"""
import hashlib,json,pathlib,struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
ROOT=pathlib.Path(__file__).resolve().parents[4]
BASE=ROOT/'uc-library/tests/recovery/uc_template_component_elements'
PACKETS=ROOT/'temp/recovery-work/sqlite-issued/packet-sol61'
OBJ=0x10000000; CHILD=OBJ+0x1000; ATTR=OBJ+0x4000; VT=ATTR+0x100; GET=ATTR+0x200; SET=GET+4; TEXT=OBJ+0x10000; STACK=OBJ+0x20000; STOP=OBJ+0x30000
TKEYS=['inherit','paramlist','classname','classfallback','classdata']; CKEYS=['template','name','group']
def sha(b):return hashlib.sha256(b).hexdigest()
def w(u,a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
def word(u,a):return struct.unpack('<I',u.mem_read(a,4))[0]
def string(u,a):
 if not a:return ''
 b=bytearray()
 while True:
  x=u.mem_read(a+len(b),1)
  if x==b'\0':return b.decode('ascii')
  b+=x
class Image:
 def __init__(self,o):
  self.path=ROOT/o['elf_path'];self.raw=self.path.read_bytes();assert sha(self.raw)==o['elf']
  self.f=self.path.open('rb');self.elf=ELFFile(self.f);self.syms={s.name.split('@@')[0]:s for s in self.elf.get_section_by_name('.symtab').iter_symbols() if s['st_size'] and s['st_value']}
  self.targets={}
 def verify(self,o):
  s=self.elf.get_section(o['section']);off=s['sh_offset']+o['address']-s['sh_addr'];assert off==o['file_offset'];b=self.raw[off:off+o['size']];assert sha(b)==o['range_sha256'] and b.hex()==o['range_hex'];self.targets[o['mangled']]=o
 def bytes(self,a,n):
  for s in self.elf.iter_sections():
   if s['sh_addr']<=a<s['sh_addr']+s['sh_size']:return s.data()[a-s['sh_addr']:a-s['sh_addr']+n]
  raise ValueError(hex(a))
 def cstr(self,a):return self.bytes(a,200).split(b'\0')[0].decode()
 def data_evidence(self):
  out={}
  for cls,parent in [('TemplateElement','Element'),('ComponentElement','TemplateElement')]:
   n=f'N8Presonus2UC{len(cls)}{cls}E';p=f'N8Presonus2UC{len(parent)}{parent}E'
   ti=self.syms['_ZTI'+n];v=struct.unpack('<III',self.bytes(ti['st_value'],12));assert v[2]==self.syms['_ZTI'+p]['st_value']
   tv=self.syms['_ZTV'+n];out[cls]={'rtti_hex':self.bytes(ti['st_value'],12).hex(),'vtable_hex':self.bytes(tv['st_value'],tv['st_size']).hex()}
  load=next(o for name,o in self.targets.items() if 'TemplateElement4load' in name)
  literals=struct.unpack('<8I',self.bytes(load['address']+load['size']-32,32))
  table=literals[-1];raw=self.bytes(table,32)
  entries=[(self.cstr(struct.unpack('<I',raw[i:i+4])[0]),struct.unpack('<I',raw[i+4:i+8])[0]) for i in range(0,24,8)]
  assert entries==[('public',1),('mutable',2),('private-params',4)] and raw[24:]==bytes(8)
  out['literal_keys']=[{'address':a,'text':self.cstr(a)} for a in literals[:-1]]
  assert [x['text'] for x in out['literal_keys']]==TKEYS+['flags','']
  out['flags_table']={'address':table,'hex':raw.hex(),'sha256':sha(raw),'entries':[list(x) for x in entries]}
  return out
 def execute(self,o,attrs,phase,children=0):
  cls='ComponentElement' if 'ComponentElement' in o['mangled'] else 'TemplateElement';n=f'N8Presonus2UC{len(cls)}{cls}'
  ctor='_Z'+n+'C1ERKNS0_11MetaElementE';load='_Z'+n+'4loadERKNS0_17ElementAttributesE';save='_ZNK'+n[1:]+'4saveERNS0_17ElementAttributesE'
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);maxaddr=max(s['p_vaddr']+s['p_memsz'] for s in self.elf.iter_segments() if s['p_type']=='PT_LOAD');u.mem_map(0,(maxaddr+4095)&~4095)
  for s in self.elf.iter_segments():
   if s['p_type']=='PT_LOAD':u.mem_write(s['p_vaddr'],s.data())
  u.mem_map(OBJ,0x40000);u.mem_write(OBJ,b'\xa5'*0x1000);w(u,ATTR,VT);w(u,VT,GET);w(u,VT+4,SET)
  allowed=[]
  appnames=[ctor,load,save,'_ZN8Presonus2UC15TemplateElementC2ERKNS0_11MetaElementE','_ZN8Presonus2UC15TemplateElement4loadERKNS0_17ElementAttributesE','_ZNK8Presonus2UC15TemplateElement4saveERNS0_17ElementAttributesE','_ZN8Presonus2UC7ElementC2ERKNS0_11MetaElementE','_ZN8Presonus2UC7ElementD2Ev','_ZN8Presonus2UC7Element4loadERKNS0_17ElementAttributesE','_ZNK8Presonus2UC7Element4saveERNS0_17ElementAttributesE',o['mangled']]
  for name in appnames:
   s=self.syms[name];allowed.append((s['st_value'],s['st_value']+s['st_size']))
  providers={}
  names={'str64c':'_ZN4Core13CStringBufferILi64EEC1EPKc','str64a':'_ZN4Core13CStringBufferILi64EEaSEPKc','str128':'_ZN4Core13CStringBufferILi128EEC1EPKc','parse':'_ZN4Core8EnumInfo13parseMultipleINS_11ConstStringEEEiRKT_PKS0_','print':'_ZN4Core8EnumInfo13printMultipleINS_13CStringBufferILi128EEEEEvRT_iPKS0_','resize':'_ZN4Core6VectorIPN8Presonus2UC7ElementEE6resizeEi','vector_dtor':'_ZN4Core6VectorIPN8Presonus2UC7ElementEED1Ev','delete':'_ZdlPv'}
  for kind,name in names.items():providers[self.syms[name]['st_value']]=kind
  gets=[];stores=[];deleted=[];calls={};instructions=0;cursor=TEXT
  def table(a):
   t=[]
   while word(u,a):t.append((string(u,word(u,a)),word(u,a+4)));a+=8
   assert t==[('public',1),('mutable',2),('private-params',4)];return t
  def put(a,s,cap):u.mem_write(a,(s.encode()[:cap-1]+b'\0').ljust(cap,b'\0'))
  def hook(uc,pc,size,_):
   nonlocal cursor,instructions
   if pc in providers or pc in (GET,SET):
    kind=providers.get(pc,'get' if pc==GET else 'set');calls[kind]=calls.get(kind,0)+1;x=uc.reg_read(UC_ARM_REG_R0);y=uc.reg_read(UC_ARM_REG_R1);z=uc.reg_read(UC_ARM_REG_R2);ret=x
    if kind=='get':
     key=string(uc,y);gets.append(key);s=attrs.get(key);ret=0
     if s is not None:ret=cursor;put(cursor,s,len(s)+1);cursor+=len(s)+4
    elif kind=='set':stores.append([string(uc,y),string(uc,z)])
    elif kind in ('str64c','str64a','str128'):put(x,string(uc,y),128 if kind=='str128' else 64)
    elif kind=='parse':
     s=string(uc,word(uc,x));ret=0
     for name,v in table(y):
      i=s.find(name)
      if i>=0 and (i==0 or s[i-1]==' ') and (i+len(name)==len(s) or s[i+len(name)]==' '):ret|=v
    elif kind=='print':put(x,' '.join(name for name,v in table(z) if y&v==v),128)
    elif kind=='resize':assert y==0
    elif kind=='vector_dtor':w(uc,x+4,0);w(uc,x+8,0);w(uc,x+12,0)
    elif kind=='delete':
     assert x in (OBJ,CHILD) and x not in deleted;deleted.append(x);uc.mem_unmap(x,0x1000)
    uc.reg_write(UC_ARM_REG_R0,ret);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
   if any(a<=pc and pc+size<=b for a,b in allowed):instructions+=1;return
   raise RuntimeError(f'Unbound PC {pc:#x}')
  u.hook_add(UC_HOOK_CODE,hook)
  def run(name,obj=OBJ):
   u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,ATTR);u.reg_write(UC_ARM_REG_SP,STACK+0xf000);u.reg_write(UC_ARM_REG_LR,STOP);u.emu_start(self.syms[name]['st_value'],STOP,count=10000);assert u.reg_read(UC_ARM_REG_PC)==STOP
   return u.reg_read(UC_ARM_REG_R0)
  run(o['mangled'] if phase=='constructor' else ctor)
  if phase=='lifecycle':
   if children:
    run(ctor,CHILD);w(u,OBJ+0x50,OBJ+0x8000);w(u,OBJ+0x54,1);w(u,OBJ+0x8000,CHILD)
    childd='_Z'+n+'D0Ev';s=self.syms[childd];allowed.append((s['st_value'],s['st_value']+s['st_size']))
   run(o['mangled']);return {'parent_deleted':OBJ in deleted,'children_deleted':int(CHILD in deleted),'instructions':instructions,'provider_calls':calls}
  if phase=='reset':
   final=attrs;attrs={k:'seed' for k in ['id']+TKEYS+CKEYS};attrs['flags']='public mutable private-params';run(load);attrs=final
  if phase!='constructor':run(load)
  # Constructor defaults and native fields are observed independently of C++.
  offsets=[4,0x60,0xa0,0xe0,0x120,0x160]+([0x1a4,0x1e4,0x224] if cls=='ComponentElement' else [])
  state=[string(u,OBJ+a) for a in offsets];flags=word(u,OBJ+0x1a0)
  run(save)
  return {'gets':gets,'stores':stores,'state':state,'flags':flags,'instructions':instructions,'provider_calls':calls}
def generate():
 images={};originals=[];cases=[]
 for p in sorted(PACKETS.glob('*/CONTEXT.json')):
  d=json.loads(p.read_text())
  for entry in d['originals']:
   o=entry['original'];im=images.setdefault(o['elf'],None)
   if im is None:im=images[o['elf']]=Image(o)
   im.verify(o);originals.append(o)
 for o in originals:
  im=images[o['elf']];name=o['mangled'];cls=int('ComponentElement' in name)
  if 'D0Ev' in name or 'D1Ev' in name:
   for children in [0,1]:cases.append({'original':o['anchor'],'class':cls,'phase':'lifecycle','children':children,'attrs':{},'expected':im.execute(o,{},'lifecycle',children)})
  elif 'C1E' in name or 'C2E' in name:cases.append({'original':o['anchor'],'class':cls,'phase':'constructor','attrs':{},'expected':im.execute(o,{},'constructor')})
  else:
   inputs=[{}, {k:'' for k in ['id']+TKEYS+CKEYS+['flags']}]
   for length in [1,62,63,64,65,150]:inputs.append({k:(k[0]*length) for k in ['id']+TKEYS+CKEYS})
   for flags in ['public','mutable','private-params','public mutable private-params','unknown','xpublic public','publicx public',' public  mutable ','public\tmutable','public public','mutable private-params public']:
    inputs.append({**{k:k+'-value' for k in ['id']+TKEYS+CKEYS},'flags':flags})
   cases.append({'original':o['anchor'],'class':cls,'phase':'reset','attrs':{},'expected':im.execute(o,{},'reset')})
   for attrs in inputs:cases.append({'original':o['anchor'],'class':cls,'phase':'attributes','attrs':attrs,'expected':im.execute(o,attrs,'attributes')})
 return {'version':1,'originals':originals,'rtti':{k:v.data_evidence() for k,v in images.items()},'provider_boundaries':'CString64/128 truncation, ConstString/EnumInfo, vector allocation and deletion modeled; no historical Core instructions; delete callback genuinely unmaps allocated object page. App base constructor/load/save/destructor execute.','cases':cases}
if __name__=='__main__':
 data=generate();(BASE/'fixtures.json').write_text(json.dumps(data,indent=2)+'\n');print(len(data['cases']),'independent original ARM cases')
