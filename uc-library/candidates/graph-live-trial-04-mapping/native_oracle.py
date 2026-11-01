#!/usr/bin/env python3
"""Bounded original ARM executions with explicit external call boundary doubles."""
import hashlib,json,pathlib,struct,sys
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
from elftools.elf.elffile import ELFFile
BASE=pathlib.Path('uc-library/candidates/graph-live-trial-04-mapping')
ELF=pathlib.Path('rootfs/CS18_v13840/home/root/surface')
def run():
 data=ELF.read_bytes(); digest=hashlib.sha256(data).hexdigest(); assert digest=='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
 scope=json.loads((BASE/'scope.json').read_text()); cases=[]; ranges=[]
 with ELF.open('rb') as f:
  ef=ELFFile(f); sections=list(ef.iter_sections())
  for x in scope:
   o=x['original']; sec=sections[int(o['section_json'])]; off=sec['sh_offset']+o['address']-sec['sh_addr']; b=data[off:off+o['size']]
   ranges.append(dict(original=o,file_offset=off,section=sec.name,sha256=hashlib.sha256(b).hexdigest()))
   for found in (0,0x210000):
    for flag in (0,1):
     u=Uc(UC_ARCH_ARM,UC_MODE_ARM); u.mem_map(0,0x400000)
     for seg in ef.iter_segments():
      if seg['p_type']=='PT_LOAD': u.mem_write(seg['p_vaddr'],seg.data())
     u.mem_write(0x200000,struct.pack('<III',0,0x220000,3)); u.mem_write(0x230000,b'key\0')
     u.reg_write(UC_ARM_REG_R0,0x200000); u.reg_write(UC_ARM_REG_R1,0x230000); u.reg_write(UC_ARM_REG_R2,flag);u.reg_write(UC_ARM_REG_SP,0x3f0000);u.reg_write(UC_ARM_REG_LR,0x300000)
     trace=[]; target=o['address']
     def hook(uc,a,size,user):
      regs=lambda:[uc.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
      if a==0x300000: uc.emu_stop();return
      if a==0x76148:
       trace.append({'call':'Item::Item boundary','args':regs()[1:3]});uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
      if a==0xac84:
       rr=regs();trace.append({'call':'bsearch boundary','base':rr[1],'count':rr[2],'stride':rr[3],'comparator':struct.unpack('<I',uc.mem_read(uc.reg_read(UC_ARM_REG_SP),4))[0]});uc.reg_write(UC_ARM_REG_R0,found);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
      if a==0x762a8 and target!=a:
       trace.append({'call':'findItem boundary','name':regs()[1]});uc.reg_write(UC_ARM_REG_R0,found);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
      names={0x75fd0:'setFullOff',0x7605c:'setInverseMode',0x75974:'setEnabled',0x76010:'setImmediate'}
      if a in names:
       trace.append({'call':names[a],'item':regs()[0],'flag':None if a==0x75fd0 else regs()[1]});uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
     u.hook_add(UC_HOOK_CODE,hook);u.emu_start(target,0x300004,count=200)
     assert u.reg_read(UC_ARM_REG_PC)==0x300000
     cases.append({'task_id':x['task_id'],'found':found,'flag':flag,'trace':trace,'r0_observed':u.reg_read(UC_ARM_REG_R0),'table_bytes_after':bytes(u.mem_read(0x200000,12)).hex(),'item_bytes_after':bytes(u.mem_read(0x210000,72)).hex()})
 return {'elf_sha256':digest,'scope':'original target bodies only; dependency calls are explicit boundary doubles; no item behavior, comparison, original return declaration or ARM ABI claim','ranges':ranges,'cases':cases}
if __name__=='__main__':
 result=run()
 if '--verify' in sys.argv:
  assert result==json.loads((BASE/'native-boundary-fixtures.json').read_text()), 'Native fixture replay differs'
 else:
  (BASE/'native-boundary-fixtures.json').write_text(json.dumps(result,indent=2)+'\n')
 print('20 original ARM boundary cases passed')
