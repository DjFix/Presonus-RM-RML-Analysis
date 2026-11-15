"""Original application matches execution; Core/libc boundaries explicitly modeled.
Provider observations must separately establish the pinned-source adaptation.
"""
import hashlib,json,pathlib,struct,io,sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
ELF=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared05/snapshot/rootfs/CS18_v13840/home/root/surface')
b=ELF.read_bytes();assert hashlib.sha256(b).hexdigest()=='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
e=ELFFile(io.BytesIO(b));symbol=next(x for x in e.get_section_by_name('.symtab').iter_symbols() if x.name=='_ZNK8Presonus13FocusRestorer10FindFilter7matchesEPKN4Core8Portable4ViewE');section=e.get_section(symbol['st_shndx']);assert symbol['st_value']==0x6522c and symbol['st_size']==272 and symbol['st_shndx']==12;assert section['sh_addr']<=symbol['st_value'] and symbol['st_value']+272<=section['sh_addr']+section['sh_size'];offset=section['sh_offset']+symbol['st_value']-section['sh_addr'];code=b[offset:offset+272];assert hashlib.sha256(code).hexdigest()=='79dea2747606bf29892201e047c93410e6e4f7d71986014842bece1e0474276d'
rows=[]
for change in ['equal','null','unfocused','wrong_magic','rect0','rect1','rect2','rect3','point0','point1','name']:
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x60000,0x10000);u.mem_write(0x6522c,code);u.mem_write(0x65338,b[offset+268:offset+272]);u.mem_map(0x100000,0x10000)
 put=lambda p,x:u.mem_write(p,struct.pack('<'+('I'*len(x)),*x))
 state=0x100100;view=0x100200;size=0x100300;obj=0x100000
 rect=[0,0,30,40];point=[12,23];name='focus'
 put(obj,[0,state]);put(state,[1449747831,*rect,*point]);u.mem_write(state+28,b'focus\0');u.mem_write(view+8,b'focus\0');put(view+64,[4]);put(size,[5,7,35,47])
 if change=='wrong_magic':put(state,[0])
 if change=='unfocused':put(view+64,[0])
 if change.startswith('rect'):put(state+4+int(change[-1])*4,[99])
 if change.startswith('point'):put(state+20+int(change[-1])*4,[99])
 if change=='name':u.mem_write(view+8,b'other\0')
 calls=[]
 def hook(uc,pc,n,d):
  if pc not in [0x10e9bc,0x10e9a8,0x10e928,0xb0f8]:return
  a=uc.reg_read(UC_ARM_REG_R0);c=uc.reg_read(UC_ARM_REG_R1);calls.append(pc)
  if pc==0x10e9bc:put(c,rect)
  elif pc==0x10e9a8:uc.reg_write(UC_ARM_REG_R0,size)
  elif pc==0x10e928:put(c,point)
  else:
   def string(p):
    out=b''
    while True:
     z=bytes(uc.mem_read(p,1));p+=1
     if z==b'\0':return out
     out+=z
   uc.reg_write(UC_ARM_REG_R0,0 if string(a)==string(c) else 1)
  uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,hook)
 # Core targets need executable mapped pages, but bodies never execute.
 u.mem_map(0x10000,0x1000);u.mem_map(0xb000,0x1000)
 u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,0 if change=='null' else view);u.reg_write(UC_ARM_REG_SP,0x10f000);u.reg_write(UC_ARM_REG_LR,0x60000)
 u.emu_start(0x6522c,0x60000,count=300)
 assert u.reg_read(UC_ARM_REG_PC)==0x60000
 rows.append(dict(case=change,result=u.reg_read(UC_ARM_REG_R0),calls=calls))
text=json.dumps({'file_offset':offset,'section_index':12,'address':symbol['st_value'],'size':symbol['st_size'],'returned':True,'range_sha256':hashlib.sha256(code).hexdigest(),'cases':rows,'limitations':'Boundary models, not original Core/libc binary execution; view/state pointers valid except explicit null early-exit.'},indent=2)+'\n'
out=pathlib.Path(__file__).with_name('fixtures.json')
if '--verify' in sys.argv: assert out.read_text()==text
else: out.write_text(text)
