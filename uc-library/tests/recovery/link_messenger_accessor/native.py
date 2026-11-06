"""Exact app-range ARM oracle; explicit call boundaries, no Core execution."""
import hashlib,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
ELF=Path('rootfs/RML16AI_Rack_13731/home/root/mixer')
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
START=0x8696c; SIZE=116; OFFSET=0x7e96c; CELL=0x494c3c

def observations():
 with ELF.open('rb') as f:
  e=ELFFile(f); symbol=next(s for s in e.get_section_by_name('.symtab').get_symbol_by_name('_ZN8Presonus4Link12getMessengerEv') if s['st_value']==START and s['st_size']==SIZE); section=e.get_section(symbol['st_shndx']); assert section.name=='.text'; assert section['sh_offset']+START-section['sh_addr']==OFFSET
 data=ELF.read_bytes(); assert hashlib.sha256(data).hexdigest()==SHA
 code=data[OFFSET:OFFSET+SIZE]; assert hashlib.sha256(code).hexdigest()=='858d00882e7abd2efb4205784e4147f932bd6f829e594d7ef6280563da81d94d'
 # singleton literal comes from verified original range, rather than guessed storage
 cell=struct.unpack_from('<I',code,108)[0]
 cases=[]
 for mode in ['first','existing','constructor-failure','allocation-failure']:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for addr,size in [(0x86000,0x1000),(0xa000,0x1000),(0x126000,0x1000),(cell&~4095,4096),(0x200000,4096),(0x300000,0x2000),(0x400000,4096)]: u.mem_map(addr,size)
  u.mem_write(START,code); u.mem_write(cell,struct.pack('<I',0x200000 if mode=='existing' else 0))
  u.reg_write(UC_ARM_REG_SP,0x301000);u.reg_write(UC_ARM_REG_LR,0x400000)
  events=[]; terminal=[]
  def word(a):return struct.unpack('<I',u.mem_read(a,4))[0]
  def hook(uc,pc,size,_):
   if pc==0x400000: terminal.append('return');uc.emu_stop();return
   if pc==0xa7e4:
    events.append(['allocate',uc.reg_read(UC_ARM_REG_R0)])
    if mode=='allocation-failure': terminal.append('allocator-unwind-boundary');uc.emu_stop();return
    uc.reg_write(UC_ARM_REG_R0,0x200000)
   elif pc==0x868a0:
    events.append(['construct',uc.reg_read(UC_ARM_REG_R0)])
    if mode=='constructor-failure':
     uc.reg_write(UC_ARM_REG_R0,0xabcdef);uc.reg_write(UC_ARM_REG_PC,0x869c4);return
   elif pc==0x126cfc:
    events.append(['register',uc.reg_read(UC_ARM_REG_R0),word(cell),word(0x200000),word(0x200004)])
   elif pc==0xac10:events.append(['delete',uc.reg_read(UC_ARM_REG_R0)])
   elif pc==0xacd0:
    events.append(['resume-unwind',uc.reg_read(UC_ARM_REG_R0)]);terminal.append('unwind');uc.emu_stop();return
   else:
    assert START<=pc<START+108,hex(pc)
    return
   uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,hook);u.emu_start(START,0,count=1000)
  cases.append(dict(mode=mode,events=events,terminal=terminal,returned=u.reg_read(UC_ARM_REG_R0),singleton=word(cell)))
 return dict(elf_sha256=SHA,address=START,size=SIZE,file_offset=OFFSET,section='.text',range_sha256=hashlib.sha256(code).hexdigest(),singleton_cell=cell,cases=cases,limitations='Constructor throw transfers explicitly to native landing pad; external unwinder and Core bodies are boundaries, not executed. Allocation failure stops at allocator unwind boundary.')
if __name__=='__main__':print(json.dumps(observations(),indent=2))
