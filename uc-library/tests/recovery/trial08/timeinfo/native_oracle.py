"""Execute original ARM ranges; capture explicit call boundaries and state writes."""
import json, pathlib, hashlib, struct
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP, UC_ARM_REG_LR, UC_ARM_REG_PC
ROOT=pathlib.Path(__file__).resolve().parents[5]
def main():
 rows=json.loads((ROOT/'uc-library/candidates/graph-live-trial-08-timeinfo/range-verification.json').read_text()); data=(ROOT/'rootfs/CS18_v13840/home/root/surface').read_bytes(); fixtures=[]
 for row in rows:
  assert hashlib.sha256(data).hexdigest()==row['elf_sha256']
  for flag in (0,1):
   u=Uc(UC_ARCH_ARM, UC_MODE_ARM); u.mem_map(0x10000,0x400000); u.mem_write(0x10000,data[:min(len(data),0x400000)])
   start=row['address']; body=data[row['file_offset']:row['file_offset']+row['size']]; u.mem_write(start,body)
   u.mem_map(0x1000000,0x10000); u.mem_map(0x2000000,0x10000)
   state=bytearray(0x400); state[0x134:0x137]=bytes([flag]*3); u.mem_write(0x1000000,bytes(state)); u.mem_write(0x1001000,bytes(0x1000)); u.mem_write(0x1002000,bytes(0x1000))
   for reg,val in ((UC_ARM_REG_R0,0x1000000),(UC_ARM_REG_R1,0x1001000),(UC_ARM_REG_R2,0x1002000),(UC_ARM_REG_SP,0x200f000),(UC_ARM_REG_LR,0x2000000)):
    u.reg_write(reg,val)
   if 'Eb' in row['mangled']: u.reg_write(UC_ARM_REG_R1,flag)
   if '15updateTimeParam' in row['mangled']: u.reg_write(UC_ARM_REG_R1,0)
   if '4init' in row['mangled'] or '23locateTransportRelative' in row['mangled']: u.reg_write(UC_ARM_REG_R1,0)
   traces=[]
   def hook(uc,addr,size,user):
    if addr==0x2000000: uc.emu_stop(); return
    if not start<=addr<start+len(body):
     traces.append({'target':addr,'args':[uc.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]}); uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
   u.hook_add(UC_HOOK_CODE,hook)
   try:
    u.emu_start(start,0,count=10000); outcome='bounded-execution'
   except Exception as e: outcome=str(e)
   fixtures.append({'mangled':row['mangled'],'flag':flag,'state_before':bytes(state).hex(),'state_after':bytes(u.mem_read(0x1000000,0x400)).hex(),'argument_after':bytes(u.mem_read(0x1001000,0x100)).hex(),'output_after':bytes(u.mem_read(0x1002000,0x100)).hex(),'external_boundaries':traces,'outcome':outcome,'limitations':'External calls intercepted without implementation; this is boundary evidence only.'})
 out=ROOT/'uc-library/candidates/graph-live-trial-08-timeinfo/native-boundaries.json'; out.write_text(json.dumps(fixtures,indent=2)+'\n'); print(len(fixtures),'original executions; boundary interception only')
if __name__=='__main__':main()
