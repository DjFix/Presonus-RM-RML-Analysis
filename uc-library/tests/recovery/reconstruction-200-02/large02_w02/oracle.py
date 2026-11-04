"""Bound original ARM instructions; external providers are explicit observation stubs."""
import argparse, hashlib, json, struct, subprocess
from pathlib import Path
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
from elftools.elf.elffile import ELFFile
ELF_HASH="9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07"
SELF=0x700000; MIXER=0x702000; STATE=0x704000; PARAM=0x706000; VTABLE=0x708000; ARRAY=0x70a000; DATA=0x70c000; STOP=0x800000
REGS=[UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3]
def u32(n):return struct.pack("<I",n&0xffffffff)
def bits(f):return struct.unpack("<I",struct.pack("<f",f))[0]
def flt(n):return struct.unpack("<f",u32(n))[0]
def observe(elf_path, row, scenario):
 raw=Path(elf_path).read_bytes();assert hashlib.sha256(raw).hexdigest()==ELF_HASH
 for off,length,hashvalue in [(0x4a92c,112,"3d17b1826ef7e0c35bd2e9853e243790a5a1904a91963e10e4279ac66888c7ad"),(0x4aae0,204,"68351853593c84c531f329b35aa0b4bc515f0b4167535aa2e51b2dc391b5180d")]:
  assert hashlib.sha256(raw[off:off+length]).hexdigest()==hashvalue
 assert hashlib.sha256(raw[0x5da9c:0x5da9c+1396]).hexdigest()=="70e0af1cd97f7239888d529c0528f4d179c988e5af69844b850f24780e18e521"
 target=row["target"];start=target["address"];end=start+target["size"]
 assert hashlib.sha256(raw[row["offset"]:row["offset"]+target["size"]]).hexdigest()==row["evidence_sha256"]
 uc=Uc(UC_ARCH_ARM,UC_MODE_ARM);uc.mem_map(0,0x900000)
 with open(elf_path,"rb") as f:
  for s in ELFFile(f).iter_segments():
   if s["p_type"]=="PT_LOAD":uc.mem_write(s["p_vaddr"],s.data())
 def put(a,n):uc.mem_write(a,u32(n))
 def get(a):return struct.unpack("<I",uc.mem_read(a,4))[0]
 # Isolated app object/state and virtual dispatch boundaries; no Core body runs.
 for a in [SELF,MIXER,STATE,PARAM]:put(a,VTABLE)
 for slot in range(0,0x200,4):put(VTABLE+slot,0x810000+slot)
 put(SELF+0x8c,MIXER);put(SELF+0x100,0 if scenario.get("storing_null") else STATE);put(MIXER+0x2dc,STATE)
 put(SELF+0x134,ARRAY);put(SELF+0x138,scenario.get("count",0))
 put(SELF+0x108,scenario.get("mode",0));put(SELF+0x104,STATE)
 uc.mem_write(SELF+0x16b,bytes([scenario.get("blocked",0)]))
 for i in range(4):
  a=PARAM+i*0x100;put(a,VTABLE);put(a+12,a+0x40);put(a+0x44,scenario.get("tag",200)+i);put(ARRAY+i*4,a)
 put(MIXER+0x170,ARRAY+0x100);put(MIXER+0x174,2);put(MIXER+0x184,ARRAY+0x200);put(MIXER+0x188,2)
 for i in range(2):put(ARRAY+0x100+i*4,0x720000+i*0x100);put(ARRAY+0x200+i*4,0x730000+i*0x100)
 uc.mem_write(DATA,bytes([scenario.get("byte",0),1,0,0]))
 args=[SELF,scenario.get("arg1",1),bits(scenario.get("value",1.0)),DATA]
 if "ComponentC" in target["mangled"]:args=[SELF,MIXER,STATE,DATA]
 if "controlChanged" in target["mangled"]:args=[SELF,STATE,scenario.get("command",83),DATA]
 if "faderLocateDirty" in target["mangled"]:args[1]=scenario.get("channel",0)
 for r,v in zip(REGS,args):uc.reg_write(r,v)
 uc.reg_write(UC_ARM_REG_SP,0x7f0000);uc.reg_write(UC_ARM_REG_LR,STOP)
 trace=[];writes=[];calls=0;freed=False;last_tag=0
 def hook(u,address,size,_):
  nonlocal calls,freed,last_tag
  if address==STOP:u.emu_stop();return
  if start<=address<end:return
  # Assigned Panel dependencies execute before FrontPanel consumers.
  lifecycle="FrontPanelComponentC" in target["mangled"] or "FrontPanelComponentD" in target["mangled"]
  if lifecycle and (0x52ae0<=address<0x52bac or 0x5292c<=address<0x5299c):
   if address in [0x52ae0,0x5292c]:trace.append({"target":address,"args":[u.reg_read(r) for r in REGS]})
   return
  # Only the reviewed false-only dependency slice is executed. No full helper claim.
  if 0x65a9c<=address<=0x65abc and u.reg_read(UC_ARM_REG_R1)==0:
   if address==0x65a9c:trace.append({"target":address,"args":[u.reg_read(r) for r in REGS]})
   return
  calls+=1
  if calls>200:raise RuntimeError("call budget")
  a=[u.reg_read(r) for r in REGS]
  trace.append({"target":address,"args":a})
  value=a[0]
  if address==0x119c4c:
   last_tag=a[1]
   value=0 if ((scenario.get("missing8") and a[1]==8) or (scenario.get("missing1") and a[1]==1)) else PARAM+(a[1]%4)*0x100
  elif address in [0x157940,0x1578e0]:value=int(flt(a[0])>flt(a[1])) if address==0x157940 else int(flt(a[0])==flt(a[1]))
  elif address==0x15746c:value=bits(float(a[0]))
  elif address==0x157550:value=bits(flt(a[0])*flt(a[1]))
  elif address==0x810044:
   v=scenario.get("param_value",0.0)
   if scenario.get("active_meter") and last_tag!=scenario["active_meter"]:v=0.0
   if "active_index" in scenario and (a[0]-PARAM)//256!=scenario["active_index"]:v=0.0
   value=bits(v)
  elif address==0x810050:value=42
  elif address==0x8c6c0:value=scenario.get("executing",0)
  elif address==0x121dbc:value=STATE
  elif address==0x11dc28:value=0
  elif address==0x639d0:value=scenario.get("meter",0)
  elif address==0xac10:
   # Explicit allocator model, reached only through the original D0 call.
   assert a[0]==SELF
   u.mem_unmap(SELF,0x1000)
   assert not any(first<=SELF<=last for first,last,perms in u.mem_regions())
   freed=True;value=0
  u.reg_write(UC_ARM_REG_R0,value);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
 def write(u,access,address,size,value,_):
  if SELF<=address<SELF+0x200:writes.append([address-SELF,size,value])
 uc.hook_add(UC_HOOK_CODE,hook);uc.hook_add(UC_HOOK_MEM_WRITE,write)
 uc.emu_start(start,STOP+4,count=10000)
 assert uc.reg_read(UC_ARM_REG_PC)==STOP,"execution did not return"
 return {"r0":uc.reg_read(UC_ARM_REG_R0),"calls":trace,"writes":writes,"allocator_model_object_freed":freed}
