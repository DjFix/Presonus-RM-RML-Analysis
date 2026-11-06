"""Execute only original FileMute activation; explicit archive/tree/cache/allocator
boundaries. Guest Core and host system calls never execute."""
import hashlib,json,struct,itertools
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent
ELF=R/'rootfs/RML16AI_Rack_13731/home/root/mixer';SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07';NAME='_ZN8Presonus13FileMuteGroup8activateEv'
RAW=ELF.read_bytes();assert hashlib.sha256(RAW).hexdigest()==SHA
with ELF.open('rb') as f:
 e=ELFFile(f);s=next(s for s in e.get_section_by_name('.symtab').iter_symbols() if s.name==NAME);sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr']
 RANGE=dict(mangled=NAME,address=s['st_value'],size=s['st_size'],section=sec.name,file_offset=off,sha256=hashlib.sha256(RAW[off:off+s['st_size']]).hexdigest())
 SEGS=[(s['p_vaddr'],s.data()) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
def execute(archive,tree):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x400000)
 for addr,data in SEGS:
  if addr<0x400000:u.mem_write(addr,data[:0x400000-addr])
 u.mem_protect(0,0x400000,5);u.mem_map(0x400000,0x40000)
 obj=0x400000;mix=0x401000;vt=0x402000;stop=0x430000
 def w(a,v):u.mem_write(a,struct.pack('<I',v))
 w(obj+0x24,mix);w(mix,vt);w(vt+0x20,stop+4)
 events=[];pcs=[];attributes=None
 def hook(uc,pc,size,data):
  nonlocal attributes
  if pc==stop:u.emu_stop();return
  if RANGE['address']<=pc<RANGE['address']+RANGE['size']:pcs.append(pc);return
  r=[u.reg_read(x) for x in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]];result=0
  if pc==0x121dbc:events.append('allocator');result=0x405000
  elif pc==0x121a68:attributes=r[0];assert r[1]==0x405000;events.append('construct')
  elif pc==0x117fa8:
   sp=u.reg_read(UC_ARM_REG_SP);assert r==[attributes,obj+0xb4,0,0];assert bytes(u.mem_read(sp,8))==bytes(8);events.append('archive');result=archive
  elif pc==stop+4:
   assert r[0]==mix;storage=r[1];assert u.mem_read(storage,1)==b'\0';assert struct.unpack('<IIIII',u.mem_read(storage+32,20))==(obj+0xb0,0,0,0,attributes);events.append('tree');result=tree
  elif pc==0x74fe0:assert r[:2]==[obj,attributes];events.append('cache')
  elif pc==0x1228b0:assert r[0]==attributes;events.append('destroy')
  else:raise AssertionError(hex(pc))
  u.reg_write(UC_ARM_REG_R0,result);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,hook)
 for reg,val in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_SP,0x41ff00),(UC_ARM_REG_LR,stop)]:u.reg_write(reg,val)
 u.emu_start(RANGE['address'],stop,count=150);assert u.reg_read(UC_ARM_REG_PC)==stop
 return dict(input=[archive,tree],events=events,executed_pcs=pcs)
def cases():return [execute(a,t) for a,t in itertools.product([0,1],[0,1])]
if __name__=='__main__':
 data=dict(elf_sha256=SHA,ranges=[RANGE],cases=cases());(T/'fixtures.json').write_text(json.dumps(data,indent=2)+'\n');print('4 original instruction executions')
