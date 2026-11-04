"""Execute only exact assigned ARM instructions; intercept Book call, never Core."""
import hashlib,json,sys,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
ELF=Path('rootfs/RML16AI_Rack_13731/home/root/mixer')
SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
START=0x6d81c
SIZE=60
RANGE='b59ae3dc457f5079701b9e704646aa97b731ec4b1ae436357b9ecd43caa372d9'
def observe():
 data=ELF.read_bytes(); assert hashlib.sha256(data).hexdigest()==SHA
 with ELF.open('rb') as f:
  elf=ELFFile(f); sec=elf.get_section(12)
  assert sec.name=='.text' and sec['sh_addr']<=START and START+SIZE<=sec['sh_addr']+sec['sh_size']
  off=sec['sh_offset']+START-sec['sh_addr']
 assert off==0x6581c
 body=data[off:off+SIZE]; assert hashlib.sha256(body).hexdigest()==RANGE
 inputs=[(0,0,0),(1,0x220004,0x230008),(-1,0x220004,0),(-2147483648,0,0x230008),(2147483647,0xffffffff,0xffffffff),(17,0x220004,0x220004)]
 cases=[]
 for value,a,b in inputs:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM); u.mem_map(0x60000,0x40000); u.mem_write(START,body)
  u.mem_map(0x100000,0x1000); u.mem_map(0x200000,0x10000); u.mem_map(0x300000,0x1000)
  this=0x100100; stop=0x300000
  u.mem_write(this,bytes([0xa5])*0x100)
  for r,v in [(UC_ARM_REG_R0,this),(UC_ARM_REG_R1,value&0xffffffff),(UC_ARM_REG_R2,a),(UC_ARM_REG_R3,b),(UC_ARM_REG_SP,0x208000),(UC_ARM_REG_LR,stop)]: u.reg_write(r,v)
  calls=[]; writes=[]
  def code(mu,addr,size,_):
   if addr==0x97bfc:
    calls.append({'target':addr,'this':mu.reg_read(UC_ARM_REG_R0),'value_u32':mu.reg_read(UC_ARM_REG_R1)})
    # Fixture boundary: no base-body execution or base state simulation.
    for r in [UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]: mu.reg_write(r,0xdeadbeef)
    mu.reg_write(UC_ARM_REG_PC,mu.reg_read(UC_ARM_REG_LR))
  def write(mu,access,addr,size,v,_):
   if this<=addr<this+0x100: writes.append([addr-this,size,v])
  u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
  u.emu_start(START,stop,count=100)
  assert u.reg_read(UC_ARM_REG_PC)==stop
  assert calls==[{'target':0x97bfc,'this':this,'value_u32':value&0xffffffff}]
  assert writes==[[152,4,a],[0,4,0x32a220],[156,4,b]]
  final=bytes(u.mem_read(this,0x100))
  touched=set(range(152,160))|set(range(4))
  assert all(v==0xa5 for i,v in enumerate(final) if i not in touched)
  assert u.reg_read(UC_ARM_REG_R0)==this
  cases.append({'input':[value,a,b],'native_calls':calls,'native_writes':writes,'returned_this':True,'untouched_sentinel_verified':True,'portable_expected':[value,struct.unpack_from('<I',final,152)[0],struct.unpack_from('<I',final,156)[0]]})
 return {'version':1,'elf_sha256':SHA,'range_sha256':RANGE,'address':START,'size':SIZE,'section':'.text','file_offset':off,'boundary':'Book(int) intercepted, no body emulated; r0-r3 clobbered','cases':cases}
if __name__=='__main__':
 result=observe()
 if len(sys.argv)==2: Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+'\n')
 else: print(json.dumps(result))
