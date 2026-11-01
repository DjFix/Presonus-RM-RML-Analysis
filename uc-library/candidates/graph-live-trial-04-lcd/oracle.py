import re,json,hashlib
from pathlib import Path
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn.arm_const import *
rows=[]
for i in range(1,6):
 p=Path(f'temp/recovery-work/graph-live-trial-04/trial04_lcd_{i}-packet/ELF_CONTEXT.md');t=p.read_text();a=int(re.search(r'address `0x([0-9a-f]+)',t)[1],16)
 code=bytes.fromhex(''.join(re.findall(r'^\w{8}  ([0-9a-f]{8}) ',t,re.M)))
 expected=re.search(r'SHA256 `([a-f0-9]+)',t)[1];assert hashlib.sha256(code).hexdigest()==expected
 for marker in (0,1,0x7fffffff,0xffffffff):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
  for base in (0x60000,0x96000,0x100000,0x200000,0x300000):u.mem_map(base,0x1000)
  u.mem_write(a,code);u.mem_write(0x100000,(0x200000).to_bytes(4,'little'))
  for slot in range(0,64,4):u.mem_write(0x200000+slot,(0x300000+slot*4).to_bytes(4,'little'))
  u.reg_write(UC_ARM_REG_SP,0x100ff0);u.reg_write(UC_ARM_REG_LR,0x300f00);u.reg_write(UC_ARM_REG_R0,0x100100);trace=[]
  def hook(u,pc,size,data):
   if pc==0x96274:trace.append(['getBook',u.reg_read(UC_ARM_REG_R0)]);u.reg_write(UC_ARM_REG_R0,0x100000);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
   elif 0x300000<=pc<0x300100:trace.append(['dispatch',(pc-0x300000)//4,u.reg_read(UC_ARM_REG_R0)]);u.reg_write(UC_ARM_REG_R0,marker);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
   elif pc==0x300f00:u.emu_stop()
  u.hook_add(UC_HOOK_CODE,hook);u.emu_start(a,0,count=100)
  rows.append({'packet':i,'marker':marker,'trace':trace,'r0':u.reg_read(UC_ARM_REG_R0),'range_sha256':expected})
Path('uc-library/candidates/graph-live-trial-04-lcd/native-fixtures.json').write_text(json.dumps(rows,indent=2)+'\n')
print(len(rows),'original ARM boundary executions')
