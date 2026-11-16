#!/usr/bin/env python3
"""Original application ARM execution only; pinned Core boundaries are captured, not emulated."""
import hashlib,io,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
T=Path(__file__).resolve().parent;TASK=T.name
RUN=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261116')
PACKET=RUN/'prepared-main/packets'/TASK
READS=json.loads((RUN/'READ_INPUTS-prepared-main-real10_g02.json').read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def generate():
 target=json.loads((PACKET/'request.json').read_text())['targets'][0]
 raw=Path(READS['rootfs/CS18_v13840/home/root/surface']['frozen_read_path']).read_bytes()
 assert sha(raw)==target['original_elf_sha256']
 elf=ELFFile(io.BytesIO(raw));section=elf.get_section(target['section'])
 sym=next(s for s in elf.get_section_by_name('.symtab').iter_symbols() if s.name==target['mangled'])
 assert (sym['st_value'],sym['st_size'],sym['st_shndx'])==(target['address'],target['size'],target['section'])
 start=target['address'];size=target['size'];offset=section['sh_offset']+start-section['sh_addr'];body=raw[offset:offset+size]
 assert section.name=='.text' and start+size<=section['sh_addr']+section['sh_size']
 rows=[]
 for obj in [0x2000100,0x2000500]:
  for seed in [0,17,255]:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
   for base in {start&~4095,(start+size-1)&~4095,0x5d000,0x11b000,0xa000,0x2000000,0x3000000,0x4000000}:u.mem_map(base,4096)
   u.mem_write(start,body);initial=bytes((seed+j)%256 for j in range(0x200));u.mem_write(obj,initial)
   sp=0x3000800;stop=0x4000000;pcs=[];writes=[];calls=[]
   boundaries={0x5d36c:'pinned Core Vector<AliasParam*> destructor',0x11b5e0:'pinned Core Component destructor',0xad5c:'operator delete boundary'}
   def code(uc,pc,n,data):
    if pc==stop:uc.emu_stop();return
    if pc in boundaries:
     calls.append(dict(address=pc,name=boundaries[pc],receiver_offset=uc.reg_read(UC_ARM_REG_R0)-obj))
     uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
    assert start<=pc<start+size,hex(pc)
    pcs.append(pc)
   def write(uc,access,addr,n,value,data):
    assert sp-24<=addr<sp or obj<=addr<obj+0x200,(addr,n)
    writes.append([addr-obj if obj<=addr<obj+0x200 else addr-sp,n,value&((1<<(n*8))-1),'receiver' if obj<=addr<obj+0x200 else 'stack'])
   u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
   u.reg_write(UC_ARM_REG_CPSR,0x10);u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_LR,stop);u.reg_write(UC_ARM_REG_R0,obj)
   u.emu_start(start,stop+4,count=128)
   assert u.reg_read(UC_ARM_REG_PC)==stop and u.reg_read(UC_ARM_REG_SP)==sp
   final=bytes(u.mem_read(obj,0x200));normalized=bytearray(initial)
   for addr,n,value,kind in writes:
    if kind=='receiver':normalized[addr:addr+n]=value.to_bytes(n,'little')
   assert bytes(normalized)==final
   rows.append(dict(self=obj,seed=seed,pcs=pcs,writes=writes,calls=calls,r0_offset=u.reg_read(UC_ARM_REG_R0)-obj,unchanged_bytes_preserved=True,stack_restored=True))
 return dict(task_id=TASK,target=target,section=section.name,file_offset=offset,range_sha256=sha(body),elf_sha256=sha(raw),producer_sha256=sha(Path(__file__).read_bytes()),unicorn_version=unicorn.__version__,cases=rows,domain='Six sentinel/receiver-address cases executing exact original normal-path app instructions. All receiver and stack writes, external call identities/arguments, r0 and stack restoration captured.',limitations='Core vector/component and runtime delete bodies are explicit captured call boundaries, not firmware-recovered or natively executed providers. EH paths, original layout/ABI and hardware excluded. Actual pinned providers execute independently in host replay.')
if __name__=='__main__':print(json.dumps(generate(),indent=2))
