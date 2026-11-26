"""Bounded execution of exact app ranges; libc/attribute boundaries are explicit stubs."""
import hashlib,io,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0 as R0,UC_ARM_REG_R1 as R1,UC_ARM_REG_R2 as R2,UC_ARM_REG_PC as PC,UC_ARM_REG_LR as LR,UC_ARM_REG_SP as SP
P=Path('temp/recovery-work/sqlite-issued/packet-sol61')
OBJ=0x51001000; ATTR=0x51002000; TEXT=0x51003000; META=0x51004000; STOP=0x5200ff00
PREFIX='_ZN8Presonus2UC11DataElement'
INPUTS=[None,'','short','A'*31,'B'*32,'C'*80,'x\0tail']
def digest(b):return hashlib.sha256(b).hexdigest()
def originals():
 return [r['original'] for p in sorted(P.glob('sqlite15_data_element_*/CONTEXT.json')) for r in json.loads(p.read_text())['originals']]
class Machine:
 def __init__(self,o):
  raw=Path(o['elf_path']).read_bytes();assert digest(raw)==o['elf'];e=ELFFile(io.BytesIO(raw));self.syms={s.name:s for s in e.get_section_by_name('.symtab').iter_symbols()};s=self.syms[o['mangled']];sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];assert (s['st_value'],s['st_size'],s['st_shndx'],off)==(o['address'],o['size'],o['section'],o['file_offset']);assert raw[off:off+o['size']].hex()==o['range_hex'];assert digest(raw[off:off+o['size']])==o['range_sha256']
  self.u=Uc(UC_ARCH_ARM,UC_MODE_ARM);segments=[s for s in e.iter_segments() if s['p_type']=='PT_LOAD'];lo=min(s['p_vaddr'] for s in segments)&~4095;hi=(max(s['p_vaddr']+s['p_memsz'] for s in segments)+4095)&~4095;self.u.mem_map(lo,hi-lo)
  for s in segments:self.u.mem_write(s['p_vaddr'],s.data())
  self.u.mem_map(0x51000000,0x10000);self.u.mem_map(0x52000000,0x10000);self.events=[];self.freed=[];self.next=0x51008000
  rel=e.get_section_by_name('.rel.plt');dyn=e.get_section(rel['sh_link']);plt=e.get_section_by_name('.plt');imports={plt['sh_addr']+20+i*12:dyn.get_symbol(r['r_info_sym']).name for i,r in enumerate(rel.iter_relocations())}
  self.imports=imports;self.u.hook_add(UC_HOOK_CODE,self.hook)
  self.u.mem_write(ATTR,struct.pack('<I',ATTR+0x100));self.u.mem_write(ATTR+0x100,struct.pack('<II',0x52001000,0x52001004));self.value=None
 def addr(self,n):return self.syms[n]['st_value']
 def word(self,a,v=None):
  if v is not None:self.u.mem_write(a,struct.pack('<I',v))
  return struct.unpack('<I',self.u.mem_read(a,4))[0]
 def string(self,a):
  if not a:return ''
  return bytes(self.u.mem_read(a,256)).split(b'\0',1)[0].decode('ascii')
 def hook(self,u,a,size,data):
  x,y,z=[u.reg_read(r) for r in (R0,R1,R2)];n=self.imports.get(a)
  if a==0x52001000:
   key=self.string(y);self.events.append(['lookup',key]);v=self.value if key=='type' else 'fixture-id';u.mem_write(TEXT,(v or '').encode()+b'\0');u.reg_write(R0,TEXT if v is not None else 0)
  elif a==0x52001004:self.events.append(['store',self.string(y),self.string(z)])
  elif n=='strlen':u.reg_write(R0,len(self.string(x)))
  elif n in ('memcpy','memmove'):u.mem_write(x,bytes(u.mem_read(y,z)))
  elif n=='memset':u.mem_write(x,bytes([y&255])*z)
  elif n in ('strncpy',):
   b=self.string(y).encode()[:z];u.mem_write(x,b.ljust(z,b'\0'))
  elif n in ('free','_ZdlPv','_ZdaPv'):
   if x:self.freed.append([n,x])
  elif n=='realloc':
   assert x==0;out=self.next;self.next+=(y+15)&~15;u.reg_write(R0,out)
  elif n in ('malloc','_Znwj','_Znaj'):
   out=self.next;self.next+=(x+15)&~15;u.reg_write(R0,out)
  elif n:raise AssertionError(('unsupported import',n,hex(a)))
  else:
   for label in ('_ZN8Presonus2UC7ElementC2ERKNS0_11MetaElementE','_ZN8Presonus2UC7ElementD2Ev','_ZN4Core2IO6BufferD1Ev'):
    if label in self.syms and a==self.addr(label):self.events.append([label,x])
   return
  u.reg_write(PC,u.reg_read(LR))
 def call(self,n,x=OBJ,y=0):
  u=self.u;u.reg_write(R0,x);u.reg_write(R1,y);u.reg_write(SP,STOP-256);u.reg_write(LR,STOP);u.emu_start(self.addr(n),STOP,count=50000);assert u.reg_read(PC)==STOP;return u.reg_read(R0)
def run():
 result=[]
 for o in originals():
  m=Machine(o);n=o['mangled'];m.call(PREFIX+'C1ERKNS0_11MetaElementE',OBJ,META);assert m.string(OBJ+0x60)=='';assert m.word(OBJ+0x98)==8192
  assert m.word(OBJ)==m.addr('_ZTVN8Presonus2UC11DataElementE')+8
  cases=[]
  if 'C1E' in n or 'C2E' in n:
   m=Machine(o);m.call(n,OBJ,META);cases=[dict(type=m.string(OBJ+0x60),grow=m.word(OBJ+0x98),events=m.events)]
  elif '4load' in n or '4save' in n:
   for v in INPUTS:
    m.value=v;m.events=[];m.call(PREFIX+'4loadERKNS0_17ElementAttributesE',OBJ,ATTR);loaded=m.string(OBJ+0x60);load=list(m.events);m.events=[];m.call('_ZNK8Presonus2UC11DataElement4saveERNS0_17ElementAttributesE',OBJ,ATTR);cases.append(dict(input=v,type=loaded,load=load,save=m.events))
  else:
   # Arrange an owned native buffer through MemoryStream's original byte writer.
   m.u.mem_write(TEXT,b'payload');m.u.reg_write(R2,7);m.call('_ZN4Core2IO12MemoryStream10writeBytesEPKvi',OBJ+0x80,TEXT);buffer=m.word(OBJ+0x88);assert buffer
   m.events=[];m.freed=[];m.call(n);assert any(p==buffer for _,p in m.freed);assert any(p==OBJ for _,p in m.freed)==('D0E' in n);cases=[dict(events=m.events,freed=m.freed)]
  result.append(dict(original=o,cases=cases))
 return result
if __name__=='__main__':print(json.dumps(run(),indent=2))
