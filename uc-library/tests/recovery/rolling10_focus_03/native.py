import hashlib,io,json,pathlib,struct,sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
p=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared05/snapshot/rootfs/CS18_v13840/home/root/surface');b=p.read_bytes();assert hashlib.sha256(b).hexdigest()=='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
e=ELFFile(io.BytesIO(b));s=next(x for x in e.get_section_by_name('.symtab').iter_symbols() if x.name=='_ZN8Presonus13FocusRestorer9FocusInfo7setViewERN4Core8Portable4ViewE');sec=e.get_section(s['st_shndx']);assert s['st_value']==0x6533c and s['st_size']==112 and s['st_shndx']==12
assert sec['sh_addr']<=s['st_value'] and s['st_value']+s['st_size']<=sec['sh_addr']+sec['sh_size'];off=sec['sh_offset']+s['st_value']-sec['sh_addr'];code=b[off:off+112]
rows=[]
for left,top,w,h,parentx,parenty in [(5,7,30,40,0,0),(0,0,0,0,0,0),(10,20,90,100,30,40)]:
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x60000,0x10000);u.mem_write(0x6533c,code);u.mem_map(0x100000,0x10000)
 put=lambda p,x:u.mem_write(p,struct.pack('<'+len(x)*'I',*x))
 obj=0x100000;view=0x100100;sz=0x100200
 u.mem_write(obj,b'\xaa'*64);u.mem_write(view+8,b'focus\0'+bytes(26));put(sz,[left,top,left+w,top+h]);calls=[]
 def hook(uc,pc,n,d):
  if pc not in [0x10e9bc,0x10e9a8,0x10e928]:return
  out=uc.reg_read(UC_ARM_REG_R1);calls.append(pc)
  if pc==0x10e9bc:put(out,[0,0,w,h])
  elif pc==0x10e9a8:uc.reg_write(UC_ARM_REG_R0,sz)
  else:
   x,y=struct.unpack('<II',uc.mem_read(out,8));put(out,[x+left+parentx,y+top+parenty])
  uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,hook);u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,view);u.reg_write(UC_ARM_REG_SP,0x10f000);u.reg_write(UC_ARM_REG_LR,0x60000);u.emu_start(0x6533c,0x60000,count=100);assert u.reg_read(UC_ARM_REG_PC)==0x60000
 rows.append(dict(input=[left,top,w,h,parentx,parenty],state=list(struct.unpack('<7I',u.mem_read(obj,28))),name=bytes(u.mem_read(obj+28,32)).hex(),calls=calls,returned=True))
result=dict(elf_sha256=hashlib.sha256(b).hexdigest(),file_offset=off,address=s['st_value'],size=s['st_size'],section_index=12,range_sha256=hashlib.sha256(code).hexdigest(),cases=rows)
text=json.dumps(result,indent=2)+'\n';out=pathlib.Path(__file__).with_name('fixtures.json')
if '--verify' in sys.argv:assert out.read_text()==text
else:out.write_text(text)
