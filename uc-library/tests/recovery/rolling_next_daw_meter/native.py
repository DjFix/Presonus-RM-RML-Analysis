"""Original ARM method with an explicitly controlled virtual interface boundary.
The provider result is independent input, not a value derived from reconstructed C++.
"""
import hashlib,json,random,struct,sys
from pathlib import Path
from elftools.elf.elffile import ELFFile
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn.arm_const import *
TARGET={'mangled': '_ZNK8Presonus7Surface15DAWMixerHandler20getSelectedMeterModeEv', 'address': 505992, 'size': 56, 'anchor': 'a95452c86a4fdcabdc090fa246296991baf8c878942de854ef8bd600b9aa4d75', 'firmware': 'CS18AI surface 13840', 'role': 'client', 'section': 12, 'original_elf_sha256': '304c6cd1f7b4319c4f82ceaa241ab59736a0a6a8495dc2a980d855ec5aa449a0'}
RANGE_SHA='5c60e8943113d4d9bedbf360744bd6fbdfc3baa4c63805a6f4f125219b29aff5'
NAME=TARGET['mangled'];ELF=Path('/home/rs/projects/opencs/ai-line-analysis/temp/recovery-work/control10x20-after-4fed70d11/packeting/panel-first02-batch02/snapshot/rootfs/CS18_v13840/home/root/surface')
FIRST,LAST=(34, 37)
def generate():
 data=ELF.read_bytes();assert hashlib.sha256(data).hexdigest()==TARGET['original_elf_sha256']
 with ELF.open('rb') as stream:
  e=ELFFile(stream);syms=e.get_section_by_name('.symtab').get_symbol_by_name(NAME);assert len(syms)==1;s=syms[0];sec=e.get_section(s['st_shndx']);off=sec['sh_offset']+s['st_value']-sec['sh_addr'];body=data[off:off+s['st_size']]
  assert (s['st_value'],s['st_size'],s['st_shndx'])==(TARGET['address'],TARGET['size'],TARGET['section'])
  assert hashlib.sha256(body).hexdigest()==RANGE_SHA
  identity=dict(mangled=NAME,address=s['st_value'],size=s['st_size'],section=sec.name,section_index=s['st_shndx'],file_offset=off,sha256=RANGE_SHA)
 u=Uc(UC_ARCH_ARM,UC_MODE_ARM);base=TARGET['address']&~4095;u.mem_map(base,4096);u.mem_write(TARGET['address'],body)
 for a in [0x400000,0x500000,0x600000,0x800000,0x900000,0xe00000]:u.mem_map(a,4096)
 def put(a,v):u.mem_write(a,struct.pack('<I',v&0xffffffff))
 put(0x500000,0x600000);put(0x600004,0xe00000)
 trace=[];sites=set();answer=0
 def hook(uc,a,size,_):
  if TARGET['address']<=a<TARGET['address']+TARGET['size']:sites.add(a);return
  assert a==0xe00000,hex(a)
  assert uc.reg_read(UC_ARM_REG_R0)==0x500000
  first,last=uc.reg_read(UC_ARM_REG_R1),uc.reg_read(UC_ARM_REG_R2);assert (first,last)==(FIRST,LAST)
  trace.append([first,last]);uc.reg_write(UC_ARM_REG_R0,answer&0xffffffff);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 def write(uc,access,a,size,v,_):assert 0x800000<=a and a+size<=0x801000
 u.hook_add(UC_HOOK_CODE,hook);u.hook_add(UC_HOOK_MEM_WRITE,write)
 values=list(range(-40,70))+[-2147483648,2147483647,-65536,65536];rng=random.Random(20261113);values += [rng.randint(-2147483648,2147483647) for _ in range(256)]
 cases=[]
 for present,answer in [(0,0)]+[(1,x) for x in values]:
  trace.clear();put(0x400008,0x500000 if present else 0)
  for reg,val in [(UC_ARM_REG_R0,0x400000),(UC_ARM_REG_SP,0x800f00),(UC_ARM_REG_LR,0x900000)]:u.reg_write(reg,val)
  u.emu_start(TARGET['address'],0x900000,count=100);assert u.reg_read(UC_ARM_REG_PC)==0x900000
  result=u.reg_read(UC_ARM_REG_R0);result=result if result<0x80000000 else result-0x100000000
  assert len(trace)==present
  cases.append({'input':[present,answer],'expected':result,'trace':list(trace)})
 return {'elf_sha256':TARGET['original_elf_sha256'],'ranges':[identity],'cases':cases,'native_sites':sorted(sites),'scope':'Complete original app method; getRadioValue virtual slot is a controlled boundary with arguments/call count verified. Stack-only writes. Real Mapping/CCL provider exercised separately; original declarations/layout/ABI unresolved.'}
if __name__=='__main__':
 result=generate();Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+'\n');print(len(result['cases']),'original ARM cases')
