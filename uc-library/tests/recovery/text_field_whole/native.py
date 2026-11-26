"""Whole original app bodies. Core is an explicit provider boundary, never emulated.
Libc memory/string calls are bounded test adapters. Display uses all real slot numbers.
"""
import hashlib,io,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0 as R0,UC_ARM_REG_R1 as R1,UC_ARM_REG_R2 as R2,UC_ARM_REG_R3 as R3,UC_ARM_REG_PC as PC,UC_ARM_REG_LR as LR,UC_ARM_REG_SP as SP
PACKET=Path('temp/recovery-work/rolling-c001-20261124/packeting/sqlite-cycle02/text_field_whole_sol61_r4')
OBJ=0x51001000; INFO=0x51004000; BUF=0x51005000; PARAM=0x51006000; DISPLAY=0x51007000; VTABLE=0x51008000; STOP=0x5200ff00
F='_ZN8Presonus5Panel12FieldElement';T='_ZN8Presonus5Panel16TextEntryElement'
def digest(b):return hashlib.sha256(b).hexdigest()
def originals():return [x['original'] for x in json.loads((PACKET/'NATIVE-CONTEXT.json').read_text())['items']]
CACHE={}
class Machine:
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
def run(target=None):
 result=[]
 for o in originals():
  if target is not None and o["mangled"] != target:continue
  m=Machine(o);n=o['mangled'];cases=[]
  if 'C1E' in n or 'C2E' in n:
   m.call(n,OBJ,INFO);assert bytes(m.u.mem_read(OBJ+4,96))==bytes(m.u.mem_read(INFO,96));assert m.word(OBJ+0x74)==1 and m.word(OBJ+0x78)==0;assert bytes(m.u.mem_read(OBJ+0x64,16))==bytes(16);cases=[dict(record_copy=True,name=m.string(OBJ+24),dirty=1)]
  elif 'D0E' in n or 'D1E' in n or 'D2E' in n:
   m.setup('abc',param=True);m.word(m.addr(T+'14s_encoderParamE'),PARAM);m.provider=[];m.call(n);assert any(x==OBJ for _,x in m.freed)==('D0E' in n);cases=[dict(provider=m.provider,freed=m.freed)]
  elif '12paramChanged' in n:
   for message in (0,3,5):
    m=Machine(o);m.setup('abc',param=True);m.word(OBJ+0x74,0);m.call(n,OBJ,PARAM,message);cases.append(dict(message=message,snapshot=m.snapshot(),provider=m.provider))
  elif '13getDrawStringEPK' in n:
   for param,enabled in [(False,True),(True,False),(True,True)]:
    m=Machine(o);m.setup('abcdefghijklmnopqrstuvwxyz0123456789',param=param,enabled=enabled);m.call(n,OBJ,PARAM if param else 0,BUF,32);cases.append(dict(param=param,enabled=enabled,text=m.string(BUF),provider=m.provider))
  elif '13getDrawString' in n:
   for param,enabled in [(False,True),(True,False),(True,True)]:
    m=Machine(o);m.setup('abcdefghijklmnopqrstuvwxyz0123456789' if param else 'abc',param=param,enabled=enabled);m.call(n,OBJ,BUF,32);cases.append(dict(param=param,enabled=enabled,text=m.string(BUF),provider=m.provider))
  elif '6render' in n or '4draw' in n:
   for text in ('','abc'):
    for color in (0,1,2):
     for force in (0,1):
      for repeat in (None,'same','short','empty'):
       first='longer' if repeat else text
       m=Machine(o);m.setup(first,cursor=1,param=n.startswith(F));m.word(OBJ+0x58,color);m.word(OBJ+0x78,force)
       if repeat:
        m.call(n,OBJ,DISPLAY,force);m.events=[]
        updated=first if repeat=='same' else 'a' if repeat=='short' else ''
        m.value=updated;m.put(OBJ+0xa1c,updated)
       m.call(n,OBJ,DISPLAY,force);cases.append(dict(input=dict(text=first,color=color,force=force,repeat=repeat),param=n.startswith(F),snapshot=m.snapshot(),current=list(struct.unpack('<iiii',m.u.mem_read(OBJ+0x64,16))),previous=list(struct.unpack('<iiii',m.u.mem_read(OBJ+0xa04,16)))))
  else:
   for text in ('','A','abc','a c',' '*31,'z'*31):
    for cursor in (0,1,2,30,31,32):
     for delta in ((-4,-2,-1,0,1,2,4) if '12deltaEncoder' in n else (0,)):
      m=Machine(o);m.setup(text,cursor=cursor);m.word(OBJ+0x74,0);arg=delta if '12deltaEncoder' in n else ord('X') if '14setCurrentChar' in n else cursor if '7getChar' in n else 0;ret=m.call(n,OBJ,arg);case=dict(input=dict(text=text,cursor=cursor,delta=delta),snapshot=m.snapshot());
      if any(k in n for k in ('14getCurrentChar','7getChar','12deltaEncoder','3tap','4next')):case['return']=ret
      cases.append(case)
  result.append(dict(original=o,cases=cases))
 return result
if __name__=='__main__':print(json.dumps(run(),indent=2))
