import hashlib,json,struct
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
ELF=Path('rootfs/CS18_v13840/home/root/surface')
def run(index,value=0):
 p=Path(f'temp/recovery-work/reconstruction-200-01/large-batch01/packets/large01_w09_{index:02d}')
 req=json.loads((p/'request.json').read_text()); target=req['targets'][0]
 assert hashlib.sha256(ELF.read_bytes()).hexdigest()==target['original_elf_sha256']
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x300000)
 with ELF.open('rb') as f:
  e=ELFFile(f)
  for s in e.iter_sections():
   if s['sh_type']!='SHT_NOBITS' and s['sh_flags']&2:u.mem_write(s['sh_addr'],s.data())
 u.mem_map(0x400000,0x40000);obj=0x401000;arg=0x402000
 u.reg_write(UC_ARM_REG_SP,0x430000);u.reg_write(UC_ARM_REG_LR,0x420000)
 u.reg_write(UC_ARM_REG_R0,obj);u.reg_write(UC_ARM_REG_R1,(value or 0)&0xffffffff)
 if index==1:
  u.reg_write(UC_ARM_REG_R1,arg);u.mem_write(arg,struct.pack('<I',0 if value is None else arg+0x100))
  if value is not None:u.mem_write(arg+0x108,struct.pack('<I',(value or 0)&0xffffffff))
 if index==6:u.mem_write(obj+0x94,bytes([value&255]))
 if index in (8,9):u.mem_write(obj+0x9c,struct.pack('<I',(value or 0)&0xffffffff))
 writes=[];calls=[]
 def code(uc,address,size,data):
  if address==0x420000:uc.emu_stop()
  if address==0x11b5e0:
   calls.append(address);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 def write(uc,access,address,size,value,data):
  if obj<=address<obj+0x200:writes.append([address-obj,size,value])
 u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
 u.emu_start(target['address'],0x420004,count=200)
 result=u.reg_read(UC_ARM_REG_R0)
 if index==7:result=bytes(u.mem_read(result,32)).split(b'\0')[0].decode()
 if index in (4,10):result=struct.unpack('<I',u.mem_read(obj+(0xbc if index==4 else 0x9c),4))[0]
 return dict(index=index,input=value,result=result,writes=writes,calls=calls)
def fixtures():
 cases=[]
 for i in range(1,11):
  values=([None,0,1,5,6,10,11,2147483647,-2147483648] if i==1 else [0,1,127,255] if i==6 else [0,1,-1,-2147483648,2147483647] if i in (4,8,9,10) else [0])
  cases += [run(i,v) for v in values]
 return cases
if __name__=='__main__':print(json.dumps(fixtures(),indent=2))
