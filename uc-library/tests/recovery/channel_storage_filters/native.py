"""Original ARM app oracle. CCL/cast/string boundaries intercepted; float helper executes native.
No hardware/syscall passthrough. Controller and value accesses are synthetic boundary observations.
"""
import hashlib,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import *
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[4];T=Path(__file__).resolve().parent
ELF=R/'rootfs/RML16AI_Rack_13731/home/root/mixer'
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
RAW=ELF.read_bytes();assert hashlib.sha256(RAW).hexdigest()==SHA
NAMES=[None,'','eq','filter','gate','comp','limit','EQ','compressor','eqx']
CONTROLLERS=[None,None,'comp','limit','eq','filter','gate','','EQ','other']
RANGES=[]
with ELF.open('rb') as f:
 e=ELFFile(f)
 for suffix in ['Load','Save']:
  name='_ZNK8Presonus5Mixer19ChannelPresetFilter10should'+suffix+'EiPKcPv'
  s=next(x for x in e.get_section_by_name('.symtab').iter_symbols() if x.name==name);sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr']
  RANGES.append(dict(mangled=name,address=s['st_value'],size=s['st_size'],section=sec.name,file_offset=off,sha256=hashlib.sha256(RAW[off:off+s['st_size']]).hexdigest()))
def execute(c):
 mode,typ,ni,mask,bits,equal,kind,ci=c
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x500000);u.mem_map(0x1000000,0x20000)
 with ELF.open('rb') as f:
  for s in ELFFile(f).iter_segments():
   if s['p_type']=='PT_LOAD':u.mem_write(s['p_vaddr'],s.data())
 obj=0x1000000;p=0x1001000;vt=0x1002000;ctl=0x1003000;stop=0x1010000
 def w(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def r(a):return struct.unpack('<I',u.mem_read(a,4))[0]
 def string(a):
  out=bytearray()
  while a and u.mem_read(a,1)!=b'\0':out.extend(u.mem_read(a,1));a+=1
  return out.decode()
 def ret(v):u.reg_write(UC_ARM_REG_R0,v&0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 actual=p if kind else 0;w(obj+4,actual if equal else obj+0x800)
 for i in range(3):w(obj+8+4*i,p+0x100*(i+1) if mask&(1<<i) else 0);w(p+0x100*(i+1),vt)
 w(vt+0x44,stop+4)
 name=NAMES[ni];u.mem_write(obj+0x900,(name or '').encode()+b'\0');u.mem_write(ctl+8,(CONTROLLERS[ci] or '').encode()+b'\0')
 reads=[];trace=[];helper=0
 def hook(uc,a,size,data):
  nonlocal helper
  x=uc.reg_read(UC_ARM_REG_R0);y=uc.reg_read(UC_ARM_REG_R1)
  if a==stop:uc.emu_stop()
  elif a==stop+4:reads.append((x-p)//0x100-1);ret(bits)
  elif a==0xaf70:ret(0 if string(x)==string(y) else 1)
  elif a==0x18224:ret(int(string(r(x))==string(y)))
  elif a==0x11c1d4:trace.append('controller');ret(ctl if ci else 0)
  elif a==0xacf4:trace.append('cast');ret(ctl if ci>=2 else 0)
  elif a==0x157940:helper+=1
  elif not (0x502d0<=a<0x5052c or 0x157848<=a<0x157958):raise AssertionError(hex(a))
 def write_hook(uc,access,address,size,value,data):
  assert 0x101e000 <= address < 0x101f000, (hex(address),size)
 u.hook_add(UC_HOOK_MEM_WRITE,write_hook)
 u.hook_add(UC_HOOK_CODE,hook)
 for reg,val in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_R1,typ),(UC_ARM_REG_R2,obj+0x900 if name is not None else 0),(UC_ARM_REG_R3,actual),(UC_ARM_REG_SP,0x101f000),(UC_ARM_REG_LR,stop)]:u.reg_write(reg,val)
 u.emu_start(RANGES[mode]['address'],stop,count=10000)
 assert u.reg_read(UC_ARM_REG_PC)==stop
 return {'result':u.reg_read(UC_ARM_REG_R0),'reads':reads,'trace':trace,'native_float_calls':helper}
def cases():
 out=[]
 for typ in [0,0x436f6d70,0x50617261]:
  for ni in range(len(NAMES)):
   for mask in range(8):
    for bits in [0,0x80000000,0x3f800000,0xbf800000,0x7f800000,0xff800000,0x7fc00000,0x7f800001,1,0x80000001]:
     c=[0,typ,ni,mask,bits,0,1,0];out.append({'input':c,'output':execute(c)})
 for typ in [0,0x436f6d70,0x50617261]:
  for equal in [0,1]:
   for kind in [0,1]:
    for ci in range(len(CONTROLLERS)):
     c=[1,typ,0,0,0,equal,kind,ci];out.append({'input':c,'output':execute(c)})
 return out
if __name__=='__main__':
 data={'elf_sha256':SHA,'ranges':RANGES,'cases':cases()};(T/'fixtures.json').write_text(json.dumps(data,indent=2)+'\n');print(len(data['cases']))
