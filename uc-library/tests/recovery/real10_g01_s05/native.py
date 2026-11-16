import hashlib,json,struct,subprocess
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
R=Path(__file__).resolve().parents[4]
EXE=R/'temp/recovery-work/real10_g01_s05/replay'
ELF=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/reconstruction10x10-20261116/prepared-main/snapshot/rootfs/CS18_v13840/home/root/surface')
SHA='304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0';NAME='_ZN8Presonus7Surface23GroupsEditPageComponentD0Ev';ADDRESS=611612;SIZE=252
GROUP=True
DELETING=True

def generate():
 data=ELF.read_bytes();assert hashlib.sha256(data).hexdigest()==SHA
 with ELF.open('rb') as f:
  e=ELFFile(f);symbol=next(s for s in e.get_section_by_name('.symtab').iter_symbols() if s.name==NAME)
  assert (symbol['st_value'],symbol['st_size'])==(ADDRESS,SIZE)
  section=e.get_section(symbol['st_shndx']);offset=section['sh_offset']+ADDRESS-section['sh_addr'];body=data[offset:offset+SIZE]
  ranges=[dict(mangled=NAME,address=ADDRESS,size=SIZE,section=section.name,section_index=symbol['st_shndx'],file_offset=offset,sha256=hashlib.sha256(body).hexdigest())]
 inputs=[(count,children,parameters) for count in [0,1,17] for children in [0,1,2] for parameters in [0,1]]
 payload=''.join('%d %d %d\n'%x for x in inputs)
 provider=subprocess.check_output([str(EXE),'--provider'],input=payload,text=True).splitlines()
 assert len(provider)==len(inputs)
 cases=[]
 for inp,expected in zip(inputs,provider):
  u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.mem_map(0,0x1000000);u.mem_write(ADDRESS,body)
  calls=[];sites=[];writes=[]
  boundaries={0x5d36c:'alias_vector_destructor',0x94e20:'item_vector_destructor',0x11b5e0:'component_destructor',0xad5c:'operator_delete'}
  def code(u,a,n,_):
   if ADDRESS<=a<ADDRESS+SIZE:sites.append(a);return
   if a not in boundaries:raise RuntimeError('unexpected native target '+hex(a))
   arg=u.reg_read(UC_ARM_REG_R0);calls.append([boundaries[a],arg-0x400000])
   u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
  u.hook_add(UC_HOOK_CODE,code)
  u.hook_add(UC_HOOK_MEM_WRITE,lambda u,k,a,n,v,_:writes.append([a-0x400000,n,v]) if 0x400000<=a<0x401000 else None)
  for reg,value in [(UC_ARM_REG_R0,0x400000),(UC_ARM_REG_SP,0x801000),(UC_ARM_REG_LR,0xf00000),(UC_ARM_REG_R4,0x12345678),(UC_ARM_REG_R5,0x87654321)]:u.reg_write(reg,value)
  u.emu_start(ADDRESS,0xf00000,count=200)
  assert u.reg_read(UC_ARM_REG_PC)==0xf00000 and u.reg_read(UC_ARM_REG_SP)==0x801000
  assert u.reg_read(UC_ARM_REG_R0)==0x400000
  assert u.reg_read(UC_ARM_REG_R4)==0x12345678 and u.reg_read(UC_ARM_REG_R5)==0x87654321
  expected_calls=([['item_vector_destructor',0xdc]] if GROUP else [])+[['alias_vector_destructor',0xb4],['component_destructor',0]]+([['operator_delete',0]] if DELETING else [])
  assert calls==expected_calls
  cases.append(dict(stdin='%d %d %d'%inp,stdout=expected))
 return dict(elf_sha256=SHA,ranges=ranges,native_calls=calls,native_receiver_writes=writes,cases=cases,case_count=len(cases),domain='Valid nonthrowing receivers; empty/1/17 vector entries, 0/1/2 owned children, 0/1 CCL-owned numeric parameter; alias/item pointers borrowed; Groups tagged state owns its items with empty secondary state parameter list.',native_boundary='Original app instructions executed in Unicorn; Core vector/component destructor and libc++ delete imports are explicit trace-only boundaries, not executed firmware provider bodies. Provider observations separately execute actual pinned CCL vectors/component/parameter cleanup and allocation release in --provider mode.',provider='Independent Provider/ProviderGroup containers compile actual CCL Vector/Component code; actual delete/delete[] call std::free after watched-pointer logging; callbacks originate from actual child/parameter destruction. No reconstructed destructor called in provider mode.',producer_version=__import__('unicorn').__version__)
if __name__=='__main__':
 import sys
 Path(sys.argv[1]).write_text(json.dumps(generate(),indent=2)+'\n')
