import hashlib,json,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_MEM_READ,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_R0
elf=Path('rootfs/CS18_v13840/home/root/surface')
assert hashlib.sha256(elf.read_bytes()).hexdigest()=='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'
with elf.open('rb') as f:
 e=ELFFile(f); sec=e.get_section(12)
 assert sec.name=='.text'
 off=sec['sh_offset']+0x63370-sec['sh_addr']
 f.seek(off); body=f.read(28)
 data=next(s for s in e.iter_sections() if s['sh_addr']<=2527540<s['sh_addr']+s['sh_size'])
 assert data['sh_type']=='SHT_NOBITS'
assert off==0x5b370
assert hashlib.sha256(body).hexdigest()=='63bb9d9badd22be007a545eb1cb630868a1449a11675208fa532533cae580fea'
cases=[]
for value in [0,1,4,0x1000,0x12345678,0x80000000,0xffffffff,0,0x200000]:
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
 for addr,size in [(0x63000,0x1000),(0x269000,0x1000),(0x700000,0x2000),(0x900000,0x1000)]: u.mem_map(addr,size)
 u.mem_write(0x63370,body); u.mem_write(2527540,struct.pack('<I',value))
 u.reg_write(UC_ARM_REG_SP,0x701000);u.reg_write(UC_ARM_REG_LR,0x900000)
 reads=[];writes=[]
 u.hook_add(UC_HOOK_MEM_READ,lambda u,a,addr,size,v,d: reads.append([addr,size,bytes(u.mem_read(addr,size)).hex()]))
 u.hook_add(UC_HOOK_MEM_WRITE,lambda u,a,addr,size,v,d: writes.append([addr,size,v]))
 u.emu_start(0x63370,0x900000,count=20)
 result=u.reg_read(UC_ARM_REG_R0)
 assert result==value
 assert [2527540,4,struct.pack('<I',value).hex()] in reads
 assert not any(w[0]==2527540 for w in writes)
 cases.append(dict(input=value,result=result,reads=reads,writes=writes))
print(json.dumps(dict(elf_sha256=hashlib.sha256(elf.read_bytes()).hexdigest(),offset=off,size=28,section='.text',body_sha256=hashlib.sha256(body).hexdigest(),data_storage='SHT_NOBITS; loader zero initial state tested with zero; other words injected',cases=cases),indent=2))
