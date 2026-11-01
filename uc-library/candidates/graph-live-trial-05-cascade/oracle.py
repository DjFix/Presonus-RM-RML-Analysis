import hashlib,json,itertools,struct
from elftools.elf.elffile import ELFFile
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
ELF=Path('rootfs/RML16AI_Rack_13731/home/root/mixer')
EXPECTED='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
RANGES=[(0x5dbd4,24),(0x5dbf4,28),(0x5dabc,32),(0x5dc18,40),(0x5e9bc,56)]
def produce():
 data=ELF.read_bytes();assert hashlib.sha256(data).hexdigest()==EXPECTED
 ranges=[];cases=[]
 with ELF.open('rb') as stream:
  elf=ELFFile(stream);section=elf.get_section_by_name('.text');section_address=int(section['sh_addr']);section_offset=int(section['sh_offset']);section_size=int(section['sh_size'])
 for method,(addr,size) in enumerate(RANGES,1):
  assert section_address <= addr and addr+size <= section_address+section_size
  offset=section_offset+addr-section_address
  assert offset==addr-0x8000
  body=data[offset:offset+size]
  packet=json.loads(Path(f'temp/recovery-work/graph-live-trial-05/trial05_cascade_{method}-packet/native-context.json').read_text())
  bound=packet['bodies'][packet['roots'][0]]
  assert bound['address']==addr and bound['size']==size and bound['file_offset']==offset
  assert bound['bytes_sha256']==hashlib.sha256(body).hexdigest()
  ranges.append(dict(address=addr,size=size,file_offset=offset,section='.text',sha256=hashlib.sha256(body).hexdigest()))
  for selected,item,present,card in itertools.product([0,0x210000,0x210004],[0,0x210000,0x210004],[0,1],[0,1]):
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x50000,0x10000);u.mem_write(addr,body)
   u.mem_map(0x200000,0x20000);u.mem_map(0x300000,0x10000);u.mem_map(0x400000,0x1000)
   u.mem_write(0x2000a0,struct.pack('<I',selected));u.reg_write(UC_ARM_REG_R0,0x200000);u.reg_write(UC_ARM_REG_R1,card if method==5 else item);u.reg_write(UC_ARM_REG_SP,0x308000);u.reg_write(UC_ARM_REG_LR,0x400000)
   trace=[]
   def hook(uc,pc,size,user):
    if pc==0x400000:uc.emu_stop();return
    if pc in (0x5dadc,0x5dc40,0x5e7e4,0x5dcb0):assert uc.reg_read(UC_ARM_REG_R0)==0x200000
    if pc==0x5dadc:
     trace.append(f'select {uc.reg_read(UC_ARM_REG_R1)} {uc.reg_read(UC_ARM_REG_R2)}');uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    elif pc==0x5dc40:
     trace.append('get');uc.reg_write(UC_ARM_REG_R0,0x210000 if present else 0);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    elif pc==0x5e7e4:
     trace.append(f'changed {uc.reg_read(UC_ARM_REG_R1)}');uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
    elif pc==0x5dcb0:
     trace.append('sync');uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   before=bytes(u.mem_read(0x200000,256))
   u.hook_add(UC_HOOK_CODE,hook);u.emu_start(addr,0,count=200)
   after=bytes(u.mem_read(0x200000,256));expected=bytearray(before)
   if method==5:expected[0x8c]=card
   assert after==expected
   assert u.reg_read(UC_ARM_REG_SP)==0x308000
   if method==3:trace.append(f'result {u.reg_read(UC_ARM_REG_R0)}')
   if method==5:trace.append(f'card {u.mem_read(0x20008c,1)[0]}')
   cases.append(dict(argv=[str(x) for x in [method,selected,item,present,card]],observed=trace))
 return dict(elf_sha256=EXPECTED,ranges=ranges,cases=cases,limitations='Dependencies intercepted at original entry addresses, no dependency body or hardware behavior claimed.')
if __name__=='__main__':Path('uc-library/candidates/graph-live-trial-05-cascade/fixtures.json').write_text(json.dumps(produce(),indent=2)+'\n')
