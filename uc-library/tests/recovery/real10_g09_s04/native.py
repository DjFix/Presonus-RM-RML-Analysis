"""Execute original doSelect app body, tracing explicit external CCL/RTTI/observer boundaries."""
import argparse,hashlib,io,json,struct,itertools,importlib.metadata
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
def generate(path):
 raw=Path(path).read_bytes();assert hashlib.sha256(raw).hexdigest()==SHA
 elf=ELFFile(io.BytesIO(raw));sec=elf.get_section(12);start=0x2d008;size=376;off=sec['sh_offset']+start-sec['sh_addr'];assert hashlib.sha256(raw[off:off+size]).hexdigest()=='5da0615530ac407070255f4e395ac03a9faa7d2713adc9f04cdf060b9fe4469a'
 syms=elf.get_section_by_name('.symtab');pvt=syms.get_symbol_by_name('_ZTVN4Core8Portable12NumericParamE')[0]['st_value']+8;cases=[]
 for count,partner,slave,guard,selected,dirty,observers in itertools.product([0,1,3],[0,2,4],[0,1],[0,1],[0,1],[0,1],[0,2]):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0x8000,0x600000)
  for segment in elf.iter_segments():
   if segment['p_type']=='PT_LOAD':u.mem_write(segment['p_vaddr'],segment.data())
  u.mem_map(0x1000000,0x20000);obj=0x1000000;vec=obj+0x1000;sp=obj+0x18000;stop=obj+0x1f000
  ptr=lambda i:obj+0x2000+i*0x400 if i else 0
  par=lambda i:obj+0x6000+i*0x100
  def word(a,v):u.mem_write(a,struct.pack('<I',v))
  def read(a):return struct.unpack('<I',u.mem_read(a,4))[0]
  word(obj+0x120,vec);word(obj+0x124,count);word(obj+0x310,ptr(3));word(obj+0x370,obj+0x9000);word(obj+0x374,observers)
  u.mem_write(obj+0x11a,bytes([selected]));u.mem_write(obj+0x36a,bytes([dirty]));u.mem_write(obj+0x4c8,bytes([guard]));u.mem_write(ptr(1)+0x8d,bytes([slave]));word(ptr(1)+0x88,ptr(partner))
  ids={}
  for i in range(1,4):word(vec+4*(i-1),ptr(i));word(ptr(i)+0xfc,par(i));word(par(i),pvt);ids[par(i)]=i
  for i in range(observers):
   o=obj+0xa000+i*0x100;word(obj+0x9000+4*i,o);word(o,obj+0xc000);word(obj+0xc000,stop-0x800)
  setter=read(pvt+0x58);calls=[];casts=[]
  def code(u,a,n,d):
   r0=u.reg_read(UC_ARM_REG_R0)
   if a==0x116a38:calls.append(['debug'])
   elif a==0xacf4:
    casts.append([u.reg_read(r) for r in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]])
    u.reg_write(UC_ARM_REG_R0,ptr(partner) if partner in [1,2,3] else 0)
   elif a==setter:calls.append(['set',ids[r0],u.reg_read(UC_ARM_REG_R1),u.reg_read(UC_ARM_REG_R2)])
   elif a==0x11dc28:calls.append(['changed',ids[r0]])
   elif a==stop-0x800:calls.append(['observer',(r0-obj-0xa000)//0x100])
   else:return
   u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,code)
  for r,v in [(UC_ARM_REG_R0,obj),(UC_ARM_REG_R1,ptr(1)),(UC_ARM_REG_SP,sp),(UC_ARM_REG_LR,stop)]:u.reg_write(r,v)
  u.emu_start(start,stop,count=10000);assert u.reg_read(UC_ARM_REG_PC)==stop
  cases.append({'input':[count,partner,slave,guard,selected,dirty,observers],'calls':calls,'rtti_boundary_calls':casts,'output':{'selected':(read(obj+0x310)-obj-0x2000)//0x400,'cascadeSelected':u.mem_read(obj+0x11a,1)[0],'cascadeDirty':u.mem_read(obj+0x36a,1)[0]}})
 return {'elf_sha256':SHA,'range':{'address':start,'size':size,'section':12,'file_offset':off},'producer':{'sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'unicorn_version':importlib.metadata.version('unicorn'),'oracle':'original app ARM instructions; NumericParam primary-table setter, DebugPrintf, changed, RTTI and unknown observer slot0 are explicit traced boundaries'},'domain':'empty/1/3 channels; no/channel/nonchannel partner; slave/guard combinations; unequal/equal incoming cascade bytes; zero/two observers; required nonnull target/selection parameters; synchronous nonmutating callbacks','cases':cases}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--elf',required=True);p.add_argument('--out',required=True);a=p.parse_args();Path(a.out).write_text(json.dumps(generate(a.elf),indent=2)+'\n')
