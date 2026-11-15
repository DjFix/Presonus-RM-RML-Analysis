"""Independent execution of exact original application lookup/count bodies only."""
import hashlib,json,struct,io
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_PC
BASE=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/rolling10x10-20261114')
SNAP=BASE/'prepared-idle-refill-proposed01/snapshot'
ELF_SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07'
ELF=SNAP/'rootfs/RML16AI_Rack_13731/home/root/mixer'
PREFIX='temp/recovery-work/rolling10x10-20261114/selection/next100/'
EVIDENCE={
'wolverine_lookup':PREFIX+'closed-switches01/native/rolling10_next100_wolverine_lookup.json',
'wolverine_counts':PREFIX+'closed-switches01/native/rolling10_next100_wolverine_counts.json',
'beast_lookup':PREFIX+'closed-switches03/native/rolling10_next100_beast_lookup.json',
'beast_counts':PREFIX+'closed-switches03/native/rolling10_next100_beast_counts.json'}
MAPPING=PREFIX+'paraminfo-adapter01/TABLE_MAPPING.json'
BITS=PREFIX+'paraminfo-typed03/TABLE_MAPPING_BITS.json'
def sha(data):return hashlib.sha256(data).hexdigest()
def collect():
 raw=ELF.read_bytes(); assert sha(raw)==ELF_SHA
 elf=ELFFile(io.BytesIO(raw)); symbols=list(elf.get_section_by_name('.symtab').iter_symbols()); secs=[s for s in elf.iter_sections() if s['sh_flags']&2 and s['sh_type']!='SHT_NOBITS']
 def read(addr,n):
  s=next(s for s in secs if s['sh_addr']<=addr and addr+n<=s['sh_addr']+s['sh_size']); off=s['sh_offset']+addr-s['sh_addr']; return raw[off:off+n],off
 mapping=json.loads((SNAP/MAPPING).read_text()); bits=json.loads((SNAP/BITS).read_text()); tables=[]
 strings={}
 for s in mapping['relocated_strings']:
  data,off=read(s['address'],s['size']); assert off==s['file_offset'] and sha(data)==s['sha256'] and data.hex()==s['hex']; strings[s['address']]=data[:-1].decode('ascii')
 for table in bits['tables']:
  addr,size=table['identity'][1:];
  for alias in table['original_symbol_aliases']:
   assert any(sym.name==alias['mangled'] and sym['st_value']==addr and sym['st_size']==size and sym['st_shndx']==alias['section'] for sym in symbols)
  data,off=read(addr,size); assert sha(data)==table['bytes_sha256'] and off==table['file_offset']; records=[]
  for i in range(size//84):
   r=data[i*84:(i+1)*84]; given=table['records'][i]; assert r.hex()==given['raw84_hex'] and sha(r)==given['raw_sha256']; vals=struct.unpack('<ii32s5I6I',r)
   pointers=vals[9:]; assert pointers[2]==0
   records.append({'type':vals[0],'tag':vals[1],'name32':vals[2].hex(),'float_bits':list(vals[3:8]),'flags':vals[8],'strings':[strings[p] if p else None for p in [pointers[0],pointers[1],pointers[3],pointers[4]]],'pointers':list(pointers)})
  tables.append({'address':addr,'size':size,'file_offset':off,'sha256':sha(data),'aliases':table['original_symbol_aliases'],'records':records})
 groups=list(range(-3,25))+[-2147483648,2147483647,-65536,65536,-1]
 observations={}; ranges={}
 for key,path in EVIDENCE.items():
  e=json.loads((SNAP/path).read_text()); target=e['target']; assert any(sym.name==target['mangled'] and sym['st_value']==target['address'] and sym['st_size']==target['size'] and sym['st_shndx']==target['section'] for sym in symbols); body=e['verified_body']; addr=body['address']; size=body['size']; data,off=read(addr,size); assert sha(data)==body['bytes_sha256'] and off==body['file_offset']
  ranges[key]={'target':e['target'],'range':{k:v for k,v in body.items() if k!='instructions'},'evidence':path,'evidence_sha256':sha((SNAP/path).read_bytes())}
  mu=Uc(UC_ARCH_ARM,UC_MODE_ARM); page=addr&~4095; mu.mem_map(page,((addr+size-page+4095)//4096)*4096); mu.mem_write(addr,data)
  mu.mem_map(0x1000000,0x10000); mu.mem_map(0x2000000,4096)
  executed=[]; writes=[]
  def code(uc,pc,n,_):
   assert addr<=pc<addr+size,(key,hex(pc)); executed.append(pc)
  def write(uc,_,a,n,v,ud):
   assert 0x1000000<=a<a+n<=0x1010000; writes.append([a,n,v])
  mu.hook_add(UC_HOOK_CODE,code);mu.hook_add(UC_HOOK_MEM_WRITE,write)
  rows=[]
  for g in groups:
   executed.clear();writes.clear(); mu.reg_write(UC_ARM_REG_SP,0x1008000);mu.reg_write(UC_ARM_REG_LR,0x2000000);mu.reg_write(UC_ARM_REG_R0,0x1001000);mu.reg_write(UC_ARM_REG_R1,g&0xffffffff)
   mu.emu_start(addr,0x2000000,count=200); assert mu.reg_read(UC_ARM_REG_PC)==0x2000000
   result=mu.reg_read(UC_ARM_REG_R0)
   if key.endswith('lookup'): assert result==0 or result in {t['address'] for t in tables}
   rows.append({'group':g,'result':result,'executed':list(executed),'stack_writes':list(writes)})
  observations[key]=rows
 return {'elf_sha256':ELF_SHA,'ranges':ranges,'tables':tables,'strings':strings,'observations':observations,'domain':'33 signed-int cases per original lookup/count; every indexed branch, default, signed extremes and uint32 interpretation. Writes confined to caller stack; no external/Core body executed.'}
if __name__=='__main__':
 import sys
 Path(sys.argv[1]).write_text(json.dumps(collect(),indent=2)+'\n')
