import json,hashlib,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ELF='rootfs/RML16AI_Rack_13731/home/root/mixer'
def observe():
 data=Path(ELF).read_bytes(); assert hashlib.sha256(data).hexdigest()=='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
 out=[]
 for p in sorted(Path('temp/recovery-work/reconstruction-200-01/large-batch01/packets').glob('large01_w08_*')):
  d=json.loads((p/'request.json').read_text()); o=d['originals'][0]['original']; a=o['address']; n=o['size']
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM); u.mem_map(0,0x1000000)
  with open(ELF,'rb') as f:
   e=ELFFile(f)
   for s in e.iter_segments():
    if s['p_type']=='PT_LOAD': u.mem_write(s['p_vaddr'],s.data())
   sec=e.get_section(int(o['section_json'])); off=sec['sh_offset']+a-sec['sh_addr']; raw=data[off:off+n]
  u.mem_map(0x1000000,0x40000); u.mem_write(0x1001000,b'\xa5'*128)
  u.reg_write(UC_ARM_REG_SP,0x1030000); u.reg_write(UC_ARM_REG_LR,0x1000000)
  audio='AudioEngine' in o['mangled']; u.reg_write(UC_ARM_REG_R0,0x1001000 if audio else 0x1003000);u.reg_write(UC_ARM_REG_R1,0x1001000);u.reg_write(UC_ARM_REG_R2,0x1001020)
  writes=[]
  u.hook_add(UC_HOOK_MEM_WRITE,lambda uc,ac,ad,sz,v,ud:writes.append([ad,sz,v]))
  u.emu_start(a,0x1000000,count=100)
  row={'original':o,'file_offset':off,'range_sha256':hashlib.sha256(raw).hexdigest(),'writes':writes,'kind':'audio' if audio else 'network'}
  if audio: row['words']=list(struct.unpack('<14I',u.mem_read(0x1001000,56)))
  else:
   row['port']=struct.unpack('<H',u.mem_read(0x1001000,2))[0]
   vals=[]
   for offset in [4,12]:
    ptr=struct.unpack('<I',u.mem_read(0x1001020+offset,4))[0]; b=bytes(u.mem_read(ptr,100)); vals.append(b.split(b'\0')[0].decode())
   row['strings']=vals
  out.append(row)
 return out
if __name__=='__main__': print(json.dumps(observe(),indent=2))
