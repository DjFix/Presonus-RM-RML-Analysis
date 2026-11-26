"""Independent exact native executions. ObservationMachine is the bounded
application/ELF observation harness derived from the accepted Text18 producer.
Core and display callbacks are explicit observation boundaries, not emulated
Core implementations; actual providers execute in the independent Linux replay.
"""
# Observation harness donor SHA-256: f6d4d7b6285bd512814292f1094c6d83cb248647e67b9e701395acb207574986
import hashlib,io,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0 as R0,UC_ARM_REG_R1 as R1,UC_ARM_REG_R2 as R2,UC_ARM_REG_R3 as R3,UC_ARM_REG_PC as PC,UC_ARM_REG_LR as LR,UC_ARM_REG_SP as SP
PACKET=None  # Historical producer packet is not a runtime dependency.
OBJ=0x51001000; INFO=0x51004000; BUF=0x51005000; PARAM=0x51006000; DISPLAY=0x51007000; VTABLE=0x51008000; STOP=0x5200ff00
F='_ZN8Presonus5Panel12FieldElement';T='_ZN8Presonus5Panel16TextEntryElement'
def digest(b):return hashlib.sha256(b).hexdigest()
CACHE={}
class ObservationMachine:
 def __init__(self,o):
  self.original=o
  if o['elf'] not in CACHE:
   raw=Path(o['elf_path']).read_bytes();assert digest(raw)==o['elf'];e=ELFFile(io.BytesIO(raw));syms={s.name:s for s in e.get_section_by_name('.symtab').iter_symbols()};CACHE[o['elf']]=(raw,e,syms)
  raw,e,self.syms=CACHE[o['elf']];s=self.syms[o['mangled']];sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];assert (s['st_value'],s['st_size'],s['st_shndx'],off)==(o['address'],o['size'],o['section'],o['file_offset']);assert raw[off:off+o['size']].hex()==o['range_hex'];assert digest(raw[off:off+o['size']])==o['range_sha256']
  self.u=Uc(UC_ARCH_ARM,UC_MODE_ARM);segments=[s for s in e.iter_segments() if s['p_type']=='PT_LOAD'];lo=min(s['p_vaddr'] for s in segments)&~4095;hi=(max(s['p_vaddr']+s['p_memsz'] for s in segments)+4095)&~4095;self.u.mem_map(lo,hi-lo)
  for s in segments:self.u.mem_write(s['p_vaddr'],s.data())
  self.u.mem_map(0x51000000,0x20000);self.u.mem_map(0x52000000,0x10000);self.events=[];self.freed=[];self.provider=[];self.value='';self.enabled=True;self.lookup=0;self.pos=(0,0)
  rel=e.get_section_by_name('.rel.plt');dyn=e.get_section(rel['sh_link']);plt=e.get_section_by_name('.plt');self.imports={plt['sh_addr']+20+i*12:dyn.get_symbol(r['r_info_sym']).name for i,r in enumerate(rel.iter_relocations())}
  self.core={s['st_value']:s.name for s in self.syms.values() if s.name.startswith('_ZN4Core') or s.name.startswith('_ZNK4Core')}
  self.u.hook_add(UC_HOOK_CODE,self.hook)
  record=bytearray(96);struct.pack_into('<iii',record,4,10,20,7);record[20:26]=b'level\0';self.u.mem_write(INFO,bytes(record));self.word(DISPLAY,VTABLE)
  for i in range(23):self.word(VTABLE+4*i,0x52001000+4*i)
  self.word(PARAM,VTABLE+0x100);self.word(VTABLE+0x120,0x52002000);self.word(VTABLE+0x170,0x52002004)
  # Actual original singleton/delegate routing is executed; only external
  # lookup delegate and pinned-Core observer boundaries are replaced.
  for n,s in self.syms.items():
   if 'LCDManager' in n and 'theInstance' in n and s['st_info']['type']=='STT_OBJECT':self.word(s['st_value'],0x51009000)
  self.word(0x51009004,0x51009100);self.word(0x51009100,0x51009200);self.word(0x51009200,0x52002008)
 def addr(self,n):return self.syms[n]['st_value']
 def word(self,a,v=None):
  if v is not None:self.u.mem_write(a,struct.pack('<I',v&0xffffffff))
  return struct.unpack('<I',self.u.mem_read(a,4))[0]
 def string(self,a):return bytes(self.u.mem_read(a,512)).split(b'\0',1)[0].decode('latin1') if a else ''
 def put(self,a,s):self.u.mem_write(a,s.encode('latin1')+b'\0')
 def hook(self,u,a,size,data):
  x,y,z,w=[u.reg_read(r) for r in (R0,R1,R2,R3)];n=self.imports.get(a);core=self.core.get(a)
  if a==0x52002000:self.provider.append(['enabled',self.enabled]);u.reg_write(R0,int(self.enabled))
  elif a==0x52002004:self.provider.append(['format',z]);self.put(y,self.value[:max(0,z-1)] if z else '')
  elif a==0x52002008:self.provider.append(['lookup',self.string(y)]);u.reg_write(R0,self.lookup)
  elif 0x52001000<=a<0x52001000+23*4:
   slot=(a-0x52001000)//4
   if slot==20:self.pos=(y,z);self.events.append(f'move {y} {z}')
   elif slot==15:
    text=self.string(y);self.events.append(f'text {text} {z} {int(w!=0)}')
    if w:u.mem_write(w,struct.pack('<iiii',*self.pos,len(text)*6,8 if text else 0))
   elif slot==19:self.events.append(f'color {y}');u.reg_write(R0,0)
   elif slot in (9,10,11):self.events.append(('fill' if slot==9 else 'erase' if slot==10 else 'invert')+' '+' '.join(map(str,struct.unpack('<iiii',u.mem_read(y,16)))))
   elif slot==17:self.events.append('pixel '+self.string(y));u.reg_write(R0,len(self.string(y))*6)
   elif slot==4:self.events.append('height');u.reg_write(R0,9)
   else:raise AssertionError(('unexpected display slot',slot))
  elif core:
   if 'CStringBufferILi128EEC' in core:self.put(x,self.string(y))
   elif 'CStringBufferILi128EE9subString' in core:
    text=self.string(x);start=z if z<0x80000000 else z-0x100000000;count=w if w<0x80000000 else w-0x100000000;self.put(y,text[start:] if count<0 else text[start:start+count])
   elif 'removeObserver' in core:self.provider.append(['remove',x==PARAM,y==OBJ+0x97c])
   elif 'addObserver' in core:self.provider.append(['add',x==PARAM,y==OBJ+0x97c])
   elif 'StringParam14getDefaultText' in core:self.put(BUF+256,'fallback');u.reg_write(R0,BUF+256)
   else:raise AssertionError(('unexpected Core boundary',core,hex(a)))
  elif n=='strlen':u.reg_write(R0,len(self.string(x)))
  elif n in ('memcpy','memmove'):u.mem_write(x,bytes(u.mem_read(y,z)))
  elif n=='memset':u.mem_write(x,bytes([y&255])*z)
  elif n=='strcpy':self.put(x,self.string(y))
  elif n=='strcmp':u.reg_write(R0,0 if self.string(x)==self.string(y) else 1)
  elif n=='strncpy':u.mem_write(x,self.string(y).encode('latin1')[:z].ljust(z,b'\0'))
  elif n=='strncat':self.put(x,self.string(x)+self.string(y)[:z])
  elif n=='__dynamic_cast':u.reg_write(R0,x if x==PARAM else 0)
  elif n in ('free','_ZdlPv','_ZdaPv'):self.freed.append([n,x])
  elif n:raise AssertionError(('unexpected import',n,hex(a)))
  else:return
  u.reg_write(PC,u.reg_read(LR))
 def call(self,n,x=OBJ,y=0,z=0,w=0):
  u=self.u
  for r,v in zip((R0,R1,R2,R3),(x,y,z,w)):u.reg_write(r,v&0xffffffff)
  u.reg_write(SP,STOP-256);u.reg_write(LR,STOP);u.emu_start(self.addr(n),STOP,count=100000);assert u.reg_read(PC)==STOP,(n,hex(u.reg_read(PC)));return u.reg_read(R0)
 def setup(self,text='',cursor=0,remainder=0,param=False,enabled=True):
  self.call((F if self.original['mangled'].startswith(F) else T)+'C1ERKNS0_11ElementInfoE',OBJ,INFO);self.put(OBJ+0xa1c,text);self.word(OBJ+0xa14,cursor);self.word(OBJ+0xa18,remainder);self.word(OBJ+0x980,PARAM if param else 0);self.lookup=PARAM if param else 0;self.value=text;self.enabled=enabled
 def snapshot(self):
  rem=self.word(OBJ+0xa18);return dict(text=self.value if self.word(OBJ+0x980) else self.string(OBJ+0xa1c),cursor=self.word(OBJ+0xa14),remainder=rem if rem<0x80000000 else rem-0x100000000,dirty=self.word(OBJ+0x74),events=self.events)

