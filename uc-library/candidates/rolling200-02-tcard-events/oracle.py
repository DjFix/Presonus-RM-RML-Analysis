import hashlib,json,struct
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_READ
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
from elftools.elf.elffile import ELFFile
ROOT=Path(__file__).resolve().parents[3]
elf=ROOT/'evidence/recovery/2026-10-28/vm-migration/legacy-uc-recovery/inputs/mixer-13731.elf'
b=elf.read_bytes();assert hashlib.sha256(b).hexdigest()=='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
with elf.open('rb') as f:
 e=ELFFile(f);s=e.get_section(12);offset=s['sh_offset']+0x9e9b0-s['sh_addr'];assert offset==0x969b0
code=b[offset:offset+56];assert hashlib.sha256(code).hexdigest()=='7aa5e573450c4f8e25506b36a83054c63dc170e8359822477796613543062acf'
cases=[]
for schedule in [[0],[1,0],[5,4,2,0],[4294967295,4294967295,1,0],[7]*9]:
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
 for addr,size in [(0x9e000,0x1000),(0x10e000,0x1000),(0x200000,0x2000),(0x300000,0x2000),(0x400000,0x1000)]:u.mem_map(addr,size)
 u.mem_write(0x9e9b0,code);u.mem_write(0x2000a4,struct.pack('<I',schedule[0]));u.reg_write(UC_ARM_REG_R0,0x200000);u.reg_write(UC_ARM_REG_SP,0x301000);u.reg_write(UC_ARM_REG_LR,0x400000)
 reads=[];sleeps=[];done=[False];bounded=[False]
 def read(uc,access,addr,size,value,data):
  if addr==0x2000a4:reads.append(struct.unpack('<I',uc.mem_read(addr,4))[0])
 def hook(uc,addr,size,data):
  if addr==0x400000:done[0]=True;uc.emu_stop()
  if addr==0x10e948:
   sleeps.append(uc.reg_read(UC_ARM_REG_R0));n=len(sleeps)
   if n==8 and schedule[-1]!=0:bounded[0]=True;uc.emu_stop();return
   uc.mem_write(0x2000a4,struct.pack('<I',schedule[min(n,len(schedule)-1)]));uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_READ,read);u.emu_start(0x9e9b0,0x400004,count=1000)
 assert done[0] or bounded[0]
 cases.append(dict(schedule=schedule,reads=reads,sleeps=sleeps,returned=done[0],bounded=bounded[0]))
out=ROOT/'evidence/recovery/2026-11-05/rolling200-02/tcard-events/native.json'
out.write_text(json.dumps(dict(elf=str(elf.relative_to(ROOT)),elf_sha256=hashlib.sha256(b).hexdigest(),address=649648,size=56,section=12,offset=offset,range_sha256=hashlib.sha256(code).hexdigest(),oracle='Unicorn ARM original instructions; sleep boundary intercepted only',cases=cases),indent=2)+'\n')
print('native original range verified and executed: 5 schedules')
