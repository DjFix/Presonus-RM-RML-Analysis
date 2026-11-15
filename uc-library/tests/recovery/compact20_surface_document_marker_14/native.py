import hashlib,json,struct,subprocess
from pathlib import Path
from unicorn import *
from unicorn.arm_const import *
NAME='_ZNK8Presonus7Surface19MarkerPageComponent12isLocateModeEv'
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
ELF=Path('/home/rs/projects/opencs/ai-line-analysis/rootfs/CS18_v13840/home/root/surface')
def generate(exe):
 data=ELF.read_bytes(); assert hashlib.sha256(data).hexdigest()==SHA
 body=data[0xab074:0xab0c4];assert hashlib.sha256(body).hexdigest()=='b671632e14614316d6f3ab50177d19b4e02023c793efcc23819d8170272a02d2'
 inputs=[(0,0)]+[(1,b) for b in [0,0x80000000,1,0x80000001,0x3f800000,0xbf800000,0x7f800000,0xff800000,0x7fc00000,0xffc00000,0x7f7fffff,0x00800000]]
 payload=''.join(f'{p} {b}\n' for p,b in inputs)
 observed=subprocess.check_output([str(exe),'provider'],input=payload.encode()).decode().splitlines();cases=[]
 for (present,bits),line in zip(inputs,observed):
  found,value=map(int,line.split());assert found==present;assert not present or value==bits
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for a in [0xb3000,0x11f000,0x11e000,0x187000,0x700000,0x800000,0x900000]:u.mem_map(a,4096)
  u.mem_write(0xb3074,body);u.mem_write(0x700100,struct.pack('<I',0x700200));u.mem_write(0x700244,struct.pack('<I',0x11e48c));trace=[];sites=[]
  def hook(uc,a,s,_):
   sites.append(a)
   if a==0x11f24c:
    assert uc.reg_read(UC_ARM_REG_R1)==1007;trace.append('ParamList.byTag');uc.reg_write(UC_ARM_REG_R0,0x700100 if found else 0);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   elif a==0x11e48c:
    assert uc.reg_read(UC_ARM_REG_R0)==0x700100;trace.append('NumericParam.getValue');uc.reg_write(UC_ARM_REG_R0,value);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   elif a==0x1877e0:
    assert uc.reg_read(UC_ARM_REG_R1)==0;trace.append('language_fcmpgt');v=struct.unpack('<f',struct.pack('<I',uc.reg_read(UC_ARM_REG_R0)))[0];uc.reg_write(UC_ARM_REG_R0,int(v>0));uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   else:assert 0xb3074<=a<0xb30c0,hex(a)
  u.hook_add(UC_HOOK_CODE,hook)
  for reg,v in [(UC_ARM_REG_R0,0x700000),(UC_ARM_REG_SP,0x800f00),(UC_ARM_REG_LR,0x900000)]:u.reg_write(reg,v)
  u.emu_start(0xb3074,0x900000,count=100);assert u.reg_read(UC_ARM_REG_PC)==0x900000
  cases.append({'input':[present,bits],'expected':u.reg_read(UC_ARM_REG_R0),'provider_bits':value,'trace':trace,'sites':sites})
 return {'elf_sha256':SHA,'range':{'address':733300,'size':80,'file_offset':700532,'section_index':12,'sha256':hashlib.sha256(body).hexdigest()},'cases':cases,'scope':'Original app instructions only; real pinned CCL provider observations supplied by executable provider mode independent of method. IEEE comparison runtime intercept; excludes Core and helper binary equivalence, signalling NaNs, ABI/layout and original bool declaration.'}