from types import SimpleNamespace
base=SimpleNamespace(Machine=ObservationMachine,OBJ=OBJ,INFO=INFO,DISPLAY=DISPLAY,PARAM=PARAM,BUF=BUF,R0=R0,R1=R1,R2=R2,R3=R3,PC=PC,LR=LR)
ROOT=Path('/home/rs/projects/opencs/ai-line-analysis')
TASKS={'_ZN8Presonus5Panel11FillElementC1ERKNS0_11ElementInfoE': 'sqlite25_page_book_02e167c886', '_ZN8Presonus5Panel11FillElementC2ERKNS0_11ElementInfoE': 'sqlite25_page_book_6d2699e43b', '_ZN8Presonus5Panel13StaticElement6renderERNS0_8IDisplayEb': 'sqlite25_page_book_2ba414338f', '_ZN8Presonus5Panel13StaticElementC1ERKNS0_11ElementInfoE': 'sqlite25_page_book_038ccec030', '_ZN8Presonus5Panel13StaticElementC2ERKNS0_11ElementInfoE': 'sqlite25_page_book_0bfc6853e3', '_ZN8Presonus5Panel16OffscreenElement4drawERNS0_8IDisplayE': 'sqlite25_page_book_b6c08a1955', '_ZN8Presonus5Panel4Book12deltaEncoderEi': 'sqlite25_page_book_ed6ef49b7e', '_ZN8Presonus5Panel4Book12makeValidPosEv': 'sqlite25_page_book_b7e542c375', '_ZN8Presonus5Panel4Book12switchToPageEPKc': 'sqlite25_page_book_0c46a5e830', '_ZN8Presonus5Panel4Book12switchToPageEi': 'sqlite25_page_book_a4ab6417c4', '_ZN8Presonus5Panel4Book16loadPreviousPageEv': 'sqlite25_page_book_0f79c8fdae', '_ZN8Presonus5Panel4Book3tapEv': 'sqlite25_page_book_eb37a23c3e', '_ZN8Presonus5Panel4Book4nextEv': 'sqlite25_page_book_5159d3274d', '_ZN8Presonus5Panel4Book5storeEv': 'sqlite25_page_book_de70058145', '_ZN8Presonus5Panel4Book6pageupEv': 'sqlite25_page_book_d8bbbb6cfd', '_ZN8Presonus5Panel4Book6recallEv': 'sqlite25_page_book_af1a813db3', '_ZN8Presonus5Panel4Book6updateERNS0_8IDisplayE': 'sqlite25_page_book_a1ae8f64d6', '_ZN8Presonus5Panel4Book7prepareEv': 'sqlite25_page_book_b851218019', '_ZN8Presonus5Panel4Book8pagedownEv': 'sqlite25_page_book_d792a46351', '_ZN8Presonus5Panel4Book8previousEv': 'sqlite25_page_book_886286bb6b', '_ZN8Presonus5Panel4Page12deltaEncoderEi': 'sqlite25_page_book_7d4b02b33c', '_ZN8Presonus5Panel4Page12updateParamsEv': 'sqlite25_page_book_16faf234b2', '_ZN8Presonus5Panel4Page13previousFieldEv': 'sqlite25_page_book_75fa1a7876', '_ZN8Presonus5Panel4Page14setActiveParamEPN4Core8Portable9ParameterE': 'sqlite25_page_book_1bdae2c9c9', '_ZN8Presonus5Panel4Page14setActiveParamEj': 'sqlite25_page_book_9d033f1351', '_ZN8Presonus5Panel4Page3addEPNS0_7ElementE': 'sqlite25_page_book_5898f65f24', '_ZN8Presonus5Panel4Page3tapEv': 'sqlite25_page_book_7fb73de796', '_ZN8Presonus5Panel4Page6updateERNS0_8IDisplayE': 'sqlite25_page_book_aff476650a', '_ZN8Presonus5Panel4Page8activateEPKc': 'sqlite25_page_book_06b3075383', '_ZN8Presonus5Panel4Page9nextFieldEv': 'sqlite25_page_book_79c3d24aba', '_ZN8Presonus5Panel4PageC1EPKcPKNS0_11ElementInfoEi': 'sqlite25_page_book_16a4a83ee3', '_ZN8Presonus5Panel4PageC2EPKcPKNS0_11ElementInfoEi': 'sqlite25_page_book_99be603992', '_ZN8Presonus5Panel7Element4drawERNS0_8IDisplayE': 'sqlite25_page_book_dc1f216d98', '_ZN8Presonus5Panel7Element8editableEv': 'sqlite25_page_book_0a0b9f9daf', '_ZNK8Presonus5Panel4Book11canShowPageEi': 'sqlite25_page_book_1512a32a85'}
P=Path(__file__).resolve().parent
OBJ=base.OBJ;INFO=base.INFO;DISPLAY=base.DISPLAY;PARAM=base.PARAM
PREFIX='_ZN8Presonus5Panel';PAGE=PREFIX+'4Page';BOOK=PREFIX+'4Book'
class Machine(base.Machine):
 def __init__(self,o):
  super().__init__(o);self.u.mem_map(0x53000000,0x100000);self.heap=0x53000000;self.allocations=[];self.key=False
  self.word(PARAM+12,PARAM+64);self.word(PARAM+68,7)
  for n,s in self.syms.items():
   if 'KeyInputProvider' in n and 'theInstance' in n:self.word(s['st_value'],0x5100a000)
  self.word(0x5100a000,self.addr("_ZTVN8Presonus5Panel16KeyInputProviderE")+8);self.word(0x5100a004,0x5100a080);self.word(0x5100a080,0x5100a100);self.word(0x5100a100,0x52003000)
 def hook(self,u,a,size,data):
  x,y,z,w=[u.reg_read(r) for r in (base.R0,base.R1,base.R2,base.R3)];n=self.imports.get(a)
  if n=='_Znwj':
   result=self.heap;self.heap+=(x+255)&~255;self.allocations.append(result);u.reg_write(base.R0,result)
  elif n=='__dynamic_cast':
   target=next((s.name for s in self.syms.values() if s['st_value']==z),'')
   vt=self.word(x) if x else 0
   istext=vt==self.addr('_ZTVN8Presonus5Panel16TextEntryElementE')+8
   isfield=vt==self.addr('_ZTVN8Presonus5Panel12FieldElementE')+8
   if x==PARAM:result=x
   elif '16TextEntryElementE' in target:result=x if istext else 0
   elif '12FieldElementE' in target:result=x if istext or isfield else 0
   else:raise AssertionError(('unexpected cast target',target))
   u.reg_write(base.R0,result)
  elif a==0x52003000:u.reg_write(base.R0,int(self.key))
  elif 0x52001000<=a<0x52001000+23*4:
   slot=(a-0x52001000)//4
   if slot in (6,7):
    point=list(struct.unpack('<ii',u.mem_read(z,8)));rect=list(struct.unpack('<iiii',u.mem_read(w,16)));self.events.append(('copy' if slot==6 else 'capture')+' '+' '.join(map(str,point+rect)))
   elif slot in (8,22):self.events.append('clear' if slot==8 else 'update '+str(y))
   else:return super().hook(u,a,size,data)
  else:return super().hook(u,a,size,data)
  u.reg_write(base.PC,u.reg_read(base.LR))
 def construct(self,n,info=None):
  obj=self.heap;self.heap+=0x2000;self.call(n,obj,info or INFO);return obj
 def info(self,selector=2,name='level'):
  self.u.mem_write(INFO,bytes(96));self.word(INFO,selector);self.word(INFO+4,10);self.word(INFO+8,20);self.word(INFO+12,30);self.word(INFO+16,8);self.put(INFO+20,name);self.u.mem_write(INFO+92,b'\1')
 def page(self,at=OBJ,count=2,field=False):
  self.put(base.BUF,'page');self.call(PAGE+'C1EPKcPKNS0_11ElementInfoEi',at,base.BUF,INFO,0)
  self.info(1 if field else 2)
  children=[]
  for i in range(count):
   child=self.construct(PREFIX+('12FieldElement' if field else '16TextEntryElement')+'C1ERKNS0_11ElementInfoE');self.put(child+0xa1c,'abc');self.word(child+0xa14,0);self.call(PAGE+'3addEPNS0_7ElementE',at,child);children.append(child)
  self.word(self.addr(PREFIX+'16TextEntryElement14s_encoderParamE'),PARAM)
  return children
 def snapshot(self,children):
  active=self.word(OBJ+0xd0);return dict(active=children.index(active) if active in children else -1,cursors=[self.word(x+0xa14) for x in children],activations=[self.word(x+0x78) for x in children],dirty=[self.word(x+0x74) for x in children],redraw=self.word(OBJ+0x114),previous=self.string(OBJ+6),events=self.events)
