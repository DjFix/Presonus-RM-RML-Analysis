#!/usr/bin/env python3
"""Execute original application instructions with explicit nonexecuted provider boundaries."""
import argparse,hashlib,json
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
TASK=Path(__file__).parent.name
SYMBOL="_ZN8Presonus5Mixer12AliasMappingC2EPN4Core8Portable10AliasParamEPNS3_9ParameterEPKc" if TASK.endswith("10") else "_ZN8Presonus5Mixer19ChannelDCAComponent"+{"07":"D1","08":"D2","09":"D0"}[TASK[-2:]]+"Ev"
ADDR={"real10_g05_s07":(0x5d850,92),"real10_g05_s08":(0x5d790,92),"real10_g05_s09":(0x5d7ec,100),"real10_g05_s10":(0x1d29c,56)}
SHA="9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
def produce(elf):
 raw=Path(elf).read_bytes(); assert hashlib.sha256(raw).hexdigest()==SHA
 with open(elf,"rb") as f:
  e=ELFFile(f); sec=e.get_section(12); start,size=ADDR[TASK]; off=sec["sh_offset"]+start-sec["sh_addr"]; body=raw[off:off+size]
  symbols=e.get_section_by_name(".symtab").get_symbol_by_name(SYMBOL); assert symbols and any(x["st_value"]==start and x["st_size"]==size and x["st_shndx"]==12 for x in symbols)
  segments=[(int(x["p_vaddr"]),x.data()) for x in e.iter_segments() if x["p_type"]=="PT_LOAD"]
 cases=[]
 for index in range(3 if not TASK.endswith("10") else 6):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM); u.mem_map(0x8000,0x500000)
  for addr,data in segments: u.mem_write(addr,data)
  u.mem_map(0x800000,0x20000); obj=0x800100; stop=0x810000
  u.mem_write(obj,bytes([0xa5])*512)
  u.reg_write(UC_ARM_REG_R0,obj); u.reg_write(UC_ARM_REG_SP,0x80f000); u.reg_write(UC_ARM_REG_LR,stop)
  alias=0 if index%2==0 else 0x800800; param=0 if index<2 else 0x800900; name=0 if index==0 else 0x800a00
  for reg,value in [(UC_ARM_REG_R1,alias),(UC_ARM_REG_R2,param),(UC_ARM_REG_R3,name)]: u.reg_write(reg,value)
  calls=[]; writes=[]
  boundaries={0x1d230:"ControlMapping",0x5da08:"CoreVector",0x11a53c:"CoreComponent",0xac10:"delete"}
  def code(uc,address,size,_):
   if address==stop: uc.emu_stop(); return
   if address in boundaries:
    args=[uc.reg_read(r) for r in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2)]
    calls.append({"boundary":boundaries[address],"args":args})
    uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
  def write(uc,access,address,size,value,_):
   if obj<=address<obj+512: writes.append([address-obj,size,value])
  u.hook_add(UC_HOOK_CODE,code); u.hook_add(UC_HOOK_MEM_WRITE,write)
  u.emu_start(start,stop,count=1000); assert u.reg_read(UC_ARM_REG_PC)==stop
  cases.append({"index":index,"alias":alias,"parameter":param,"name":name,"calls":calls,"receiver_writes":writes,"return":u.reg_read(UC_ARM_REG_R0)})
 return {"task_id":TASK,"elf_sha256":SHA,"address":start,"size":size,"section":12,"file_offset":off,"range_sha256":hashlib.sha256(body).hexdigest(),"producer":"Unicorn original application ARM instructions; named canonical/Core calls intercepted, not executed natively","cases":cases,"case_count":len(cases),"domain":"valid allocated receiver; normal return; explicit named provider boundaries; no EH, hardware or ABI claim"}
if __name__=="__main__":
 p=argparse.ArgumentParser(); p.add_argument("--elf",required=True); p.add_argument("--out",required=True); a=p.parse_args(); Path(a.out).write_text(json.dumps(produce(a.elf),indent=2)+"\n")