def parameter_tables(elf_path):
 raw=Path(elf_path).read_bytes();assert hashlib.sha256(raw).hexdigest()==ELF_HASH
 tables=[]
 with open(elf_path,"rb") as f:
  e=ELFFile(f)
  for address,count,name,expected_hash in [
   (0x32690c,134,"_ZN8Presonus4XMenL19FrontpanelParamListE","a035e27477dab234265ac82551b71975bbb23f349c31bbd1cea314b210bbc0ef"),
   (0x329504,2,"_ZN8Presonus4XMenL23FP_DiagnosticsParamListE","83d97462eacc2cb98d40f992e56c4274ee971afacac8175b864e0ce0ff6ad2f3")]:
   section=next(x for x in e.iter_sections() if x["sh_addr"]<=address<x["sh_addr"]+x["sh_size"])
   offset=section["sh_offset"]+address-section["sh_addr"]
   data=raw[offset:offset+count*84];assert hashlib.sha256(data).hexdigest()==expected_hash
   records=[]
   for i in range(count):
    entry=data[i*84:(i+1)*84]
    records.append({"index":i,"type":struct.unpack_from("<i",entry)[0],"tag":struct.unpack_from("<i",entry,4)[0],"name_hex":entry[8:40].split(b"\0")[0].hex(),"value_bits":list(struct.unpack_from("<5I",entry,40)),"flags":struct.unpack_from("<I",entry,60)[0],"pointer_words":list(struct.unpack_from("<5I",entry,64))})
   tables.append({"mangled":name,"address":address,"size":len(data),"section":section.name,"file_offset":offset,"sha256":expected_hash,"records":records})
 return tables
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--metadata",required=True);ap.add_argument("--elf",required=True);ap.add_argument("--output",required=True);ap.add_argument("--provider-executable",required=True);a=ap.parse_args()
 rows=json.loads(Path(a.metadata).read_text())["packets_read"];cases=[]
 for row in rows:
  scenarios=[{},{"value":0.0},{"param_value":1.0},{"count":3,"tag":200,"param_value":1.0},{"arg1":0},{"executing":1},{"blocked":1},{"command":115,"byte":32},{"command":85,"byte":1},{"arg1":200,"count":3,"tag":200,"param_value":1.0},{"arg1":6,"param_value":1.0},{"count":1,"tag":199,"param_value":1.0},{"count":1,"tag":214,"param_value":1.0},{"count":1,"tag":220,"param_value":1.0},{"mode":2},{"mode":2,"arg1":0},{"param_value":-1.0},{"value":-1.0}]
  if row['packet'].endswith('_05'):scenarios += [{'storing_null':1},{'missing8':1}]
  if row['packet'].endswith('_07'):scenarios += [{'missing1':1}]
  if row['packet'].endswith('_12'):scenarios += [{'count':3,'tag':200,'param_value':1.0,'active_index':1},{'count':3,'tag':200,'param_value':1.0,'active_index':2}]
  if row['packet'].endswith('_13'):scenarios += [{'param_value':1.0,'active_meter':tag} for tag in range(1,7)]
  for scenario in scenarios:
   cases.append({"packet":row["packet"],"scenario":scenario,"observed":observe(a.elf,row,scenario)})
 provider_output=subprocess.check_output([a.provider_executable,"104","1","1","0","0","200","0","0"],text=True).strip()
 assert provider_output.startswith("provider_cleanup ")
 provider_cleanup_count=int(provider_output.split()[1])
 Path(a.output).write_text(json.dumps({"elf_sha256":ELF_HASH,"oracle":"Unicorn original app instruction execution, external stubs only","cases":cases,"parameter_tables":parameter_tables(a.elf),"source_provider_observation":{"core_parameter_cleanup_count":provider_cleanup_count,"scope":"Pinned CCL Component/ParamList only; provider-only host branch invokes no reconstructed methods"}},indent=2)+"\n")
 print(len(cases),"original ARM cases")
if __name__=="__main__":main()
