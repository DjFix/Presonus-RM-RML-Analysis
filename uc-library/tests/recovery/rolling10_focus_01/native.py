import hashlib,json,pathlib,io
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
p=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared05/snapshot/rootfs/CS18_v13840/home/root/surface')
b=p.read_bytes(); assert hashlib.sha256(b).hexdigest()=='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
elf=ELFFile(io.BytesIO(b)); symbols=elf.get_section_by_name('.symtab'); rows=[]
for address,sha in [(0x653ac,'3b8715a405052bf9eaefa99805e2dab20e3d5d3cc9b35939adbdb360b27638e4'),(0x653f0,'d663f0f83b92dc390245fee8cc2a8736124d1f2d7c4c6e23c6d64c3285c3c82b')]:
 symbol=next(x for x in symbols.iter_symbols() if x.name=='_ZN8Presonus13FocusRestorer9FocusInfo'+('C1' if address==0x653ac else 'C2')+'Ev'); assert symbol['st_value']==address and symbol['st_size']==68 and symbol['st_shndx']==12
 section=elf.get_section(symbol['st_shndx']); assert section.name=='.text' and section['sh_addr']<=address and address+68<=section['sh_addr']+section['sh_size']; offset=section['sh_offset']+address-section['sh_addr']
 code=b[offset:offset+68];assert hashlib.sha256(code).hexdigest()==sha
 for fill in [0,0x55,0xaa,0xff]:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x20000,0x50000);u.mem_write(address,code);u.mem_map(0x100000,0x10000);u.mem_write(0x100000,bytes([fill])*128);u.reg_write(UC_ARM_REG_R0,0x100000);u.reg_write(UC_ARM_REG_SP,0x10f000);u.reg_write(UC_ARM_REG_LR,0x60000)
  calls=[]
  def hook(uc,pc,size,data):
   if pc==0x24268:
    calls.append([uc.reg_read(UC_ARM_REG_R0)-0x100000,uc.reg_read(UC_ARM_REG_R1)])
    # Declared boundary model: provider initializes only first char for nullptr.
    uc.mem_write(uc.reg_read(UC_ARM_REG_R0),b'\0');uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,hook);u.emu_start(address,0x60000,count=100)
  assert u.reg_read(UC_ARM_REG_PC)==0x60000
  rows.append(dict(address=address,fill=fill,state=bytes(u.mem_read(0x100000,28)).hex(),first_char=u.mem_read(0x10001c,1)[0],calls=calls,range_sha256=sha,file_offset=offset,section_index=12,section_name=section.name,returned=True))
out=json.dumps(rows,indent=2)+'\n'
path=pathlib.Path(__file__).with_name('fixtures.json')
import sys
if '--verify' in sys.argv: assert path.read_text()==out
else: path.write_text(out)
