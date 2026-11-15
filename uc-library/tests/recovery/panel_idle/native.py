#!/usr/bin/env python3
"""Execute only the exact app body; record and stop at CCL provider entry."""
import argparse, hashlib, io, json, struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
import unicorn
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
KIND=Path(__file__).parent.name.removeprefix('panel_')
def sha(b): return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--elf',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 raw=Path(a.elf).read_bytes();assert sha(raw)=='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
 packet=Path('temp/recovery-work/production-20261112/prepared03/packets/rolling_next_panel_'+KIND)
 t=json.loads((packet/'request.json').read_text())['targets'][0];elf=ELFFile(io.BytesIO(raw));sym=next(s for s in elf.get_section_by_name('.symtab').iter_symbols() if s.name==t['mangled']);sec=elf.get_section(sym['st_shndx']);start=sym['st_value'];size=sym['st_size'];off=sec['sh_offset']+start-sec['sh_addr'];assert (start,size)==(t['address'],t['size'])
 target=0x1196a8 if KIND=='idle' else 0x11b7d8
 regs=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2];rows=[]
 for self in [0x2000000,0x2000080]:
  for param in ([0] if KIND=='idle' else [0,0x2001000,0x2001100]):
   for message in ([0] if KIND=='idle' else [0,1,2,3,4,5,0x7fffffff,0x80000000,0xffffffff]):
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
    for addr in sorted(set([start&~4095,target&~4095,0x2000000,0x2001000,0x3000000])):u.mem_map(addr,4096)
    u.mem_write(start,raw[off:off+size]);u.mem_write(0x2000000,b'\xa5'*4096);u.mem_write(0x2001000,b'\x5a'*4096)
    sp=0x3000800;lr=0x4000000;pcs=[];writes=[];calls=[]
    def code(uc,pc,n,data):
     if pc==target:
      calls.append([uc.reg_read(r) for r in regs]);assert uc.reg_read(UC_ARM_REG_SP)==sp and uc.reg_read(UC_ARM_REG_LR)==lr;uc.emu_stop();return
     assert start<=pc<start+size;pcs.append(pc)
    def write(uc,access,addr,n,value,data):
     assert sp-16<=addr<addr+n<=sp;writes.append([addr,n,value])
    u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
    u.reg_write(UC_ARM_REG_CPSR,0x10);u.reg_write(UC_ARM_REG_SP,sp);u.reg_write(UC_ARM_REG_LR,lr)
    for reg,val in zip(regs,[self,param,message]):u.reg_write(reg,val)
    u.emu_start(start,target+4,count=20);assert calls==[[self,param,message]];assert pcs==list(range(start,start+size,4));assert bytes(u.mem_read(0x2000000,4096))==b'\xa5'*4096;assert bytes(u.mem_read(0x2001000,4096))==b'\x5a'*4096
    rows.append(dict(input=[self,param,message],provider_entry=target,args=calls[0],pcs=pcs,writes=writes,object_unchanged=True,stack_restored=True))
 out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 proof=dict(elf_sha256=sha(raw),mangled=t['mangled'],address=start,size=size,section=sec.name,file_offset=off,range_sha256=sha(raw[off:off+size]),producer_sha256=sha(Path(__file__).read_bytes()),unicorn=unicorn.__version__,cases=rows,limitations='Only original app instructions execute; stop before actual Core entry. No original Core execution, hardware, original declaration/layout/ARM interoperability claim.')
 (out/'native.json').write_text(json.dumps(proof,indent=2)+'\n');print('Native boundary cases:',len(rows))
if __name__=='__main__':main()