def originals():
 return [row['original'] for row in json.loads((P/'fixtures.json').read_text())]

def mode(n):
 if n.startswith(PAGE):return 'page_'+n[len(PAGE):].split('E')[0]
 if n.startswith(BOOK):return 'book_'+n[len(BOOK):].split('E')[0]
 if n.startswith('_ZNK8Presonus5Panel4Book'):return 'book_can'
 if '11FillElementC' in n:return 'fill_ctor'
 if '13StaticElementC' in n:return 'static_ctor'
 if '13StaticElement6render' in n:return 'static_render'
 if '16OffscreenElement4draw' in n:return 'offscreen_draw'
 if '7Element8editable' in n:return 'element_editable'
 if '7Element4draw' in n:return 'element_draw'
 raise AssertionError(n)
def run(target=None):
 out=[]
 for o in originals():
  if target and o['mangled']!=target:continue
  n=o['mangled'];md=mode(n);cases=[]
  for variant in range(9 if "PageC1" in n or "PageC2" in n else 7 if "4Page" in n else 6 if "4Book" in n else 4 if "editable" in n else 3):
   m=Machine(o);m.info();ret=None
   if md.startswith('page_'):
    children=m.page(count=0 if variant==0 else 32 if variant==3 else 2,field=variant==6);m.events=[];m.enabled=variant!=5
    if variant==6:m.lookup=PARAM;m.value="abc"
    if children and variant==2:m.call(PAGE+'13activeElementEPNS0_7ElementE',OBJ,children[0]);m.word(children[0]+0xa14,32)
    if children and variant in (4,5):m.call(PAGE+'13activeElementEPNS0_7ElementE',OBJ,children[-1])
    if 'C1' in md or 'C2' in md:
     selector=variant if variant<5 else 0 if variant<7 else 1
     name=['level']*5+['Link ID:','Subgroup Merge:','global/link_id','global/subgroupmerge']
     m.info(selector,name[variant]);m.put(base.BUF,'factory');m.call(n,OBJ,base.BUF,INFO,1);children=[m.word(m.word(OBJ+0x48)+4*i) for i in range(m.word(OBJ+0x4c))];expected=dict(count=len(children),name=m.string(OBJ+0xd4),selector=selector)
    else:
     y=PARAM if 'EPN4' in n else 7 if n.endswith('Ej') else base.BUF if '8activate' in n else DISPLAY if '6update' in n else 2 if 'deltaEncoder' in n else 0
     if variant==4 and 'setActiveParam' in n:y=0 if 'EPN4' in n else 99
     if '8activate' in n:m.put(base.BUF,'before')
     if '3add' in n:
      child=m.construct(PREFIX+'11FillElementC1ERKNS0_11ElementInfoE');m.call(n,OBJ,child);expected=dict(count=m.word(OBJ+0x4c))
     else:
      ret=m.call(n,OBJ,y);expected=m.snapshot(children)
      if 'setActiveParam' in n:expected['return']=ret
   elif md.startswith('book_'):
    # Real native Pages in the native owning Book roster.
    m.call(BOOK+'C1Ei',OBJ,0);pages=[0x53080000,0x53082000]
    for i,p in enumerate(pages):m.page(p,0);m.put(p+0xd4,'first' if i==0 else 'second');m.call(BOOK+'3addEPNS0_4PageE',OBJ,p)
    if variant==5 and not ('makeValidPos' in n or 'prepare' in n):m.word(OBJ+8,0)
    m.word(OBJ+0x90,0);m.u.mem_write(pages[1]+5,bytes([0 if variant==0 else 1]));m.u.mem_write(pages[1]+4,bytes([1 if variant==2 else 0]));m.key=variant==1;m.word(OBJ+0x94,1);m.events=[]
    if '12switchToPageEPKc' in n:m.put(base.BUF,'second');y=base.BUF
    elif 'switchToPage' in n or md=='book_can':y=1
    elif '6update' in n:y=DISPLAY
    elif 'deltaEncoder' in n:y=2
    else:y=0
    if ('12switchToPageEi' in n or md=='book_can') and variant in (3,4):y=-1 if variant==3 else 2
    if 'makeValidPos' in n or 'prepare' in n:m.u.mem_write(pages[0]+5,b'\0')
    ret=m.call(n,OBJ,y);expected=dict(position=m.word(OBJ+0x90),previous=m.word(OBJ+0x94),previousNames=[m.string(p+6) for p in pages],redraw=[m.word(p+0x114) for p in pages],events=m.events)
    if md=='book_can':expected['return']=ret
   else:
    if md=='fill_ctor':m.call(n,OBJ,INFO);expected=dict(bounds=list(struct.unpack('<iiii',m.u.mem_read(OBJ+0x64,16))),dirty=m.word(OBJ+0x74))
    elif md=='static_ctor':m.call(n,OBJ,INFO);expected=dict(bounds=list(struct.unpack('<iiii',m.u.mem_read(OBJ+0x64,16))),dirty=m.word(OBJ+0x74))
    elif md=='element_editable':
     m.call(PREFIX+'12FieldElementC1ERKNS0_11ElementInfoE',OBJ,INFO);m.lookup=PARAM if variant else 0;m.enabled=variant!=2
     if variant==3:m.u.mem_write(OBJ+0x60,b'\0')
     ret=m.call(n);expected=dict(result=ret)
    elif md=='element_draw':m.call(PREFIX+'7ElementC1ERKNS0_11ElementInfoE',OBJ,INFO);m.word(OBJ+0x78,variant);m.call(n,OBJ,DISPLAY);expected=dict(dirty=m.word(OBJ+0x74),events=m.events)
    else:
     m.call(PREFIX+'13StaticElementC1ERKNS0_11ElementInfoE',OBJ,INFO);m.word(OBJ+0x58,variant);m.events=[];m.call(n,OBJ,DISPLAY,variant==2)
     if md=='offscreen_draw':m.call(n,OBJ,DISPLAY)
     expected=dict(bounds=list(struct.unpack('<iiii',m.u.mem_read(OBJ+0x64,16))),dirty=m.word(OBJ+0x74),events=m.events)
   cases.append(dict(variant=variant,expected=expected))
  out.append(dict(original=o,mode=md,cases=cases))
 return out
if __name__=='__main__':print(json.dumps(run(),indent=2))
