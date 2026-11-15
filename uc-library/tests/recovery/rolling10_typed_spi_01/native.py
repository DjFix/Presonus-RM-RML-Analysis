import hashlib,io,json,pathlib,sys,struct
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
base=pathlib.Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114/prepared06/snapshot')
b=(base/'rootfs/RML16AI_Rack_13731/home/root/mixer').read_bytes();assert hashlib.sha256(b).hexdigest()=='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
e=ELFFile(io.BytesIO(b));symbols={s.name:s for s in e.get_section_by_name('.symtab').iter_symbols()}
def extract(name,address,size):
 s=symbols[name];assert s['st_value']==address and s['st_size']==size
 sec=e.get_section(s['st_shndx']);assert sec['sh_addr']<=address and address+size<=sec['sh_addr']+sec['sh_size'];off=sec['sh_offset']+address-sec['sh_addr'];data=b[off:off+size]
 return data,dict(mangled=name,address=address,size=size,section=s['st_shndx'],file_offset=off,sha256=hashlib.sha256(data).hexdigest())
def emit(result):
 text=json.dumps(result,indent=2)+'\n';out=pathlib.Path(__file__).with_name('fixtures.json')
 if '--verify' in sys.argv:assert out.read_text()==text
 else:out.write_text(text)
code,rng=extract('_ZN8Presonus5Panel10SPIControl14broadcastValueEi',708560,60)
assert rng['sha256']=='6f3d97cb6914e88c7e4b404bcd7207114757fd835889d585ec079b59fa104a26'
provider,prng=extract('_ZN8Presonus5Panel8IPanelIO9broadcastEPNS0_7ControlE',614792,20);assert prng['sha256']=='52014dc35dcb0a43c02dfc6dec01fdeeafcc563ba02addaa7295df3a7a57226c'
rows=[]
for before,value in [(0,0),(0,1),(1,0),(-1,-1),(-1,2147483647),(2147483647,-2147483648),(-2147483648,2147483647)]:
 for io_bound in [True,False]:
  if not io_bound and before!=value:continue # Native dereferences valid IO on changes.
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0xa0000,0x10000);u.mem_write(708560,code);u.mem_map(0x90000,0x10000);u.mem_write(614792,provider);u.mem_map(0x100000,0x10000)
  put=lambda p,x:u.mem_write(p,struct.pack('<I',x&0xffffffff))
  obj=0x100000;io=0x100100;vt=0x100200;put(obj+4,before);put(obj+20,io if io_bound else 0);put(io,vt);put(vt+8,614792);calls=[]
  def hook(uc,pc,n,d):
   if pc==614792:calls.append(dict(receiver=uc.reg_read(UC_ARM_REG_R0)==io,control=uc.reg_read(UC_ARM_REG_R1)==obj,level=struct.unpack('<i',uc.mem_read(obj+4,4))[0]))
  u.hook_add(UC_HOOK_CODE,hook)
  for reg,v in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_R1,value),(UC_ARM_REG_SP,0x10f000),(UC_ARM_REG_LR,0xa0000)]:u.reg_write(reg,v&0xffffffff)
  u.emu_start(708560,0xa0000,count=100);assert u.reg_read(UC_ARM_REG_PC)==0xa0000 and u.reg_read(UC_ARM_REG_SP)==0x10f000
  rows.append(dict(before=before,value=value,io_bound=io_bound,after=struct.unpack('<i',u.mem_read(obj+4,4))[0],calls=calls,returned=True,stack_restored=True))
emit(dict(range=rng,actual_native_provider=prng,cases=rows,limitations='Actual inherited IPanelIO default only; no unknown derived override, no hardware; changed value requires live IO.'))
