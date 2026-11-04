"""Fresh range checks and original ARM executions using saved research producer logic."""
import hashlib,json
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_MEM_WRITE,UC_HOOK_CODE
from unicorn.arm_const import *
SOURCE=Path("evidence/recovery/2026-11-03/dependency-graph/frontier-scale01/root-equivalence-review01/frontier_scale01_r10/NATIVE_OBSERVATIONS.json")
def observe():
 rows=json.loads(SOURCE.read_text())["originals"]
 for row in rows:
  path=Path("rootfs/CS18_v13840/home/root/surface" if row["role"]=="client" else "rootfs/RML16AI_Rack_13731/home/root/mixer")
  raw=path.read_bytes(); assert hashlib.sha256(raw).hexdigest()==row["elf"]
  with path.open("rb") as f:
   elf=ELFFile(f);sec=elf.get_section(int(row["section_json"]));off=row["address"]-sec["sh_addr"]+sec["sh_offset"]
  assert off==row["file_offset"]
  body=raw[off:off+row["size"]];assert hashlib.sha256(body).hexdigest()==row["range_sha256"]
  for case in row["observations"]:
   u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(row["address"]&~4095,4096);u.mem_write(row["address"],body)
   for base,size in [(0x1000000,4096),(0x2000000,8192),(0x3000000,4096)]:u.mem_map(base,size)
   u.mem_write(0x1000000+472,case["input_word"].to_bytes(4,"little"));before=bytes(u.mem_read(0x1000000,4096))
   for reg,value in [(UC_ARM_REG_R0,0x1000000),(UC_ARM_REG_SP,0x2001000),(UC_ARM_REG_LR,0x3000000),(UC_ARM_REG_FP,0x123400)]:u.reg_write(reg,value)
   writes=[];instructions=[]
   u.hook_add(UC_HOOK_MEM_WRITE,lambda u,a,addr,size,val,data:writes.append([addr,size,val]))
   u.hook_add(UC_HOOK_CODE,lambda u,addr,size,data:instructions.append(addr))
   u.emu_start(row["address"],0x3000000,count=6)
   assert u.reg_read(UC_ARM_REG_R0)==case["r0"] and bytes(u.mem_read(0x1000000,4096))==before
   assert u.reg_read(UC_ARM_REG_SP)==0x2001000 and u.reg_read(UC_ARM_REG_FP)==0x123400
   assert len(instructions)==5 and len(writes)==4
   case["instruction_addresses"]=instructions;case["stack_writes"]=writes;case["external_calls"]=[]
 return {"oracle":"fresh original ELF ARM execution; adapted saved research producer", "originals":rows}
if __name__=="__main__":print(json.dumps(observe(),indent=2))
