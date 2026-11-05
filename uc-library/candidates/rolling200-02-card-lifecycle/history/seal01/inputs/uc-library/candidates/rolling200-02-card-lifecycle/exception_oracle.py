"""Controlled provider exception-entry experiment, not ARM unwind ABI proof."""
from pathlib import Path
import hashlib,json,struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[3];E=R/'evidence/recovery/2026-11-05/rolling200-02/card-lifecycle';elf=R/'rootfs/RML16AI_Rack_13731/home/root/mixer';raw=elf.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
with elf.open('rb') as f:
 ef=ELFFile(f);segments=[(int(s['p_vaddr']),s.data(),int(s['p_memsz'])) for s in ef.iter_segments() if s['p_type']=='PT_LOAD']
OBJ=0x1000000;STACK=0x1100000;HEAP=0x1200000;EXCEPTION=0x1200800;GLOBAL=0x495368;cases=[]
for start,landing,name in ((0x9d534,0x9d604,'C1'),(0x9d280,0x9d350,'C2')):
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);pages=set()
 for a,b,n in segments:
  for pg in range(a&~4095,(a+n+4095)&~4095,4096):
   if pg not in pages:u.mem_map(pg,4096);pages.add(pg)
  u.mem_write(a,b)
 for a,n in ((OBJ,4096),(STACK,8192),(HEAP,4096)):u.mem_map(a,n)
 u.mem_write(GLOBAL,bytes(4));u.mem_write(OBJ,bytes([0xa5])*104)
 u.reg_write(UC_ARM_REG_R0,OBJ);u.reg_write(UC_ARM_REG_SP,STACK+4096);u.reg_write(UC_ARM_REG_LR,0x1300000)
 events=[];done=[False];deletes=[];pcs=[]
 def ret():u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def hook(uc,pc,size,data):
  if start<=pc<start+240:pcs.append(pc);return
  r0=u.reg_read(UC_ARM_REG_R0)
  if pc==0xa4b38:assert r0==OBJ;events.append('base');ret()
  elif pc==0xa7e4:assert r0==456;events.append('new');u.reg_write(UC_ARM_REG_R0,HEAP);ret()
  elif pc==0xa2e64:
   assert r0==HEAP;events.append('provider_exception_entry');u.reg_write(UC_ARM_REG_R0,EXCEPTION);u.reg_write(UC_ARM_REG_PC,landing)
  elif pc==0xac10:assert r0==HEAP;events.append('delete_spi_storage');deletes.append(r0);ret()
  elif pc==0xacd0:assert r0==EXCEPTION;events.append('end_cleanup');done[0]=True;u.emu_stop()
  else:raise AssertionError(('unapproved pc',hex(pc)))
 def write(uc,access,a,n,v,data):
  assert (STACK<=a and a+n<=STACK+8192) or (OBJ<=a and a+n<=OBJ+104),(hex(a),n)
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write);u.emu_start(start,0,count=500)
 assert done[0] and deletes==[HEAP] and landing in pcs
 assert events==['base','new','provider_exception_entry','delete_spi_storage','end_cleanup']
 assert bytes(u.mem_read(GLOBAL,4))==bytes(4)
 cases.append(dict(variant=name,address=start,size=240,controlled_exception_landing=landing,events=events,delete_pointers=deletes,executed_native_pcs=pcs))
(E/'constructor-exception-native.json').write_text(json.dumps(dict(elf_sha256=hashlib.sha256(raw).hexdigest(),cases=cases,limitations=['Injected reviewed exception landing at SPI constructor import; native cleanup instructions executed','Does not execute ARM personality/unwind runtime; does not prove ARM exception ABI','Host allocation failure tested independently using actual std::bad_alloc and compiler cleanup']),indent=2)+'\n')
print('two original constructor cleanup paths executed after controlled provider exception entry')
