#!/usr/bin/env python3
"""Only the four app ranges execute. Core/libc are explicit semantic boundaries."""
import argparse,ctypes,hashlib,io,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ELF=Path('rootfs/RML16AI_Rack_13731/home/root/mixer')
HASH='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
PACKETS=Path('temp/recovery-work/rolling200-02/next-implementation08/prepared09-permissions_lifecycle08/packets')
SELF,SELECTED,ARRAY,STACK,STOP=0x1000000,0x1002000,0x1004000,0x1100000,0x1200000
REGS=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
def sha(b):return hashlib.sha256(b).hexdigest()
class Oracle:
 def __init__(self):
  self.raw=ELF.read_bytes();assert sha(self.raw)==HASH
  elf=ELFFile(io.BytesIO(self.raw));syms={s.name:s for s in elf.get_section_by_name('.symtab').iter_symbols()};self.ranges=[];self.targets=[]
  for p in sorted(PACKETS.iterdir()):
   t=json.loads((p/'request.json').read_text())['targets'][0];s=syms[t['mangled']];sec=elf.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];assert s['st_value']==t['address'] and s['st_size']==t['size'];self.targets.append(t);self.ranges.append(dict(mangled=t['mangled'],address=t['address'],size=t['size'],section=sec.name,file_offset=off,sha256=sha(self.raw[off:off+t['size']])))
  self.u=Uc(UC_ARCH_ARM,UC_MODE_ARM);pages=set()
  for s in elf.iter_segments():
   if s['p_type']!='PT_LOAD':continue
   for a in range(s['p_vaddr']&~4095,(s['p_vaddr']+s['p_memsz']+4095)&~4095,4096):
    if a not in pages:self.u.mem_map(a,4096);pages.add(a)
   self.u.mem_write(s['p_vaddr'],s.data())
  for a,n in [(SELF,0x10000),(STACK,0x10000),(STOP,4096)]:self.u.mem_map(a,n)
  self.u.hook_add(UC_HOOK_CODE,self.code);self.u.hook_add(UC_HOOK_MEM_WRITE,self.write)
  self.boundaries={0xae68:'memcpy',0x1a134:'ctor',0x50580:'mix',0x505a8:'other',0xaf70:'strcmp',0xad18:'strstr',0xae98:'strlen',0x52304:'substring',0xafdc:'sscanf',0xac10:'delete',0x52468:'vector',0x11a53c:'component'}
  self.lib=ctypes.CDLL(None)
 def put(self,a,v):self.u.mem_write(a,struct.pack('<I',v))
 def string(self,a):
  out=bytearray()
  while a and len(out)<1024:
   b=self.u.mem_read(a,1)[0];a+=1
   if not b:break
   out.append(b)
  return bytes(out)
 def mem(self,a,b):
  assert STACK<=a and a+len(b)<=STACK+0x10000 or SELF+0x99<=a and a+len(b)<=SELF+0xe4
  self.writes.append([a,b.hex(),'boundary']);self.u.mem_write(a,b)
 def write(self,u,access,a,n,v,data):
  assert STACK<=a and a+n<=STACK+0x10000 or SELF<=a and a+n<=SELF+0x1000
  self.writes.append([a,n,v])
 def code(self,u,a,n,data):
  if a==STOP:self.done=True;u.emu_stop();return
  if a not in self.boundaries:
   assert self.target['address']<=a<self.target['address']+self.target['size'],hex(a)
   self.pcs.append(a);return
  name=self.boundaries[a];r0,r1,r2,r3=[u.reg_read(r) for r in REGS];result=0;detail={}
  if name=='memcpy':self.mem(r0,bytes(u.mem_read(r1,r2)));result=r0
  elif name=='ctor':self.mem(r0,b'\0')
  elif name in ['mix','other']:self.mem(r1,self.case[name].encode()+b'\0')
  elif name=='strcmp':
   x,y=self.string(r0),self.string(r1);result=(x>y)-(x<y)
  elif name=='strstr':
   x,y=self.string(r0),self.string(r1);i=x.find(y);result=r0+i if i>=0 else 0
  elif name=='strlen':result=len(self.string(r0))
  elif name=='substring':
   text=self.string(r0);idx=r2 if r2<2**31 else r2-2**32;count=r3 if r3<2**31 else r3-2**32
   if 0<=idx<len(text):
    count=len(text)-idx if count<0 else count
    if count>0:self.mem(r1,text[idx:idx+count]+b'\0')
  elif name=='sscanf':
   value=ctypes.c_longlong(0);fmt=self.string(r1);assert fmt==b'%lld';result=self.lib.sscanf(ctypes.c_char_p(self.string(r0)),ctypes.c_char_p(fmt),ctypes.byref(value))
   if result==1:self.mem(r2,struct.pack('<q',value.value))
  elif name=='delete':
   assert r0 in self.live,('invalid/double delete',r0);self.live.remove(r0);self.events.append(['selected' if r0==SELECTED else 'object','delete'])
  elif name=='vector':
   assert r0==SELF+0xe4;self.events.append(['vector','destroy']);self.live.discard(ARRAY)
  elif name=='component':assert r0==SELF;self.events.append(['component','destroy'])
  self.calls.append(dict(pc=a,name=name,args=[r0,r1,r2,r3],result=result));u.reg_write(UC_ARM_REG_R0,result&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def run(self,c):
  self.case=c;self.target=self.targets[c['op']];self.writes=[];self.calls=[];self.pcs=[];self.events=[];self.done=False;self.live={SELF}
  self.u.mem_write(SELF,b'\xcc'*0x10000);self.u.mem_write(STACK,bytes([c.get('pattern',0xcc)])*0x10000)
  if c['op']:
   self.put(SELF+0xf8,SELECTED if c['selected'] else 0);self.put(SELF+0xe8,ARRAY if c['vector'] else 0)
   if c['selected']:self.live.add(SELECTED)
   if c['vector']:self.live.add(ARRAY)
  for r in REGS:self.u.reg_write(r,0)
  self.u.reg_write(UC_ARM_REG_CPSR,0x10);self.u.reg_write(UC_ARM_REG_SP,STACK+0xff00);self.u.reg_write(UC_ARM_REG_LR,STOP);self.u.reg_write(UC_ARM_REG_R0,SELF)
  before=bytes(self.u.mem_read(SELF,0x10000));self.u.emu_start(self.target['address'],STOP+4,count=20000);assert self.done
  after=bytes(self.u.mem_read(SELF,0x10000));allowed=set(range(0x99,0xe4)) if not c['op'] else set(range(8))|set(range(0xf8,0xfc));assert all(x==y or i in allowed for i,(x,y) in enumerate(zip(before,after)))
  if not c['op']:
   assert self.u.reg_read(UC_ARM_REG_R0)==SELF+0x99;result=dict(prefix=after[0x99:0xa5].hex(),suffix=after[0xa5:0xe4].hex(),returns_storage=True)
  else:result=dict(events=self.events,selected_cleared=after[0xf8:0xfc]==b'\0'*4,object_deleted=SELF not in self.live)
  return result,dict(calls=self.calls,pcs=self.pcs,writes=self.writes,input_guard_checked=True)
def cases():
 mixes=['','None','none','FOH','foh','All Auxes','All auxes','Aux ','Aux','xAux 1','Aux 1','Aux 32','Aux 0','Aux 33','Aux -1','Aux +1','Aux 1/2','Aux 9/12','Aux 1/','Aux /2','Aux 1//2','Aux 1/Aux 2','Aux 1tail','Aux  2','Aux 9223372036854775807','Aux -9223372036854775808','Aux 18446744073709551616','Aux 01','Aux 0x10']+[f'Aux {i}' for i in range(1,33)]
 for mix in mixes:
  for other in ['', 'None','Ch Rename','Wheel Only','ch rename','Wheel Only ']:
   for pattern in [0x00,0x55,0xaa]:yield dict(op=0,mix=mix,other=other,pattern=pattern)
 for op in [1,2,3]:
  for selected in [False,True]:
   for vector in [False,True]:yield dict(op=op,selected=selected,vector=vector)
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True);o=Oracle();rows=[]
 with (out/'native-traces.jsonl').open('w') as f:
  for i,c in enumerate(cases()):
   result,trace=o.run(c);rows.append(dict(id=i,input=c,observed=result));f.write(json.dumps(dict(id=i,**trace))+'\n')
 (out/'native-fixtures.json').write_text(json.dumps(dict(cases=rows),indent=2)+'\n')
 (out/'native-proof.json').write_text(json.dumps(dict(elf_path=str(ELF),elf_sha256=HASH,ranges=o.ranges,cases=len(rows),producer_sha256=sha(Path(__file__).read_bytes()),unicorn=unicorn.__version__,boundaries=o.boundaries,domain='Only four original app bodies. Core/provider and named libc semantic hooks, host libc sscanf for %lld. Lifecycle boundaries record native calls, not execution of Core bodies; vector/base cleanup independently checked in compiled replay. EH paths excluded.',fixture_sha256=sha((out/'native-fixtures.json').read_bytes()),trace_sha256=sha((out/'native-traces.jsonl').read_bytes())),indent=2)+'\n');print(len(rows))
if __name__=='__main__':main()
