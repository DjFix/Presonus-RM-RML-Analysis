"""Offline exact ARM constructor oracle. No reconstructed code imported."""
import hashlib,json,struct,sys,tempfile
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
ELF=Path('rootfs/RML16AI_Rack_13731/home/root/mixer')
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
def run():
 data=ELF.read_bytes();assert hashlib.sha256(data).hexdigest()==SHA
 with ELF.open('rb') as f:
  elf=ELFFile(f);sec=elf.get_section(12);ranges=[]
  for address,size,sha in [(0xad280,72,'2610cc58c6d9c6ff0329f2cdaf424145d35ec56bde1c6b92dfc8f559b85d1596'),(0x8d890,44,'9bd627b390f8f2168d743c86039578eb1db73e74e60a3cbb9a29bdf5aa1aa39b')]:
   offset=sec['sh_offset']+address-sec['sh_addr'];blob=data[offset:offset+size]
   assert hashlib.sha256(blob).hexdigest()==sha
   ranges.append(dict(address=address,size=size,section=12,section_name=sec.name,file_offset=offset,sha256=sha))
  segments=[(s['p_vaddr'],s.data()) for s in elf.iter_segments() if s['p_type']=='PT_LOAD']
 cases=[]
 for groupId,argument,width in [(0,0,2),(7,42,3),(-1,-1,5),(2147483647,-2147483648,0),(-2147483648,2147483647,-1),(12,99,8)]:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x810000)
  for ad,blob in segments:u.mem_write(ad,blob)
  u.mem_write(0x200000,b'\xa5'*0x500)
  writes=[];calls=[]
  def code(u,ad,size,_):
   if ad==0x8d890:calls.append({'target':ad,'r0':u.reg_read(UC_ARM_REG_R0),'r1':u.reg_read(UC_ARM_REG_R1),'r2':u.reg_read(UC_ARM_REG_R2)})
  def write(u,access,ad,size,value,_):
   if 0x200000<=ad<0x200500:writes.append({'offset':ad-0x200000,'size':size,'value':value})
  u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
  for reg,v in [(UC_ARM_REG_R0,0x200000),(UC_ARM_REG_R1,groupId),(UC_ARM_REG_R2,argument),(UC_ARM_REG_R3,width),(UC_ARM_REG_SP,0x700000),(UC_ARM_REG_LR,0x600000)]:u.reg_write(reg,v&0xffffffff)
  u.emu_start(0xad280,0x600000,count=1000)
  assert u.reg_read(UC_ARM_REG_SP)==0x700000
  word=lambda off:struct.unpack('<I',u.mem_read(0x200000+off,4))[0]
  signed=lambda v:v if v<0x80000000 else v-0x100000000
  cases.append({'input':[groupId,argument,width],'calls':calls,'writes':writes,'return_this':u.reg_read(UC_ARM_REG_R0),'state_414':word(0x414),'state_418':word(0x418),'dirty':u.mem_read(0x200426,1)[0], 'portable_observation':[signed(word(4)),signed(word(12)),signed(word(0x414)),signed(word(0x418)),u.mem_read(0x200426,1)[0],0]})
 # Existing ranked09 oracle's exact SPI native ranges, reused with explicit
 # bounded three-control state; ioctl is the sole intercepted external boundary.
 for address,size,sha in [(0xad15c,192,'cd5dce178d76e2c96d90fc26ab0c4947e42e26285c72fafbcc285ce13a9dd9a9'),(0xad00c,336,'b302ffc228551baab3bcc4c962c2682f50a705a435c239f167605caf99430079')]:
  offset=sec['sh_offset']+address-sec['sh_addr'];assert hashlib.sha256(data[offset:offset+size]).hexdigest()==sha
  ranges.append(dict(address=address,size=size,section=12,file_offset=offset,sha256=sha))
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x810000)
 for ad,blob in segments:u.mem_write(ad,blob)
 def w(ad,v):u.mem_write(ad,struct.pack('<I',v&0xffffffff))
 w(0x200008,0x210000);w(0x20000c,3);w(0x200414,2);w(0x200418,7);u.mem_write(0x200426,b'\x01')
 for n,v in enumerate([1,0,-1]):w(0x210000+4*n,0x230000+8*n);w(0x230004+8*n,v)
 idle_calls=[]
 def ioctl(u,ad,size,_):
  if ad==0xab80:
   fd=u.reg_read(UC_ARM_REG_R0);request=u.reg_read(UC_ARM_REG_R1);ptr=u.reg_read(UC_ARM_REG_R2)
   words=struct.unpack('<8I',u.mem_read(ptr,32));tx,rx,length=words[0],words[2],words[4]
   idle_calls.append(dict(fd=fd,request=request,tx=list(u.mem_read(tx,length)),length=length))
   u.mem_write(rx,bytes(0xa0+i for i in range(length)));u.reg_write(UC_ARM_REG_R0,0xffffffff);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,ioctl)
 u.reg_write(UC_ARM_REG_R0,0x200000);u.reg_write(UC_ARM_REG_SP,0x700000);u.reg_write(UC_ARM_REG_LR,0x600000)
 u.emu_start(0xad15c,0x600000,count=10000)
 integration={'controls':[1,0,-1],'calls':idle_calls,'portable_observation':[len(idle_calls),int(idle_calls[0]['fd']),int(idle_calls[0]['request']),u.mem_read(0x200426,1)[0],*u.mem_read(0x20041c,2),*u.mem_read(0x200421,2)]}
 return {'integration':integration,'elf_sha256':SHA,'ranges':ranges,'cases':cases,'oracle':'Unicorn original constructor/native ControlGroup C2 and existing ranked09 SPI ranges; injected bounded object/control state and intercepted ioctl with deterministic receive bytes; no Core firmware execution/device calls'}
if __name__=='__main__':
 out=run();Path(sys.argv[1]).write_text(json.dumps(out,indent=2)+'\n');print('native constructor cases',len(out['cases']))
