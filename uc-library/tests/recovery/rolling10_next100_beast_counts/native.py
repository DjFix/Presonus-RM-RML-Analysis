import hashlib,io,json,pathlib,sys,struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM
from unicorn.arm_const import *
base=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared06/snapshot')
p=base/'rootfs/RML16AI_Rack_13731/home/root/mixer';b=p.read_bytes();assert hashlib.sha256(b).hexdigest()=='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
e=ELFFile(io.BytesIO(b));s=next(x for x in e.get_section_by_name('.symtab').iter_symbols() if x.name=='_ZN8Presonus5Panel19BeastPanelRegistrar29getParamInfoListSizeFromGroupEi');assert s['st_value']==500688 and s['st_size']==204 and s['st_shndx']==12
sec=e.get_section(12);assert sec['sh_addr']<=s['st_value'] and s['st_value']+204<=sec['sh_addr']+sec['sh_size'];off=sec['sh_offset']+s['st_value']-sec['sh_addr'];code=b[off:off+204];assert hashlib.sha256(code).hexdigest()=='b5f1e752ff968c6125231d6f602ccc00258e1acc40b5f9f86c50cb17e03f3a18'
table=struct.unpack('<17I',code[24:92]);assert all(s['st_value']<=v<s['st_value']+204 and v%4==0 for v in table)
rows=[]
for group in [*range(17),-1,-2,-2147483648,17,18,2147483647,65536]:
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x70000,0x10000);u.mem_write(s['st_value'],code);u.mem_map(0x100000,0x10000);u.mem_write(0x100000,b'\xaa'*64);u.reg_write(UC_ARM_REG_R0,0x100000);u.reg_write(UC_ARM_REG_R1,group&0xffffffff);u.reg_write(UC_ARM_REG_SP,0x10f000);u.reg_write(UC_ARM_REG_LR,0x70000);u.emu_start(s['st_value'],0x70000,count=40);assert u.reg_read(UC_ARM_REG_PC)==0x70000 and u.reg_read(UC_ARM_REG_SP)==0x10f000 and bytes(u.mem_read(0x100000,64))==b'\xaa'*64
 rows.append(dict(group=group,result=u.reg_read(UC_ARM_REG_R0),object_unchanged=True,returned=True,stack_restored=True))
text=json.dumps(dict(elf_sha256=hashlib.sha256(b).hexdigest(),address=s['st_value'],size=s['st_size'],section=12,file_offset=off,range_sha256=hashlib.sha256(code).hexdigest(),jump_destinations=table,cases=rows),indent=2)+'\n';out=pathlib.Path(__file__).with_name('fixtures.json')
if '--verify' in sys.argv:assert out.read_text()==text
else:out.write_text(text)
