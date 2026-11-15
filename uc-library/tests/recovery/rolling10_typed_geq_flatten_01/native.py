import json,hashlib,struct
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import *
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[4];SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07';NAME='_ZN8Presonus5Mixer12GEQComponent7flattenEv';ADDRESS=248460;SIZE=72

def generate(inventory=None):
 if inventory is None:inventory=json.loads((Path(__file__).parent/'fixtures.json').read_text())['provider_inventory']
 binding=json.loads((R/'temp/recovery-work/rolling10x10-20261114/READ_INPUTS-prepared06-rolling10_surface_input.json').read_text());path=Path(binding['rootfs/RML16AI_Rack_13731/home/root/mixer']['frozen_read_path']);data=path.read_bytes();assert hashlib.sha256(data).hexdigest()==SHA
 with path.open('rb') as f:
  e=ELFFile(f);s=next(x for x in e.get_section_by_name('.symtab').iter_symbols() if x.name==NAME);sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+ADDRESS-sec['sh_addr'];body=data[off:off+SIZE];assert s['st_value']==ADDRESS and s['st_size']==SIZE and hashlib.sha256(body).hexdigest()=='4b573525b94659cae9ebc090e7203749f05e8e135b166e4621ef4e01f0f36ac6'
  vt=next(x for x in e.get_section_by_name('.symtab').iter_symbols() if x.name=='_ZTVN4Core8Portable12NumericParamE');sec=e.get_section(vt['st_shndx']);voff=sec['sh_offset']+vt['st_value']-sec['sh_addr'];vbody=data[voff:voff+vt['st_size']];assert hashlib.sha256(vbody).hexdigest()=='e23afb2051e88ceba917eb243b7f67cc942188e5a8a0bcd62f26a5f0f913b8b1'
  reset=struct.unpack_from('<I',vbody,8+0x5c)[0];reset_symbol=next(x.name for x in e.get_section_by_name('.symtab').iter_symbols() if x['st_value']==reset and 'resetValue' in x.name);assert 'NumericParam' in reset_symbol
 cases=[]
 for row in inventory:
  caseid,*presence=row;assert len(presence)==31
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x1000000);u.mem_write(ADDRESS,body);trace=[];sites=[];writes=[]
  put=lambda a,v:u.mem_write(a,struct.pack('<I',v));put(0x51005c,reset)
  for tag in range(31):put(0x500000+tag*16,0x510000)
  def hook(u,a,n,_):
   if a==0xf00000:u.emu_stop();return
   if ADDRESS<=a<ADDRESS+SIZE:sites.append(a);return
   if a==0x119c4c:
    tag=u.reg_read(UC_ARM_REG_R1);assert u.reg_read(UC_ARM_REG_R0)==0x400000 and 0<=tag<31;trace.append(['lookup',tag]);u.reg_write(UC_ARM_REG_R0,0x500000+tag*16 if presence[tag] else 0)
   elif a==reset:
    tag=(u.reg_read(UC_ARM_REG_R0)-0x500000)//16;assert presence[tag];edit=u.reg_read(UC_ARM_REG_R1);trace.append(['reset',tag,edit])
   else:raise RuntimeError(hex(a))
   u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,lambda u,ac,a,n,v,_:writes.append([a,n,v]))
  for reg,v in [(UC_ARM_REG_R0,0x400000),(UC_ARM_REG_SP,0x8ff000),(UC_ARM_REG_LR,0xf00000)]:u.reg_write(reg,v)
  u.emu_start(ADDRESS,0xf00000,count=1000);assert [x[1] for x in trace if x[0]=='lookup']==list(range(31));assert all(0x8fe000<=w[0]<0x8ff000 for w in writes)
  cases.append(dict(case=caseid,trace=trace,sites=sorted(set(sites)),writes=writes))
 return dict(elf_sha256=SHA,mangled=NAME,address=ADDRESS,size=SIZE,file_offset=off,section='.text',range_sha256=hashlib.sha256(body).hexdigest(),numeric_vtable=dict(address=vt['st_value'],size=vt['st_size'],file_offset=voff,sha256=hashlib.sha256(vbody).hexdigest(),reset_symbol=reset_symbol,reset_address=reset),provider_inventory=inventory,cases=cases,boundary='Actual CCL inventory establishes lookup presence. ARM application executes every instruction; lookup/reset are explicit Core boundary models. Actual pinned resetValue(true) effects and notifications replayed separately using native observed reset calls.')
if __name__=='__main__':
 import sys,subprocess
 inventory=[list(map(int,l.split())) for l in subprocess.check_output([sys.argv[1],'--inventory'],text=True).splitlines()]
 Path(sys.argv[2]).write_text(json.dumps(generate(inventory),indent=2)+'\n')
