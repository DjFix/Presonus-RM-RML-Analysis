import json,hashlib,struct,random
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import *
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[4];NAME='_ZNK8Presonus5Panel24StormFrontPanelComponent17getTablesForGroupEiRPKiS4_Ri';SHA='9320c53b9bccf379a823ce4b24822b29eae4f5558f9221925c935adfc7a16f07';ADDRESS=467244;SIZE=160

def generate():
 bindings=json.loads((R/'temp/recovery-work/rolling10x10-20261114/READ_INPUTS-prepared06-rolling10_surface_input.json').read_text());path=Path(bindings['rootfs/RML16AI_Rack_13731/home/root/mixer']['frozen_read_path']);data=path.read_bytes();assert hashlib.sha256(data).hexdigest()==SHA
 with path.open('rb') as f:
  e=ELFFile(f);symbols=list(e.get_section_by_name('.symtab').iter_symbols());s=next(s for s in symbols if s.name==NAME);sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+ADDRESS-sec['sh_addr'];body=data[off:off+SIZE];assert s['st_value']==ADDRESS and s['st_size']==SIZE and hashlib.sha256(body).hexdigest()=='c2f9029d549e80fa8434bb5827c3df0138cd3af860a9daebd5a48c0ec6b9625d'
  segments=[(x['p_vaddr'],x.data()) for x in e.iter_segments() if x['p_type']=='PT_LOAD'];sections=[(x['sh_addr'],x['sh_offset'],x['sh_size']) for x in e.iter_sections()]
 cases=[];tables={}
 for group in list(range(-8,9))+[-2147483648,2147483647]+[random.Random(i).randrange(-2147483648,2147483648) for i in range(32)]:
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x1000000)
  for a,b in segments:u.mem_write(a,b)
  put=lambda a,v:u.mem_write(a,struct.pack('<I',v&0xffffffff));get=lambda a:struct.unpack('<I',u.mem_read(a,4))[0]
  put(0x600000,0x700000);put(0x600004,0x700004);put(0x600008,77);put(0x8ff000,0x600008);sites=[];writes=[]
  def hook(u,a,n,_):
   if a==0xf00000:u.emu_stop();return
   assert ADDRESS<=a<ADDRESS+SIZE,hex(a);sites.append(a)
  u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,lambda u,ac,a,n,v,_:writes.append([a,n,v]))
  for reg,v in [(UC_ARM_REG_R0,0x400000),(UC_ARM_REG_R1,group&0xffffffff),(UC_ARM_REG_R2,0x600000),(UC_ARM_REG_R3,0x600004),(UC_ARM_REG_SP,0x8ff000),(UC_ARM_REG_LR,0xf00000)]:u.reg_write(reg,v)
  u.emu_start(ADDRESS,0xf00000,count=60);a,b,count=get(0x600000),get(0x600004),get(0x600008)
  case=dict(group=group,count=count,pointers=[a,b],writes=[w for w in writes if not 0x8fe000<=w[0]<0x8ff000],sites=sites)
  if group in [0,1,2]:
   case['values']=[list(struct.unpack('<'+'i'*count,u.mem_read(p,count*4))) for p in [a,b]]
   for p in [a,b]:
    symbol=next(s for s in symbols if s['st_value']==p and s['st_size']>0);ad,fo,sz=next(x for x in sections if x[0]<=p<x[0]+x[2]);payload=data[fo+p-ad:fo+p-ad+symbol['st_size']];tables[str(p)]=dict(mangled=symbol.name,address=p,size=symbol['st_size'],file_offset=fo+p-ad,sha256=hashlib.sha256(payload).hexdigest(),values=list(struct.unpack('<'+'i'*(len(payload)//4),payload)))
  else:assert [a,b,count]==[0x700000,0x700004,77] and not case['writes']
  cases.append(case)
 return dict(elf_sha256=SHA,mangled=NAME,address=ADDRESS,size=SIZE,section='.text',file_offset=off,range_sha256=hashlib.sha256(body).hexdigest(),cases=cases,tables=tables)
if __name__=='__main__':
 import sys
 Path(sys.argv[1]).write_text(json.dumps(generate(),indent=2)+'\n')
